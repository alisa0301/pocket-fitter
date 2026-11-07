import { useEffect, useRef, useState } from "react";
import { sendChat, type Message } from "./api";

const STARTERS = [
  { title: "Find my irons", text: "Answer a few questions and get an iron recommendation." },
  { title: "Wedge gapping", text: "Build lofts that cover every distance inside 100 m." },
  { title: "Driver fit", text: "Dial in loft and shaft for more carry." },
];

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send(text: string) {
    const content = text.trim();
    if (!content || loading) return;
    if (content === "Start over") return reset();
    const next: Message[] = [...messages, { role: "user", content }];
    setMessages(next);
    setSuggestions([]);
    setInput("");
    setError("");
    setLoading(true);
    try {
      const res = await sendChat(next);
      setMessages([...next, { role: "assistant", content: res.reply }]);
      setSuggestions(res.suggestions);
    } catch {
      setError("Couldn't reach the fitter. Is the backend running?");
    } finally {
      setLoading(false);
    }
  }

  function reset() {
    setMessages([]);
    setSuggestions([]);
    setInput("");
    setError("");
  }

  const empty = messages.length === 0;

  return (
    <div className="app">
      <header className="topbar">
        <button className="brand" onClick={reset}>Pocket Fitter</button>
        <span className="tag">Virtual club fitting</span>
      </header>

      <main className="thread">
        {empty ? (
          <section className="hero">
            <p className="eyebrow">Your personal fitter</p>
            <h1>Clubs that fit your game.</h1>
            <p className="lead">
              Tell us how you play. We'll guide you to the right setup in a couple of minutes.
            </p>
            <div className="starters">
              {STARTERS.map((s) => (
                <button key={s.title} className="card" onClick={() => send(s.title)}>
                  <span className="card-title">{s.title}</span>
                  <span className="card-text">{s.text}</span>
                  <span className="arrow" aria-hidden>→</span>
                </button>
              ))}
            </div>
          </section>
        ) : (
          <div className="messages">
            {messages.map((m, i) => (
              <div key={i} className={`msg ${m.role}`}>
                {m.role === "assistant" && <span className="avatar" aria-hidden>PF</span>}
                <p className="bubble">{m.content}</p>
              </div>
            ))}
            {loading && (
              <div className="msg assistant">
                <span className="avatar" aria-hidden>PF</span>
                <p className="bubble typing"><span /><span /><span /></p>
              </div>
            )}
            {error && <p className="error">{error}</p>}
            {suggestions.length > 0 && !loading && (
              <div className="chips">
                {suggestions.map((s) => (
                  <button key={s} className="chip" onClick={() => send(s)}>{s}</button>
                ))}
              </div>
            )}
            <div ref={endRef} />
          </div>
        )}
      </main>

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
          placeholder="Ask about irons, wedges, shafts…"
          aria-label="Message"
        />
        <button type="submit" disabled={!input.trim() || loading}>Send</button>
      </form>
    </div>
  );
}
