import type { ClubComparison, Recommendation } from "./api";

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

      {rec.iron_set.image_url && (
        <a className="rec-photo" href={rec.iron_set.url ?? undefined} target="_blank" rel="noreferrer">
          <img src={`${rec.iron_set.image_url}?width=900`} alt={rec.iron_set.name} loading="lazy" />
        </a>
      )}

      <div className="rec-grid">
        <section>
          <p className="rec-label">Irons</p>
          <h3>{rec.iron_set.name}</h3>
          {rec.iron_set.price_eur != null && (
            <p className="rec-price">€{rec.iron_set.price_eur.toFixed(0)}</p>
          )}
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
      {rec.comparison && <Comparison c={rec.comparison} />}
      {rec.iron_set.url && (
        <a className="rec-cta" href={rec.iron_set.url} target="_blank" rel="noreferrer">
          View {rec.iron_set.name} <span aria-hidden>→</span>
        </a>
      )}
    </article>
  );
}

const SOURCE: Record<string, string> = { you: "your spec", estimate: "estimated", default: "assumed" };

function Comparison({ c }: { c: ClubComparison }) {
  const fmt = (v: number) => (Number.isInteger(v) ? v : v.toFixed(1));
  return (
    <section className="cmp">
      <p className="rec-label">Your clubs vs {c.takomo.label}</p>
      <div className="cmp-heads">
        <div>
          <span className="cmp-name">{c.current.label}</span>
          <span className="cmp-spec">
            7i {c.current.loft_deg}° ({SOURCE[c.current.loft_source]}) · forgiveness {c.current.forgiveness}/5
          </span>
        </div>
        <div className="cmp-vs" aria-hidden>vs</div>
        <div>
          <span className="cmp-name accent">{c.takomo.label}</span>
          <span className="cmp-spec">7i {c.takomo.loft_deg}° · forgiveness {c.takomo.forgiveness}/5</span>
        </div>
      </div>

      {c.highlights.length > 0 && (
        <ul className="cmp-highlights">{c.highlights.map((h) => <li key={h}>{h}</li>)}</ul>
      )}

      <table className="cmp-table">
        <thead>
          <tr><th />{/* metric */}<th>Now</th><th>Takomo</th><th>Change</th></tr>
        </thead>
        <tbody>
          {c.metrics.map((m) => (
            <tr key={m.name} className={m.better}>
              <th scope="row">{m.name}</th>
              <td>{fmt(m.current)} {m.unit}</td>
              <td>{fmt(m.takomo)} {m.unit}</td>
              <td className="cmp-diff">
                {m.better === "same" ? "≈" : `${m.difference > 0 ? "+" : ""}${fmt(m.difference)} ${m.unit}`}
              </td>
            </tr>
          ))}
        </tbody>
      </table>

      <details className="cmp-how">
        <summary>How we compared</summary>
        <p>
          Both clubs hit the same {c.swing_speed_mph} mph swing with your typical strike pattern in a
          calibrated ball-flight model. These are model estimates, not launch-monitor results.
        </p>
        <ul>{c.assumptions.map((a) => <li key={a}>{a}</li>)}</ul>
      </details>
    </section>
  );
}
