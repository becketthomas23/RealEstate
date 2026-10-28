/** Thin typed client for the Deal Scope API.
 *
 * Requests are same-origin: in production the API serves the static site, and
 * in development Next.js proxies ``/v1`` to the API (see next.config.ts), so
 * the session cookie travels with every call. ``NEXT_PUBLIC_API_URL`` can
 * still point at a separate host when a deployment needs it.
 */

export const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "";

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

function redirectToSignIn() {
  if (typeof window === "undefined" || window.location.pathname.startsWith("/login")) return;
  // The static frontend learns that a session expired only when the API says
  // so; the sign-in page is a separate route, so a full navigation is intended.
  // eslint-disable-next-line @next/next/no-location-assign-relative-destination
  window.location.assign("/login/");
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const isFormData = typeof FormData !== "undefined" && init?.body instanceof FormData;
  let response: Response;
  try {
    response = await fetch(API_URL + path, {
      ...init,
      credentials: "include",
      headers: { ...(isFormData ? {} : { "Content-Type": "application/json" }), ...init?.headers },
    });
  } catch {
    throw new ApiError("The Deal Scope API is not reachable. Start the backend, then try again.", 0);
  }
  if (response.status === 204) return undefined as T;
  const data: unknown = await response.json().catch(() => null);
  if (!response.ok) {
    if (response.status === 401 && !path.startsWith("/v1/auth/")) redirectToSignIn();
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
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!response.ok) {
    if (response.status === 401) redirectToSignIn();
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
