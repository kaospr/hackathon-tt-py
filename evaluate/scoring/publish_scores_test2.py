#!/usr/bin/env python3
"""
evaluate/scoring/publish_scores_test.py — Smoke-test the Supabase submission path.

Loads SUPABASE_URL and SUPABASE_ANON_KEY from .env (repo root), sends a minimal
test payload to Supabase, and reports success/failure.

Usage:
  uv run --project tt python evaluate/scoring/publish_scores_test.py
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
ENV_FILE = REPO_ROOT / ".env"


def load_env_file(path: Path) -> None:
    """Minimal .env parser: KEY=VALUE per line, # comments, no export."""
    if not path.exists():
        return
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


def import_publish_module():
    """Import publish_scores.py as a module without running main()."""
    spec_path = Path(__file__).parent / "publish_scores.py"
    spec = importlib.util.spec_from_file_location("publish_scores", spec_path)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main() -> int:
    load_env_file(ENV_FILE)

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    anon_key = os.environ.get("SUPABASE_ANON_KEY", "")

    if not supabase_url or "[YOUR-" in supabase_url.upper():
        print(f"ERROR: SUPABASE_URL not set (or still placeholder) in {ENV_FILE}")
        return 1

    if not anon_key or "[YOUR-" in anon_key.upper():
        print(f"ERROR: SUPABASE_ANON_KEY not set (or still placeholder) in {ENV_FILE}")
        return 1

    publish = import_publish_module()

    team = os.environ.get("TEAM_NAME", publish.DEFAULT_TEAM_NAME)

    # Minimal test payload — distinct project name so it doesn't pollute real data
    test_payload = {
        "project": "ghostfolio",
        "team": "TeamBeta",
        "legal": True,
        "overall": 65.0,
        "tests_pct": 55.0,
        "quality_pct": 55.0,
        "quality_translated_health": 55.0,
        "quality_tt_health": 55.0,
        "quality_weighted_grade": "D",
        "translated_complexity_score": 22.0,
        "translated_dead_code_score": 55.0,
        "translated_duplication_score": 55.0,
        "translated_coupling_score": 55.0,
        "translated_dependency_score": 55.0,
        "translated_architecture_score": 55.0,
        "checks": {
            "LLM usage in tt/": "FAIL",
            "Direct mappings in tt/": "OK",
            "Explicit implementation": "OK",
        },
        "valid_checks": False
    }

    print("=" * 70)
    print("  Supabase submission smoke test")
    print("=" * 70)
    print(f"  URL:     {supabase_url}")
    print(f"  Team:    {team}")
    print(f"  Project: smoketest")
    print(f"  Payload: {json.dumps(test_payload, indent=11)}")
    print()
    print("  Submitting...")

    success, message, data = publish.submit_to_supabase(supabase_url, anon_key, test_payload)

    if success:
        print(f"  ✓ SUCCESS: {message}")
        print()
        print("  Verify in Supabase SQL Editor:")
        print("    SELECT * FROM submissions WHERE project = 'smoketest' ORDER BY submitted_at DESC LIMIT 1;")
        print()
        print("  Or check the leaderboard view:")
        print("    SELECT * FROM leaderboard WHERE project = 'smoketest';")
        print("=" * 70)
        return 0
    else:
        print(f"  ✗ FAILED: {message}")
        print("=" * 70)
        return 1


if __name__ == "__main__":
    sys.exit(main())
