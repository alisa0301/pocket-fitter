export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  content: string;
}
export interface ChatResponse {
  reply: string;
  suggestions: string[];
  step: number;
  total_steps: number;
  fitting_id: string | null;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail ?? `${res.status} ${res.statusText}`);
  }
  return res.json() as Promise<T>;
}

export const sendChat = (messages: Message[], fittingId: string | null) =>
  api<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ messages, fitting_id: fittingId }),
  });
