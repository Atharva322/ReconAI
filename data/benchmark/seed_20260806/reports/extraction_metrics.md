# Extraction Evaluation

- Scenarios: 12
- Fields scored: 72
- Matched fields: 66
- Field exact match rate: 0.917
- Documents requiring review: 2

## Status Counts

- `invoice:EXTRACTED`: 11
- `invoice:INSUFFICIENT_EVIDENCE`: 1
- `remittance:EXTRACTED`: 11
- `remittance:INSUFFICIENT_EVIDENCE`: 1

## Misses

### s11_9662
- `invoice.invoice_number` expected `NSB-INV-9662`, got `None`
- `invoice.invoice_total` expected `2500.00`, got `None`
- `remittance.payment_reference` expected `PAY-NSB-9662`, got `None`
- `remittance.invoice_number` expected `NSB-INV-9662`, got `None`
- `remittance.payment_received` expected `2500.00`, got `None`
- `remittance.authorized_promotion` expected `0.00`, got `None`
