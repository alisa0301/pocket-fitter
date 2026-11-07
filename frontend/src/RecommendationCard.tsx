import type { Recommendation } from "./api";

export function RecommendationCard({ rec }: { rec: Recommendation }) {
  const pct = Math.round(rec.confidence * 100);
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
        <div>
          <dt>Set makeup</dt>
          <dd>{rec.set_makeup}</dd>
        </div>
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
