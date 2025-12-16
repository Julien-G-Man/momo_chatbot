import re
import os
import logging
import asyncio
import unicodedata
import tiktoken
from openai import AzureOpenAI
from fastapi import HTTPException
from datetime import datetime
from collections import defaultdict, Counter
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple, Optional
from knowledge_base import (BASIC_SERVICES, TRANSFERS, MOMOPAY, MOMOAPP, BANKTECH, MOMO_ADVANCE, 
    ECW_TRANSACTIONS_DETAILS, XTRACASH, REMITTANCE, SELF_REVERSAL, SELF_PIN_RESET, SUPPORT)

logger = logging.getLogger(__name__)
load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2025-01-01-preview"

KNOWLEDGE_BASE = f"""
MOMO SERVICES:
1. BASIC SERVICES\n{BASIC_SERVICES}\n
2. TRANSFERS\n{TRANSFERS}\n
3. MOMOPAY\n{MOMOPAY}\n
4. MOMOAPP\n{MOMOAPP}\n
5. BANKTECH\n{BANKTECH}\n
6. MOMO ADVANCE\n{MOMO_ADVANCE}\n
7. ECW TRANSACTIONS DETAILS\n{ECW_TRANSACTIONS_DETAILS}\n
8. MOMO XTRA CASH\n{XTRACASH}\n
9. REMITTANCE\n{REMITTANCE}\n
10. SELF REVERSAL\n{SELF_REVERSAL}\n
11. SELF PIN RESET\n{SELF_PIN_RESET}
"""

CURRENT_TIME = datetime.now().strftime("%H:%M:%S")
CURRENT_DATE = datetime.now().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
You are MoMoChat, a highly efficient and concise company chatbot mainly dedicated to answering customer queries based mainly on the knowledge provided for the MTN Momo Congo Products and Services.
DO NOT use outside knowledge for company specific questions, except for general questions. If the answer to a company-specific question is not contained in this knowledge base, state clearly that you do not have that information.
You can also answer other questions not related to the company in general.
Your tone should be professional and helpful.
You are multilingual, identify the user's language and answer accordingly. You also understand Lingala, that will be of great help to those who only speak Lingala.
Avoid using markdown formatting. Use well-indented bullet points (•), or (❖) when making a list of items (never use numbers), hanging indent for each item. Use (❖) for main items and use (•) for sub-items.
Here's an example output:
Eligibility Requirements
 • The customer must be active on MTN Mobile Money.
 • Must have been subscribed to MoMo for at least 6 months.
 • Since MoMo Advance is a credit facility, MTN evaluates the customer’s creditworthiness to determine eligibility.
 • The customer must be at least 18 years old.
 
this example shows proper indentation while providing a list.
Here are references for human customer support when a problem is beyond what you can handle or beyind your knowledge base: \n{SUPPORT}
In case you're asked, the current time is {CURRENT_TIME}, and today's date is {CURRENT_DATE}.

Knowledge Base Data:\n
{KNOWLEDGE_BASE}
"""

# Globals
STRUCTURED_KB: dict = {}
KB_INIT_TASK: Optional[asyncio.Task] = None
KB_STATUS = {"ready": False, "last_error": None, "keys": []}

INITIAL_KB_CHUNKS = {
    'BASIC_SERVICES': BASIC_SERVICES.strip(),
    'TRANSFERS': TRANSFERS.strip(),
    'MOMOPAY': MOMOPAY.strip(),
    'MOMOAPP': MOMOAPP.strip(),
    'BANKTECH': BANKTECH.strip(),
    'MOMO_ADVANCE': MOMO_ADVANCE.strip(),
    'ECW_DETAILS': ECW_TRANSACTIONS_DETAILS.strip(),
    'XTRA_CASH': XTRACASH.strip(),
    'REMITTANCE': REMITTANCE.strip(),
    'SELF_REVERSAL': SELF_REVERSAL.strip(),
    'SELF_PIN_RESET': SELF_PIN_RESET.strip(),
    'SUPPORT': SUPPORT.strip(),
}


# ---- Config ----
STOP_WORDS = {
    # English
    "the","is","are","what","how","to","a","an","and","or","of","for","in","on",
    # French
    "le","la","les","un","une","des","et","ou","de","du","pour", "par","avec","dans",
}

SYNONYMS = {
    # french -> english and close variants
    "desactiver": ["unsubscribe","disable","deactivate","se désabonner","desinscrire"],
    "desinscrire": ["unsubscribe","desactiver"],
    "solde": ["balance","soldes"],
    "pret": ["loan","advance","avance"],
    "avance": ["loan","advance","pret"],
    "recharger": ["topup","recharge"],
    "code": ["pin","code"],
    "loan": ["xtracash", "xtra cash", "pret"],
    
}

# Tuning
MAX_KB_TOKENS = 600
MAX_CHUNKS = 2
MIN_TOKEN_KEEP = 100  

# ---- Helpers ----
def normalize_text(s: str) -> str:
    # lowercase, remove accents, keep alphanum and spaces
    s = s or ""
    s = s.lower()
    s = unicodedata.normalize("NFD", s)
    s = "".join(ch for ch in s if unicodedata.category(ch) != "Mn")  # remove accents
    s = re.sub(r"[^\w\s'-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s

def extract_keywords(query: str, top_n: int = 12) -> List[str]:
    q = normalize_text(query)
    # grabs tokens of 3+ letters (covers French accents after normalization)
    tokens = re.findall(r"\b[a-z0-9]{3,}\b", q)
    tokens = [t for t in tokens if t not in STOP_WORDS]
    if not tokens:
        return []
    counts = Counter(tokens)
    keywords = []
    for token, _ in counts.most_common(top_n):
        keywords.append(token)
        # add synonyms expansion
        if token in SYNONYMS:
            for s in SYNONYMS[token]:
                keywords.append(normalize_text(s))
    # de-dupe preserving order
    seen = set()
    out = []
    for k in keywords:
        if k not in seen:
            seen.add(k)
            out.append(k)
    return out

# ---- Inverted index builder (called once at startup) ----
def build_inverted_index(kb_chunks: Dict[str, str]) -> Dict[str, List[str]]:
    """
    kb_chunks: {key: text}
    returns: dict token -> list of chunk_keys that contain it
    """
    index = defaultdict(list)
    for key, text in kb_chunks.items():
        norm = normalize_text(text)
        tokens = set(re.findall(r"\b[a-z0-9]{3,}\b", norm))
        for t in tokens:
            index[t].append(key)
    return index

MODEL_FOR_TOKEN_COUNT = "gpt-4o-mini"

def count_number_of_tokens(text: str, model:str = MODEL_FOR_TOKEN_COUNT) -> tuple[int, int, int]:
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

    return num_tokens, num_words, num_tokens

# ---- Core filter (fast) ----
def get_keyword_filtered_context(
    user_query: str,
    kb_chunks: Dict[str, str],
    inverted_index: Dict[str, List[str]],
    max_chunks: int = MAX_CHUNKS,
    max_kb_tokens: int = MAX_KB_TOKENS
) -> str:
    """
    Find the most relevant KB chunks using keyword matching and return them
    concatenated up to a token budget. Logs token counts per chunk and total.
    """
    if not user_query:
        return ""

    keywords = extract_keywords(user_query)
    print(f"\nUser message: {user_query}")
    print(f"\nFiltered Key words: {keywords}")
    if not keywords:
        return ""

    # aggregate matched chunk keys with simple scoring
    score = Counter()
    for kw in keywords:
        # exact token in index
        if kw in inverted_index:
            for k in inverted_index[kw]:
                score[k] += 2  # exact token match heavier weight
        # also check substring fallback across chunks 
        else:
            lkw = kw
            for k, text in kb_chunks.items():
                if lkw in normalize_text(text):
                    score[k] += 1

    if not score:
        return ""

    # rank by score desc, tie-breaker by chunk length asc (prefer concise)
    ranked = sorted(score.items(), key=lambda x: (-x[1], len(kb_chunks.get(x[0], ""))))
    selected: List[Tuple[str, str]] = []
    tokens_used = 0
    total_kb_tokens = 0

    for key, sc in ranked:
        if len(selected) >= max_chunks:
            break
        text = kb_chunks.get(key, "")
        if not text:
            continue
        
        _, _, tcount = count_number_of_tokens(text)
        
        if tokens_used + tcount <= max_kb_tokens:
            selected.append((key, text))
            tokens_used += tcount
            total_kb_tokens += tcount
        else:
            # try to truncate text to fit
            allowed = max_kb_tokens - tokens_used
            if allowed <= 0:
                break
            
            # approximate proportional character truncation to hit allowed tokens
            # compute current tokens and length then scale down
            cur_chars = len(text)
            cur_tokens = tcount or 1
            ratio = allowed / cur_tokens
            # ensure we keep at least MIN_TOKEN_KEEP chars
            keep_chars = max(MIN_TOKEN_KEEP, int(cur_chars * ratio))
            truncated = text[:keep_chars].rsplit("\n", 1)[0].strip()

            # recompute token count of truncated chunk and append if positive
            _, _, truncated_tokens = count_number_of_tokens(truncated)
            if truncated_tokens > 0:
                selected.append((key, truncated))
                tokens_used += truncated_tokens
                total_kb_tokens += truncated_tokens
            break

    # format result and log chunk/token insights
    out_parts = []
    for k, t in selected:
        _, _, chunk_tokens = count_number_of_tokens(t)
        logger.info("KB Chunk '%s' tokens=%d", k, chunk_tokens)
        out_parts.append(f"[{k}]\n{t.strip()}")

    logger.info("Total KB tokens included: %d", total_kb_tokens)
    return "\n\n".join(out_parts)
