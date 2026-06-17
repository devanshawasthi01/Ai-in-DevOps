import { useState } from 'react'
import ReactMarkdown from 'react-markdown'

const markdownComponents = {
  p:    ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
  ul:   ({ children }) => <ul className="list-disc list-inside mb-2 space-y-0.5">{children}</ul>,
  ol:   ({ children }) => <ol className="list-decimal list-inside mb-2 space-y-0.5">{children}</ol>,
  li:   ({ children }) => <li className="ml-2">{children}</li>,
  h1:   ({ children }) => <h1 className="text-base font-bold mb-1">{children}</h1>,
  h2:   ({ children }) => <h2 className="text-sm font-bold mb-1">{children}</h2>,
  h3:   ({ children }) => <h3 className="text-sm font-semibold mb-1">{children}</h3>,
  strong: ({ children }) => <strong className="font-semibold">{children}</strong>,
  a:    ({ href, children }) => (
    <a href={href} target="_blank" rel="noopener noreferrer" className="text-blue-300 underline hover:text-blue-200">
      {children}
    </a>
  ),
  blockquote: ({ children }) => (
    <blockquote className="border-l-4 border-white/20 pl-3 italic text-slate-300 mb-2">{children}</blockquote>
  ),
  pre: ({ children }) => (
    <pre className="bg-slate-950 rounded-lg px-3 py-2.5 text-xs font-mono overflow-x-auto my-1.5 whitespace-pre scroll-dark">
      {children}
    </pre>
  ),
  code: ({ className, children }) =>
    className ? (
      <code className="text-green-300">{children}</code>
    ) : (
      <code className="bg-white/10 text-ink rounded px-1 py-0.5 text-xs font-mono">{children}</code>
    ),
}

export default function MessageBubble({ role, content, meta }) {
  const isUser = role === 'user'

  return (
    <div className={`flex gap-3 mb-5 animate-fadeInUp ${isUser ? 'flex-row-reverse' : 'flex-row'}`}>
      {/* Avatar */}
      <div
        className={`grid h-8 w-8 shrink-0 place-items-center rounded-full text-xs font-semibold ${
          isUser ? 'bg-userBubble text-white' : 'bg-botBubble text-ink'
        }`}
      >
        {isUser ? 'You' : 'AI'}
      </div>

      {/* Bubble + sources */}
      <div className={`min-w-0 max-w-[80%] ${isUser ? 'items-end text-right' : 'items-start'} flex flex-col`}>
        <div
          className={`px-4 py-2.5 rounded-2xl text-sm leading-relaxed text-left ${
            isUser
              ? 'bg-userBubble text-white rounded-tr-sm whitespace-pre-wrap'
              : 'bg-botBubble text-ink rounded-tl-sm'
          }`}
        >
          {isUser ? (
            content
          ) : (
            <ReactMarkdown components={markdownComponents}>{content}</ReactMarkdown>
          )}
        </div>

        {!isUser && meta && <Sources meta={meta} />}
      </div>
    </div>
  )
}

function Sources({ meta }) {
  const [open, setOpen] = useState(false)
  const sources = Array.isArray(meta.sources) ? meta.sources : []
  if (sources.length === 0) return null

  return (
    <div className="mt-2 w-full">
      <button
        onClick={() => setOpen((v) => !v)}
        className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-slate-200 transition-colors"
      >
        <span className={`transition-transform ${open ? 'rotate-90' : ''}`}>▸</span>
        Sources
        <span className="text-slate-500">({sources.length})</span>
        {meta.score != null && (
          <span className="ml-1 rounded bg-white/10 px-1.5 py-0.5 font-mono text-[11px] text-slate-300">
            sim {Number(meta.score).toFixed(2)}
          </span>
        )}
        {meta.refused && (
          <span className="ml-1 rounded bg-red-500/15 px-1.5 py-0.5 text-[11px] text-red-300">not grounded</span>
        )}
      </button>

      {/* Always-visible chunk chips */}
      <div className="mt-1.5 flex flex-wrap gap-1.5">
        {sources.map((s, i) => (
          <span
            key={i}
            title={typeof s === 'object' ? (s.preview || '') : String(s)}
            className={`rounded-md px-2 py-0.5 text-[11px] font-mono ${
              s && s.sent_to_llm === false
                ? 'bg-white/5 text-slate-500'
                : 'bg-userBubble/15 text-blue-200'
            }`}
          >
            [Chunk {i + 1}]
            {typeof s === 'object' && s.similarity != null ? ` ${Number(s.similarity).toFixed(2)}` : ''}
          </span>
        ))}
      </div>

      {/* Expanded previews */}
      {open && (
        <ul className="mt-2 space-y-2">
          {sources.map((s, i) => (
            <SourceCard key={i} index={i} source={s} />
          ))}
        </ul>
      )}
    </div>
  )
}

function SourceCard({ index, source: s }) {
  const isObj    = typeof s === 'object' && s !== null
  const preview  = isObj ? (s.preview ?? s.text ?? s.content ?? s.chunk ?? null) : String(s)
  const url      = isObj ? (s.url ?? s.source ?? null) : null
  const sim      = isObj ? (s.similarity ?? s.score ?? null) : null
  const belowLLM = isObj && s.sent_to_llm === false

  return (
    <li className="rounded-lg border border-white/10 bg-black/20 p-2.5 text-xs text-slate-300">
      <div className="mb-1 flex items-center gap-2">
        <span className="font-mono text-blue-200">[Chunk {index + 1}]</span>
        {sim != null && (
          <span className="rounded bg-white/10 px-1.5 py-0.5 font-mono text-[11px] text-slate-300">
            {Number(sim).toFixed(2)}
          </span>
        )}
        {belowLLM && <span className="italic text-slate-500">below threshold</span>}
      </div>
      {preview && (
        <p className="leading-relaxed text-slate-300/90 break-words">
          {preview.slice(0, 220)}{preview.length > 220 ? '…' : ''}
        </p>
      )}
      {url && (
        <a
          href={url}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-1 inline-block break-all text-blue-300 underline hover:text-blue-200"
        >
          {url}
        </a>
      )}
    </li>
  )
}
