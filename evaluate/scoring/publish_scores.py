#!/usr/bin/env python3
"""
evaluate/scoring/publish_scores.py — Generate JSON report and publish to Supabase.

Reads scoring results and quality check results, then:
  1. Prints a JSON summary
  2. If SUPABASE_URL and SUPABASE_ANON_KEY are set, submits to the leaderboard

Environment variables:
  SUPABASE_URL         — Supabase project URL (e.g. https://<project>.supabase.co)
  SUPABASE_ANON_KEY    — Supabase anon/public API key
  TEAM_NAME            — overrides default team name (default: TeamAlpha)

Usage:
  uv run --project tt python evaluate/scoring/publish_scores.py --project ghostfolio
  uv run --project tt python evaluate/scoring/publish_scores.py --project secretproject
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path

REPO_ROOT = Path(__file__).parent.parent.parent.resolve()
SCORING_RESULTS_DIR = Path(__file__).parent / "results"
CHECKS_RESULTS_DIR = REPO_ROOT / "evaluate" / "checks" / "results"

DEFAULT_TEAM_NAME = "TeamAlpha"


def load_json(path: Path) -> dict | None:
    if path.exists():
        return json.loads(path.read_text(encoding="utf-8"))
    return None


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


def submit_to_supabase(supabase_url: str, anon_key: str, payload: dict) -> tuple[bool, str, dict | None]:
    """
    Submit to Supabase REST API.
    Returns (success, message, response_data).
    """
    url = f"{supabase_url}/rest/v1/submissions"
    headers = {
        "apikey": anon_key,
        "Authorization": f"Bearer {anon_key}",
        "Content-Type": "application/json",
        "Prefer": "return=representation",
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0:
                submission_id = data[0].get("id", "unknown")
                submitted_at = data[0].get("submitted_at", "unknown")
                return True, f"Submitted! ID={submission_id} at {submitted_at}", data[0]
            return True, f"Submitted (HTTP {resp.status})", data
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        return False, f"HTTP {e.code}: {body}", None
    except urllib.error.URLError as e:
        return False, f"URLError: {e.reason}", None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


def main() -> int:
    parser = argparse.ArgumentParser(description="Publish evaluation scores")
    parser.add_argument(
        "--project",
        required=True,
        choices=["ghostfolio", "secretproject"],
        help="Project name for the submission",
    )
    args = parser.parse_args()

    # Load .env if present
    env_file = REPO_ROOT / ".env"
    load_env_file(env_file)

    supabase_url = os.environ.get("SUPABASE_URL", "").rstrip("/")
    supabase_anon_key = os.environ.get("SUPABASE_ANON_KEY", "")
    team_name = os.environ.get("TEAM_NAME", DEFAULT_TEAM_NAME)

    # --- Load results ---
    quality = load_json(SCORING_RESULTS_DIR / "latest.json")
    tests = load_json(SCORING_RESULTS_DIR / "tests_latest.json")
    checks = load_json(CHECKS_RESULTS_DIR / "latest.json")

    # --- Extract scores ---
    tests_pct = 0.0
    if tests and "percentage" in tests:
        tests_pct = tests["percentage"]

    quality_pct = 0.0
    quality_translated_health = 0.0
    quality_tt_health = 0.0
    quality_weighted_grade = "F"
    translated_scores = {}

    if quality:
        quality_pct = quality.get("weighted_score", 0.0)
        tc = quality.get("translated_code", {})
        tt = quality.get("tt_code", {})
        quality_translated_health = tc.get("health_score", 0.0)
        quality_tt_health = tt.get("health_score", 0.0)
        quality_weighted_grade = quality.get("weighted_grade", "F")

        # Extract translated sub-scores
        for key in [
            "complexity_score", "dead_code_score", "duplication_score",
            "coupling_score", "dependency_score", "architecture_score",
        ]:
            if key in tc:
                translated_scores[f"translated_{key}"] = tc[key]

    # Overall = 50% tests + 50% quality (same as overall.py)
    overall = round((tests_pct + quality_pct) / 2, 2)

    # Legal/illegal from checks
    legal = True
    checks_dict = {}
    if checks:
        legal = checks.get("legal", True)
        checks_dict = checks.get("checks", {})

    # valid_checks: true if all checks pass (OK or SKIPPED), false if any FAIL
    valid_checks = True
    for check_name, check_status in checks_dict.items():
        if check_status == "FAIL":
            valid_checks = False
            break

    # --- Build JSON report (for local file) ---
    report = {
        "project": args.project,
        "legal": legal,
        "valid_checks": valid_checks,
        "overall": overall,
        "tests_pct": tests_pct,
        "quality_pct": quality_pct,
        "quality_translated_health": quality_translated_health,
        "quality_tt_health": quality_tt_health,
        "quality_weighted_grade": quality_weighted_grade,
        **translated_scores,
        "checks": checks_dict,
    }

    report_json = json.dumps(report, indent=2)

    # Save report
    SCORING_RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    report_path = SCORING_RESULTS_DIR / "publish_latest.json"
    report_path.write_text(report_json, encoding="utf-8")

    # --- Print JSON ---
    print()
    print("=" * 70)
    print("  Scores JSON Report")
    print("=" * 70)
    print(report_json)
    print()

    # --- Build submission payload (matches dashboards/supabase schema) ---
    payload = {
        "project": args.project,
        "team": team_name,
        "legal": legal,
        "valid_checks": valid_checks,
        "overall": overall,
        "tests_pct": tests_pct,
        "quality_pct": quality_pct,
        "quality_translated_health": quality_translated_health,
        "quality_tt_health": quality_tt_health,
        "quality_weighted_grade": quality_weighted_grade,
        **{k.replace("translated_", "translated_"): v for k, v in translated_scores.items()},
        "checks": checks_dict,
    }

    # --- Submit to Supabase if configured ---
    print("=" * 70)
    print("  Publishing to Supabase")
    print("=" * 70)
    print()

    if not supabase_url or "[YOUR-" in supabase_url.upper():
        print("  SUPABASE_URL not set (or still placeholder) — dry run only")
        print(f"  Set SUPABASE_URL and SUPABASE_ANON_KEY in {env_file} to publish")
    elif not supabase_anon_key or "[YOUR-" in supabase_anon_key.upper():
        print("  SUPABASE_ANON_KEY not set (or still placeholder) — dry run only")
        print(f"  Set SUPABASE_ANON_KEY in {env_file} to publish")
    else:
        print(f"  Team:    {team_name}")
        print(f"  Project: {args.project}")
        print(f"  Overall: {overall}")
        print(f"  Legal:   {legal}")
        print()
        print("  Submitting to Supabase REST API...")
        success, message, data = submit_to_supabase(supabase_url, supabase_anon_key, payload)
        if success:
            print(f"  ✓ {message}")
        else:
            print(f"  ✗ Failed: {message}")
            print()
            print(f"  Report saved to: {report_path}")
            print("=" * 70)
            print()
            return 1

    print(f"  Report saved to: {report_path}")
    print("=" * 70)
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
