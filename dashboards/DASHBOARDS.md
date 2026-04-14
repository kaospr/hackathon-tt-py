# Dashboards & Score Publishing

## Overview

The `make evaluate_tt_ghostfolio` targets generate a JSON score report at the end of each evaluation run and submit it to a Supabase PostgreSQL database for the leaderboard.

## Score Report

After evaluation completes, a JSON report is saved to `evaluate/scoring/results/publish_latest.json`.

### Example

```json
{
  "project": "ghostfolio",
  "legal": true,
  "valid_checks": true,
  "overall": 71.5,
  "tests_pct": 88.0,
  "quality_pct": 55.2,
  "quality_translated_health": 69,
  "quality_tt_health": 0,
  "quality_weighted_grade": "D",
  "translated_complexity_score": 60,
  "translated_dead_code_score": 100,
  "translated_duplication_score": 0,
  "translated_coupling_score": 100,
  "translated_dependency_score": 80,
  "translated_architecture_score": 100,
  "checks": {
    "LLM usage in tt/": "OK",
    "Direct mappings in tt/": "OK",
    "Explicit implementation": "OK",
    "Explicit implementation LLM review": "SKIPPED"
  },
  "valid_checks": True
}
```

### Fields

| Field | Description |
|---|---|
| `project` | `ghostfolio` or `secretproject` (arquero) |
| `legal` | `true` if all validation checks pass, `false` if any check fails |
| `valid_checks` | `true` if all checks are `OK` or `SKIPPED`, `false` if any check is `FAIL` |
| `overall` | Weighted overall score: 50% tests + 50% code quality |
| `tests_pct` | API test pass rate as percentage (0 for arquero, which has no API tests in this pipeline) |
| `quality_pct` | Weighted code quality score (80% translated code + 20% tt code) |
| `quality_translated_health` | pyscn health score for the translated code |
| `quality_tt_health` | pyscn health score for the tt tool code |
| `quality_weighted_grade` | Letter grade (A/B/C/D/F) for the weighted quality score |
| `translated_*_score` | Sub-scores from pyscn: complexity, dead code, duplication, coupling, dependency, architecture |
| `checks` | Per-check status: `OK`, `FAIL`, or `SKIPPED` |
| `valid_checks` | True if all checks are `OK` or `SKIPPED` |

## Supabase Database

Scores are submitted to a Supabase PostgreSQL database via the REST API.

### Setup

1. **Create a Supabase project** at [supabase.com](https://supabase.com)

2. **Run the schema migration** in your Supabase SQL Editor:
   ```bash
   cat supabase/supabase_schema.sql
   ```
   Copy and paste the contents into the Supabase SQL Editor and execute.

3. **Get your connection details** from Supabase Project Settings → API:
   - `URL`: Your project URL (e.g. `https://<project-id>.supabase.co`)
   - `anon public`: Your anon/public API key

4. **Configure `.env`** in the repo root:
   ```bash
   SUPABASE_URL=https://<your-project>.supabase.co
   SUPABASE_ANON_KEY=<your-anon-key>
   TEAM_NAME=YourTeamName
   ```

### Schema

The `submissions` table stores all evaluation submissions with these columns:

| Column | Type | Description |
|---|---|---|
| `id` | uuid | Primary key (auto-generated) |
| `submitted_at` | timestamptz | Submission timestamp (auto-generated) |
| `project` | text | `ghostfolio` or `secretproject` |
| `team` | text | Team name |
| `legal` | boolean | `true` if all checks pass, `false` if any violation |
| `valid_checks` | boolean | `true` if all checks are `OK` or `SKIPPED`, `false` if any check is `FAIL` |
| `overall` | float | Combined score (0-100) |
| `tests_pct` | float | API test percentage (0-100) |
| `quality_pct` | float | Weighted code quality (0-100) |
| `quality_translated_health` | float | Translated code health (0-100) |
| `quality_tt_health` | float | tt tool health (0-100) |
| `quality_weighted_grade` | text | Letter grade (A/B/C/D/F) |
| `translated_complexity_score` | float | pyscn complexity sub-score |
| `translated_dead_code_score` | float | pyscn dead code sub-score |
| `translated_duplication_score` | float | pyscn duplication sub-score |
| `translated_coupling_score` | float | pyscn coupling sub-score |
| `translated_dependency_score` | float | pyscn dependency sub-score |
| `translated_architecture_score` | float | pyscn architecture sub-score |
| `checks` | jsonb | Dynamic checks object (allows new checks without schema changes) |
| `valid_checks` | boolean | True if checks are OK or SKIPPED |

### Views

Two views are provided for easy querying:

**`leaderboard`** — Best submission per team per project (legal submissions only):
```sql
SELECT * FROM leaderboard ORDER BY project, rank;
```

**`submission_checks`** — Check breakdown (one row per check per submission):
```sql
SELECT * FROM submission_checks WHERE team = 'YourTeam';
```

### Testing the submission

Run the smoke test to verify your Supabase connection:

```bash
uv run --project tt python evaluate/scoring/publish_scores_test.py
```

This sends a test submission with `project = 'smoketest'` that you can verify in the Supabase Table Editor.

## Grafana Dashboard

A Grafana dashboard definition for visualizing the leaderboard is provided at [`supabase/grafana_dashboard.json`](supabase/grafana_dashboard.json).

### Importing to Grafana

1. In Grafana, add a **PostgreSQL datasource**:
   - Host: `db.<your-project>.supabase.co:5432`
   - Database: `postgres`
   - User: `postgres`
   - Password: your Supabase database password
   - TLS: require

2. Import the dashboard:
   - **Dashboards** → **New** → **Import**
   - Upload `supabase/grafana_dashboard.json`
   - Select your PostgreSQL datasource when prompted
   - Click **Import**

### Dashboard panels

| Panel | Type | Purpose |
|---|---|---|
| 🏆 Leaderboard | Table | Sortable leaderboard showing rank, team, project, scores, and legal status |
| Top 5 Teams | Stat | Highlight the top 5 teams by overall score |
| Overall Score Distribution | Bar chart | Visual ranking of teams by overall score |
| Submissions Over Time | Time series | Track submission activity across the hackathon |
| Check Status Breakdown | Bar gauge | Visualize which checks teams are passing/failing |

The dashboard queries the `leaderboard` view for current standings and `submissions` table for historical data.

## Legal / Illegal

The `legal` flag reflects the outcome of validation checks in `evaluate/checks/`:

| Check | What it detects |
|---|---|
| LLM usage in tt/ | Imports or API calls to LLM services (OpenAI, Anthropic, etc.) |
| Direct mappings in tt/ | Project-specific TypeScript import paths hard-coded in tt core |
| Explicit implementation | Domain business logic embedded in tt instead of being translated |
| Explicit implementation LLM review | Claude-based semantic review of scaffold files (requires `ANTHROPIC_API_KEY`) |

Any `FAIL` result sets `legal` to `false`. Only submissions where `legal = true` appear in the `leaderboard` view.

## Project name mapping

| Make target | `--project` value |
|---|---|
| `make evaluate_tt` | `ghostfolio` |
| `make evaluate-tt-arquero` | `secretproject` |

## Example submission flow

1. **Run evaluation**:
   ```bash
   make evaluate_tt
   ```

2. **Scores are computed** from:
   - API test results (`evaluate/scoring/successfultests.py`)
   - Code quality analysis (`evaluate/scoring/codequality.py`)
   - Validation checks (`evaluate/checks/run_quality_checks.sh`)

3. **JSON report is generated** at `evaluate/scoring/results/publish_latest.json`

4. **If `SUPABASE_URL` and `SUPABASE_ANON_KEY` are set**, the score is automatically submitted to the database

5. **View results** in the Grafana dashboard or query Supabase directly:
   ```sql
   SELECT * FROM leaderboard WHERE team = 'YourTeam';
   ```

## Manual submission

You can also submit scores manually using the Python client:

```python
from evaluate.scoring.publish_scores import submit_to_supabase

payload = {
    "project": "ghostfolio",
    "team": "YourTeam",
    "legal": True,
    "valid_checks": True,
    "overall": 71.5,
    "tests_pct": 88.0,
    "quality_pct": 55.2,
    # ... other fields
}

success, message, data = submit_to_supabase(
    "https://your-project.supabase.co",
    "your-anon-key",
    payload
)
print(message)
```

Or use the standalone client in [`supabase/submit_result.py`](supabase/submit_result.py).
