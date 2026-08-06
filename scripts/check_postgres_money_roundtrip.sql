CREATE TEMP TABLE phase0_money_roundtrip (
  id text PRIMARY KEY,
  amount_cents bigint NOT NULL CHECK (amount_cents >= 0)
);

INSERT INTO phase0_money_roundtrip (id, amount_cents)
VALUES
  ('zero', 0),
  ('cent', 1),
  ('golden_invoice', 1845000),
  ('large', 99999999999);

SELECT id, amount_cents
FROM phase0_money_roundtrip
ORDER BY id;
