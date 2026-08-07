import { useEffect, useState } from "react";
import { getGoldenReviewCase, submitReviewDecision } from "./api/reconai";
import type { AuditEvent, ReviewCase } from "./types/review";

const formatMoney = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

export function App() {
  const [reviewCase, setReviewCase] = useState<ReviewCase | null>(null);
  const [comment, setComment] = useState("Dispute the unexplained over-claim.");
  const [isLoading, setIsLoading] = useState(true);
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

  async function handleDecision(decision: "approve" | "dispute") {
    if (!comment.trim() || reviewCase?.status !== "REVIEW_REQUIRED") {
      return;
    }

    setIsSubmitting(true);
    setError(null);
    try {
      setReviewCase(await submitReviewDecision(decision, comment.trim()));
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p>ReconAI</p>
          <h1>Review workspace</h1>
        </div>
        <span className="sync-pill">API-backed demo</span>
      </header>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="workspace-grid">
        <aside className="queue-pane" aria-label="Review queue">
          <div className="pane-heading">
            <span>Review queue</span>
            <strong>{reviewCase.status === "REVIEW_REQUIRED" ? "1 open" : "0 open"}</strong>
          </div>
          <button className="queue-item queue-item-active">
            <span className="priority">{reviewCase.priority}</span>
            <strong>{reviewCase.retailer}</strong>
            <small>{reviewCase.invoice.invoice_number} · {formatMoney(reviewCase.deduction.unexplained_cents)} unexplained</small>
          </button>
        </aside>

        <section className="case-pane" aria-label="Golden reconciliation case">
          <div className="case-header">
            <div>
              <p>{reviewCase.tenant}</p>
              <h2>Promotion over-claim review</h2>
            </div>
            <span className={`status-badge status-${reviewCase.status.toLowerCase()}`}>{reviewCase.status}</span>
          </div>

          <div className="summary-strip">
            <Metric label="Invoice" value={formatMoney(reviewCase.invoice.total_cents)} />
            <Metric label="Payment" value={formatMoney(reviewCase.payment.received_cents)} />
            <Metric label="Claimed deduction" value={formatMoney(reviewCase.deduction.claimed_cents)} />
            <Metric label="Unexplained" value={formatMoney(reviewCase.deduction.unexplained_cents)} tone="alert" />
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
                    <small>{Math.round(field.confidence * 100)}% · {field.source}</small>
                  </div>
                ))}
              </div>
            </section>

            <section className="recon-panel">
              <h3>Reconciliation</h3>
              <div className="math-stack">
                <LineItem label="Invoice total" value={reviewCase.invoice.total_cents} />
                <LineItem label="Payment received" value={-reviewCase.payment.received_cents} />
                <LineItem label="Claimed deduction" value={reviewCase.deduction.claimed_cents} emphasized />
                <LineItem label="Authorized promotion" value={-reviewCase.promotion.authorized_cents} />
                <LineItem label="Unexplained over-claim" value={reviewCase.deduction.unexplained_cents} alert />
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
