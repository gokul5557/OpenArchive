import re

# PII Patterns
PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
    "IPV4": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "PHONE": r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b"
}

def identify_pii(text: str):
    """Returns a list of identified PII segments."""
    found = []
    for label, pattern in PATTERNS.items():
        for match in re.finditer(pattern, text):
            found.append({
                "label": label,
                "start": match.start(),
                "end": match.end(),
                "text": match.group()
            })
    return found

def redact_text(text: str, mask_char="*"):
    """Redacts all identified PII in the text."""
    redacted = text
    # Sort by start descending to avoid index shifts
    found = identify_pii(text)
    found.sort(key=lambda x: x['start'], reverse=True)
    
    for item in found:
        # Simple mask - replace all but first and last char? 
        # Or standard [REDACTED] label. 
        # Let's go with labels for audit clarity.
        label = item['label']
        redacted = redacted[:item['start']] + f"[{label}]" + redacted[item['end']:]
        
    return redacted
