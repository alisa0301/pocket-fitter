export type Role = "user" | "assistant";
export interface Message {
  role: Role;
  content: string;
}
export interface SpecShare {
  value: string;
  share: number;
  label?: string | null;
}
export interface SimilarGolfers {
  count: number;
  source: "atlas_vector_search" | "in_memory";
  head: SpecShare[];
  shaft: SpecShare[];
  flex: SpecShare[];
  material: SpecShare[];
  length_in: SpecShare[];
  lie_deg: SpecShare[];
  grip: SpecShare[];
  purchase: SpecShare[];
  expected_carry_yd: number | null;
}
export interface ChatResponse {
  reply: string;
  suggestions: string[];
  step: number;
  total_steps: number;
  fitting_id: string | null;
  similar: SimilarGolfers | null;
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

export const sendChat = (messages: Message[], fittingId: string | null, recommended: boolean) =>
  api<ChatResponse>("/chat", {
    method: "POST",
    body: JSON.stringify({ messages, fitting_id: fittingId, recommended }),
  });
