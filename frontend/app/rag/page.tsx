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

  return (
    <div className="min-h-screen bg-gray-950 text-white flex flex-col">
      {/* Nav */}
      <nav className="border-b border-gray-800 px-6 py-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-4">
          <Link href="/dashboard" className="text-gray-400 hover:text-white text-sm transition">← Dashboard</Link>
          <span className="text-lg font-semibold">RAG Search</span>
        </div>
        <div className="flex items-center gap-3">
          <select
            value={mode}
            onChange={(e) => setMode(e.target.value as typeof mode)}
            className="bg-gray-800 border border-gray-700 text-sm rounded-lg px-3 py-1.5 text-gray-300 focus:outline-none"
          >
            <option value="fast">Fast</option>
            <option value="concise">Concise</option>
            <option value="dynamic">Dynamic</option>
          </select>
        </div>
      </nav>

      <div className="flex flex-1 overflow-hidden">
        {/* Sidebar — document list */}
        <aside className="w-72 border-r border-gray-800 flex flex-col shrink-0">
          <div className="p-4 border-b border-gray-800">
            <button
              onClick={() => fileRef.current?.click()}
              disabled={uploading}
              className="w-full bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-sm font-medium rounded-lg py-2 transition"
            >
              {uploading ? "Uploading…" : "+ Upload Document"}
            </button>
            <input ref={fileRef} type="file" className="hidden" onChange={handleUpload}
              accept=".pdf,.docx,.pptx,.xlsx,.csv,.zip,.png,.jpg,.jpeg" />
            {uploadError && (
              <p className="text-red-400 text-xs mt-2">{uploadError}</p>
            )}
          </div>

          <div className="flex-1 overflow-y-auto p-3 space-y-2">
            <button
              onClick={() => { setSelectedDoc(null); setMessages([]) }}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition ${
                !selectedDoc ? "bg-blue-900/50 border border-blue-700 text-blue-300" : "text-gray-400 hover:bg-gray-800"
              }`}
            >
              All documents
            </button>

            {docs.map((doc) => (
              <div
                key={doc.id}
                onClick={() => { if (doc.status === "ready") { setSelectedDoc(doc); setMessages([]) } }}
                className={`rounded-lg px-3 py-2.5 cursor-pointer transition group ${
                  selectedDoc?.id === doc.id
                    ? "bg-blue-900/50 border border-blue-700"
                    : doc.status === "ready" ? "hover:bg-gray-800" : "opacity-50 cursor-not-allowed"
                }`}
              >
                <div className="flex items-start justify-between gap-2">
                  <p className="text-sm text-white truncate">{doc.filename}</p>
                  <button
                    onClick={(e) => { e.stopPropagation(); handleDelete(doc.id) }}
                    className="text-gray-600 hover:text-red-400 text-xs opacity-0 group-hover:opacity-100 transition shrink-0"
                  >
                    ✕
                  </button>
                </div>
                <div className="flex items-center gap-2 mt-1">
                  <span className={`text-xs px-1.5 py-0.5 rounded ${
                    doc.status === "ready" ? "bg-green-900/50 text-green-400" :
                    doc.status === "processing" ? "bg-yellow-900/50 text-yellow-400" :
                    "bg-red-900/50 text-red-400"
                  }`}>
                    {doc.status}
                  </span>
                  <span className="text-xs text-gray-500">{formatSize(doc.file_size)}</span>
                  {doc.chunk_count > 0 && (
                    <span className="text-xs text-gray-600">{doc.chunk_count} chunks</span>
                  )}
                </div>
              </div>
            ))}

            {docs.length === 0 && (
              <p className="text-gray-600 text-xs text-center mt-4">No documents yet. Upload one to get started.</p>
            )}
          </div>
        </aside>

        {/* Main — chat */}
        <main className="flex-1 flex flex-col overflow-hidden">
          {/* Context header */}
          <div className="px-6 py-3 border-b border-gray-800 text-sm text-gray-400">
            {selectedDoc
              ? <>Searching in <span className="text-white">{selectedDoc.filename}</span></>
              : <>Searching across <span className="text-white">{docs.filter(d => d.status === "ready").length} ready documents</span></>
            }
          </div>

          {/* Messages */}
          <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
            {messages.length === 0 && (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="text-4xl mb-4">🔍</div>
                <h2 className="text-xl font-semibold mb-2">Ask anything about your documents</h2>
                <p className="text-gray-500 text-sm max-w-sm">
                  Upload a PDF, DOCX, PPTX, Excel, CSV, ZIP or image and ask questions in plain English.
                </p>
              </div>
            )}

            {messages.map((msg, i) => (
              <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
                <div className={`max-w-2xl rounded-2xl px-5 py-3.5 ${
                  msg.role === "user"
                    ? "bg-blue-600 text-white"
                    : "bg-gray-900 border border-gray-800 text-gray-100"
                }`}>
                  <p className="text-sm leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                  {msg.sources && msg.sources.length > 0 && (
                    <details className="mt-3">
                      <summary className="text-xs text-gray-500 cursor-pointer hover:text-gray-400">
                        {msg.sources.length} source chunk(s)
                      </summary>
                      <div className="mt-2 space-y-1.5">
                        {msg.sources.map((s, si) => (
                          <p key={si} className="text-xs text-gray-500 bg-gray-800 rounded px-2 py-1.5 line-clamp-2">
                            {s.content}
                          </p>
                        ))}
                      </div>
                    </details>
                  )}
                </div>
              </div>
            ))}

            {searching && (
              <div className="flex justify-start">
                <div className="bg-gray-900 border border-gray-800 rounded-2xl px-5 py-3.5">
                  <div className="flex gap-1.5 items-center">
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "0ms" }} />
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "150ms" }} />
                    <span className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: "300ms" }} />
                  </div>
                </div>
              </div>
            )}
            <div ref={bottomRef} />
          </div>

          {/* Input */}
          <form onSubmit={handleSearch} className="px-6 py-4 border-t border-gray-800 flex gap-3">
            <input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="Ask a question about your documents…"
              disabled={searching}
              className="flex-1 bg-gray-900 border border-gray-700 rounded-xl px-4 py-3 text-sm text-white placeholder-gray-500 focus:outline-none focus:border-blue-500 transition"
            />
            <button
              type="submit"
              disabled={searching || !query.trim()}
              className="bg-blue-600 hover:bg-blue-500 disabled:opacity-50 text-white px-5 py-3 rounded-xl text-sm font-medium transition"
            >
              Ask
            </button>
          </form>
        </main>
      </div>
    </div>
  )
}
