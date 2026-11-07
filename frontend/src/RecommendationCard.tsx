import type { Recommendation } from "./api";

const signed = (n: number, unit: string, up: string, down: string) =>
  n === 0 ? "Standard" : `${Math.abs(n)}${unit} ${n > 0 ? up : down}`;

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const pct = Math.round(rec.confidence * 100);
  const spec: [string, string][] = [
    ["Grip", rec.grip.charAt(0).toUpperCase() + rec.grip.slice(1)],
    ["Length", signed(rec.length_in, "″", "longer", "shorter")],
    ["Lie", signed(rec.lie_deg, "°", "upright", "flat")],
    ["Build", rec.purchase === "stock" ? "Stock" : "Custom"],
  ];
  if (rec.runner_up) spec.push(["Runner-up", rec.runner_up.name]);
  if (rec.set_makeup) spec.push(["Set makeup", rec.set_makeup]);
  return (
    <article className="rec">
      <header className="rec-head">
        <span className="rec-eyebrow">Your fit</span>
        <span className="rec-engine" title="Decision engine">{rec.engine}</span>
      </header>

      <div className="rec-grid">
        <section>
          <p className="rec-label">Irons</p>
          <h3>{rec.iron_set.name}</h3>
          <p className="rec-desc">{rec.iron_set.description}</p>
        </section>
        <section>
          <p className="rec-label">Shaft</p>
          <h3>{rec.shaft.name}</h3>
          <p className="rec-desc">{rec.shaft.description}</p>
        </section>
      </div>

      <dl className="rec-meta">
        {spec.map(([k, v]) => (
          <div key={k}>
            <dt>{k}</dt>
            <dd>{v}</dd>
          </div>
        ))}
        <div>
          <dt>Match confidence</dt>
          <dd className="rec-conf">
            <span className="rec-bar"><span style={{ width: `${pct}%` }} /></span>
            {pct}%
          </dd>
        </div>
      </dl>

      {rec.reasons.length > 0 && (
        <>
          <p className="rec-label">Why</p>
          <ul className="rec-list">{rec.reasons.map((r) => <li key={r}>{r}</li>)}</ul>
        </>
      )}
      {rec.adjustments.length > 0 && (
        <>
          <p className="rec-label">Adjustments</p>
          <ul className="rec-list muted">{rec.adjustments.map((a) => <li key={a}>{a}</li>)}</ul>
        </>
      )}
    </article>
  );
}
