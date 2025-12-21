import os
import re
import json
import time
import httpx
import asyncio
import logging
import tiktoken
import random
import models, schemas
from schemas import ChatRequest, ChatResponse
from typing import Optional, Union, List, Dict, Any
from datetime import datetime
from sqlalchemy.exc import IntegrityError
from dotenv import load_dotenv
from uuid import uuid4
from fastapi import FastAPI, APIRouter, HTTPException, status, Depends
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from database import engine, Base, get_db
from kb_config import INITIAL_KB_CHUNKS, SYSTEM_PROMPT, CHUNK_METADATA, preprocess_chunks, get_keyword_filtered_context, build_inverted_index
# from auth import get_password_hash, verify_password, create_access_token
# from auth import get_current_user, get_optional_user
# from auth_router import auth_router

logger = logging.getLogger(__name__)

app = FastAPI(title="MMC Chatbot API")
# app.include_router(auth_router)

load_dotenv()

AZURE_SEMAPHORE = asyncio.Semaphore(50)

AZURE_OPENAI_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_OPENAI_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_DEPLOYMENT_NAME = os.getenv("AZURE_DEPLOYMENT_NAME", "gpt-4o-mini-deployment") 

if not all([AZURE_OPENAI_ENDPOINT, AZURE_OPENAI_API_KEY]):
    raise EnvironmentError("AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY must be set in the environment.")
else:
    print("Azure OpenAI Inititialized.")
    
origins = [
    "https://momochat-cg.vercel.app",
    "https://momochat-cg.netlify.app",
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
   
@app.on_event("startup")
async def startup_event():
    print("======================================")
    print("🔧 Initializing database tables...")
    create_database_tables()
    db = next(get_db())
    ensure_guest_user(db)
    print("✓ Database ready")
    
    print("🔧 Building KB inverted index...")
    global INVERTED_INDEX
    INVERTED_INDEX = build_inverted_index(INITIAL_KB_CHUNKS)
    print(f"✓ Inverted index ready ({len(INVERTED_INDEX)} unique tokens)")
    
    print("🔧 Pre-computing chunk metadata...")
    global CHUNK_METADATA
    chunk_meta = preprocess_chunks(INITIAL_KB_CHUNKS)
    
    import kb_config
    kb_config.CHUNK_METADATA.update(chunk_meta)  
    print(f"✓ Metadata cached for {len(CHUNK_METADATA)} chunks")
    print(f"✓ Chunk keys: {list(kb_config.CHUNK_METADATA.keys())}")
    
    print("✅ All systems ready!")
    print("======================================")

@app.get("/")
async def root():
    return {"message": "Backend API is running"}
   
@app.get("/ping")
def check_health():
    """Simple health check endpoint."""
    return {"status": "ok", "message": "Chatbot API is running!"}

def ensure_guest_user(db: Session, guest_id: int = 1, 
    guest_username: str = "Guest", guest_email: str = "guest@momo.mtn.cg", guest_password="guest-user-access"
):
    """Ensures guest user exists; creates if missing."""
    try:
        user = db.get(models.User, guest_id)
    except Exception:
        user = db.query(models.User).filter_by(id=guest_id).first()

    if user:
        logger.debug(f"Guest user {guest_id} already exists")
        return user

    # create guest user
    user = models.User(
        id = guest_id,
        username = guest_username,
        email = guest_email,
        created_at = datetime.utcnow() if hasattr(models.User, 'created_at') else None,
        hashed_password = guest_password
    )
    try:
        db.add(user)
        db.commit()
        db.refresh(user)
        logger.info(f"✓ Guest user created (ID: {guest_id})")
        return user
    except IntegrityError:
        db.rollback()
        logger.warning(f"IntegrityError creating guest user; attempting to fetch...")
        try:
            user = db.query(models.User).filter_by(id=guest_id).first()
            if user:
                return user
        except Exception:
            pass
        logger.error(f"Failed to ensure guest user {guest_id} exists")
        raise HTTPException(status_code=500, detail="Database initialization failed")
    except Exception as e:
        db.rollback()
        logger.exception(f"Unexpected error ensuring guest user: {e}")
        raise

MODEL_FOR_TOKEN_COUNT = "gpt-4o-mini"

def count_number_of_tokens(text: str, model:str = MODEL_FOR_TOKEN_COUNT) -> tuple[int, int, int]:
    """
    Returns token count and prints basic stats:
      - number of characters
      - number of words
      - number of tokens (per tiktoken for chosen model)
    """
    if text is None:
        text = ""
        
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

    return num_tokens, num_words, num_tokens

def log_kb_chunk_token_usage(kb_chunks: Dict[str, str], model: str = MODEL_FOR_TOKEN_COUNT) -> None:
    """
    Logs token counts per KB chunk for debugging / token budgeting.
    """
    total = 0
    for k, text in kb_chunks.items():
        _, _, tokens = count_number_of_tokens(text, model)
        logger.info("KB chunk '%s' tokens=%d", k, tokens)
        total += tokens
    logger.info("KB TOTAL tokens (all chunks): %d", total)

def log_context_selection(query: str, context: str, is_overview: bool):
    """Logs metadata about the retrieved chunks without flooding the console with raw text."""
    # Split context by your headers [SECTION_NAME]
    sections = [line.strip("[]") for line in context.splitlines() if line.startswith("[") and line.endswith("]")]
    
    char_count = len(context)
    # Rough estimate of tokens (1 token ≈ 4 chars)
    est_tokens = char_count // 4 

    log_msg = (
        f"\n{'='*40}\n"
        f"🔍 CONTEXT LOG | Query: '{query}'\n"
        f"📝 Mode: {'GLOBAL OVERVIEW' if is_overview else 'KEYWORD FILTERED'}\n"
        f"📦 Chunks Included ({len(sections)}): {', '.join(sections)}\n"
        f"📊 Size: ~{est_tokens} tokens ({char_count} chars)\n"
        f"{'='*40}"
    )
    print(log_msg)
    
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
    
def enforce_list_indentation(text: str) -> str:
    """
    Enforces three-level list indentation:
    ❖ Main items (no indent)
      • Sub-items (2-space indent)
        ◦ Second-level sub-items (4-space indent)
    """
    lines = text.splitlines()
    new_lines = []
    
    for line in lines:
        stripped = line.strip()
        
        # preserve mpty lines
        if not stripped:
            new_lines.append("")
            continue
        
        # Main items (❖)
        if stripped.startswith('❖'):
            content = stripped[1:].strip()
            new_lines.append(f"❖ {content}")
            continue
        
        # Second-level sub-items (◦)
        if stripped.startswith('◦'):
            content = stripped[1:].strip()
            new_lines.append(f"        ◦ {content}")
            continue
        
        # First-level sub-items (•)
        if stripped.startswith('•'):
            content = stripped[1:].strip()
            new_lines.append(f"    • {content}")
            continue
        
        # Regular text or other content
        new_lines.append(line)
    
    return '\n'.join(new_lines)


# --- Utility Functions ---
async def call_azure_openai_with_backoff(
    messages_or_message: Union[List[dict], str],
    max_retries: int = 7,
    initial_backoff: float = 1.0,
    max_backoff: float = 45.0,
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
        if not messages or messages[0]["role"] != "system":
            messages.insert(0, {"role": "system", "content": SYSTEM_PROMPT})
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
        "temperature": 0.3,
        "max_tokens": 1200,
        "stream": False
    }
    
    # Tracking varilables
    total_wait_time = 0.0
    start_time = time.perf_counter()
    
    # Use an AsyncClient context manager to ensure proper cleanup
    timeout = httpx.Timeout(timeout_seconds, read=timeout_seconds, connect=10.0)
    last_exc = None

    async with httpx.AsyncClient(timeout=timeout) as client:
        for attempt in range(1, max_retries + 1):
            try:
                # Track start of this specific attempt
                attempt_start = time.perf_counter()
                
                resp = await client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                
                # SUCCESS: Log the total journey time
                total_duration = time.perf_counter() - start_time
                logger.info(
                    "✅ Azure Success | Attempt: %d | Total Duration: %.2fs | (Wait time: %.2fs)",
                    attempt, total_duration, total_wait_time
                )
                
                result = resp.json()
                return result["choices"][0]["message"]["content"].strip()

            except httpx.HTTPStatusError as e:
                status = e.response.status_code
                last_exc = e
                
                # Check for "Wait and Retry" status codes
                if status in (429, 500, 502, 503, 504):
                    # 1. Try to get wait time from Azure's header
                    retry_header = e.response.headers.get("Retry-After")
                    if retry_header and retry_header.isdigit():
                        sleep_for = float(retry_header) + random.uniform(0, 1)
                    else:
                        # 2. Fallback to our own exponential backoff
                        backoff = min(max_backoff, initial_backoff * (2 ** (attempt - 1)))
                        sleep_for = random.uniform(0, backoff)

                    total_wait_time += sleep_for
                    logger.warning(
                        "⚠️ Azure %d (Attempt %d/%d) | Wait: %.2fs | Total Wait: %.2fs",
                        status, attempt, max_retries, sleep_for, total_wait_time
                    )
                    
                    if attempt < max_retries:
                        await asyncio.sleep(sleep_for)
                        continue
                
                # If we get here, it's a non-retryable error (like 401 or 400)
                raise HTTPException(status_code=status, detail=f"Azure error: {e.response.text}")

            except (httpx.RequestError, ValueError) as e:
                last_exc = e
                logger.error("❌ Request Error: %s", str(e))
                if attempt == max_retries:
                    raise HTTPException(status_code=503, detail="Max retries reached.")
                await asyncio.sleep(initial_backoff)

    raise HTTPException(status_code=500, detail="Unexpected error loop.")

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
    class GuestUser:
        id = 1
        username = "Guest"  
        email = "guest@momo.mtn.cg"
        hashed_password="guest-user-access"  
    
    request_id = str(uuid4())[:8]
    print(f"[{request_id}] Starting request for user...{GuestUser.id}")
    

    current_user = GuestUser()
    ensure_guest_user(db, guest_id=current_user.id, guest_username=current_user.username, guest_email=current_user.email, guest_password=current_user.hashed_password)
    
    logger.info("Chat request from public user (ID: %s, Username: %s)",
                current_user.id, current_user.username)

    user_message = getattr(request, "message", None)
    if not user_message or not isinstance(user_message, str):
        raise HTTPException(
            status_code=400,
            detail="`message` must be a non-empty string in the request body."
        )
    
    # These cover the common ways users ask for the overview quick action
    OVERVIEW_INTENTS = [
        " Donne-moi un aperçu général des produits et services offerts par MTN MoMo. ",
        "apercu general", "tous les services", "overview of services", 
        "liste des produits", "que propose momo", "what does momo offer",
        "services offerts", "all services", "tout"
    ]
    
    compare_msg = user_message.lower().strip()
    compare_msg = compare_msg.replace("é", "e").replace("è", "e").replace("ç", "c")
    
    is_overview_requested = any(intent in compare_msg for intent in OVERVIEW_INTENTS)
    
    try:
        if is_overview_requested:
            all_chunks = []
            for key, content in INITIAL_KB_CHUNKS.items():
                all_chunks.append(f"[{key}\n{content}]")
                
            relevant_context = "\n\n".join(all_chunks)   
            logger.info("General Overview Triggered: Providing full KB context.") 
        else:
            relevant_context = get_keyword_filtered_context(
                user_message,
                INITIAL_KB_CHUNKS,
                INVERTED_INDEX,
                max_chunks=5,
                max_kb_tokens=3000
            )
    except Exception as e:
        logger.exception("Error retrieving KB context: %s", e)
        relevant_context = ""

    log_context_selection(user_message, relevant_context, is_overview_requested)
    
    include_kb = False
    if relevant_context.strip() and not (
        relevant_context.lower().startswith("no specific") or
        relevant_context.lower().startswith("error:") or
        "could not" in relevant_context.lower()
    ):
        include_kb = True

    personalized_system_prompt = (
        SYSTEM_PROMPT
        + f"""\nThe current user's username is {current_user.username}.
        Guest is not a name, it's the status of the user. 
        Occasionally respond using this name if appropriate."""
    )
    
    if is_overview_requested:
        system_message_content = (
            f"""{personalized_system_prompt}\n\n
            USER REQUEST: General Overview.\n
            INSTRUCTION: Provide a concise summary of all services. 
            Be comprehensive but keep descriptions to 2-3 lines per service.
            Do not list every fee, just the main utility of each category.\n\n
            Knowledge Base Data:\n{relevant_context}
            """
        )        
    else:    
        system_message_content = (
            f"{personalized_system_prompt}\n\nKnowledge Base Data:\n{relevant_context}"
            if include_kb else personalized_system_prompt
        )

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

    messages = [{"role": "system", "content": system_message_content}]
    messages.extend(conversation_messages)
    messages.append({"role": "user", "content": user_message})

    async with AZURE_SEMAPHORE:
        try:
            ai_response = await call_azure_openai_with_backoff(messages)
            ai_response = strip_markdown(ai_response)
            ai_response = enforce_list_indentation(ai_response)
            print(f"\nBot Response: {ai_response}")

            combined_input_for_count = " ".join(
                [system_message_content, " ".join(history_plain_text_parts), user_message]
            )

            log_kb_chunk_token_usage(INITIAL_KB_CHUNKS)

            input_chars, input_words, input_tokens = count_number_of_tokens(combined_input_for_count)
            output_chars, output_words, output_tokens = count_number_of_tokens(ai_response)

            hist_chars, hist_words, hist_tokens = count_number_of_tokens(" ".join(history_plain_text_parts))

            print("\n====================================== ")
            print("Token counts summary:")
            print(f"  INPUT  -> Characters: {input_chars} | Words: {input_words} | Tokens ({MODEL_FOR_TOKEN_COUNT}): {input_tokens}")
            print(f"  OUTPUT -> Characters: {output_chars} | Words: {output_words} | Tokens ({MODEL_FOR_TOKEN_COUNT}): {output_tokens}")
            print(f"  HISTORY-> Characters: {hist_chars} | Words: {hist_words} | Tokens ({MODEL_FOR_TOKEN_COUNT}): {hist_tokens}")
            print("====================================== \n")

            chat_log = models.ChatMessage(
                user_id=current_user.id,
                user_query=user_message,
                ai_response=ai_response,
            )
            db.add(chat_log)
            try:
                db.commit()
                db.refresh(chat_log)
            except IntegrityError as e:
                db.rollback()
                ensure_guest_user(db, guest_id=current_user.id, guest_username=current_user.username)
                db.add(chat_log)
                try:
                    db.commit()
                    db.refresh(chat_log)
                except Exception:
                    db.rollback()
                    logger.exception("Failed to save chat log even after creating guest user.")
             
            print(f"[{request_id}] Finished request.")
             
            return ChatResponse(response=ai_response)

        except HTTPException as e:
            logger.error("Chat failed with HTTP Error: %s", getattr(e, "detail", str(e)))
            raise e
        except Exception as e:
            logger.exception("Unexpected error while processing chat request: %s", e)
            raise HTTPException(
                status_code=500,
                detail="An unexpected error occurred while processing the request."
            ) from e
