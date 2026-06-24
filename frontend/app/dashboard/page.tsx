"use client"

import { useEffect, useState } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api } from "@/lib/api"
import { tokenStore } from "@/lib/auth"

interface Me {
  id: string
  email: string
  full_name: string
  roles: string[]
  permissions: string[]
}

export default function DashboardPage() {
  const router = useRouter()
  const [me, setMe] = useState<Me | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const token = tokenStore.getAccess()
    if (!token) { router.push("/login"); return }

    api.me(token)
      .then(setMe)
      .catch(() => { tokenStore.clear(); router.push("/login") })
      .finally(() => setLoading(false))
  }, [router])

  async function handleLogout() {
    const token = tokenStore.getAccess()
    if (token) await api.logout(token).catch(() => null)
    tokenStore.clear()
    router.push("/login")
  }

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-950 flex items-center justify-center">
        <div className="text-gray-400">Loading…</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 text-white">
      {/* Nav */}
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center justify-between">
        <span className="text-xl font-bold">Atlas</span>
        <div className="flex items-center gap-4">
          <Link href="/settings/sessions" className="text-sm text-gray-400 hover:text-white transition">
            Sessions
          </Link>
          <button
            onClick={handleLogout}
            className="text-sm bg-gray-800 hover:bg-gray-700 px-4 py-1.5 rounded-lg transition"
          >
            Sign out
          </button>
        </div>
      </nav>

      <main className="max-w-5xl mx-auto px-6 py-10">
        <h1 className="text-3xl font-bold mb-1">
          Welcome back, {me?.full_name?.split(" ")[0]}
        </h1>
        <p className="text-gray-400 mb-8">{me?.email}</p>

        {/* Role badges */}
        <div className="flex gap-2 mb-10">
          {me?.roles.map((r) => (
            <span
              key={r}
              className="bg-blue-900/50 border border-blue-700 text-blue-300 text-xs px-3 py-1 rounded-full"
            >
              {r}
            </span>
          ))}
        </div>

        {/* Feature cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
          {FEATURES.filter((f) =>
            !f.permission || me?.permissions.includes(f.permission)
          ).map((f) => (
            <div
              key={f.title}
              className="bg-gray-900 border border-gray-800 rounded-xl p-5 hover:border-gray-600 transition cursor-pointer"
            >
              <div className="text-2xl mb-3">{f.icon}</div>
              <h3 className="font-semibold mb-1">{f.title}</h3>
              <p className="text-gray-400 text-sm">{f.description}</p>
              <span className="inline-block mt-3 text-xs text-gray-500 bg-gray-800 px-2 py-0.5 rounded">
                Coming soon
              </span>
            </div>
          ))}
        </div>
      </main>
    </div>
  )
}

const FEATURES = [
  { title: "RAG Search", icon: "🔍", description: "Search your internal knowledge base with AI.", permission: "rag:search" },
  { title: "Code Review", icon: "🧠", description: "AI-assisted code review and suggestions.", permission: "review:create" },
  { title: "SQL Assistant", icon: "🗄️", description: "Generate SQL from natural language.", permission: "sql:execute" },
  { title: "Incident Analysis", icon: "🚨", description: "AI-powered incident triage and RCA.", permission: "incident:analyze" },
  { title: "Docs Generator", icon: "📄", description: "Auto-generate technical documentation.", permission: "docs:generate" },
  { title: "API Explorer", icon: "🔌", description: "Browse and test internal APIs.", permission: "api:explore" },
  { title: "Analytics", icon: "📊", description: "Platform usage and performance metrics.", permission: "analytics:read" },
  { title: "Admin", icon: "⚙️", description: "Manage users, roles, and sessions.", permission: "admin:users" },
]
