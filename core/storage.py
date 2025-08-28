import os
import json
import pandas as pd
from datetime import datetime
from typing import Dict, List

BASE_DIR = os.path.dirname(os.path.dirname(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
INTERVIEWS_DIR = os.path.join(DATA_DIR, "interviews")
CANDIDATES_CSV = os.path.join(DATA_DIR, "candidates.csv")
PERF_CSV = os.path.join(DATA_DIR, "performances.csv")

def ensure_data_dirs():
    os.makedirs(DATA_DIR, exist_ok=True)
    os.makedirs(INTERVIEWS_DIR, exist_ok=True)
    
    if not os.path.exists(CANDIDATES_CSV):
        pd.DataFrame(
            columns=["id", "name", "email", "experience", "desired_position", "tech_stack", "created_at"]
        ).to_csv(CANDIDATES_CSV, index=False)
    
    if not os.path.exists(PERF_CSV):
        pd.DataFrame(
            columns=["id", "name", "email", "role", "tech_stack", "score", "breakdown", "created_at"]
        ).to_csv(PERF_CSV, index=False)

def upsert_candidate(cand: Dict):
    df = pd.read_csv(CANDIDATES_CSV)
    now = datetime.utcnow().isoformat()
    
    row = {
        "id": cand.get("id"),
        "name": cand.get("name"),
        "email": cand.get("email"),
        "experience": cand.get("experience"),
        "desired_position": cand.get("desired_position"),
        "tech_stack": cand.get("tech_stack"),
        "created_at": now,
    }
    
    # append-only (simple audit trail)
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(CANDIDATES_CSV, index=False)

def append_performance(candidate_id: str, name: str, email: str, role: str, tech_stack: str, score: int, breakdown_json: str):
    df = pd.read_csv(PERF_CSV)
    now = datetime.utcnow().isoformat()
    
    row = {
        "id": candidate_id,
        "name": name,
        "email": email,
        "role": role,
        "tech_stack": tech_stack,
        "score": score,
        "breakdown": breakdown_json,
        "created_at": now,
    }
    
    df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
    df.to_csv(PERF_CSV, index=False)

def save_chat_history(candidate_id: str, history: List[tuple]):
    path = os.path.join(INTERVIEWS_DIR, f"{candidate_id}.json")
    
    # Convert tuples to dicts for clarity
    records = [{"role": r, "content": c} for (r, c) in history]
    
    with open(path, "w", encoding="utf-8") as f:
        json.dump(records, f, ensure_ascii=False, indent=2)