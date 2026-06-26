import { auth } from "./firebase"
import type { Session } from "@/types/auth"

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = await auth.currentUser?.getIdToken().catch(() => null)

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
  /** Revoke all Firebase refresh tokens server-side (signs out all devices). */
  logoutAll: () =>
    request<{ message: string }>("/auth/logout-all", { method: "POST" }),

  getSessions: () => request<Session[]>("/auth/sessions"),

  revokeSession: (sessionId: string) =>
    request<{ message: string }>(`/auth/sessions/${sessionId}`, { method: "DELETE" }),
}
