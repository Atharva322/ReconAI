INSERT INTO tenants (id, name)
VALUES ('00000000-0000-4000-8000-000000000001', 'Northstar Beverages')
ON CONFLICT (id) DO UPDATE SET name = EXCLUDED.name;

INSERT INTO audit_events (
  tenant_id,
  actor,
  action,
  entity_type,
  entity_id,
  after_json,
  correlation_id
)
VALUES (
  '00000000-0000-4000-8000-000000000001',
  'system',
  'seed_demo_tenant',
  'tenant',
  '00000000-0000-4000-8000-000000000001',
  '{"name": "Northstar Beverages"}'::jsonb,
  '00000000-0000-4000-8000-000000000101'
)
ON CONFLICT DO NOTHING;
