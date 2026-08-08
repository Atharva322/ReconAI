import { useEffect, useState } from "react";
import {
  getGoldenReviewCase,
  getReviewCase,
  processReviewDocuments,
  processSampleDocuments,
  submitReviewDecision
} from "./api/reconai";
import type { AuditEvent, ReviewCase } from "./types/review";

const formatMoney = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

export function App() {
  const [reviewCase, setReviewCase] = useState<ReviewCase | null>(null);
  const [comment, setComment] = useState("Dispute the unexplained over-claim.");
  const [invoiceFile, setInvoiceFile] = useState<File | null>(null);
  const [remittanceFile, setRemittanceFile] = useState<File | null>(null);
  const [promotionFile, setPromotionFile] = useState<File | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    void loadCase();
  }, []);

  async function loadCase() {
    setIsLoading(true);
    setError(null);
    try {
      setReviewCase(await getGoldenReviewCase());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to load review case.");
    } finally {
      setIsLoading(false);
    }
  }

  async function reloadCurrentCase() {
    if (!reviewCase) {
      await loadCase();
      return;
    }

    setIsLoading(true);
    setError(null);
    try {
      setReviewCase(await getReviewCase(reviewCase.case_id));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to reload review case.");
    } finally {
      setIsLoading(false);
    }
  }

  async function handleProcessDocuments(useSample = false) {
    if (!useSample && (!invoiceFile || !remittanceFile)) {
      setError("Choose both an invoice PDF and a remittance PDF.");
      return;
    }

    setIsProcessing(true);
    setError(null);
    try {
      const processed = useSample
        ? await processSampleDocuments()
        : await processReviewDocuments(invoiceFile as File, remittanceFile as File, promotionFile);
      setReviewCase(processed);
      setComment(getDefaultDecisionComment(processed));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to process submitted documents.");
    } finally {
      setIsProcessing(false);
    }
  }

  async function handleDecision(decision: "approve" | "dispute") {
    if (!comment.trim() || reviewCase?.status !== "REVIEW_REQUIRED") {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      setReviewCase(await submitReviewDecision(reviewCase.case_id, decision, comment.trim()));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Unable to submit review decision.");
    } finally {
      setIsSubmitting(false);
    }
  }

  if (isLoading) {
    return (
      <main className="app-shell">
        <section className="empty-state">Loading review case...</section>
      </main>
    );
  }

  if (!reviewCase) {
    return (
      <main className="app-shell">
        <section className="empty-state">
          <strong>Review case unavailable</strong>
          <span>{error}</span>
          <button className="secondary-button" onClick={loadCase}>Retry</button>
        </section>
      </main>
    );
  }

  const canDecide = reviewCase.status === "REVIEW_REQUIRED" && !isSubmitting && comment.trim().length >= 3;
  const canProcess = !isProcessing && Boolean(invoiceFile && remittanceFile);

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p>ReconAI</p>
          <h1>Review workspace</h1>
        </div>
        <span className="sync-pill">PDF extraction demo</span>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="processing-panel" aria-label="Document processing">
        <div>
          <h2>Process reconciliation PDFs</h2>
          <p>Digital PDF text extraction feeds deterministic reconciliation and the PostgreSQL-backed review workflow.</p>
        </div>
        <label>
          <span>Invoice PDF</span>
          <input type="file" accept="application/pdf,.pdf" onChange={(event) => setInvoiceFile(event.target.files?.[0] ?? null)} />
        </label>
        <label>
          <span>Remittance PDF</span>
          <input type="file" accept="application/pdf,.pdf" onChange={(event) => setRemittanceFile(event.target.files?.[0] ?? null)} />
        </label>
        <label>
          <span>Promotion PDF optional</span>
          <input type="file" accept="application/pdf,.pdf" onChange={(event) => setPromotionFile(event.target.files?.[0] ?? null)} />
        </label>
        <div className="processing-actions">
          <button className="secondary-button" disabled={isProcessing} onClick={() => void handleProcessDocuments(true)}>
            Use sample documents
          </button>
          <button className="primary-button" disabled={!canProcess} onClick={() => void handleProcessDocuments()}>
            {isProcessing ? "Extracting..." : "Process documents"}
          </button>
          <button className="secondary-button" disabled={isLoading} onClick={() => void reloadCurrentCase()}>
            Reload case
          </button>
        </div>
      </section>

      <section className="workspace-grid">
        <aside className="queue-pane" aria-label="Review queue">
          <div className="pane-heading">
            <span>Review queue</span>
            <strong>{reviewCase.status === "REVIEW_REQUIRED" ? "1 open" : "0 open"}</strong>
          </div>
          <button className="queue-item queue-item-active">
            <span className="priority">{reviewCase.priority}</span>
            <strong>{reviewCase.retailer}</strong>
            <small>{reviewCase.invoice.invoice_number} - {formatMoney(reviewCase.deduction.unexplained_cents)} unexplained</small>
          </button>
        </aside>

        <section className="case-pane" aria-label="Reconciliation case">
          <div className="case-header">
            <div>
              <p>{reviewCase.tenant}</p>
              <h2>{getReviewTitle(reviewCase)}</h2>
            </div>
            <span className={`status-badge status-${reviewCase.status.toLowerCase()}`}>{reviewCase.status}</span>
          </div>

          <div className="summary-strip">
            <Metric label="Invoice" value={formatMoney(reviewCase.invoice.total_cents)} />
            <Metric label="Payment" value={formatMoney(reviewCase.payment.received_cents)} />
            <Metric label={getClaimMetricLabel(reviewCase)} value={formatMoney(getClaimMetricValue(reviewCase))} />
            <Metric label={getAlertMetricLabel(reviewCase)} value={formatMoney(getAlertMetricValue(reviewCase))} tone="alert" />
          </div>

          <div className="detail-layout">
            <section className="evidence-panel">
              <h3>Extraction evidence</h3>
              <div className="field-table">
                {reviewCase.extracted_fields.map((field) => (
                  <div className="field-row" key={`${field.document_type}-${field.field_name}`}>
                    <span className="document-chip">{field.document_type}</span>
                    <div className="field-name">{field.field_name}</div>
                    <div className="field-value">{field.value}</div>
                    <small>{Math.round(field.confidence * 100)}% - {field.source}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="recon-panel">
              <h3>Reconciliation</h3>
              <div className="math-stack">
                <LineItem label="Invoice total" value={reviewCase.invoice.total_cents} />
                <LineItem label="Payment received" value={-reviewCase.payment.received_cents} />
                <LineItem label={getClaimMetricLabel(reviewCase)} value={getClaimMetricValue(reviewCase)} emphasized />
                <LineItem label="Authorized promotion" value={-reviewCase.promotion.authorized_cents} />
                <LineItem label={getAlertMetricLabel(reviewCase)} value={getAlertMetricValue(reviewCase)} alert />
              </div>
              <div className="rule-list" aria-label="Applied reconciliation rules">
                {reviewCase.rule_codes.map((rule) => (
                  <span key={rule}>{rule}</span>
                ))}
              </div>
            </section>
          </div>
        </section>

        <aside className="action-pane" aria-label="Review decision">
          <section>
            <h3>Decision</h3>
            <textarea value={comment} onChange={(event) => setComment(event.target.value)} disabled={isSubmitting} />
            {reviewCase.review_decision ? (
              <div className="decision-note">
                <strong>{reviewCase.review_decision.decision}</strong>
                <span>{reviewCase.review_decision.comment}</span>
              </div>
            ) : null}
            <div className="action-row">
              <button className="secondary-button" disabled={!canDecide} onClick={() => void handleDecision("approve")}>
                Approve
              </button>
              <button className="primary-button" disabled={!canDecide} onClick={() => void handleDecision("dispute")}>
                {isSubmitting ? "Saving..." : "Dispute"}
              </button>
            </div>
          </section>

          <section>
            <h3>Audit timeline</h3>
            <ol className="timeline">
              {reviewCase.audit_events.map((event) => (
                <li key={`${event.timestamp}-${event.action}-${event.details}`}>
                  <span>{formatAuditTime(event)}</span>
                  <strong>{event.action}</strong>
                  <small>{event.details}</small>
                </li>
              ))}
            </ol>
          </section>
        </aside>
      </section>
    </main>
  );
}

function Metric({ label, value, tone }: { label: string; value: string; tone?: "alert" }) {
  return (
    <article className={tone === "alert" ? "metric metric-alert" : "metric"}>
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function getReviewTitle(reviewCase: ReviewCase): string {
  if (reviewCase.review_reason === "partial_payment_open_balance") {
    return "Partial payment review";
  }
  if (reviewCase.review_reason === "unexplained_deduction_amount" && reviewCase.promotion.authorized_cents > 0) {
    return "Promotion over-claim review";
  }
  if (reviewCase.review_reason === "unauthorized_deduction") {
    return "Unauthorized deduction review";
  }
  if (reviewCase.review_reason === "unexplained_deduction_amount") {
    return "Unexplained deduction review";
  }
  if (["invoice_reference_conflict", "unknown_invoice_reference"].includes(reviewCase.review_reason)) {
    return "Invoice reference review";
  }
  if (reviewCase.review_reason.includes("no text") || reviewCase.review_reason.includes("insufficient")) {
    return "Insufficient evidence review";
  }
  return "Reconciliation exception review";
}

function getDefaultDecisionComment(reviewCase: ReviewCase): string {
  if (reviewCase.review_reason === "partial_payment_open_balance") {
    return "Review the remaining open balance before applying the payment.";
  }
  if (reviewCase.review_reason === "unexplained_deduction_amount" && reviewCase.promotion.authorized_cents > 0) {
    return "Dispute the unsupported portion of the promotional deduction.";
  }
  if (reviewCase.review_reason === "unauthorized_deduction") {
    return "Dispute the unsupported customer deduction.";
  }
  if (["invoice_reference_conflict", "unknown_invoice_reference"].includes(reviewCase.review_reason)) {
    return "Review the invoice reference mismatch before applying the payment.";
  }
  return "Review the reconciliation exception before applying the payment.";
}

function getClaimMetricLabel(reviewCase: ReviewCase): string {
  return reviewCase.review_reason === "partial_payment_open_balance" ? "Open balance" : "Claimed deduction";
}

function getClaimMetricValue(reviewCase: ReviewCase): number {
  return reviewCase.review_reason === "partial_payment_open_balance"
    ? reviewCase.deduction.open_balance_cents ?? reviewCase.invoice.total_cents - reviewCase.payment.received_cents
    : reviewCase.deduction.claimed_cents;
}

function getAlertMetricLabel(reviewCase: ReviewCase): string {
  return reviewCase.review_reason === "partial_payment_open_balance" ? "Open amount" : "Unexplained";
}

function getAlertMetricValue(reviewCase: ReviewCase): number {
  return reviewCase.review_reason === "partial_payment_open_balance"
    ? reviewCase.deduction.open_balance_cents ?? reviewCase.invoice.total_cents - reviewCase.payment.received_cents
    : reviewCase.deduction.unexplained_cents;
}

function LineItem({
  label,
  value,
  emphasized,
  alert
}: {
  label: string;
  value: number;
  emphasized?: boolean;
  alert?: boolean;
}) {
  const className = ["line-item", emphasized ? "line-emphasis" : "", alert ? "line-alert" : ""]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <span>{label}</span>
      <strong>{formatMoney(value)}</strong>
    </div>
  );
}

function formatAuditTime(event: AuditEvent) {
  const date = new Date(event.timestamp);
  if (Number.isNaN(date.getTime())) {
    return event.timestamp;
  }
  return date.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit", hour12: false });
}
