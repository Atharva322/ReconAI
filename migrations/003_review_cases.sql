CREATE TABLE IF NOT EXISTS review_cases (
  id text PRIMARY KEY,
  tenant_id uuid NOT NULL REFERENCES tenants(id),
  status text NOT NULL CHECK (status IN ('REVIEW_REQUIRED', 'APPROVED', 'DISPUTED')),
  decision text CHECK (decision IN ('approve', 'dispute')),
  comment text,
  actor text,
  decided_at timestamptz,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CHECK (
    (status = 'REVIEW_REQUIRED' AND decision IS NULL AND comment IS NULL AND actor IS NULL AND decided_at IS NULL)
    OR
    (status IN ('APPROVED', 'DISPUTED') AND decision IS NOT NULL AND comment IS NOT NULL AND actor IS NOT NULL AND decided_at IS NOT NULL)
  )
);

INSERT INTO review_cases (id, tenant_id, status)
VALUES ('review-golden-001', '00000000-0000-4000-8000-000000000001', 'REVIEW_REQUIRED')
ON CONFLICT (id) DO NOTHING;
