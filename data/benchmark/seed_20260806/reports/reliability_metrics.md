# Reliability Evaluation

- Valid: True
- Ingested documents: 3
- Duplicate uploads: 1
- Processing attempts: 7
- Recovered after retry: 1
- Failed documents: 1
- Audit events: 22

## Assertions

- Duplicate upload returned the original document record.
- Transient extractor failure recovered within retry budget.
- Permanent extractor failure remained failed after replay.
- Every state-changing operation produced audit events with correlation IDs.
