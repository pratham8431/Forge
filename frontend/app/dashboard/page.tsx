"use client"

export const dynamic = "force-dynamic"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { onAuthStateChanged, signOut } from "firebase/auth"
import { auth } from "@/lib/firebase"

interface Me {
  id: string
  email: string
  full_name: string
  roles: string[]
  permissions: string[]
}

function getGreeting(): string {
  const h = new Date().getHours()
  if (h < 12) return "Good morning"
  if (h < 18) return "Good afternoon"
  return "Good evening"
}

function getInitials(name: string): string {
  return name.split(" ").map((w) => w[0]).join("").slice(0, 2).toUpperCase()
}

export default function DashboardPage() {
  const router = useRouter()
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, (user) => {
      if (!user) {
        router.push("/login")
        return
      }
      setMe({
        id: user.uid,
        email: user.email ?? "",
        full_name: user.displayName || user.email?.split("@")[0] || "User",
        roles: ["user"],
        permissions: ["rag:search"],
      })
      setLoading(false)
    })
    return () => unsubscribe()
  }, [router])

  async function handleLogout() {
    await signOut(auth)
    router.push("/login")
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-black flex items-center justify-center">
        <div className="flex items-center gap-3 text-white/40">
          <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
            <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
          </svg>
          <span className="text-[15px]">Loading…</span>
        </div>
      </div>
    )
  }

  const firstName = me?.full_name?.split(" ")[0] ?? ""

  return (
    <div className="min-h-screen bg-black text-white">
      <nav className="fixed top-0 left-0 right-0 z-50 h-[52px] bg-black/72 backdrop-blur-2xl border-b border-white/[0.06] flex items-center justify-between px-6">
        <div className="flex items-center gap-2">
          <span className="text-[#0A84FF] text-[18px] leading-none select-none">◆</span>
          <span className="text-white font-semibold text-[17px] tracking-tight">Forge</span>
        </div>
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-full bg-[#0A84FF]/20 flex items-center justify-center shrink-0">
              <span className="text-[#0A84FF] text-[12px] font-semibold">
                {me?.full_name ? getInitials(me.full_name) : "?"}
              </span>
            </div>
            <span className="text-[14px] text-white/70">{firstName}</span>
          </div>
          <Link href="/settings/sessions" className="text-[14px] text-white/50 hover:text-white transition-colors duration-200">
            Sessions
          </Link>
          <button
            onClick={handleLogout}
            className="text-[14px] bg-white/[0.08] border border-white/[0.10] hover:bg-white/[0.12] text-white px-4 py-1.5 rounded-xl transition-all duration-200"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-[1100px] mx-auto px-8 pt-[52px] pb-12">
        <div className="pt-16 animate-fade-in">
          <h1 className="text-[40px] font-semibold tracking-tight text-white leading-tight">
            {getGreeting()}, {firstName}
          </h1>
          <p className="text-[16px] text-white/40 mt-1">{me?.email}</p>
          {me?.roles && me.roles.length > 0 && (
            <div className="flex flex-wrap gap-2 mt-3">
              {me.roles.map((r) => (
                <span key={r} className="bg-[#0A84FF]/10 border border-[#0A84FF]/20 text-[#0A84FF] text-[12px] font-medium px-3 py-1 rounded-full">
                  {r}
                </span>
              ))}
            </div>
          )}
        </div>

        <p className="text-[13px] font-semibold uppercase tracking-widest text-white/30 mt-12 mb-4">
          AI Tools
        </p>

        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
          {FEATURES.filter((f) =>
            !f.permission || me?.permissions.includes(f.permission)
          ).map((f) => {
            const cardContent = (
              <>
                <div className="w-11 h-11 rounded-xl bg-white/[0.06] flex items-center justify-center" style={{ color: f.accent }}>
                  {f.icon}
                </div>
                <h3 className="text-[16px] font-semibold text-white mt-4 mb-1">{f.title}</h3>
                <p className="text-[13px] text-white/50 leading-relaxed flex-1">{f.description}</p>
                <div className="mt-4">
                  {f.available ? (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-[#30D158]/15 text-[#30D158]">Available</span>
                  ) : (
                    <span className="text-[11px] font-medium px-2 py-0.5 rounded-full bg-white/[0.08] text-white/30">Coming soon</span>
                  )}
                </div>
              </>
            )

            if (f.available && f.href) {
              return (
                <Link key={f.title} href={f.href} className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-6 flex flex-col hover:bg-white/[0.07] hover:border-white/[0.12] hover:scale-[1.01] hover:shadow-[0_8px_32px_rgba(0,0,0,0.4)] hover:-translate-y-0.5 transition-all duration-200 cursor-pointer">
                  {cardContent}
                </Link>
              )
            }
            return (
              <div key={f.title} className="bg-white/[0.04] border border-white/[0.06] rounded-2xl p-6 flex flex-col opacity-60">
                {cardContent}
              </div>
            )
          })}
        </div>
      </main>
    </div>
  )
}

const FEATURES: {
  title: string; description: string; permission: string
  available: boolean; href?: string; accent: string; icon: React.ReactNode
}[] = [
  {
    title: "RAG Search", description: "Search your internal knowledge base with AI.",
    permission: "rag:search", available: true, href: "/rag", accent: "#0A84FF",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>,
  },
  {
    title: "Code Review", description: "AI-assisted code review and suggestions.",
    permission: "review:create", available: false, accent: "#BF5AF2",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/></svg>,
  },
  {
    title: "SQL Assistant", description: "Generate SQL from natural language.",
    permission: "sql:execute", available: false, accent: "#FFD60A",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><ellipse cx="12" cy="5" rx="9" ry="3"/><path d="M21 12c0 1.66-4 3-9 3s-9-1.34-9-3"/><path d="M3 5v14c0 1.66 4 3 9 3s9-1.34 9-3V5"/></svg>,
  },
  {
    title: "Incident Analysis", description: "AI-powered incident triage and RCA.",
    permission: "incident:analyze", available: false, accent: "#FF453A",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>,
  },
  {
    title: "Docs Generator", description: "Auto-generate technical documentation.",
    permission: "docs:generate", available: false, accent: "#30D158",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/><polyline points="14 2 14 8 20 8"/><line x1="16" y1="13" x2="8" y2="13"/><line x1="16" y1="17" x2="8" y2="17"/></svg>,
  },
  {
    title: "API Explorer", description: "Browse and test internal APIs.",
    permission: "api:explore", available: false, accent: "#FF9F0A",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="2"/><circle cx="4" cy="6" r="2"/><circle cx="20" cy="6" r="2"/><circle cx="4" cy="18" r="2"/><circle cx="20" cy="18" r="2"/><line x1="6" y1="6" x2="10" y2="11"/><line x1="18" y1="6" x2="14" y2="11"/><line x1="6" y1="18" x2="10" y2="13"/><line x1="18" y1="18" x2="14" y2="13"/></svg>,
  },
  {
    title: "Analytics", description: "Platform usage and performance metrics.",
    permission: "analytics:read", available: false, accent: "#64D2FF",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><line x1="18" y1="20" x2="18" y2="10"/><line x1="12" y1="20" x2="12" y2="4"/><line x1="6" y1="20" x2="6" y2="14"/></svg>,
  },
  {
    title: "Admin", description: "Manage users, roles, and sessions.",
    permission: "admin:users", available: false, accent: "#98989D",
    icon: <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round"><circle cx="12" cy="12" r="3"/><path d="M19.07 4.93a10 10 0 0 1 0 14.14M4.93 4.93a10 10 0 0 0 0 14.14"/><path d="M12 2v2M12 20v2M2 12h2M20 12h2"/></svg>,
  },
]
