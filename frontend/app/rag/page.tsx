"use client"

import { useState, useRef, useEffect, FormEvent } from "react"
import { useRouter } from "next/navigation"
import Link from "next/link"
import { tokenStore } from "@/lib/auth"

const API = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1"

interface Document {
  id: string
  filename: string
  file_type: string
  file_size: number
  chunk_count: number
  status: "processing" | "ready" | "failed"
  created_at: string
}

interface Message {
  role: "user" | "assistant"
  content: string
  sources?: { content: string; distance: number }[]
}

async function apiFetch<T>(path: string, opts: RequestInit = {}): Promise<T> {
  const token = tokenStore.getAccess()
  const res = await fetch(`${API}${path}`, {
    ...opts,
    headers: {
      "Content-Type": "application/json",
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(opts.headers as Record<string, string>),
    },
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: "Unknown error" }))
    throw new Error(err.detail ?? "Request failed")
  }
  return res.json()
}

const FILE_TYPE_COLORS: Record<string, string> = {
  pdf: "#FF453A",
  docx: "#0A84FF",
  pptx: "#FF9F0A",
  xlsx: "#30D158",
  csv: "#30D158",
  zip: "#FFD60A",
  default: "#98989D",
}

function FileIcon({ fileType }: { fileType: string }) {
  const color = FILE_TYPE_COLORS[fileType.toLowerCase()] ?? FILE_TYPE_COLORS.default
  return (
    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth="1.75" strokeLinecap="round" strokeLinejoin="round">
      <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
      <polyline points="14 2 14 8 20 8" />
    </svg>
  )
}

const MODES: { value: "fast" | "concise" | "dynamic"; label: string }[] = [
  { value: "fast", label: "Fast" },
  { value: "concise", label: "Concise" },
  { value: "dynamic", label: "Dynamic" },
]

const SUGGESTIONS = [
  "Summarize the key points",
  "What are the main findings?",
  "Explain the methodology",
]

export default function RAGPage() {
  const router = useRouter()
  const [docs, setDocs] = useState<Document[]>([])
  const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [query, setQuery] = useState("")
  const [mode, setMode] = useState<"fast" | "concise" | "dynamic">("fast")
  const [uploading, setUploading] = useState(false)
  const [searching, setSearching] = useState(false)
  const [uploadError, setUploadError] = useState("")
  const fileRef = useRef<HTMLInputElement>(null)
  const bottomRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!tokenStore.getAccess()) { router.push("/login"); return }
    loadDocuments()
  }, [router])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" })
  }, [messages])

  async function loadDocuments() {
    try {
      const data = await apiFetch<Document[]>("/rag/documents")
      setDocs(data)
    } catch {
      router.push("/login")
    }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setUploading(true)
    setUploadError("")
    try {
      const token = tokenStore.getAccess()
      const form = new FormData()
      form.append("file", file)
      const res = await fetch(`${API}/rag/documents/upload`, {
        method: "POST",
        headers: { Authorization: `Bearer ${token}` },
        body: form,
      })
      if (!res.ok) {
        const err = await res.json().catch(() => ({ detail: "Upload failed" }))
        throw new Error(err.detail)
      }
      await loadDocuments()
    } catch (err: unknown) {
      setUploadError(err instanceof Error ? err.message : "Upload failed")
    } finally {
      setUploading(false)
      if (fileRef.current) fileRef.current.value = ""
    }
  }

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    if (!query.trim()) return
    const q = query.trim()
    setQuery("")
    setMessages((m) => [...m, { role: "user", content: q }])
    setSearching(true)
    try {
      const endpoint = selectedDoc
        ? `/rag/documents/${selectedDoc.id}/search`
        : "/rag/search"
      const data = await apiFetch<{ answer: string; sources?: { content: string; distance: number }[] }>(
        endpoint,
        { method: "POST", body: JSON.stringify({ query: q, mode }) }
      )
      setMessages((m) => [...m, { role: "assistant", content: data.answer, sources: data.sources }])
    } catch (err: unknown) {
      setMessages((m) => [...m, {
        role: "assistant",
        content: err instanceof Error ? err.message : "Search failed",
      }])
    } finally {
      setSearching(false)
    }
  }

  async function handleDelete(docId: string) {
    await apiFetch(`/rag/documents/${docId}`, { method: "DELETE" }).catch(() => null)
    if (selectedDoc?.id === docId) { setSelectedDoc(null); setMessages([]) }
    await loadDocuments()
  }

  const formatSize = (bytes: number) =>
    bytes > 1_000_000 ? `${(bytes / 1_000_000).toFixed(1)} MB` : `${(bytes / 1_000).toFixed(0)} KB`

  const readyCount = docs.filter((d) => d.status === "ready").length

  return (
    <div className="h-screen bg-black text-white flex flex-col overflow-hidden">

      {/* Nav */}
      <nav className="h-[52px] bg-black/72 backdrop-blur-2xl border-b border-white/[0.06] flex items-center justify-between px-6 shrink-0 z-50">
        <div className="flex items-center gap-3">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-white/50 hover:text-white transition-colors duration-200 text-[14px]"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <polyline points="15 18 9 12 15 6" />
            </svg>
            Dashboard
          </Link>
          <span className="text-white/20 select-none">|</span>
          <span className="text-[17px] font-semibold text-white">RAG Search</span>
        </div>

        {/* Segmented mode control */}
        <div className="bg-white/[0.06] rounded-xl p-1 flex gap-1">
          {MODES.map((m) => (
            <button
              key={m.value}
              onClick={() => setMode(m.value)}
              className={`px-3 py-1.5 rounded-lg text-[13px] font-medium transition-all duration-150 ${
                mode === m.value
                  ? "bg-white/[0.12] text-white"
                  : "text-white/40 hover:text-white/70"
              }`}
            >
              {m.label}
            </button>
          ))}
        </div>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar */}
        <aside className="w-[280px] border-r border-white/[0.06] bg-black/30 flex flex-col shrink-0">
          {/* Upload section */}
          <div className="bg-white/[0.03] border-b border-white/[0.06] px-4 py-4">
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="w-full border border-dashed border-white/[0.15] rounded-xl py-3 text-[14px] text-white/60 hover:text-white hover:border-white/30 flex items-center justify-center gap-2 transition-all duration-200 disabled:opacity-50"
            >
              {uploading ? (
                <>
                  <svg className="animate-spin" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round">
                    <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4M4.93 19.07l2.83-2.83M16.24 7.76l2.83-2.83" />
                  </svg>
                  Uploading…
                </>
              ) : (
                <>
                  <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                    <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
                    <polyline points="17 8 12 3 7 8" />
                    <line x1="12" y1="3" x2="12" y2="15" />
                  </svg>
                  Upload Document
                </>
              )}
            </button>
            <input
              ref={fileRef}
              type="file"
              className="hidden"
              onChange={handleUpload}
              accept=".pdf,.docx,.pptx,.xlsx,.csv,.zip,.png,.jpg,.jpeg"
            />
            {uploadError && (
              <p className="text-[#FF453A] text-[12px] mt-2 leading-relaxed">{uploadError}</p>
            )}
          </div>

          {/* Document list */}
          <div className="flex-1 overflow-y-auto px-3 py-3 space-y-1">
            {/* All documents row */}
            <button
              onClick={() => { setSelectedDoc(null); setMessages([]) }}
              className={`w-full text-left px-3 py-2 rounded-lg text-[13px] transition-all duration-150 ${
                !selectedDoc
                  ? "bg-[#0A84FF]/10 text-[#0A84FF]"
                  : "text-white/60 hover:bg-white/[0.06]"
              }`}
            >
              All documents
            </button>

            {docs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => { if (doc.status === "ready") { setSelectedDoc(doc); setMessages([]) } }}
                className={`relative rounded-xl px-3 py-3 transition-all duration-150 group ${
                  selectedDoc?.id === doc.id
                    ? "bg-[#0A84FF]/10 border border-[#0A84FF]/15"
                    : doc.status === "ready"
                    ? "hover:bg-white/[0.06] cursor-pointer"
                    : "opacity-50 cursor-not-allowed"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <div className="flex items-center gap-2 min-w-0">
                    <FileIcon fileType={doc.file_type} />
                    <p className="text-[13px] text-white truncate">{doc.filename}</p>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(doc.id) }}
                    className="text-white/30 hover:text-[#FF453A] opacity-0 group-hover:opacity-100 transition-all duration-150 shrink-0 p-0.5"
                  >
                    <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                      <polyline points="3 6 5 6 21 6" />
                      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
                      <path d="M10 11v6M14 11v6" />
                    </svg>
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-1.5">
                  <span
                    className={`text-[11px] font-medium px-2 py-0.5 rounded-full flex items-center gap-1 ${
                      doc.status === "ready"
                        ? "bg-[#30D158]/15 text-[#30D158]"
                        : doc.status === "processing"
                        ? "bg-[#FFD60A]/15 text-[#FFD60A]"
                        : "bg-[#FF453A]/15 text-[#FF453A]"
                    }`}
                  >
                    <span className="w-1 h-1 rounded-full bg-current" />
                    {doc.status}
                  </span>
                  <span className="text-[11px] text-white/30">{formatSize(doc.file_size)}</span>
                  {doc.chunk_count > 0 && (
                    <span className="text-[11px] text-white/20">{doc.chunk_count} chunks</span>
                  )}
                </div>
              </div>
            ))}

            {docs.length === 0 && (
              <div className="flex flex-col items-center justify-center py-12 px-4 text-center">
                <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.25" strokeLinecap="round" strokeLinejoin="round" className="text-white/15 mb-3">
                  <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                  <polyline points="14 2 14 8 20 8" />
                  <line x1="12" y1="18" x2="12" y2="12" />
                  <line x1="9" y1="15" x2="15" y2="15" />
                </svg>
                <p className="text-[14px] text-white/40">No documents yet</p>
                <p className="text-[12px] text-white/25 mt-1 leading-relaxed">
                  Upload a PDF, Word, or CSV<br />to get started
                </p>
              </div>
            )}
          </div>
        </aside>

        {/* Main chat area */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Context bar */}
          <div className="px-6 py-2.5 border-b border-white/[0.06] text-[13px] text-white/40 shrink-0">
            {selectedDoc ? (
              <>Searching in <span className="text-white font-medium">{selectedDoc.filename}</span></>
            ) : (
              <>Searching across <span className="text-white font-medium">{readyCount} document{readyCount !== 1 ? "s" : ""}</span></>
            )}
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-8 space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                {/* Glowing diamond */}
                <div className="relative mb-6">
                  <div className="absolute inset-0 bg-[#0A84FF] blur-2xl opacity-20 scale-150" />
                  <span className="relative text-[#0A84FF] text-[48px] leading-none select-none">◆</span>
                </div>
                <h2 className="text-[22px] font-semibold text-white tracking-tight">
                  Ask anything about your documents
                </h2>
                <p className="text-[15px] text-white/40 max-w-sm mt-2 leading-relaxed">
                  Upload a PDF, DOCX, PPTX, Excel, CSV, or image and ask questions in plain English.
                </p>
                {/* Suggestion pills */}
                <div className="flex flex-wrap justify-center gap-2 mt-6">
                  {SUGGESTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => setQuery(s)}
                      className="bg-white/[0.05] border border-white/[0.08] rounded-full px-4 py-2 text-[13px] text-white/60 hover:bg-white/[0.09] hover:text-white transition-all duration-200 cursor-pointer"
                    >
                      {s}
                    </button>
                  ))}
                </div>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div
                  className={`rounded-2xl px-5 py-3.5 ${
                    msg.role === "user"
                      ? "bg-[#0A84FF] text-white max-w-[65%] rounded-tr-sm"
                      : "bg-white/[0.05] border border-white/[0.07] text-white/90 max-w-[75%] rounded-tl-sm"
                  }`}
                >
                  <p className="text-[15px] leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-[12px] text-white/30 cursor-pointer hover:text-white/50 transition-colors duration-150 list-none flex items-center gap-1.5">
                        <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                          <polyline points="6 9 12 15 18 9" />
                        </svg>
                        View {msg.sources.length} source{msg.sources.length !== 1 ? "s" : ""}
                      </summary>
                      <div className="mt-2.5 space-y-1.5">
                        {msg.sources.map((s, si) => (
                          <p
                            key={si}
                            className="text-[12px] text-white/40 bg-white/[0.04] rounded-lg px-3 py-2 line-clamp-2"
                          >
                            {s.content}
                          </p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))}

            {/* Typing indicator */}
            {searching && (
              <div className="flex justify-start">
                <div className="bg-white/[0.05] border border-white/[0.07] rounded-2xl rounded-tl-sm px-5 py-4">
                  <div className="flex gap-1.5 items-center">
                    {[0, 200, 400].map((delay) => (
                      <span
                        key={delay}
                        className="w-2 h-2 bg-white/50 rounded-full"
                        style={{
                          animation: `dot-pulse 1.2s ease-in-out ${delay}ms infinite`,
                        }}
                      />
                    ))}
                  </div>
                </div>
              </div>
            )}

            <div ref={bottomRef} />
          </div>

          {/* Input bar */}
          <form
            onSubmit={handleSearch}
            className="px-6 py-4 border-t border-white/[0.06] flex items-center gap-3 shrink-0"
          >
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your documents…"
              disabled={searching}
              className="flex-1 bg-white/[0.05] border border-white/[0.08] rounded-2xl px-5 py-3.5 text-[15px] text-white placeholder-white/25 focus:outline-none focus:border-[#0A84FF]/50 focus:ring-1 focus:ring-[#0A84FF]/20 transition-all duration-200 disabled:opacity-50"
            />
            <button
              type="submit"
              disabled={searching || !query.trim()}
              className={`w-11 h-11 rounded-xl flex items-center justify-center transition-all duration-200 shrink-0 ${
                searching || !query.trim()
                  ? "bg-white/[0.06] text-white/20"
                  : "bg-[#0A84FF] text-white hover:brightness-110"
              }`}
            >
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
                <line x1="12" y1="19" x2="12" y2="5" />
                <polyline points="5 12 12 5 19 12" />
              </svg>
            </button>
          </form>
        </main>
      </div>
    </div>
  )
}
