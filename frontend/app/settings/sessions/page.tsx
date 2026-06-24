"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api } from "@/lib/api"
import { tokenStore } from "@/lib/auth"
import type { Session } from "@/types/auth"

function formatRelativeTime(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return "Just now"
  if (mins < 60) return `${mins}m ago`
  const hrs = Math.floor(mins / 60)
  if (hrs < 24) return `${hrs}h ago`
  return `${Math.floor(hrs / 24)}d ago`
}

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
    <div className="min-h-screen bg-black text-white">
      {/* Fixed Nav */}
      <nav className="fixed top-0 left-0 right-0 z-50 h-[52px] bg-black/72 backdrop-blur-2xl border-b border-white/[0.06] flex items-center px-6 gap-3">
        <Link
          href="/dashboard"
          className="flex items-center gap-1.5 text-white/50 hover:text-white transition-colors duration-200 text-[14px]"
        >
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
            <polyline points="15 18 9 12 15 6" />
          </svg>
          Back
        </Link>
        <span className="text-white/20 select-none">|</span>
        <span className="text-[17px] font-semibold text-white">Active Sessions</span>
      </nav>

      <main className="max-w-[680px] mx-auto px-6 pt-[52px] pb-12">
        <div className="pt-12 animate-fade-in">
          {/* Page header */}
          <div className="flex items-start justify-between mb-8">
            <div>
              <h1 className="text-[32px] font-semibold tracking-tight text-white leading-tight">
                Devices &amp; Sessions
              </h1>
              <p className="text-[16px] text-white/40 mt-2">
                {sessions.length} active session{sessions.length !== 1 ? "s" : ""}
              </p>
            </div>
            <button
              onClick={revokeAll}
              className="flex items-center gap-2 bg-[#FF453A]/15 border border-[#FF453A]/30 text-[#FF453A] hover:bg-[#FF453A]/22 text-[13px] font-medium px-4 py-2 rounded-xl transition-all duration-200 mt-1"
            >
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" />
                <polyline points="16 17 21 12 16 7" />
                <line x1="21" y1="12" x2="9" y2="12" />
              </svg>
              Revoke all
            </button>
          </div>

          {/* Session list */}
          {loading ? (
            <div className="flex items-center gap-3 text-white/30 py-12">
              <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
              </svg>
              <span className="text-[15px]">Loading sessions…</span>
            </div>
          ) : sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1" strokeLinecap="round" strokeLinejoin="round" className="text-white/10 mb-4">
                <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
              </svg>
              <p className="text-[17px] text-white/40 font-medium">No active sessions</p>
              <p className="text-[14px] text-white/25 mt-1.5">
                You&apos;re not signed in on any other devices
              </p>
            </div>
          ) : (
            <div className="space-y-3">
              {sessions.map((s) => (
                <div
                  key={s.id}
                  className="bg-white/[0.04] border border-white/[0.06] rounded-2xl px-6 py-5 flex items-start justify-between gap-4"
                >
                  <div className="flex items-start gap-4">
                    {/* Device icon */}
                    <div className="w-11 h-11 rounded-xl bg-white/[0.06] flex items-center justify-center shrink-0 mt-0.5">
                      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" className="text-white/70">
                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2" />
                        <line x1="8" y1="21" x2="16" y2="21" />
                        <line x1="12" y1="17" x2="12" y2="21" />
                      </svg>
                    </div>
                    {/* Session details */}
                    <div>
                      <p className="text-[16px] font-medium text-white leading-tight">
                        {s.device_name ?? <span className="text-white/40">Unknown device</span>}
                      </p>
                      <p className="text-[13px] text-white/40 mt-0.5">
                        {s.ip_address ?? "—"}
                      </p>
                      <p className="text-[13px] text-white/30 mt-0.5">
                        Last active: {formatRelativeTime(s.last_used)}
                      </p>
                      <p className="text-[12px] text-white/20 mt-0.5">
                        Expires: {new Date(s.expires_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {/* Revoke button */}
                  <button
                    onClick={() => revoke(s.id)}
                    disabled={revoking === s.id}
                    className="bg-[#FF453A]/15 border border-[#FF453A]/30 text-[#FF453A] hover:bg-[#FF453A]/22 text-[13px] font-medium px-4 py-1.5 rounded-xl transition-all duration-200 disabled:opacity-40 shrink-0 flex items-center gap-1.5"
                  >
                    {revoking === s.id ? (
                      <>
                        <svg className="animate-spin" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                          <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                        </svg>
                        Revoking…
                      </>
                    ) : (
                      "Revoke"
                    )}
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      </main>
    </div>
  )
}
