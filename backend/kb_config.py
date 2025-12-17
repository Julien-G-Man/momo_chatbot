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
from knowledge_base import (BASIC_SERVICES, TRANSFERS, MOMOPAY, MOMOAPP, BANKTECH, MOMO_ADVANCE, ECW_TRANSACTIONS_DETAILS, 
    XTRACASH, REMITTANCE, BILL_PAYMENT, SELF_REVERSAL, SELF_PIN_RESET, OPEN_API, RESERVATION, ASSURANCE, MAMBOPAY, SUPPORT)

logger = logging.getLogger(__name__)
load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2025-01-01-preview"

KNOWLEDGE_BASE = f"""
1. BASIC SERVICES\n{BASIC_SERVICES}\n
2. TRANSFERS\n{TRANSFERS}\n
3. MOMOPAY\n{MOMOPAY}\n
4. MOMOAPP\n{MOMOAPP}\n
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
You are MoMoChat, a highly efficient and concise company chatbot mainly dedicated to answering customer queries based mainly on the knowledge provided for the MTN Momo Congo Products and Services.
DO NOT use outside knowledge for company specific questions, except for general questions. If the answer to a company-specific question is not contained in this knowledge base, state clearly that you do not have that information.
You can also answer other questions not related to the company in general.
Your tone should be professional and helpful.
You are multilingual, identify the user's language and answer accordingly. You also understand Lingala, that will be of great help to those who only speak Lingala.
Avoid using markdown formatting. Use well-structured hierarchical lists with proper markers and indentation:
  ❖ for main items (no indentation)
    • for sub-items (2-space indentation)
      ◦ for second-level sub-items (4-space indentation)

Here's an example output:
❖ Eligibility Requirements
  • The customer must be active on MTN Mobile Money.
  • Must have been subscribed to MoMo for at least 6 months.
    ◦ Verification requires a valid ID.
    ◦ Account must be in good standing.
  • The customer must be at least 18 years old.

❖ How to Apply
  • Visit an authorized MoMo agent.
    ◦ Bring your ID and phone.
    ◦ Have your PIN ready.
  • Complete the application form.

This example shows proper three-level indentation while providing a clear hierarchy of information.
Here are references for human customer support when a problem is beyond what you can handle or beyond your knowledge base: \n{SUPPORT}
In case you're asked, the current time is {CURRENT_TIME}, and today's date is {CURRENT_DATE}.

Knowledge Base Data explaining the main MoMo services:\n{KNOWLEDGE_BASE}
"""

# ---- Config ----
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

# Keyword extraction with semantic ranking
def extract_keywords(query: str, top_n: int = 12) -> List[str]:
    """
    Extract keywords, prioritizing product/service names and less-common terms.
    """
    q = normalize_text(query)
    tokens = re.findall(r"\b[a-z0-9]{3,}\b", q)
    
    # Filter stop words but preserve intent verbs
    intent_verbs = {"what", "how", "why", "when", "where"}
    tokens = [t for t in tokens if t not in STOP_WORDS or t in intent_verbs]
    
    if not tokens:
        return []
    
    # Rank by: rarity (inverse freq) + length (longer = more specific)
    counts = Counter(tokens)
    total = sum(counts.values())
    
    keywords = []
    for token in dict.fromkeys(tokens):  # preserve order of first occurrence
        rarity_score = 1.0 / (counts[token] / total + 0.1)  # inverse frequency
        length_bonus = len(token) * 0.1  # favor longer tokens
        score = rarity_score + length_bonus
        keywords.append((token, score))
    
    # Sort by score desc
    keywords = sorted(keywords, key=lambda x: -x[1])[:top_n]
    
    result = []
    for kw, _ in keywords:
        result.append(kw)
        if kw in SYNONYMS:
            for s in SYNONYMS[kw]:
                result.append(normalize_text(s))
    
    # Dedupe preserving order
    seen = set()
    out = []
    for k in result:
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
    Uses character bigrams (fast, no ML).
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

# ---- Main filter with caching + pre-computation ----
def get_keyword_filtered_context(
    user_query: str,
    kb_chunks: Dict[str, str],
    inverted_index: Dict[str, List[str]],
    max_chunks: int = MAX_CHUNKS,
    max_kb_tokens: int = MAX_KB_TOKENS,
    use_cache: bool = True
) -> str:
    """
    Find relevant KB chunks with caching + metadata pre-computation.
    ~10-30ms per query with cache hits; ~50-100ms on misses.
    """
    if not user_query.strip():
        return ""
    
    # --- CHECK CACHE ---
    if use_cache:
        cached = QUERY_CACHE.get(user_query)
        if cached is not None:
            logger.debug("✓ Cache hit for query")
            return cached
    
    keywords = extract_keywords(user_query)
    print(f"\n🔍 User query: {user_query}")
    print(f"📌 Keywords: {keywords}")
    
    if not keywords:
        return ""
    
    # --- STAGE 1: Keyword Scoring (exact + fuzzy) ---
    score = defaultdict(float)
    keyword_freq = Counter(keywords)
    
    for kw in keywords:
        rarity_weight = 1.0 / (keyword_freq[kw] + 0.1)
        
        # Exact match in inverted index
        if kw in inverted_index:
            for k in inverted_index[kw]:
                score[k] += 3.0 * rarity_weight
        else:
            # Fuzzy: check only against chunk keywords (not full text)
            for k, meta in CHUNK_METADATA.items():
                if kw in meta["keywords"]:
                    score[k] += 1.5 * rarity_weight
    
    if not score:
        logger.warning("⚠️  No keyword matches")
        return ""
    
    # --- STAGE 2: Similarity Boost (cheap fuzzy ranking) ---
    # Boost chunks that are *semantically similar* to query
    norm_query = normalize_text(user_query)
    for k in score:
        sim = compute_text_similarity(norm_query, CHUNK_METADATA[k]["norm_text"])
        score[k] += 0.5 * sim  # Boost by semantic similarity
    
    # --- STAGE 3: Select & Budget ---
    ranked = sorted(
        score.items(),
        key=lambda x: (-x[1], CHUNK_METADATA[x[0]]["length"])  # tie-break by conciseness
    )
    
    selected: List[Tuple[str, str]] = []
    tokens_used = 0
    
    for key, sc in ranked:
        if len(selected) >= max_chunks:
            break
        
        meta = CHUNK_METADATA[key]
        text = meta["text"]
        tcount = meta["token_count"]
        
        if tokens_used + tcount <= max_kb_tokens:
            selected.append((key, text))
            tokens_used += tcount
            logger.debug(f"  ✓ Selected '{key}' (score={sc:.2f}, tokens={tcount})")
        else:
            # Smart truncation at paragraph boundary
            allowed_tokens = max_kb_tokens - tokens_used
            if allowed_tokens < MIN_TOKEN_KEEP:
                break
            
            paragraphs = text.split("\n\n")
            truncated_parts = []
            para_tokens = 0
            
            for para in paragraphs:
                _, _, para_tcount = count_number_of_tokens(para)
                if para_tokens + para_tcount <= allowed_tokens:
                    truncated_parts.append(para)
                    para_tokens += para_tcount
                else:
                    break
            
            if truncated_parts:
                truncated = "\n\n".join(truncated_parts).strip()
                _, _, final_tokens = count_number_of_tokens(truncated)
                if final_tokens >= MIN_TOKEN_KEEP:
                    selected.append((key, truncated))
                    tokens_used += final_tokens
                    logger.debug(f"  ✓ Truncated '{key}' (tokens={final_tokens})")
            break
    
    # --- FORMAT & CACHE ---
    out_parts = []
    for k, t in selected:
        out_parts.append(f"[{k}]\n{t.strip()}")
    
    result = "\n\n".join(out_parts)
    logger.info(f"📊 KB tokens: {tokens_used}/{max_kb_tokens} | Chunks: {len(selected)}/{max_chunks}")
    
    # Store in cache
    if use_cache:
        QUERY_CACHE.set(user_query, result)
    
    return result