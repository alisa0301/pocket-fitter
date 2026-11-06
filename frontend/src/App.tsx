import { useEffect, useState } from "react";
import { api } from "./api";

export default function App() {
  const [status, setStatus] = useState("checking…");
  const [message, setMessage] = useState("");
  const [reply, setReply] = useState("");

  useEffect(() => {
    api<{ status: string }>("/health")
      .then((d) => setStatus(d.status))
      .catch(() => setStatus("offline"));
  }, []);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    const d = await api<{ reply: string }>("/echo", {
      method: "POST",
      body: JSON.stringify({ message }),
    });
    setReply(d.reply);
  }

  return (
    <main>
      <h1>Pocket Fitter</h1>
      <p>Backend: <b>{status}</b></p>
      <form onSubmit={send}>
        <input value={message} onChange={(e) => setMessage(e.target.value)} placeholder="Type something" />
        <button type="submit" disabled={!message}>Send</button>
      </form>
      {reply && <p>{reply}</p>}
    </main>
  );
}
