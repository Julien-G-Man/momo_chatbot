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

logger = logging.getLogger(__name__)
load_dotenv()

AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY")
AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT")
AZURE_API_VERSION = "2025-01-01-preview"

MOMO_ADVANCE = f"""
What is MoMo Advance?
MoMo Advance is a financial facility that allows MoMo subscribers to carry out transactions from their MoMo wallet even when their balance is zero or insufficient.
It can be used for transactions such as:
 • Buying airtime or bundles
 • Paying bills
 • Merchant payments
 • Money transfers

The service is offered to customers based on individual eligibility, which depends on:
 • Duration of subscription with MTN/MoMo
 • Frequency of recharges
 • Overall usage of the MoMo wallet

MoMo Advance helps customers meet short-term financial needs.
The product charges interest and access fees when the service is made available to a client.

Eligibility Requirements
 • The customer must be active on MTN Mobile Money.
 • Must have been subscribed to MoMo for at least 6 months.
 • Since MoMo Advance is a credit facility, MTN evaluates the customer’s creditworthiness to determine eligibility.
 • The customer must be at least 18 years old.
 
MoMo Advance Features
 • MoMo Advance is linked to your MoMo wallet, so there is no need to open a separate or different account.
 • MoMo Advance is available to you when you request it through a subscription process, or when you do not have sufficient funds to complete a transaction.
 • The MoMo Advance limit varies from one customer to another depending on eligibility criteria.
 • Your MoMo Advance facility remains available whether you use it or not, and you can choose to use it later, when you really need it.
 • Your MoMo Advance can be used either all at once or in several installments, and only the interest on the amount you actually use will be charged.
 • MoMo Advance can be used at any time, whenever you need it most.
 • The amount owed under MoMo Advance is deducted once the wallet is funded again, either in full or in part. 

Fees and Charges
 • Access fee: 4.5%
 • Interest: 0.4% per day (maximum 45% of the advance)
 • Limit offered: Up to 100,000 CFA francs

Transactions covered include:
 • Purchase of voice, SMS, and internet bundles
 • Merchant payments (\\*105# then option 6)
 • Canal+ payments
 • E2C payments 
 
Fees and Interest:
 • Access fee: These fees are applied each time the customer takes a MoMo Advance.
 • Maintenance fee (interest): This is a daily rate applied to any unpaid amount.
 • Proposed limit: (the maximum amount available under MoMo Advance — details follow in the document).

Repayment  Terms:
 • Full repayment exptected within 45 days.
 • Automatic deduction from wallet upon next recharge.
 • Partial repayments are accepted

How to Subscribe to MoMo Advance:
 • Dial *105#
 • Select option 4 (MoMo Advance)
 • Choose option 1 (Subscribe) 
 
Subscription Flow:
 • When funds are low, MoMo Advance is automatically offered.
 • Receives flash message confirming subscription.
 • Receives SMS with approval and credit limit (e.g., 3,000 XAF).

Usage Flow
 • When funds are low, MoMo Advance is automatically offered.
 • User can send money, pay bills, or buy bundles using the advance.
 • Only interest on the used amount is charged.

Menu Option (*105# → 4):
 • Check credit limit
 • View MoMo Advance balance
 • Mini statement
 • Unsubscribe
 
Example Transactions:
 • Advance used: 1,050 XAF (access fee: 17 XAF)
 • Remaining credit: 1,950 XAF
 • Repayment: 1,047 XAF deducted automatically upon wallet recharge
 
Unsubscription:
 • User receives confirmation message upon successful opt-out. 
"""

ECW_TRANSACTIONS_DETAILS = f""" 
HOW TO READ TRANSACTIONS ON ECW (Electronic Customer Wallet):

This data represents a snapshot of a user's Mobile Money (MoMo) account and overdraft facility 
as recorded in the ECW (Electronic Customer Wallet) system. It includes account-level information, 
financial balances, overdraft usage, and explanatory definitions of key fields. The purpose of 
this data is to help the LLM explain clearly to users how MoMo Advance works, how to interpret 
their account details, and how fees, limits, and interest are applied.

Account Summary:
- MSISDN: 242064661818
- Name: Chris Harmonie Liboukou
- Status: Active
- User Role: MMC STAFF PROFILE

Account Configuration:
- Default Account: Yes
- Account ID: FRI:9785870/MM
- Account Type: Money
- Display Name: Active
- Account Profile: MTNCG Normal Account Profile

Financial Overview:
- Balance: 0 FCFA
- Available Balance: 0 FCFA
- Reserved Balance: 0 FCFA
- Overdraft Status: Active
- Overdraft ID: 4076612
- Last Activity Time: 2025-12-11 10:53:48

Overdraft Transaction Details:
- Overdraft ID: 4076612
- External Overdraft ID: 4076612
- Provider Name: momo_advance
- Provider Description: MTNOVERDRAFT
- Application Date: 2025-11-05 10:18:46
- Balance Used: 2,954 FCFA
- Access Fee: 132 FCFA
- Paid Charges: 0 FCFA
- Unpaid Charges (Access Fee + Interest): 132.93 FCFA
- Account FRI: FRI:9785870/MM
- Status: Active
- Application Channel: http-xml
- Credit Limit: 3,000 FCFA
- Chargeable Interest: 0 FCFA
- Charges Limit (Max Interest Cap): 1,329 FCFA

Field Definitions:
1. Balance = Amount of MoMo Advance used by the client.
2. Limit = Maximum amount the client can borrow via MoMo Advance.
3. Access Fee = 4.5% of the borrowed amount, charged when the advance is taken.
4. Chargeable Interest = 0.4% per day on the balance, starting from Day 1 after overdraft.
5. Unpaid Charges = Total fees owed (Access Fee + accrued interest).
6. Charges Limit = Maximum interest the client will ever pay (45% of the borrowed amount).

Geographic Context:
- Country: Republic of the Congo
- MSISDN Prefix: +242 (Central Africa region)

Interpretation Guidelines:
- "Balance" = Total funds in the account.
- "Available Balance" = Immediately usable funds.
- "Reserved Balance" = Held for pending transactions or system locks.
- "Overdraft Status: Active" = User has access to MoMo Advance or credit facility.
- "Last Activity Time" = Timestamp of most recent account interaction.
- "Account Profile" = Indicates user type (e.g., staff, regular customer).
 
"""

XTRA_CASH = f"""
MoMo XtraCash – Loan Service Overview
❖ Description :
MoMo XtraCash is a short-term loan service available to Mobile Money (MoMo) subscribers in Congo, offered in partnership with UBA Congo. 
It allows users to borrow between 1,000 and 100,000 FCFA and repay later via their MoMo account.

❖ Eligibility Criteria:
• Must be an active Mobile Money user.
• Must have been a Mobile Money customer for at least 6 months.
• Must meet KYC requirements and pass eligibility checks.

❖ Loan Types and Terms:
MoMo XtraCash offers three types of short-term loans: 7-day, 28-day, and daily loans. 
Each loan type has distinct access fees, penalties, interest rates, and repayment deadlines:

1. 7-Day Loan
• Access fee: 11% of the loan amount
• Penalty fee (if overdue): 11%
• Interest rate: 0.35% per week
• Repayment deadline: 7 days from disbursement

2. 28-Day Loan
• Access fee: 12.5% of the loan amount
• Penalty fee (if overdue): 11%
• Interest rate: 0.35% per week
• Repayment deadline: 28 days (4 weeks) from disbursement

3. Daily Loan
• Access fee: 12.5% of the loan amount
• Penalty fee (if overdue): 11%
• Interest rate: 0.05%
• Repayment deadline: 1 day (maximum 30 days allowed)

❖ USSD Code Access: 
Dial *105*42# to access XtraCash services. Menu options include:
• Obtain a loan
• Repay a loan
• Check loan balance
• View loan history
• Unsubscribe
• About XtraCash

❖ Loan Example:
• Amount borrowed: 2,500 FCFA
• Fees: 312 FCFA (12.5% access fee), 1 FCFA interest
• Total repayment: 2,813 FCFA
• Duration: 1 day

❖ Repayment Process:
• Dial *105*42# then select option 2.
• Enter the repayment amount when prompted.
• Automatic debit occurs on the due date if not repaid manually.

❖ Loan Balance Inquiry:
• Dial *105*42# then select option 3.

❖ Loan History (Mini Historique):
• Dial *105*42# then select option 4.

"""

KNOWLEDGE_BASE = f"""
MOMO SERVICES:
1. MOMO ADVANCE\n{MOMO_ADVANCE}\n
2. ECW TRANSACTIONS DETAILS\n{ECW_TRANSACTIONS_DETAILS}\n
3. MOMO XTRA CASH\n{XTRA_CASH}
"""
CURRENT_TIME = datetime.now().strftime("%H:%M:%S")
CURRENT_DATE = datetime.now().strftime("%d %B %Y")

SYSTEM_PROMPT = f"""
You are MoMoChat, a highly efficient and concise company chatbot mainly dedicated to answering customer queries based mainly on the knowledge provided for the MTN Momo Congo Products and Services.
DO NOT use outside knowledge for company specific questions, except for general questions. If the answer to a company-specific question is not contained in this knowledge base, state clearly that you do not have that information.
You can also answer other questions not related to the company in general.
Your tone should be professional and helpful.
You are multilingual, identify the user's language and answer accordingly.
Avoid using markdown formatting. Use well-indented numbering or bullet points(•) when making a list of items, hanging indent for each item.
Here's an example output:
Eligibility Requirements
 • The customer must be active on MTN Mobile Money.
 • Must have been subscribed to MoMo for at least 6 months.
 • Since MoMo Advance is a credit facility, MTN evaluates the customer’s creditworthiness to determine eligibility.
 • The customer must be at least 18 years old.
 
this example shows proper indentation while providing a list.

When user is logged in, his/her username will be provided. For higher personalization, you'll also keep that in mind.

In case you're asked, the current time is {CURRENT_TIME}, and today's date is {CURRENT_DATE}.

Knowledge Base Data:\n
{KNOWLEDGE_BASE}
"""

# Globals
STRUCTURED_KB: dict = {}
KB_INIT_TASK: Optional[asyncio.Task] = None
KB_STATUS = {"ready": False, "last_error": None, "keys": []}

INITIAL_KB_CHUNKS = {
    'GENERAL_INFO': MOMO_ADVANCE.strip(),
    'ECW_DETAILS': ECW_TRANSACTIONS_DETAILS.strip(),
    'XTRA_CASH': XTRA_CASH.strip()
}


# ---- Config ----
STOP_WORDS = {
    # English
    "the","is","are","what","how","to","a","an","and","or","of","for","in","on",
    # French
    "le","la","les","un","une","des","et","ou","de","du","pour","par","avec","dans",
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
MIN_TOKEN_KEEP = 100  # when truncating, keep at least this many chars


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

# ---- Inverted index builder (call once at startup) ----
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
        # also split by words with punctuation kept? not necessary for now
    return index

def count_number_of_tokens(text: str) -> int:
    """ Returns token count and prints basic stats """
    if not isinstance(text, str):
        text = str(text)

    num_chars = len(text)
    num_words = len(text.split())

    try:
        enc = tiktoken.encoding_for_model('gpt-4o-mini')
    except Exception:
        # fallback to a generic encoding if model-specific one isn't available
        enc = tiktoken.get_encoding("cl100k_base")
    tokens = enc.encode(text)
    num_tokens = len(tokens)
    return num_tokens

# ---- Core filter (fast) ----
def get_keyword_filtered_context(
    user_query: str,
    kb_chunks: Dict[str, str],
    inverted_index: Dict[str, List[str]],
    max_chunks: int = MAX_CHUNKS,
    max_kb_tokens: int = MAX_KB_TOKENS
) -> str:
    """
    Returns concatenated KB sections that match user_query, up to token budget.
    kb_chunks: dict key -> text (your INITIAL_KB_CHUNKS)
    inverted_index: token -> [keys]
    """
    if not user_query:
        return ""

    keywords = extract_keywords(user_query)
    print(keywords)
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
    selected = []
    tokens_used = 0

    for key, sc in ranked:
        if len(selected) >= max_chunks:
            break
        text = kb_chunks.get(key, "")
        if not text:
            continue
        tcount = count_number_of_tokens(text)
        if tokens_used + tcount <= max_kb_tokens:
            selected.append((key, text))
            tokens_used += tcount
        else:
            # try to truncate text to fit
            allowed = max_kb_tokens - tokens_used
            if allowed <= 0:
                break
            # approximate char truncation proportionally
            ratio = allowed / max(1, tcount)
            keep_chars = max(MIN_TOKEN_KEEP, int(len(text) * ratio))
            truncated = text[:keep_chars].rsplit("\n", 1)[0]
            selected.append((key, truncated))
            tokens_used += count_number_of_tokens(truncated)
            break

    # format nicely with headers so LLM knows source
    out = []
    for k, t in selected:
        out.append(f"[{k}]\n{t.strip()}")
    return "\n\n".join(out)
