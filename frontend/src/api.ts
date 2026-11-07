export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  content: string;
}
export interface ChatResponse {
  reply: string;
  suggestions: string[];
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText}`);
  return res.json() as Promise<T>;
}

export const sendChat = (messages: Message[]) =>
  api<ChatResponse>("/chat", { method: "POST", body: JSON.stringify({ messages }) });
