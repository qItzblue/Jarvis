export const API_BASE: string = (import.meta.env.VITE_API as string) || "http://127.0.0.1:8765";
export const WS_BASE = API_BASE.replace(/^http/, "ws");

async function req<T>(method: string, path: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const r = await fetch(API_BASE + path, init);
  if (!r.ok) {
    let detail = r.statusText;
    try { detail = (await r.json()).detail ?? detail; } catch { /* not json */ }
    throw new Error(detail);
  }
  return r.json() as Promise<T>;
}

export const api = {
  get: <T = any>(p: string) => req<T>("GET", p),
  post: <T = any>(p: string, b?: unknown) => req<T>("POST", p, b ?? {}),
  put: <T = any>(p: string, b?: unknown) => req<T>("PUT", p, b ?? {}),
  del: <T = any>(p: string) => req<T>("DELETE", p),
  tool: async <T = any>(name: string, args: Record<string, unknown> = {}): Promise<T> =>
    (await req<{ result: T }>("POST", `/api/tools/${name}`, { args })).result,
};

export function isError(x: unknown): x is { error: string } {
  return !!x && typeof x === "object" && "error" in (x as object);
}
