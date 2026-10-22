/** Thin typed client for the underwriting API. */

export const API_URL =
  process.env.NEXT_PUBLIC_API_URL ??
  (typeof window !== "undefined" &&
  window.location.hostname !== "localhost" &&
  window.location.hostname !== "127.0.0.1"
    ? ""
    : "http://127.0.0.1:8000");

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.status = status;
  }
}

function describe(data: unknown, fallback: string): string {
  const detail = typeof data === "object" && data !== null && "detail" in data ? (data as { detail: unknown }).detail : null;
  if (Array.isArray(detail)) {
    const messages = detail
      .map((item) => (typeof item === "object" && item !== null && "msg" in item ? (item as { msg: unknown }).msg : null))
      .filter((message): message is string => typeof message === "string");
    if (messages.length) return messages.join(" ");
  }
  return typeof detail === "string" ? detail : fallback;
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(API_URL + path, {
      ...init,
      headers: { ...(isFormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
    });
  } catch {
    throw new ApiError("The underwriting API is not reachable. Start the backend, then try again.", 0);
  }
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && typeof window !== "undefined") {
      // The static frontend cannot know the session expired until the API
      // says so; the login page is served by the API, so a full navigation
      // is intended here.
      // eslint-disable-next-line @next/next/no-location-assign-relative-destination
      window.location.assign("/login/");
    }
    throw new ApiError(describe(data, "The request could not be completed."), response.status);
  }
  return data as T;
}

export const post = <T>(path: string, body: unknown) => api<T>(path, { method: "POST", body: JSON.stringify(body) });
export const patch = <T>(path: string, body: unknown) => api<T>(path, { method: "PATCH", body: JSON.stringify(body) });
export const del = (path: string) => api<void>(path, { method: "DELETE" });

/** Fetch a binary export and hand it to the browser as a download. */
export async function downloadFile(path: string, body: unknown, filename: string): Promise<void> {
  const response = await fetch(API_URL + path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    const data: unknown = await response.json().catch(() => null);
    throw new ApiError(describe(data, "The export could not be created."), response.status);
  }
  const url = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = url;
  link.download = filename;
  link.click();
  URL.revokeObjectURL(url);
}
