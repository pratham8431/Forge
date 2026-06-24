"use client"

import { useState, FormEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { api } from "@/lib/api"

function getPasswordStrength(password: string): { score: number; label: string } {
  if (password.length === 0) return { score: 0, label: "" }
  if (password.length < 6) return { score: 1, label: "Too short" }
  let score = 1
  if (password.length >= 8) score++
  if (/[A-Z]/.test(password)) score++
  if (/[0-9]/.test(password) && /[^A-Za-z0-9]/.test(password)) score++
  const labels = ["", "Too short", "Weak", "Good", "Strong"]
  return { score, label: labels[score] ?? "Strong" }
}

const STRENGTH_COLORS = ["", "#FF453A", "#FF9F0A", "#FFD60A", "#30D158"]

export default function RegisterPage() {
  const router = useRouter()
  const [form, setForm] = useState({ full_name: "", email: "", password: "" })
  const [error, setError] = useState("")
  const [success, setSuccess] = useState("")
  const [loading, setLoading] = useState(false)

  function update(field: string, value: string) {
    setForm((f) => ({ ...f, [field]: value }))
  }

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError("")
    setSuccess("")
    setLoading(true)

    try {
      const data = await api.register(form.email, form.password, form.full_name)
      setSuccess(data.message)
      setTimeout(() => router.push("/login"), 2500)
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Registration failed")
    } finally {
      setLoading(false)
    }
  }

  const strength = getPasswordStrength(form.password)

  return (
    <main className="min-h-screen flex items-center justify-center bg-black relative overflow-hidden">
      {/* Background radial glow */}
      <div className="absolute inset-0 bg-[radial-gradient(ellipse_80%_60%_at_50%_-10%,rgba(10,132,255,0.15),transparent)] pointer-events-none" />

      <div className="relative w-full max-w-[400px] mx-auto px-4 animate-fade-in">
        {/* Glass card */}
        <div className="bg-white/[0.04] backdrop-blur-xl border border-white/[0.08] rounded-2xl p-10 shadow-[0_0_0_1px_rgba(255,255,255,0.06),0_32px_80px_rgba(0,0,0,0.8)]">

          {/* Logo */}
          <div className="flex items-center justify-center gap-2 mb-8">
            <span className="text-[#0A84FF] text-[28px] leading-none select-none">◆</span>
            <span className="text-white font-semibold text-[20px] tracking-tight">Forge</span>
          </div>

          <h1 className="text-[28px] font-semibold tracking-tight text-white text-center leading-tight">
            Create your account
          </h1>
          <p className="text-[15px] text-white/55 mt-1 mb-8 text-center">
            Start using Forge today
          </p>

          <form onSubmit={handleSubmit} className="space-y-5">
            <div>
              <label className="block text-[13px] font-medium text-white/60 mb-1.5">
                Full name
              </label>
              <input
                type="text"
                required
                value={form.full_name}
                onChange={(e) => update("full_name", e.target.value)}
                placeholder="Jane Smith"
                className="w-full bg-white/[0.06] text-white rounded-xl px-4 py-3 text-[15px] border border-white/[0.10] placeholder-white/25 focus:outline-none focus:border-[#0A84FF] focus:ring-2 focus:ring-[#0A84FF]/20 transition-all duration-200"
              />
            </div>

            <div>
              <label className="block text-[13px] font-medium text-white/60 mb-1.5">
                Email
              </label>
              <input
                type="email"
                required
                value={form.email}
                onChange={(e) => update("email", e.target.value)}
                placeholder="you@company.com"
                className="w-full bg-white/[0.06] text-white rounded-xl px-4 py-3 text-[15px] border border-white/[0.10] placeholder-white/25 focus:outline-none focus:border-[#0A84FF] focus:ring-2 focus:ring-[#0A84FF]/20 transition-all duration-200"
              />
            </div>

            <div>
              <label className="block text-[13px] font-medium text-white/60 mb-1.5">
                Password
              </label>
              <input
                type="password"
                required
                value={form.password}
                onChange={(e) => update("password", e.target.value)}
                placeholder="Min 8 chars, 1 uppercase, 1 number"
                className="w-full bg-white/[0.06] text-white rounded-xl px-4 py-3 text-[15px] border border-white/[0.10] placeholder-white/25 focus:outline-none focus:border-[#0A84FF] focus:ring-2 focus:ring-[#0A84FF]/20 transition-all duration-200"
              />
              {/* Password strength indicator */}
              {form.password.length > 0 && (
                <div className="mt-2.5">
                  <div className="flex gap-1">
                    {[1, 2, 3, 4].map((i) => (
                      <div
                        key={i}
                        className="h-1 flex-1 rounded-full transition-all duration-300"
                        style={{
                          backgroundColor:
                            i <= strength.score
                              ? STRENGTH_COLORS[strength.score]
                              : "rgba(255,255,255,0.08)",
                        }}
                      />
                    ))}
                  </div>
                  <p
                    className="text-[12px] mt-1.5 transition-colors duration-200"
                    style={{ color: STRENGTH_COLORS[strength.score] }}
                  >
                    {strength.label}
                  </p>
                </div>
              )}
            </div>

            {error && (
              <div className="bg-[#FF453A]/10 border border-[#FF453A]/20 rounded-xl px-4 py-3 flex items-center gap-2 animate-fade-in">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#FF453A" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                  <path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z" />
                  <line x1="12" y1="9" x2="12" y2="13" />
                  <line x1="12" y1="17" x2="12.01" y2="17" />
                </svg>
                <span className="text-[#FF453A] text-[13px]">{error}</span>
              </div>
            )}

            {success && (
              <div className="bg-[#30D158]/10 border border-[#30D158]/20 rounded-xl px-4 py-3 flex items-center gap-2 animate-fade-in">
                <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="#30D158" strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round" className="shrink-0">
                  <polyline points="20 6 9 17 4 12" />
                </svg>
                <span className="text-[#30D158] text-[13px]">{success}</span>
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="w-full bg-[#0A84FF] text-white font-semibold rounded-xl py-3 text-[15px] hover:brightness-110 hover:scale-[1.01] active:scale-[0.99] disabled:opacity-50 transition-all duration-200 flex items-center justify-center gap-2 mt-1"
            >
              {loading ? (
                <>
                  <svg className="animate-spin" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Creating account…
                </>
              ) : (
                "Create account"
              )}
            </button>
          </form>

          <p className="text-center text-[14px] text-white/40 mt-6">
            Already have an account?{" "}
            <Link href="/login" className="text-[#0A84FF] hover:underline">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </main>
  )
}
