import type { TokenResponse, Session, User } from "@/types/auth"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

async function request<T>(
  path: string,
  options: RequestInit = {},
  token?: string,
): Promise<T> {
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  }
  if (token) headers["Authorization"] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...options, headers })

  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json() as Promise<T>
}

export const api = {
  register: (email: string, password: string, full_name: string) =>
    request<{ message: string }>("/auth/register", {
      method: "POST",
      body: JSON.stringify({ email, password, full_name }),
    }),

  login: (email: string, password: string) =>
    request<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify({ email, password }),
    }),

  refresh: (refresh_token: string) =>
    request<TokenResponse>("/auth/refresh", {
      method: "POST",
      body: JSON.stringify({ refresh_token }),
    }),

  logout: (token: string) =>
    request<{ message: string }>("/auth/logout", { method: "POST" }, token),

  logoutAll: (token: string) =>
    request<{ message: string }>("/auth/logout-all", { method: "POST" }, token),

  me: (token: string) =>
    request<User & { roles: string[]; permissions: string[] }>("/auth/me", {}, token),

  verifyEmail: (otp: string) =>
    request<{ message: string }>("/auth/verify-email", {
      method: "POST",
      body: JSON.stringify({ token: otp }),
    }),

  forgotPassword: (email: string) =>
    request<{ message: string }>("/auth/forgot-password", {
      method: "POST",
      body: JSON.stringify({ email }),
    }),

  resetPassword: (token: string, new_password: string) =>
    request<{ message: string }>("/auth/reset-password", {
      method: "POST",
      body: JSON.stringify({ token, new_password }),
    }),

  getSessions: (token: string) =>
    request<Session[]>("/auth/sessions", {}, token),

  revokeSession: (sessionId: string, token: string) =>
    request<{ message: string }>(`/auth/sessions/${sessionId}`, { method: "DELETE" }, token),
}
