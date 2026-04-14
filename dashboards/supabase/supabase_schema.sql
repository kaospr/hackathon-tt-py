-- ============================================================
-- Hackathon Leaderboard Schema for Supabase
-- ============================================================

-- Main submissions table
CREATE TABLE submissions (
  id                              uuid DEFAULT gen_random_uuid() PRIMARY KEY,
  submitted_at                    timestamptz DEFAULT now(),

  -- Identity
  project                         text NOT NULL,
  team                            text NOT NULL,
  legal                           boolean NOT NULL DEFAULT false,

  -- Top-level scores
  overall                         float,
  tests_pct                       float,
  quality_pct                     float,
  quality_translated_health       float,
  quality_tt_health               float,
  quality_weighted_grade          text,

  -- Translated sub-scores
  translated_complexity_score     float,
  translated_dead_code_score      float,
  translated_duplication_score    float,
  translated_coupling_score       float,
  translated_dependency_score     float,
  translated_architecture_score   float,

  -- Dynamic checks stored as JSONB so new checks need no schema change
  checks                          jsonb DEFAULT '{}'::jsonb,
  valid_checks BOOLEAN DEFAULT FALSE
);

-- Index for fast leaderboard queries
CREATE INDEX idx_submissions_project   ON submissions (project);
CREATE INDEX idx_submissions_team      ON submissions (team);
CREATE INDEX idx_submissions_overall   ON submissions (overall DESC);
CREATE INDEX idx_submissions_submitted ON submissions (submitted_at DESC);

-- ============================================================
-- View: best submission per team per project
-- Shows the highest-overall submission for each team.
-- ============================================================
CREATE VIEW leaderboard AS
SELECT DISTINCT ON (project, team)
  id,
  submitted_at,
  project,
  team,
  legal,
  overall,
  tests_pct,
  quality_pct,
  quality_translated_health,
  quality_tt_health,
  quality_weighted_grade,
  translated_complexity_score,
  translated_dead_code_score,
  translated_duplication_score,
  translated_coupling_score,
  translated_dependency_score,
  translated_architecture_score,
  checks,
  -- Derived rank within project
  RANK() OVER (PARTITION BY project ORDER BY overall DESC NULLS LAST) AS rank
FROM submissions
WHERE legal = true          -- only count legal submissions
ORDER BY project, team, overall DESC NULLS LAST;

-- ============================================================
-- View: check breakdown (one row per check per submission)
-- Useful for Grafana bar charts / stat panels on check status.
-- ============================================================
CREATE VIEW submission_checks AS
SELECT
  s.id            AS submission_id,
  s.submitted_at,
  s.project,
  s.team,
  s.overall,
  kv.key          AS check_name,
  kv.value #>> '{}' AS check_status   -- unwrap JSON string
FROM submissions s,
     jsonb_each(s.checks) AS kv;

-- ============================================================
-- Row Level Security (RLS)
-- Anyone can INSERT (teams submit) but only authenticated
-- users (Grafana service account) can SELECT freely.
-- Adjust policies to match your Supabase auth setup.
-- ============================================================
ALTER TABLE submissions ENABLE ROW LEVEL SECURITY;

-- Allow any anon client to insert
CREATE POLICY "teams can submit"
  ON submissions FOR INSERT
  TO anon
  WITH CHECK (true);

-- Allow anon to read (so Grafana public dashboard works).
-- Remove this and use a service_role key in Grafana if you
-- want the leaderboard to be private.
CREATE POLICY "public can read"
  ON submissions FOR SELECT
  TO anon
  USING (true);

-- ============================================================
-- Example insert (for testing)
-- ============================================================
-- INSERT INTO submissions (
--   project, team, legal, overall, tests_pct, quality_pct,
--   quality_translated_health, quality_tt_health, quality_weighted_grade,
--   translated_complexity_score, translated_dead_code_score,
--   translated_duplication_score, translated_coupling_score,
--   translated_dependency_score, translated_architecture_score,
--   checks
-- ) VALUES (
--   'ghostfolio', 'hardcoders', true, 71.5, 88.0, 55.2,
--   69, 0, 'D',
--   60, 100, 0, 100, 80, 100,
--   '{"LLM usage in tt/": "OK", "Direct mappings in tt/": "OK",
--     "Explicit implementation": "FAIL",
--     "Explicit implementation LLM review": "SKIPPED"}'::jsonb
-- );
