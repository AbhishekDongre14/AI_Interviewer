# core/evaluator.py
import json
import re
import math
from typing import List, Dict, Any

# Keep the old parser available (for backward compatibility if needed)
def safe_parse_json(s: str) -> Dict[str, Any]:
    try:
        return json.loads(s)
    except Exception:
        start = s.find("{")
        end = s.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(s[start : end + 1])
            except Exception:
                pass
        return {"justification": s.strip()[:200], "score": 0}


# Try to import sklearn for TF-IDF + cosine similarity; if not available, use fallback
try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity

    _SKLEARN_AVAILABLE = True
except Exception:
    _SKLEARN_AVAILABLE = False


# Small stopword list (keeps evaluator self-contained)
_STOPWORDS = {
    "the", "is", "are", "in", "on", "for", "a", "an", "of", "and", "to",
    "with", "by", "at", "from", "as", "that", "this", "it", "be", "or",
    "which", "we", "you", "i", "they", "have", "has", "was", "were", "but",
}


def _tokenize(text: str) -> List[str]:
    if not isinstance(text, str):
        return []
    # keep alphanumerics and '+' '#' '.' '-' as tokens if present
    tokens = re.findall(r"[A-Za-z0-9#+\-.]+", text.lower())
    return [t for t in tokens if t and t not in _STOPWORDS]


def _extract_keywords(text: str, top_k: int = 6) -> List[str]:
    tokens = _tokenize(text)
    if not tokens:
        return []
    # Frequency order
    freq = {}
    for t in tokens:
        freq[t] = freq.get(t, 0) + 1
    # Sort by frequency then length to prefer meaningful tokens
    sorted_tokens = sorted(freq.items(), key=lambda x: (-x[1], -len(x[0])))
    keywords = [t for t, _ in sorted_tokens[:top_k]]
    return keywords


def _keyword_overlap_score(question: str, answer: str) -> float:
    keywords = _extract_keywords(question, top_k=6)
    if not keywords:
        return 0.0
    ans_lower = (answer or "").lower()
    found = 0
    for kw in keywords:
        # word boundary check
        if re.search(rf"\b{re.escape(kw)}\b", ans_lower):
            found += 1
    overlap = found / len(keywords)
    # return 0..1
    return max(0.0, min(1.0, overlap))


def _semantic_similarity(question: str, answer: str) -> float:
    q = (question or "").strip()
    a = (answer or "").strip()
    if not q or not a:
        return 0.0
    # Prefer sklearn TF-IDF cosine similarity if present
    if _SKLEARN_AVAILABLE:
        try:
            vec = TfidfVectorizer().fit([q, a])
            mat = vec.transform([q, a])
            sim = float(cosine_similarity(mat[0], mat[1])[0][0])
            # safety
            if math.isnan(sim):
                return 0.0
            return max(0.0, min(1.0, sim))
        except Exception:
            # fallback to token Jaccard
            pass

    # Fallback: token Jaccard similarity
    q_tokens = set(_tokenize(q))
    a_tokens = set(_tokenize(a))
    if not q_tokens or not a_tokens:
        return 0.0
    inter = q_tokens & a_tokens
    union = q_tokens | a_tokens
    sim = len(inter) / len(union) if union else 0.0
    return max(0.0, min(1.0, sim))


def _is_gibberish(answer: str) -> (bool, str):
    if not isinstance(answer, str):
        return True, "non-string answer"
    a = answer.strip()
    if not a:
        return True, "empty answer"

    # too many repeated characters (e.g., 'aaaaa....')
    if re.search(r"(.)\1{6,}", a):
        return True, "repeated character sequence"

    # compute alphabetic ratio
    total_chars = len(a)
    alpha_chars = sum(1 for c in a if c.isalpha())
    alpha_ratio = alpha_chars / total_chars if total_chars > 0 else 0.0

    # if answer is long but contains very few letters -> gibberish
    if total_chars >= 15 and alpha_ratio < 0.25:
        return True, f"low alpha ratio ({alpha_ratio:.2f})"

    # if it's extremely short and contains no meaningful tokens, consider gibberish
    tokens = _tokenize(a)
    if total_chars < 6 and len(tokens) == 0:
        return True, "too short / no tokens"

    return False, ""


def grade_qa_batch(evaluator_llm, eval_prompt, qa_list: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """
    Local hybrid evaluator — keeps the same signature to avoid breaking other modules.

    Algorithm (per QA):
      1. If empty / gibberish -> score = 0.
      2. Compute keyword overlap (0..1) between question and answer.
      3. Compute semantic similarity (0..1) using TF-IDF cosine (sklearn) or Jaccard tokens fallback.
      4. Combine: final = w_sim * sim + w_kw * overlap  (defaults: w_sim=0.6, w_kw=0.4)
      5. Map final (0..1) -> score (0..10). If final < threshold (0.15) -> score = 0 to avoid rewarding random text.
      6. justification contains details.

    Returns list of dicts:
      { "question": q, "answer": a, "justification": "...", "score": <0..10 float> }
    """
    results: List[Dict[str, Any]] = []
    # Defensive: allow qa_list to be JSON string if passed accidentally
    if isinstance(qa_list, str):
        try:
            qa_list = json.loads(qa_list)
        except Exception:
            qa_list = []

    for item in qa_list:
        try:
            q = item.get("q", "") if isinstance(item, dict) else ""
            a = item.get("a", "") if isinstance(item, dict) else str(item)

            # basic normalization
            q_text = (q or "").strip()
            a_text = (a or "").strip()

            # gibberish / empty checks
            is_gib, reason = _is_gibberish(a_text)
            if is_gib:
                justification = f"Gibberish/invalid answer detected: {reason}"
                score = 0.0
                results.append({
                    "question": q_text,
                    "answer": a_text,
                    "justification": justification,
                    "score": score,
                })
                continue

            # keyword overlap and semantic similarity
            kw_overlap = _keyword_overlap_score(q_text, a_text)  # 0..1
            sim = _semantic_similarity(q_text, a_text)  # 0..1

            # Combine scores
            w_sim = 0.6
            w_kw = 0.4
            combined = (w_sim * sim) + (w_kw * kw_overlap)

            # Threshold to filter near-random matches
            MIN_ACCEPT_THRESHOLD = 0.15  # below this, treat as 0 relevance
            if combined < MIN_ACCEPT_THRESHOLD:
                score = 0.0
                justification = (
                    f"Low relevance (combined={combined:.3f} < {MIN_ACCEPT_THRESHOLD}). "
                    f"Keyword overlap: {kw_overlap:.2f}, Similarity: {sim:.2f}."
                )
            else:
                # Map to 0..10
                score_raw = combined * 10.0
                # final rounding to 2 decimals
                score = round(max(0.0, min(10.0, score_raw)), 2)
                justification = (
                    f"Keyword overlap: {kw_overlap:.2f}, Similarity: {sim:.2f}, "
                    f"Combined: {combined:.3f} => score {score:.2f}/10"
                )

            results.append({
                "question": q_text,
                "answer": a_text,
                "justification": justification,
                "score": score,
            })
        except Exception as exc:
            # Fail-safe entry so we never break the pipeline
            results.append({
                "question": item.get("q", "") if isinstance(item, dict) else "",
                "answer": item.get("a", "") if isinstance(item, dict) else str(item),
                "justification": f"Evaluator error: {str(exc)[:200]}",
                "score": 0.0,
            })

    return results
