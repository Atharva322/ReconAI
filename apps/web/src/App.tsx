type FoundationCheck = {
  label: string;
  value: string;
};

const checks: FoundationCheck[] = [
  { label: "API", value: "FastAPI health endpoint" },
  { label: "DB", value: "PostgreSQL migrations and seed SQL" },
  { label: "Demo tenant", value: "Northstar Beverages" },
  { label: "Money", value: "Integer cents only" }
];

export function App() {
  return (
    <main className="app-shell">
      <section className="workspace">
        <div className="masthead">
          <p>ReconAI</p>
          <h1>Financial reconciliation workspace</h1>
        </div>

        <div className="status-grid" aria-label="Phase 1 foundation checks">
          {checks.map((check) => (
            <article className="status-card" key={check.label}>
              <span>{check.label}</span>
              <strong>{check.value}</strong>
            </article>
          ))}
        </div>
      </section>
    </main>
  );
}
