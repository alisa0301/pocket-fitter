import { useEffect, useRef, useState } from "react";
import { sendChat, type Message, type SimilarGolfers } from "./api";
import SimilarCard from "./SimilarCard";

const GREETING: Message = {
  role: "assistant",
  content: "Hi, I'm your Pocket Fitter. I'll help you find clubs that fit your game. What brings you here?",
};
const RESET_WORDS = new Set(["start over"]);
const START_OPTIONS = ["I'm looking for new gear", "Just researching", "Comparing brands", "I'm new to golf"];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([GREETING]);
  const [suggestions, setSuggestions] = useState<string[]>(START_OPTIONS);
  const [step, setStep] = useState({ current: 0, total: 4 });
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  // Id of this fitting in MongoDB (null when the backend runs without a database).
  const [fittingId, setFittingId] = useState<string | null>(null);
  // "Golfers like you" stats, attached to the message index that carried the recommendation.
  const [similar, setSimilar] = useState<{ at: number; data: SimilarGolfers } | null>(null);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, loading, suggestions]);

  function reset() {
    setMessages([GREETING]);
    setSuggestions(START_OPTIONS);
    setStep({ current: 0, total: 4 });
    setInput("");
    setError("");
    setFittingId(null);
    setSimilar(null);
  }

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    if (RESET_WORDS.has(content.toLowerCase())) return reset();
    const next: Message[] = [...messages, { role: "user", content }];
    setMessages(next);
    setSuggestions([]);
    setInput("");
    setError("");
    setLoading(true);
    try {
      // Greeting is UI-only; the backend sees the real conversation.
      const res = await sendChat(next.slice(1), fittingId, similar !== null);
      setMessages([...next, { role: "assistant", content: res.reply }]);
      setSuggestions(res.suggestions);
      setFittingId(res.fitting_id);
      if (res.similar) setSimilar({ at: next.length, data: res.similar });
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
        <span className="nav">Virtual club fitting</span>
      </header>

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
              <p className="bubble">{m.content}</p>
              {similar?.at === i && <SimilarCard data={similar.data} />}
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
