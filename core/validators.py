import re
from typing import List, Tuple

EMAIL_RE = re.compile(r"^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$")
TECH_TOKEN_RE = re.compile(r"^[A-Za-z0-9#+.\- ]{1,30}$")

def is_valid_email(email: str) -> bool:
    return bool(EMAIL_RE.match(email or ""))

def is_nonempty_string(s: str) -> bool:
    return isinstance(s, str) and len(s.strip()) > 1

def parse_and_validate_tech_stack(csv_text: str) -> Tuple[List[str], str | None]:
    if not is_nonempty_string(csv_text):
        return [], "Tech stack cannot be empty."
    
    items = [t.strip() for t in csv_text.split(",") if t.strip()]
    if not items:
        return [], "Please provide at least one technology (comma-separated)."
    
    for t in items:
        if not TECH_TOKEN_RE.match(t):
            return [], f"Invalid tech name: '{t}'. Use letters, digits, +, #, ., - and spaces."
    
    return items, None