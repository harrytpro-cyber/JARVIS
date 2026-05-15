const BASE_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail ?? `HTTP ${res.status}`);
  }
  return res.json();
}

export const api = {
  auth: {
    register: (data: { email: string; username: string; password: string; full_name?: string }) =>
      request("/api/v1/auth/register", { method: "POST", body: JSON.stringify(data) }),

    login: (data: { email: string; password: string }) =>
      request<{ access_token: string; refresh_token: string; token_type: string }>(
        "/api/v1/auth/login",
        { method: "POST", body: JSON.stringify(data) }
      ),

    refresh: (refresh_token: string) =>
      request<{ access_token: string; token_type: string }>("/api/v1/auth/refresh", {
        method: "POST",
        body: JSON.stringify({ refresh_token }),
      }),

    me: (token: string) =>
      request("/api/v1/auth/me", { headers: { Authorization: `Bearer ${token}` } }),
  },

  health: () => request<{ status: string; services: Record<string, string> }>("/health"),
};
