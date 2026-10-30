"""Rule-based ticket categorization."""
RULES = {
    "Security": ["phishing", "malware", "virus", "suspicious", "breach", "ransomware"],
    "Network": ["vpn", "wifi", "wi-fi", "network", "dns", "router", "lan", "internet", "connect"],
    "Email": ["outlook", "email", "mail", "mailbox", "calendar", "sync"],
    "Database": ["database", "sql", "query", "queries", "oracle", "db"],
    "Hardware": ["printer", "laptop", "keyboard", "monitor", "mouse", "disk", "paper"],
    "Software": ["install", "software", "application", "app ", "license", "update", "adobe"],
    "Access & Identity": ["password", "locked", "login", "account", "access", "mfa", "reset"],
    "Server": ["server", "cpu", "memory", "srv", "outage"],
}
URGENT = ["critical", "down", "outage", "production", "breach", "ransomware", "phishing", "urgent"]


def categorize(text):
    t = (text or "").lower()
    scores = {c: [k for k in kws if k in t] for c, kws in RULES.items()}
    best = max(scores, key=lambda c: len(scores[c]))
    hits = scores[best]
    if not hits:
        return {"category": "Other", "confidence": 0.0, "matched": [], "suggested_priority": "3 - Moderate"}
    urgent = any(u in t for u in URGENT)
    return {"category": best, "confidence": round(min(1.0, 0.4 + 0.2 * len(hits)), 2),
            "matched": hits, "suggested_priority": "1 - Critical" if urgent else "3 - Moderate"}


def categorize_incident(inc):
    return categorize(f"{inc.get('short_description', '')} {inc.get('description', '')}")
