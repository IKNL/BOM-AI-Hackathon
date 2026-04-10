// frontend/lib/types.ts

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
  id?: string;
  sourceCards?: SourceCard[];
  chartData?: ChartData[];
}

export interface SourceCard {
  source: string;
  url: string;
  reliability: string;
  contributed: boolean;
}

export interface ChartData {
  type: "line" | "bar" | "value";
  title: string;
  data: Record<string, unknown>[];
  xKey: string;
  yKey: string;
  unit?: string;
}

export type UserProfile = "patient" | "professional" | "policymaker";

export interface ChatRequest {
  message: string;
  session_id: string;
  profile: UserProfile;
  history: Pick<ChatMessage, "role" | "content">[];
}

export interface SSEEvent {
  event: "token" | "source_card" | "chart_data" | "done" | "error";
  data: Record<string, unknown>;
}

export interface DoneEventData {
  message_id: string;
  sources_tried: string[];
}

export interface ErrorEventData {
  code: string;
  message: string;
}

export interface FeedbackRequest {
  session_id: string;
  message_id: string;
  rating: "positive" | "negative";
  comment?: string;
  query: string;
  sources_tried: string[];
}
