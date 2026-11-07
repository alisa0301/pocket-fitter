import { useEffect, useRef, useState } from "react";
import { sendChat, type Message, type Recommendation } from "./api";
import { RecommendationCard } from "./RecommendationCard";
import SimilarCard from "./SimilarCard";

const GREETING: Message = {
  role: "assistant",
  content: "Hi, I'm your Pocket Fitter. I'll help you find clubs that fit your game. What brings you here?",
};
const RESET_WORDS = new Set(["start over"]);
const START_OPTIONS = ["I'm looking for new gear", "Just researching", "Comparing brands", "I'm new to golf"];

type Item = Message & { recommendation?: Recommendation };

export default function App() {
  const [messages, setMessages] = useState<Item[]>([GREETING]);
  const [suggestions, setSuggestions] = useState<string[]>(START_OPTIONS);
  const [step, setStep] = useState({ current: 0, total: 4 });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Id of this fitting in MongoDB (null when the backend runs without a database).
  const [fittingId, setFittingId] = useState<string | null>(null);
  const [demo, setDemo] = useState(() => new URLSearchParams(location.search).has("demo"));
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, suggestions]);

  function switchMode(nextDemo: boolean) {
    if (nextDemo === demo) return;
    setDemo(nextDemo);
    const url = new URL(location.href);
    if (nextDemo) url.searchParams.set("demo", "");
    else url.searchParams.delete("demo");
    history.replaceState(null, "", url);
    reset();
  }

  function reset() {
    setMessages([GREETING]);
    setSuggestions(START_OPTIONS);
    setStep({ current: 0, total: 4 });
    setInput("");
    setError("");
    setFittingId(null);
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    if (RESET_WORDS.has(content.toLowerCase())) return reset();
    const next: Item[] = [...messages, { role: "user", content }];
    setMessages(next);
    setSuggestions([]);
    setInput("");
    setError("");
    setLoading(true);
    try {
      // Greeting is UI-only; the backend sees the real conversation (recommendations as text).
      const res = await sendChat(next.slice(1).map(toBackendMessage), fittingId, demo);
      setMessages([
        ...next,
        { role: "assistant", content: res.reply, recommendation: res.recommendation ?? undefined },
      ]);
      setSuggestions(res.suggestions);
      setFittingId(res.fitting_id);
      setStep({ current: res.step, total: res.total_steps || 4 });
    } catch (e) {
      setError(`Couldn't get an answer from the fitter. ${e instanceof Error ? e.message : ""}`);
    } finally {
      setLoading(false);
    }
  }

  const done = step.current >= step.total;
  const progress = Math.max(4, (step.current / step.total) * 100);
  const stepLabel = String(Math.min(step.current + 1, step.total)).padStart(2, "0");

  return (
    <div className="page">
      <header className="topbar">
        <button className="brand" onClick={reset}>Pocket Fitter</button>
        <nav className="tabs" aria-label="Mode">
          <button className={!demo ? "tab on" : "tab"} onClick={() => switchMode(false)}>Live</button>
          <button className={demo ? "tab on" : "tab"} onClick={() => switchMode(true)}>Demo</button>
        </nav>
      </header>
      {demo && (
        <p className="demo-banner">
          Demo mode: scripted questions and rule-based picks on Takomo&apos;s data. No AI calls,
          nothing is saved.
        </p>
      )}

      <section className="panel" aria-label="Fitting assistant">
        <div className="panel-head">
          <p className="crumb">
            <span className="accent">Fitting assistant</span> / {done ? "Your fit" : `Step ${stepLabel}`}
          </p>
          <button className="icon-btn" onClick={reset} aria-label="Start over" title="Start over">✕</button>
        </div>
        <div className="progress">
          <div className="bar"><span style={{ width: `${progress}%` }} /></div>
          <span className={`check ${done ? "on" : ""}`} aria-hidden>✓</span>
        </div>

        <div className="messages">
          {messages.map((m, i) => (
            <div key={i} className={`msg ${m.role}`}>
              <div className="msg-body">
                <p className="bubble">{m.content}</p>
                {m.recommendation && <RecommendationCard rec={m.recommendation} />}
                {m.recommendation?.similar && <SimilarCard data={m.recommendation.similar} />}
              </div>
            </div>
          ))}
          {loading && (
            <div className="msg assistant">
              <p className="bubble typing"><span /><span /><span /></p>
            </div>
          )}
          {error && <p className="error">{error}</p>}
          {suggestions.length > 0 && !loading && (
            <div className="options">
              {suggestions.map((s) => (
                <button key={s} className="option" onClick={() => send(s)}>{s}</button>
              ))}
            </div>
          )}
          <div ref={endRef} />
        </div>

        <form
          className="composer"
          onSubmit={(e) => {
            e.preventDefault();
            send(input);
          }}
        >
          <input
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Type your answer or ask a question…"
            aria-label="Message"
          />
          <button type="submit" className="send" disabled={!input.trim() || loading}>
            Send <span aria-hidden>→</span>
          </button>
        </form>
      </section>
    </div>
  );
}

function toBackendMessage(m: Item): Message {
  if (!m.recommendation) return { role: m.role, content: m.content };
  const r = m.recommendation;
  const text =
    `${m.content}\n[Recommendation] Irons: ${r.iron_set.name}` +
    (r.runner_up ? ` (runner-up ${r.runner_up.name})` : "") +
    `. Shaft: ${r.shaft.name}. Grip: ${r.grip}. Length: ${r.length_in}in. Lie: ${r.lie_deg}deg. ` +
    `${r.purchase}. Reasons: ${r.reasons.join(" ")} Adjustments: ${r.adjustments.join(" ")}`;
  return { role: m.role, content: text };
}
