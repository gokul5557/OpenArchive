import re

# PII Patterns
PATTERNS = {
    "EMAIL": r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+",
    "CREDIT_CARD": r"\b(?:\d[ -]*?){13,16}\b",
    "IPV4": r"\b(?:[0-9]{1,3}\.){3}[0-9]{1,3}\b",
    "SSN": r"\b\d{3}-\d{2}-\d{4}\b",
    "PHONE": r"\b(?:\+?\d{1,3}[- ]?)?\(?\d{3}\)?[- ]?\d{3}[- ]?\d{4}\b",
    "IBAN": r"\b[A-Z]{2}\d{2}[A-Z\d]{4}\d{7}([A-Z\d]?){0,16}\b",
    "SECRET_KEY": r"\b(?:AWS|KEY|SECRET|TOKEN|API)([A-Z0-9/=+-]{20,})\b"
}

def identify_pii(text: str):
    """Returns a list of identified PII segments."""
    found = []
    if not text: return found
    
    for label, pattern in PATTERNS.items():
        try:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                found.append({
                    "label": label,
                    "start": match.start(),
                    "end": match.end(),
                    "text": match.group()
                })
        except Exception as e:
            print(f"PII Scan Error for {label}: {e}")
            
    return found

def redact_text(text: str, mask_char="*"):
    """Redacts all identified PII in the text."""
    if not text: return ""
    
    # Sort by start descending to avoid index shifts
    found = identify_pii(text)
    found.sort(key=lambda x: x['start'], reverse=True)
    
    # Handle overlaps? For now, we just process.
    # To handle overlaps properly, we can merge segments.
    
    redacted = text
    for item in found:
        label = item['label']
        # Ensure we haven't already redacted this section (due to overlap)
        if item['end'] <= len(redacted):
            redacted = redacted[:item['start']] + f"[{label}]" + redacted[item['end']:]
        
    return redacted
