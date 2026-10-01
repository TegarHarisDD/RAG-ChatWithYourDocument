export interface Session {
  id: string;
  title: string;
  created_at: string;
  last_active_at: string;
  document_count: number;
  chat_id: string | null;
}

export interface Chat {
  id: string;
  session_id: string;
  title: string;
  created_at: string;
  last_active_at: string;
}

export interface Document {
  id: string;
  session_id: string;
  filename: string;
  content_type: string;
  size_bytes: number;
  status: "pending" | "processing" | "ready" | "failed";
  error: string | null;
  chunk_count: number;
  embedding_model: string | null;
  created_at: string;
  updated_at: string;
}

export interface Citation {
  index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  locator: Record<string, string | null>;
  snippet: string;
}

export interface Source {
  index: number;
  chunk_id: string;
  document_id: string;
  filename: string;
  chunk_index: number;
  locator: Record<string, string | null>;
  snippet: string;
}

export interface Chunk {
  id: string;
  session_id: string;
  document_id: string;
  filename: string | null;
  chunk_index: number;
  text: string;
  locator: Record<string, string | null>;
}

export interface Message {
  id: string;
  chat_id: string;
  session_id: string;
  role: "user" | "assistant";
  content: string;
  citations: Citation[];
  created_at: string;
  model: string | null;
  finish_reason: string | null;
}

export interface AuthUser {
  username: string;
}

export interface AuthStatus {
  setup_required: boolean;
}

export interface MessageSearchResult {
  message_id: string;
  chat_id: string;
  session_id: string;
  session_title: string;
  role: "user" | "assistant";
  snippet: string;
}

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (res.status === 204) {
    return undefined as T;
  }

  const text = await res.text();
  const body = text ? JSON.parse(text) : null;

  if (!res.ok) {
    const detail = body && typeof body.detail === "string" ? body.detail : res.statusText;
    throw new ApiError(res.status, detail);
  }
  return body as T;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(path, {
    credentials: "same-origin",
    headers: { "Content-Type": "application/json", ...(init?.headers ?? {}) },
    ...init,
  });
  return handle<T>(res);
}

async function upload<T>(path: string, body: FormData): Promise<T> {
  const res = await fetch(path, { method: "POST", credentials: "same-origin", body });
  return handle<T>(res);
}

export const api = {
  me: () => request<AuthUser>("/api/auth/me"),
  status: () => request<AuthStatus>("/api/auth/status"),
  setup: (username: string, password: string) =>
    request<AuthUser>("/api/auth/setup", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  login: (username: string, password: string) =>
    request<AuthUser>("/api/auth/login", {
      method: "POST",
      body: JSON.stringify({ username, password }),
    }),
  logout: () => request<void>("/api/auth/logout", { method: "POST" }),

  listSessions: () => request<Session[]>("/api/sessions"),
  createSession: (title?: string) =>
    request<Session>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
    }),
  getSession: (id: string) => request<Session>(`/api/sessions/${id}`),
  renameSession: (id: string, title: string) =>
    request<Session>(`/api/sessions/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteSession: (id: string) => request<void>(`/api/sessions/${id}`, { method: "DELETE" }),

  listChats: (sessionId: string) => request<Chat[]>(`/api/sessions/${sessionId}/chats`),
  createChat: (sessionId: string, title?: string) =>
    request<Chat>(`/api/sessions/${sessionId}/chats`, {
      method: "POST",
      body: JSON.stringify({ title: title ?? null }),
    }),
  getChat: (id: string) => request<Chat>(`/api/chats/${id}`),
  renameChat: (id: string, title: string) =>
    request<Chat>(`/api/chats/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ title }),
    }),
  deleteChat: (id: string) => request<void>(`/api/chats/${id}`, { method: "DELETE" }),
  listMessages: (chatId: string) => request<Message[]>(`/api/chats/${chatId}/messages`),
  clearMessages: (chatId: string) =>
    request<void>(`/api/chats/${chatId}/messages`, { method: "DELETE" }),
  deleteMessage: (chatId: string, messageId: string) =>
    request<void>(`/api/chats/${chatId}/messages/${messageId}`, { method: "DELETE" }),
  truncateMessages: (chatId: string, fromMessageId: string) =>
    request<void>(
      `/api/chats/${chatId}/messages?from_message_id=${encodeURIComponent(fromMessageId)}`,
      { method: "DELETE" }
    ),

  searchMessages: (query: string, limit = 20) =>
    request<MessageSearchResult[]>(
      `/api/search/messages?q=${encodeURIComponent(query)}&limit=${limit}`
    ),

  listDocuments: (sessionId: string) =>
    request<Document[]>(`/api/sessions/${sessionId}/documents`),
  uploadDocuments: (sessionId: string, files: File[]) => {
    const form = new FormData();
    for (const file of files) {
      form.append("files", file);
    }
    return upload<Document[]>(`/api/sessions/${sessionId}/documents`, form);
  },
  getDocument: (id: string) => request<Document>(`/api/documents/${id}`),
  renameDocument: (id: string, filename: string) =>
    request<Document>(`/api/documents/${id}`, {
      method: "PATCH",
      body: JSON.stringify({ filename }),
    }),
  deleteDocument: (id: string) => request<void>(`/api/documents/${id}`, { method: "DELETE" }),
  reprocessDocument: (id: string) =>
    request<Document>(`/api/documents/${id}/reprocess`, { method: "POST" }),
  getChunk: (id: string) => request<Chunk>(`/api/chunks/${id}`),
};

export type StreamHandler = (event: string, data: Record<string, unknown>) => void;

function parseSseBlock(
  block: string
): { event: string; data: Record<string, unknown> } | null {
  let event = "message";
  let data = "";
  for (const line of block.split("\n")) {
    if (line.startsWith("event:")) event = line.slice(6).trim();
    else if (line.startsWith("data:")) data += line.slice(5).trim();
  }
  if (!data) return null;
  try {
    return { event, data: JSON.parse(data) as Record<string, unknown> };
  } catch {
    return null;
  }
}

export async function streamMessage(
  chatId: string,
  content: string,
  onEvent: StreamHandler,
  signal: AbortSignal
): Promise<void> {
  const res = await fetch(`/api/chats/${chatId}/messages`, {
    method: "POST",
    credentials: "same-origin",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text();
    let detail = res.statusText;
    try {
      const body = JSON.parse(text);
      if (body && typeof body.detail === "string") detail = body.detail;
    } catch {
      /* keep statusText */
    }
    throw new ApiError(res.status, detail);
  }
  if (!res.body) {
    throw new ApiError(0, "Streaming is not supported in this browser");
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  for (;;) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    let index: number;
    while ((index = buffer.indexOf("\n\n")) !== -1) {
      const block = buffer.slice(0, index);
      buffer = buffer.slice(index + 2);
      const parsed = parseSseBlock(block);
      if (parsed) onEvent(parsed.event, parsed.data);
    }
  }
}
