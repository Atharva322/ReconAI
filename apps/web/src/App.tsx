type ExtractedField = {
  document_type: string;
  field_name: string;
  value: string;
  confidence: number;
  source: string;
};

const extractedFields: ExtractedField[] = [
  {
    document_type: "invoice",
    field_name: "invoice_number",
    value: "NSB-INV-1001",
    confidence: 0.98,
    source: "northstar_invoice.pdf page 1"
  },
  {
    document_type: "invoice",
    field_name: "invoice_total",
    value: "$18,450.00",
    confidence: 0.98,
    source: "northstar_invoice.pdf page 1"
  },
  {
    document_type: "remittance",
    field_name: "payment_reference",
    value: "PAY-NORTHSTAR-0001",
    confidence: 0.98,
    source: "northstar_remittance.pdf page 1"
  },
  {
    document_type: "remittance",
    field_name: "payment_received",
    value: "$17,200.00",
    confidence: 0.98,
    source: "northstar_remittance.pdf page 1"
  }
];

const auditEvents = [
  ["09:00", "documents_processed", "Invoice and remittance fields extracted with provenance."],
  ["09:01", "reconciliation_completed", "$1,250 claimed, $1,000 validated, $250 unexplained."],
  ["09:02", "review_task_created", "Unexplained deduction routed to human review."]
];

const formatMoney = (cents: number) =>
  new Intl.NumberFormat("en-US", { style: "currency", currency: "USD" }).format(cents / 100);

export function App() {
  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p>ReconAI</p>
          <h1>Review workspace</h1>
        </div>
        <span className="sync-pill">Benchmark-backed demo</span>
      </header>

      <section className="workspace-grid">
        <aside className="queue-pane" aria-label="Review queue">
          <div className="pane-heading">
            <span>Review queue</span>
            <strong>1 open</strong>
          </div>
          <button className="queue-item queue-item-active">
            <span className="priority">High</span>
            <strong>Fictional Market Co.</strong>
            <small>NSB-INV-1001 · $250 unexplained</small>
          </button>
        </aside>

        <section className="case-pane" aria-label="Golden reconciliation case">
          <div className="case-header">
            <div>
              <p>Northstar Beverages</p>
              <h2>Promotion over-claim review</h2>
            </div>
            <span className="status-badge">REVIEW_REQUIRED</span>
          </div>

          <div className="summary-strip">
            <Metric label="Invoice" value={formatMoney(1845000)} />
            <Metric label="Payment" value={formatMoney(1720000)} />
            <Metric label="Claimed deduction" value={formatMoney(125000)} />
            <Metric label="Unexplained" value={formatMoney(25000)} tone="alert" />
          </div>

          <div className="detail-layout">
            <section className="evidence-panel">
              <h3>Extraction evidence</h3>
              <div className="field-table">
                {extractedFields.map((field) => (
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
                <LineItem label="Invoice total" value={1845000} />
                <LineItem label="Payment received" value={-1720000} />
                <LineItem label="Claimed deduction" value={125000} emphasized />
                <LineItem label="Authorized promotion" value={-100000} />
                <LineItem label="Unexplained over-claim" value={25000} alert />
              </div>
              <div className="rule-list" aria-label="Applied reconciliation rules">
                {["EXACT_INVOICE_REFERENCE", "AMOUNT_ARITHMETIC_EXACT", "PROMOTION_VALIDATED", "UNEXPLAINED_DEDUCTION_REVIEW"].map((rule) => (
                  <span key={rule}>{rule}</span>
                ))}
              </div>
            </section>
          </div>
        </section>

        <aside className="action-pane" aria-label="Review decision">
          <section>
            <h3>Decision</h3>
            <textarea defaultValue="Dispute the unexplained $250 over-claim." />
            <div className="action-row">
              <button className="secondary-button">Approve</button>
              <button className="primary-button">Dispute</button>
            </div>
          </section>

          <section>
            <h3>Audit timeline</h3>
            <ol className="timeline">
              {auditEvents.map(([time, action, detail]) => (
                <li key={action}>
                  <span>{time}</span>
                  <strong>{action}</strong>
                  <small>{detail}</small>
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
