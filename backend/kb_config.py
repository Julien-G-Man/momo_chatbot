import re
import os
import logging
import asyncio
import unicodedata
import tiktoken
import hashlib
from functools import lru_cache
from datetime import datetime
from collections import defaultdict, Counter
from dotenv import load_dotenv
from typing import Dict, List, Any, Tuple, Optional
from knowledge_base import *

logger = logging.getLogger(__name__)
load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2025-01-01-preview"

KNOWLEDGE_BASE = f"""
1. BASIC SERVICES\n{BASIC_SERVICES}\n
2. TRANSFERS\n{TRANSFERS}\n
3. MOMOPAY\n{MOMOPAY}\n
4. MOMO APP\n{MOMOAPP}\n
5. BANKTECH\n{BANKTECH}\n
6. MOMO ADVANCE\n{MOMO_ADVANCE}\n
7. ECW TRANSACTIONS DETAILS\n{ECW_TRANSACTIONS_DETAILS}\n
8. MOMO XTRA CASH\n{XTRACASH}\n
9. REMITTANCE\n{REMITTANCE}\n
10. BILL_PAYMENT\n{BILL_PAYMENT}\n
11. SELF REVERSAL\n{SELF_REVERSAL}\n
12. SELF PIN RESET\n{SELF_PIN_RESET}\n
13. MOMO OPEN API\n{OPEN_API}\n
14. RESERVATION\n{RESERVATION}\n
15. ASSURANCE\n{ASSURANCE}\n
16. MAMBOPAY\n{MAMBOPAY}\n
"""

# Globals
STRUCTURED_KB: dict = {}
KB_INIT_TASK: Optional[asyncio.Task] = None
KB_STATUS = {"ready": False, "last_error": None, "keys": []}

CHUNK_METADATA = {}  # Filled at startup

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
    'BILL_PAYMENT': BILL_PAYMENT.strip(),
    'SELF_REVERSAL': SELF_REVERSAL.strip(),
    'SELF_PIN_RESET': SELF_PIN_RESET.strip(),
    'OPEN_API': OPEN_API.strip(),
    'RESERVATION': RESERVATION.strip(),
    'ASSURANCE': ASSURANCE.strip(), 
    'MAMBOPAY': MAMBOPAY.strip(),
    'SUPPORT': SUPPORT.strip(),
}

CURRENT_TIME = datetime.now().strftime("%H:%M:%S")
CURRENT_DATE = datetime.now().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
You are MoMoChat, the official information assistant for MTN MoMo Congo. 
Your goal is to provide complete and accurate details about MoMo products and services.

RULES:
1. Use ONLY the 'Knowledge Base Context' provided below to answer company-specific questions.
2. If the info isn't there, politely say you don't know and suggest calling support: \n{SUPPORT}.
3. STRUCTURE: Always use ❖ for main items, • for sub-items, and ◦ for details.
4. TONE: Be helpful, professional, and reassuring (e.g., "Don't worry, your funds are safe").
5. LANGUAGE: You are multilingual. Respond in the user's language (French, Lingala, or English).
6. When giving an answer about services, especialy before making a list, always start with a short introduction, for example: "Here's an overview of the products and services offered by MTN MoMo:"

In case the user asks:
Today's Date: {CURRENT_DATE}
Current Time: {CURRENT_TIME}

[Knowledge Base Context]
{{context}}
"""

# ---- Config ----

MOMO_DOMAIN_TERMS = {
    "mucodec", "bgfi", "bsca", "forfait", "achat", "credit", "recharger", "transfer"
    "unsub", "desactiver", "code", "pin", "reversement", "reversal", "argent",
    "105", "106", "170", "fcfa", "mambopay", "xtracash", "pret", "momo"
}

STOP_WORDS = {
    # English
    "the","is","are","what","how","to","a","an","and","or","of","for","in","on",
    # French
    "le","la","les","un","une","des","et","ou","de","du","pour", "par","avec","dans",
}

SYNONYMS = {
    "desactiver": ["unsubscribe","disable","deactivate"],
    "unsubscribe": ["desactiver","disable","deactivate"],
    "solde": ["balance","soldes"],
    "pret": ["loan","advance","avance","xtracash"],
    "avance": ["loan","pret","xtracash"],
    "xtra": ["xtracash","xtra cash","loan"],
    "xtracash": ["xtra cash","loan","pret"],
    "recharger": ["topup","recharge","credit"],
    "code": ["pin","code"],
    "momo": ["mobile money","momowallet"],
    "transfer": ["send money","envoi","renvoyer"],
}

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

# Keyword extraction with semantic ranking
def extract_keywords(query: str, top_n: int = 12) -> List[str]:
    q = normalize_text(query)
    tokens = re.findall(r"\b[a-z0-9]{3,}\b", q)
    
    intent_verbs = {"what", "how", "why", "when", "where"}
    tokens = [t for t in tokens if t not in STOP_WORDS or t in intent_verbs]
    
    if not tokens:
        return []
    
    counts = Counter(tokens)
    total = sum(counts.values())
    
    keywords = []
    for token in dict.fromkeys(tokens):
        # 1. Base Score (Length is a good proxy for specificity)
        score = len(token) * 0.2 
        
        # 2. Domain Boost (If they mention a specific bank or service, prioritize it!)
        if token in MOMO_DOMAIN_TERMS:
            score += 10.0 
            
        # 3. Rarity Weight
        rarity_score = 1.0 / (counts[token] / total + 0.1)
        score += rarity_score
        
        keywords.append((token, score))
    
    # Sort by the new weighted score
    keywords = sorted(keywords, key=lambda x: -x[1])[:top_n]
    
    # Process Synonyms and Dedupe
    result = []
    for kw, _ in keywords:
        result.append(kw)
        if kw in SYNONYMS:
            for s in SYNONYMS[kw]:
                result.append(normalize_text(s))
    
    seen = set()
    return [k for k in result if not (k in seen or seen.add(k))]

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

# ---- Caching layer for query results ----
class QueryCache:
    """
    LRU cache for query → KB context mapping.
    Dramatically reduces redundant filtering on repeated queries.
    """
    def __init__(self, max_size: int = 500):
        self.cache = {}
        self.access_order = []
        self.max_size = max_size
    
    def _hash_query(self, query: str) -> str:
        """Create stable hash of normalized query."""
        return hashlib.md5(normalize_text(query).encode()).hexdigest()
    
    def get(self, query: str) -> Optional[str]:
        """Returns cached KB context or None."""
        h = self._hash_query(query)
        if h in self.cache:
            # Move to end (LRU)
            self.access_order.remove(h)
            self.access_order.append(h)
            return self.cache[h]
        return None
    
    def set(self, query: str, context: str):
        """Cache KB context for a query."""
        h = self._hash_query(query)
        
        if h in self.cache:
            self.access_order.remove(h)
        elif len(self.cache) >= self.max_size:
            # Evict oldest
            oldest = self.access_order.pop(0)
            del self.cache[oldest]
        
        self.cache[h] = context
        self.access_order.append(h)
    
    def clear(self):
        self.cache.clear()
        self.access_order.clear()

QUERY_CACHE = QueryCache(max_size=500)

# ---- Fuzzy matching (lightweight semantic-ish ranking) ----
def compute_text_similarity(text1: str, text2: str) -> float:
    """
    Quick similarity metric between two texts (0.0 to 1.0).
    Uses character bigrams
    """
    def get_bigrams(s: str) -> set:
        s = normalize_text(s)
        return {s[i:i+2] for i in range(len(s)-1)}
    
    bigrams1 = get_bigrams(text1)
    bigrams2 = get_bigrams(text2)
    
    if not bigrams1 or not bigrams2:
        return 0.0
    
    intersection = len(bigrams1 & bigrams2)
    union = len(bigrams1 | bigrams2)
    
    return intersection / union  # Jaccard similarity

# ---- Pre-compute chunk metadata at startup ----
def preprocess_chunks(kb_chunks: Dict[str, str]) -> Dict[str, dict]:
    """
    Pre-compute metadata for all chunks (done once at startup).
    Includes: normalized text, token count, keywords, length.
    """
    metadata = {}
    for key, text in kb_chunks.items():
        norm_text = normalize_text(text)
        _, _, token_count = count_number_of_tokens(text)
        
        # Extract top keywords from chunk itself
        tokens = re.findall(r"\b[a-z0-9]{3,}\b", norm_text)
        chunk_keywords = set(t for t in tokens if t not in STOP_WORDS)
        
        metadata[key] = {
            "text": text,
            "norm_text": norm_text,
            "token_count": token_count,
            "keywords": chunk_keywords,
            "length": len(text),
        }
    return metadata

# Tuning
MAX_KB_TOKENS = 2000
MAX_CHUNKS = 5
MIN_TOKEN_KEEP = 150  

# ---- Main filter with caching + pre-computation ----
def get_keyword_filtered_context(
    user_query: str,
    kb_chunks: Dict[str, str],
    inverted_index: Dict[str, List[str]],
    max_chunks: int = 5,           
    max_kb_tokens: int = 3000,
    use_cache: bool = True
) -> str:
    """
    Finds relevant KB chunks. Optimized to prevent truncation by 
    treating chunks as atomic units.
    """
    if not user_query.strip():
        return ""
    
    # 1. --- CACHE CHECK ---
    if use_cache:
        cached = QUERY_CACHE.get(user_query)
        if cached is not None:
            logger.debug("✓ Cache hit")
            return cached
    
    # 2. --- KEYWORD EXTRACTION ---
    keywords = extract_keywords(user_query)
    if not keywords:
        return ""
    
    # 3. --- SCORING ---
    score = defaultdict(float)
    for kw in keywords:
        # Exact matches get high priority
        if kw in inverted_index:
            for k in inverted_index[kw]:
                score[k] += 3.0
        # Fuzzy/Keyword metadata matches
        else:
            for k, meta in CHUNK_METADATA.items():
                if kw in meta["keywords"]:
                    score[k] += 1.0
    
    if not score:
        return ""
    
    # Boost by semantic similarity
    norm_query = normalize_text(user_query)
    for k in score:
        sim = compute_text_similarity(norm_query, CHUNK_METADATA[k]["norm_text"])
        score[k] += 1.5 * sim 

    # 4. --- RANKING ---
    ranked = sorted(score.items(), key=lambda x: -x[1])
    
    # 5. --- SELECTION  ---
    selected_parts = []
    tokens_used = 0
    
    for key, sc in ranked:
        if len(selected_parts) >= max_chunks:
            break
            
        meta = CHUNK_METADATA[key]
        tcount = meta["token_count"]
        
        # We take the WHOLE chunk if it fits in the budget.
        if tokens_used + tcount <= max_kb_tokens:
            selected_parts.append(f"[{key}]\n{meta['text'].strip()}")
            tokens_used += tcount
            logger.debug(f"✓ Included {key} ({tcount} tokens)")
        elif not selected_parts:
            # SAFETY: If even the first chunk is too big, take it anyway.
            selected_parts.append(f"[{key}]\n{meta['text'].strip()}")
            tokens_used += tcount
            break

    # 6. --- FINAL FORMAT ---
    result = "\n\n".join(selected_parts)
    
    if use_cache:
        QUERY_CACHE.set(user_query, result)
        
    print(f"Final Context: {tokens_used} tokens from {len(selected_parts)} chunks.")
    return result