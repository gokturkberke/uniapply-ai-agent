// Thin fetch wrapper around the backend. A 200 response is returned as-is
// (including grounded refusals, which carry insufficient_context: true and are
// NOT errors). Any non-2xx, or an unreachable backend, raises ApiError.

const DEFAULT_BASE_URL = "http://localhost:8000";

export function apiBaseUrl(): string {
  const configured = import.meta.env.VITE_API_BASE_URL;
  return (configured ?? DEFAULT_BASE_URL).replace(/\/+$/, "");
}

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;

  constructor(status: number, detail: unknown, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
  }
}

async function parseBody(response: Response): Promise<unknown> {
  const text = await response.text();
  if (!text) {
    return null;
  }
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

function messageForStatus(status: number, body: unknown): string {
  if (body && typeof body === "object" && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
  }
  return `Request failed (HTTP ${status}).`;
}

async function request<TRes>(path: string, init: RequestInit): Promise<TRes> {
  let response: Response;
  try {
    response = await fetch(`${apiBaseUrl()}${path}`, init);
  } catch {
    throw new ApiError(
      0,
      null,
      "Cannot reach the backend. Is the API running?",
    );
  }

  const body = await parseBody(response);
  if (!response.ok) {
    throw new ApiError(response.status, body, messageForStatus(response.status, body));
  }
  return body as TRes;
}

export function getJson<TRes>(path: string): Promise<TRes> {
  return request<TRes>(path, { method: "GET" });
}

export function postJson<TReq, TRes>(path: string, payload: TReq): Promise<TRes> {
  return request<TRes>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}
