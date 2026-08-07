export type ReviewStatus = "REVIEW_REQUIRED" | "APPROVED" | "DISPUTED";

export type Invoice = {
  invoice_number: string;
  po_number: string;
  issue_date: string;
  total_cents: number;
};

export type Payment = {
  payment_reference: string;
  payment_date: string;
  received_cents: number;
};

export type Deduction = {
  claimed_cents: number;
  validated_cents: number;
  unexplained_cents: number;
  reason_code: string;
};

export type Promotion = {
  promotion_code: string;
  authorized_cents: number;
  validity: string;
};

export type ExtractedField = {
  document_type: string;
  field_name: string;
  value: string;
  confidence: number;
  source: string;
};

export type AuditEvent = {
  timestamp: string;
  actor: string;
  action: string;
  details: string;
};

export type ReviewDecision = {
  decision: "approve" | "dispute";
  comment: string;
  actor: string;
};

export type ReviewCase = {
  case_id: string;
  tenant: string;
  retailer: string;
  status: ReviewStatus;
  priority: string;
  assignee: string;
  invoice: Invoice;
  payment: Payment;
  deduction: Deduction;
  promotion: Promotion;
  extracted_fields: ExtractedField[];
  rule_codes: string[];
  review_reason: string;
  audit_events: AuditEvent[];
  review_decision?: ReviewDecision;
};

export type ReviewDecisionRequest = {
  decision: "approve" | "dispute";
  comment: string;
};
