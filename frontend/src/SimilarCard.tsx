import type { SimilarGolfers, SpecShare } from "./api";

const pct = (s: SpecShare) => `${Math.round(s.share * 100)}%`;
const signed = (v: string, unit: string) => {
  const n = Number(v);
  return n === 0 ? "standard" : `${n > 0 ? "+" : ""}${n}${unit}`;
};

/** What fitted the most similar golfers in Takomo's data. */
export default function SimilarCard({ data }: { data: SimilarGolfers }) {
  const top = (list: SpecShare[], fmt: (v: string) => string = (v) => v) =>
    list[0] ? `${list[0].label ?? fmt(list[0].value)} · ${pct(list[0])}` : "–";
  const facts: [string, string][] = [
    ["Shaft", top(data.shaft)],
    ["Flex", top(data.flex)],
    ["Grip", top(data.grip)],
    ["Length", top(data.length_in, (v) => signed(v, "″"))],
    ["Lie", top(data.lie_deg, (v) => signed(v, "°"))],
  ];
  return (
    <aside className="similar" aria-label="Golfers like you">
      <p className="similar-title">
        <span className="accent">Golfers like you</span> · {data.count} closest matches in Takomo's fitting data
      </p>
      <ul className="similar-heads">
        {data.head.map((h) => (
          <li key={h.value}>
            <span className="name">{h.label ?? h.value}</span>
            <span className="meter"><span style={{ width: pct(h) }} /></span>
            <span className="num">{pct(h)}</span>
          </li>
        ))}
      </ul>
      <dl className="similar-facts">
        {facts.map(([k, v]) => (
          <div key={k}><dt>{k}</dt><dd>{v}</dd></div>
        ))}
        {data.expected_carry_yd && (
          <div><dt>7-iron carry</dt><dd>≈ {Math.round(data.expected_carry_yd)} yd</dd></div>
        )}
      </dl>
      {data.source === "atlas_vector_search" && <p className="similar-src">MongoDB Atlas Vector Search</p>}
    </aside>
  );
}
