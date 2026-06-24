"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api } from "@/lib/api"
import { tokenStore } from "@/lib/auth"
import type { Session } from "@/types/auth"

export default function SessionsPage() {
  const router = useRouter()
  const [sessions, setSessions] = useState<Session[]>([])
  const [loading, setLoading] = useState(true)
  const [revoking, setRevoking] = useState<string | null>(null)

  useEffect(() => {
    const token = tokenStore.getAccess()
    if (!token) { router.push("/login"); return }

    api.getSessions(token)
      .then(setSessions)
      .catch(() => { tokenStore.clear(); router.push("/login") })
      .finally(() => setLoading(false))
  }, [router])

  async function revoke(sessionId: string) {
    const token = tokenStore.getAccess()
    if (!token) return
    setRevoking(sessionId)
    try {
      await api.revokeSession(sessionId, token)
      setSessions((s) => s.filter((x) => x.id !== sessionId))
    } catch {
      // silently ignore
    } finally {
      setRevoking(null)
    }
  }

  async function revokeAll() {
    const token = tokenStore.getAccess()
    if (!token) return
    await api.logoutAll(token).catch(() => null)
    tokenStore.clear()
    router.push("/login")
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center gap-4">
        <Link href="/dashboard" className="text-gray-400 hover:text-white transition text-sm">
          ← Dashboard
        </Link>
        <span className="text-lg font-semibold">Active Sessions</span>
      </nav>

      <main className="max-w-3xl mx-auto px-6 py-10">
        <div className="flex items-center justify-between mb-6">
          <p className="text-gray-400 text-sm">{sessions.length} active session(s)</p>
          <button
            onClick={revokeAll}
            className="text-sm text-red-400 hover:text-red-300 border border-red-800 hover:border-red-600 px-3 py-1.5 rounded-lg transition"
          >
            Revoke all sessions
          </button>
        </div>

        {loading ? (
          <div className="text-gray-500 text-sm">Loading sessions…</div>
        ) : sessions.length === 0 ? (
          <div className="text-gray-500 text-sm">No active sessions found.</div>
        ) : (
          <div className="space-y-3">
            {sessions.map((s) => (
              <div
                key={s.id}
                className="bg-gray-900 border border-gray-800 rounded-xl p-4 flex items-start justify-between"
              >
                <div>
                  <p className="font-medium text-sm">{s.device_name ?? "Unknown device"}</p>
                  <p className="text-gray-400 text-xs mt-0.5">IP: {s.ip_address ?? "—"}</p>
                  <p className="text-gray-500 text-xs mt-0.5">
                    Last used: {new Date(s.last_used).toLocaleString()}
                  </p>
                  <p className="text-gray-600 text-xs">
                    Expires: {new Date(s.expires_at).toLocaleString()}
                  </p>
                </div>
                <button
                  onClick={() => revoke(s.id)}
                  disabled={revoking === s.id}
                  className="text-xs text-red-400 hover:text-red-300 border border-red-900 hover:border-red-700 px-3 py-1 rounded-lg transition disabled:opacity-40"
                >
                  {revoking === s.id ? "Revoking…" : "Revoke"}
                </button>
              </div>
            ))}
          </div>
        )}
      </main>
    </div>
  )
}
