"""
submit_result.py — Hackathon leaderboard submission client
==========================================================

Usage:
    python submit_result.py

Or import and call submit() directly from your evaluation script.

Setup:
    pip install requests
    Set the two environment variables below, or hardcode them for the hackathon.
"""

import os
import json
import requests

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.getenv("SUPABASE_URL", "https://<your-project>.supabase.co")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY", "<your-anon-key>")
# ─────────────────────────────────────────────────────────────────────────────


def submit(
    project: str,
    team: str,
    legal: bool,
    overall: float,
    tests_pct: float,
    quality_pct: float,
    quality_translated_health: float,
    quality_tt_health: float,
    quality_weighted_grade: str,
    translated_complexity_score: float,
    translated_dead_code_score: float,
    translated_duplication_score: float,
    translated_coupling_score: float,
    translated_dependency_score: float,
    translated_architecture_score: float,
    checks: dict,           # e.g. {"LLM usage in tt/": "OK", ...}
) -> dict:
    """
    Submit evaluation results to the leaderboard.
    Returns the Supabase response dict on success, raises on failure.
    """
    payload = {
        "project": project,
        "team": team,
        "legal": legal,
        "overall": overall,
        "tests_pct": tests_pct,
        "quality_pct": quality_pct,
        "quality_translated_health": quality_translated_health,
        "quality_tt_health": quality_tt_health,
        "quality_weighted_grade": quality_weighted_grade,
        "translated_complexity_score": translated_complexity_score,
        "translated_dead_code_score": translated_dead_code_score,
        "translated_duplication_score": translated_duplication_score,
        "translated_coupling_score": translated_coupling_score,
        "translated_dependency_score": translated_dependency_score,
        "translated_architecture_score": translated_architecture_score,
        "checks": checks,   # JSONB — any dict works, new keys are fine
    }

    headers = {
        "apikey": SUPABASE_ANON_KEY,
        "Authorization": f"Bearer {SUPABASE_ANON_KEY}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    resp = requests.post(
        f"{SUPABASE_URL}/rest/v1/submissions",
        headers=headers,
        data=json.dumps(payload),
        timeout=10,
    )

    if resp.status_code not in (200, 201):
        raise RuntimeError(
            f"Submission failed [{resp.status_code}]: {resp.text}"
        )

    result = resp.json()
    print(f"✅ Submitted! id={result[0]['id']}")
    return result[0]


# ── Example / quick test ──────────────────────────────────────────────────────
if __name__ == "__main__":
    submit(
        project="ghostfolio",
        team="hardcoders",
        legal=True,
        overall=71.5,
        tests_pct=88.0,
        quality_pct=55.2,
        quality_translated_health=69,
        quality_tt_health=0,
        quality_weighted_grade="D",
        translated_complexity_score=60,
        translated_dead_code_score=100,
        translated_duplication_score=0,
        translated_coupling_score=100,
        translated_dependency_score=80,
        translated_architecture_score=100,
        checks={
            "LLM usage in tt/": "OK",
            "Direct mappings in tt/": "OK",
            "Explicit implementation": "FAIL",
            "Explicit implementation LLM review": "SKIPPED",
            # Add any future checks here — no schema change needed
        },
    )
