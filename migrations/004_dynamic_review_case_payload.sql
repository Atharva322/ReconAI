ALTER TABLE review_cases
ADD COLUMN IF NOT EXISTS case_payload jsonb;
