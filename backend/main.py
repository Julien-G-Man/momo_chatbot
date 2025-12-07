import os
import re
import json
import httpx
import asyncio
import logging
import tiktoken
import random
import models, schemas
from schemas import ChatRequest, ChatResponse
from typing import Optional, Union, List, Dict, Any
from datetime import datetime
from dotenv import load_dotenv
from uuid import uuid4
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base
from knowledge_base import INITIAL_KB_CHUNKS, SYSTEM_PROMPT, get_keyword_filtered_context, build_inverted_index
from dependencies import get_db
# from auth import get_password_hash, verify_password, create_access_token
# from auth import get_current_user, get_optional_user
# from auth_router import auth_router

logger = logging.getLogger(__name__)

app = FastAPI(title="MMC Chatbot API")
# app.include_router(auth_router)

load_dotenv()

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini-deployment") 

if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY]):
    raise EnvironmentError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in the environment.")
else:
    print("Azure OpenAI Inititialized.")
    
origins = [
    "https://momobot-cg.vercel.app",
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

guest_sessions: dict[str, list[dict]] = {}

def create_database_tables():
    """Creates all database tables defined in models.py."""
    Base.metadata.create_all(bind=engine)


INVERTED_INDEX = build_inverted_index(INITIAL_KB_CHUNKS)
    
@app.on_event("startup")
async def startup_event():
    print("Initializing database tables...")
    create_database_tables()
    print("Database tables initialized.")
    print("Inverted index built.")
   
@app.get("/health")
def read_root():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Chatbot API is running!"}


MODEL_FOR_TOKEN_COUNT = "gpt-4o-mini"

def count_number_of_tokens(text: str) -> int:
    """
    Returns token count and prints basic stats:
      - number of characters
      - number of words
      - number of tokens (per tiktoken for chosen model)
    """
    if not isinstance(text, str):
        text = str(text)

    num_chars = len(text)
    num_words = len(text.split())

    try:
        enc = tiktoken.encoding_for_model(MODEL_FOR_TOKEN_COUNT)
    except Exception:
        # fallback to a generic encoding if model-specific one isn't available
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    num_tokens = len(tokens)

    print(f"Characters: {num_chars}")
    print(f"Words: {num_words}")
    print(f"Tokens ({MODEL_FOR_TOKEN_COUNT}): {num_tokens}")
    return num_tokens

def strip_markdown(text: str) -> str:
    """Removes non-essential Markdown characters from a string, preserving list markers and codes."""
    text = text.replace('***', '').replace('**', '')
    text = text.replace('###', '').replace('##', '')
    text = text.replace(' ```', '').replace('``', '')
    text = text.replace('__', '').replace('_', '')
    
    lines = text.splitlines()
    new_lines = []
    for line in lines:
        line = re.sub(r'^\s*[#=>]\s*', '', line).strip()
        new_lines.append(line)
    text = '\n'.join(new_lines)    
    
    return text.strip()
    
def enforce_list_indentation(text, indent_spaces: int) -> str:
    """
    Detects and enforces consistent indentation and list markers for
    bulleted and numbered lists in a block of text.

    Args:
        text (str or list): The text output from the LLM, can be a string or nested list.
        indent_spaces (int): The number of spaces to use for indentation.

    Returns:
        str: The text with enforced indentation and clean markers.
    """
    indent = ' ' * indent_spaces

    # Flatten nested lists if necessary
    def flatten_lines(lines):
        for item in lines:
            if isinstance(item, list):
                yield from flatten_lines(item)
            else:
                yield str(item)

    if isinstance(text, list):
        lines = list(flatten_lines(text))
    else:
        lines = text.splitlines()

    new_lines = []
    list_marker_pattern = re.compile(r'^\s*([*-]|\d+\.)\s*(.*)$')
    numbered_list_counter = 0

    for line in lines:
        stripped = line.strip()
        # Skip lines with command indicators
        if '->' in stripped or '→' in stripped or '=>' in stripped:
            new_lines.append(stripped)
            numbered_list_counter = 0
            continue

        match = list_marker_pattern.match(stripped)
        if match:
            marker = match.group(1).strip()
            content = match.group(2).strip()
            if marker in ['*', '-']:
                new_lines.append(f"{indent}• {content}")
                numbered_list_counter = 0
            else:
                if numbered_list_counter == 0:
                    numbered_list_counter = 1
                new_lines.append(f"{indent}{numbered_list_counter}. {content}")
                numbered_list_counter += 1
        else:
            # Plain line resets numbering
            new_lines.append(stripped)
            numbered_list_counter = 0

    return '\n'.join(new_lines)


# --- Utility Functions ---
async def call_azure_openai_with_backoff(
    messages_or_message: Union[List[dict], str],
    max_retries: int = 5,
    initial_backoff: float = 1.0,
    max_backoff: float = 30.0,
    timeout_seconds: float = 30.0
) -> str:
    """
    Calls the Azure OpenAI chat completions endpoint with exponential backoff + jitter.
    Accepts either:
      - a list of messages (each a dict with 'role' and 'content'), OR
      - a single user message string (will be wrapped into messages with system prompt if needed).
    Returns the assistant message content (string) or raises HTTPException.
    """
    # Normalize input into messages list
    if isinstance(messages_or_message, str):
        # if caller supplies only the user's message string, create a minimal system+user wrapper.
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": messages_or_message}
        ]
    elif isinstance(messages_or_message, list):
        messages = messages_or_message
    else:
        raise ValueError("messages_or_message must be a list or str")

    api_version = "2025-01-01-preview"
    url = (
        f"{AZURE_OPENAI_ENDPOINT.rstrip('/')}/openai/deployments/"
        f"{AZURE_DEPLOYMENT_NAME}/chat/completions?api-version={api_version}"
    )
    headers = {
        "Content-Type": "application/json",
        "api-key": AZURE_OPENAI_API_KEY,
    }
    payload = {
        "messages": messages,
        "temperature": 0.5,
        "max_tokens": 512,
        "stream": False
    }

    # Use an AsyncClient context manager to ensure proper cleanup
    timeout = httpx.Timeout(timeout_seconds, read=timeout_seconds, connect=10.0)
    last_exc = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, max_retries + 1):
            try:
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                result = resp.json()

                # defensive parsing
                choices = result.get("choices")
                if not choices or not isinstance(choices, list):
                    raise ValueError("Response missing 'choices' array")

                first_choice = choices[0]
                # Azure chat shape: choices[0].message.content
                message_obj = first_choice.get("message") or {}
                content = message_obj.get("content")
                if not isinstance(content, str):
                    raise ValueError("Response 'message.content' missing or not a string")

                return content.strip()

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                safe_text = (e.response.text or "")[:1000]  # avoid huge logs
                logger.warning("Azure API HTTP error (attempt %d/%d): %s %s", attempt, max_retries, status, safe_text)

                if status in (401, 403):
                    raise HTTPException(status_code=500, detail="Authorization/configuration error for Azure OpenAI.") from e

                # If not retryable and not transient, fail fast
                if status not in (429, 502, 503, 504):
                    raise HTTPException(status_code=502, detail=f"Azure OpenAI returned HTTP {status}") from e

                last_exc = e

            except (httpx.RequestError, ValueError) as e:
                logger.warning("Request/parse error on attempt %d/%d: %s", attempt, max_retries, str(e))
                last_exc = e

            # if will retry
            if attempt == max_retries:
                logger.error("Exhausted retries calling Azure OpenAI")
                raise HTTPException(status_code=503, detail="Service unavailable after retries.") from last_exc

            # exponential backoff with full jitter
            backoff = min(max_backoff, initial_backoff * (2 ** (attempt - 1)))
            sleep_for = random.uniform(0, backoff)
            logger.info("Retrying in %.2f seconds (attempt %d/%d)...", sleep_for, attempt + 1, max_retries)
            await asyncio.sleep(sleep_for)

    # unreachable
    raise HTTPException(status_code=500, detail="Unexpected failure calling Azure OpenAI")

MAX_HISTORY_TURNS = 2

@app.post("/chat", response_model=ChatResponse)
async def chat_with_bot(
    request: ChatRequest,
    db: Session = Depends(get_db),
):
    """
    Handles an incoming user message and returns a response from Azure OpenAI.
    Injects relevant knowledge base data and maintains a short chat history
    for context. Supports guest users without breaking if the user is unauthenticated.
    """
    
    # 1. Identify the user (guest mode)
    class GuestUser:
        id = 1
        username = "Guest"

    current_user = GuestUser()
    logger.info("Chat request from public user (ID: %s, Username: %s)",
                current_user.id, current_user.username)

    # 2. Validate the incoming message
    user_message = getattr(request, "message", None)
    if not user_message or not isinstance(user_message, str):
        raise HTTPException(
            status_code=400,
            detail="`message` must be a non-empty string in the request body."
        )

    # 3. Retrieve relevant KB context
    try:
        relevant_context = get_keyword_filtered_context(
            user_message,
            INITIAL_KB_CHUNKS,
            INVERTED_INDEX,
            max_chunks=2,
            max_kb_tokens=600
        )
    except Exception as e:
        logger.exception("Error retrieving KB context: %s", e)
        relevant_context = ""

    include_kb = False
    if relevant_context.strip() and not (
        relevant_context.lower().startswith("no specific") or
        relevant_context.lower().startswith("error:") or
        "could not" in relevant_context.lower()
    ):
        include_kb = True

    # 4. Build system prompt
    personalized_system_prompt = (
        SYSTEM_PROMPT
        + f"\nThe current user's username is {current_user.username}. "
          "Guest is not a name, it's the status of the user. "
          "Occasionally respond using this name if appropriate."
    )

    system_message_content = (
        f"{personalized_system_prompt}\n\nKnowledge Base Data:\n{relevant_context}"
        if include_kb else personalized_system_prompt
    )

    # 5. Retrieve recent conversation history
    history_rows = (
        db.query(models.ChatMessage)
        .filter(models.ChatMessage.user_id == current_user.id)
        .order_by(models.ChatMessage.timestamp.desc())
        .limit(MAX_HISTORY_TURNS)
        .all()
    )
    history_rows.reverse()

    conversation_messages = []
    history_plain_text_parts = []

    for row in history_rows:
        user_q = row.user_query or ""
        ai_r = row.ai_response or ""
        conversation_messages.append({"role": "user", "content": user_q})
        conversation_messages.append({"role": "assistant", "content": ai_r})
        history_plain_text_parts.extend([user_q, ai_r])

    # 6. Build final messages payload
    messages = [{"role": "system", "content": system_message_content}]
    messages.extend(conversation_messages)
    messages.append({"role": "user", "content": user_message})

    # 7. Call Azure OpenAI
    try:
        ai_response = await call_azure_openai_with_backoff(messages)
        ai_response = strip_markdown(ai_response)
        ai_response = enforce_list_indentation(ai_response, 2)

        # 8. Token counting 
        combined_input_for_count = " ".join(
            [system_message_content, " ".join(history_plain_text_parts), user_message]
        )
        print("Input token counts:")
        count_number_of_tokens(combined_input_for_count)
        print("\nOutput token counts:")
        count_number_of_tokens(ai_response)

        # 9. Save chat in DB (guest user)
        chat_log = models.ChatMessage(
            user_id=current_user.id,
            user_query=user_message,
            ai_response=ai_response,
        )
        db.add(chat_log)
        try:
            db.commit()
            db.refresh(chat_log)
        except Exception:
            logger.exception("DB commit failed, rolling back.")
            db.rollback()

        return ChatResponse(response=ai_response)

    except HTTPException as e:
        logger.error("Chat failed with HTTP Error: %s",
                     getattr(e, "detail", str(e)))
        raise e
    except Exception as e:
        logger.exception("Unexpected error while processing chat request: %s", e)
        raise HTTPException(
            status_code=500,
            detail="An unexpected error occurred while processing the request."
        ) from e
