import { useEffect, useRef, useState } from 'react'
import MessageBubble from './MessageBubble'
import { ingestUrl, sendMessage } from '../api/chat'
import { getMessages } from '../api/sessions'

// Ingest progress stages. /ingest is a single synchronous backend call, so these
// are advanced client-side while the request is in flight (no backend change).
const STAGES = ['Fetching document…', 'Chunking content…', 'Building embeddings…', 'Ready']

const looksLikeUrl = (s) => /^https?:\/\/.+\..+/i.test(s.trim())

export default function ChatWindow({ sessionId, docId, docUrlLabel, onDocLoaded, onSessionUpdated }) {
  const [messages,  setMessages]  = useState([])
  const [input,     setInput]     = useState('')
  const [loading,   setLoading]   = useState(false)
  const [docUrl,    setDocUrl]    = useState('')
  const [docStatus, setDocStatus] = useState(null) // null | {state, stage?, chunks?, message?}
  const [showPanel, setShowPanel] = useState(false)
  const bottomRef = useRef(null)
  const stageTimer = useRef(null)

  // Load history when the active session changes.
  useEffect(() => {
    if (!sessionId) { setMessages([]); return }
    getMessages(sessionId)
      .then((r) => setMessages(r.data))
      .catch(() => setMessages([]))
  }, [sessionId])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  // Mark doc ready when parent restores docId from localStorage.
  // Intentionally keyed on docId only; the docStatus guard prevents re-runs.
  useEffect(() => {
    if (docId && !docStatus) setDocStatus({ state: 'ok', stage: 3, chunks: null })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [docId])

  useEffect(() => () => clearInterval(stageTimer.current), [])

  const handleIngest = async () => {
    const url = docUrl.trim()
    if (!url || docStatus?.state === 'loading') return
    if (!looksLikeUrl(url)) {
      setDocStatus({ state: 'error', message: 'That doesn’t look like a valid URL. Use http:// or https://' })
      return
    }

    // Simulate staged progress while the synchronous request runs.
    setDocStatus({ state: 'loading', stage: 0 })
    clearInterval(stageTimer.current)
    stageTimer.current = setInterval(() => {
      setDocStatus((s) =>
        s?.state === 'loading' ? { ...s, stage: Math.min((s.stage ?? 0) + 1, 2) } : s
      )
    }, 1100)

    try {
      const r = await ingestUrl(url)
      const { document_id, chunks_count } = r.data
      clearInterval(stageTimer.current)
      if (!chunks_count) {
        setDocStatus({ state: 'error', message: 'The document appears to be empty — no content was extracted.' })
        return
      }
      setDocStatus({ state: 'ok', stage: 3, chunks: chunks_count })
      onDocLoaded(document_id, url)
      setDocUrl('')
      setTimeout(() => setShowPanel(false), 700) // let "Ready" show briefly
    } catch (err) {
      clearInterval(stageTimer.current)
      setDocStatus({ state: 'error', message: friendlyError(err) })
    }
  }

  const handleSend = async () => {
    const q = input.trim()
    if (!q || !sessionId || !docId || loading) return
    setInput('')
    setMessages((prev) => [...prev, { role: 'user', content: q }])
    setLoading(true)
    try {
      const r = await sendMessage(docId, q, sessionId)
      const data = r.data
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: data.answer,
          meta: {
            score: data.score,
            chunks_used: data.chunks_used,
            sources: data.sources,
            refused: data.refused,
          },
        },
      ])
      onSessionUpdated?.()
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        { role: 'assistant', content: '⚠ ' + friendlyError(err) },
      ])
    } finally {
      setLoading(false)
    }
  }

  // No active session — invite the user to start one.
  if (!sessionId) {
    return (
      <div className="flex-1 flex flex-col items-center justify-center bg-chat text-center px-6">
        <div className="grid h-14 w-14 place-items-center rounded-2xl bg-userBubble/20 text-2xl mb-4">📄</div>
        <h2 className="text-xl font-semibold text-ink">Talk To Docs</h2>
        <p className="mt-2 max-w-sm text-sm text-slate-400">
          Click <span className="text-slate-200 font-medium">New Chat</span> in the sidebar, paste a documentation
          URL, and ask questions answered only from that document.
        </p>
      </div>
    )
  }

  const isDocLoading = docStatus?.state === 'loading'
  const panelOpen = !docId || showPanel

  return (
    <div className="flex-1 flex flex-col min-w-0 bg-chat">
      {/* Top bar */}
      <div className="flex items-center justify-between border-b border-white/10 px-5 py-3 shrink-0">
        <div className="min-w-0">
          <h2 className="text-[15px] font-semibold text-ink leading-tight">Talk To Docs</h2>
          <p className="truncate text-xs text-slate-400">
            {docId
              ? <>Loaded: <span className="text-slate-300">{docUrlLabel || 'document'}</span></>
              : 'No document loaded yet'}
          </p>
        </div>
        {docId && (
          <button
            onClick={() => { setShowPanel(true); setDocStatus(null) }}
            className="shrink-0 rounded-lg border border-white/15 px-3 py-1.5 text-xs text-slate-300 hover:bg-white/5 transition-colors"
          >
            Load another doc
          </button>
        )}
      </div>

      {/* URL submission panel */}
      {panelOpen && (
        <div className="border-b border-white/10 px-5 py-4 shrink-0">
          <div className="mx-auto max-w-2xl">
            <label className="mb-1.5 block text-xs font-medium text-slate-400">Documentation URL</label>
            <div className="flex items-center gap-2">
              <input
                className="flex-1 rounded-xl border border-white/15 bg-canvas px-3.5 py-2.5 text-sm text-ink placeholder:text-slate-500 outline-none focus:border-userBubble disabled:opacity-50"
                placeholder="https://docs.example.com/guide"
                value={docUrl}
                disabled={isDocLoading}
                onChange={(e) => { setDocUrl(e.target.value); if (docStatus?.state === 'error') setDocStatus(null) }}
                onKeyDown={(e) => e.key === 'Enter' && handleIngest()}
              />
              <button
                onClick={handleIngest}
                disabled={isDocLoading || !docUrl.trim()}
                className="shrink-0 flex items-center gap-1.5 rounded-xl bg-userBubble px-4 py-2.5 text-sm font-medium text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
              >
                {isDocLoading ? <><Spinner /> Processing…</> : 'Process'}
              </button>
            </div>

            {/* Progress states */}
            {isDocLoading && <ProgressSteps stage={docStatus.stage ?? 0} />}
            {docStatus?.state === 'ok' && (
              <p className="mt-2 text-xs font-medium text-green-400">
                ✓ Ready{docStatus.chunks != null ? ` — ${docStatus.chunks} chunks embedded` : ''}
              </p>
            )}
            {docStatus?.state === 'error' && (
              <p className="mt-2 rounded-lg bg-red-500/10 border border-red-500/30 px-3 py-2 text-xs text-red-300">
                ✗ {docStatus.message}
              </p>
            )}
          </div>
        </div>
      )}

      {/* Messages */}
      <div className="flex-1 overflow-y-auto scroll-dark px-4 py-6">
        <div className="mx-auto max-w-3xl">
          {messages.length === 0 && !panelOpen && (
            <p className="mt-16 text-center text-sm text-slate-400">
              Ask a question about the loaded document.
            </p>
          )}
          {messages.length === 0 && panelOpen && docId && (
            <p className="mt-16 text-center text-sm text-slate-400">
              Document ready — ask your first question below.
            </p>
          )}
          {messages.map((m, i) => (
            <MessageBubble key={i} role={m.role} content={m.content} meta={m.meta} />
          ))}
          {loading && (
            <div className="flex gap-3 mb-5">
              <div className="grid h-8 w-8 shrink-0 place-items-center rounded-full bg-botBubble text-xs font-semibold text-ink">AI</div>
              <div className="flex items-center gap-1.5 rounded-2xl rounded-tl-sm bg-botBubble px-4 py-3">
                <Dot /><Dot delay="0.2s" /><Dot delay="0.4s" />
              </div>
            </div>
          )}
          <div ref={bottomRef} />
        </div>
      </div>

      {/* Composer */}
      <div className="px-4 pb-5 pt-2 shrink-0">
        <div className="mx-auto max-w-3xl">
          <div className="flex items-end gap-2 rounded-2xl border border-white/15 bg-canvas px-3 py-2 focus-within:border-userBubble transition-colors">
            <textarea
              rows={1}
              className="flex-1 resize-none bg-transparent px-1.5 py-1.5 text-sm text-ink placeholder:text-slate-500 outline-none max-h-40 scroll-dark"
              placeholder={
                !docId  ? 'Load a document first…' :
                loading ? 'Waiting for response…' :
                          'Message Talk To Docs…  (Enter to send, Shift+Enter for newline)'
              }
              value={input}
              disabled={!docId || loading}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() }
              }}
            />
            <button
              onClick={handleSend}
              disabled={!docId || !input.trim() || loading}
              className="shrink-0 grid h-9 w-9 place-items-center rounded-xl bg-userBubble text-white hover:bg-blue-500 disabled:opacity-40 transition-colors"
              title="Send"
            >
              {loading ? <Spinner /> : <SendIcon />}
            </button>
          </div>
          <p className="mt-1.5 text-center text-[11px] text-slate-500">
            Answers are grounded only in the loaded document.
          </p>
        </div>
      </div>
    </div>
  )
}

function ProgressSteps({ stage }) {
  return (
    <div className="mt-3 space-y-1.5">
      {STAGES.map((label, i) => {
        const done = i < stage
        const active = i === stage
        return (
          <div key={label} className="flex items-center gap-2 text-xs">
            {done ? (
              <span className="text-green-400">✓</span>
            ) : active ? (
              <Spinner className="text-userBubble" />
            ) : (
              <span className="text-slate-600">○</span>
            )}
            <span className={done ? 'text-slate-400' : active ? 'text-ink' : 'text-slate-600'}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function friendlyError(err) {
  if (err.response) {
    const status = err.response.status
    const detail = err.response.data?.detail
    if (status === 422) return detail || 'The document could not be processed (it may be empty or unreachable).'
    if (status === 404) return detail || 'Session not found. Start a new chat.'
    if (status >= 500) return 'The backend hit an error processing this request. Please try again.'
    return detail || `Request failed (${status}).`
  }
  if (err.request) return 'Could not reach the backend. Is it running on http://localhost:8000?'
  return err.message || 'Something went wrong.'
}

function Spinner({ className = '' }) {
  return (
    <svg className={`h-3.5 w-3.5 shrink-0 animate-spin ${className}`} xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
    </svg>
  )
}

function Dot({ delay = '0s' }) {
  return <span className="h-1.5 w-1.5 rounded-full bg-slate-400 animate-blink" style={{ animationDelay: delay }} />
}

function SendIcon() {
  return (
    <svg className="h-4 w-4" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
      <path d="M22 2 11 13M22 2l-7 20-4-9-9-4 20-7z" />
    </svg>
  )
}
