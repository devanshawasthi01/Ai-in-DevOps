import { useState } from 'react'

function fmtDate(dt) {
  if (!dt) return ''
  // SQLite returns UTC without Z — append it so Date parses correctly
  return new Date(dt.endsWith('Z') ? dt : dt + 'Z').toLocaleDateString([], {
    month: 'short',
    day: 'numeric',
  })
}

export default function SessionItem({ session, isActive, onSelect, onRename, onDelete }) {
  const [editing, setEditing] = useState(false)
  const [draft, setDraft]     = useState('')

  const startEdit = (e) => {
    e.stopPropagation()
    setDraft(session.title || '')
    setEditing(true)
  }

  const commitRename = (e) => {
    e?.stopPropagation()
    if (draft.trim()) onRename(session.id, draft.trim())
    setEditing(false)
  }

  const cancelEdit = (e) => {
    e?.stopPropagation()
    setEditing(false)
  }

  return (
    <div
      onClick={() => !editing && onSelect(session.id)}
      className={`group relative flex flex-col px-3 py-2 rounded-xl cursor-pointer mb-0.5 transition-colors ${
        isActive ? 'bg-white/10 text-ink' : 'hover:bg-white/5 text-slate-300'
      }`}
    >
      {editing ? (
        <div className="flex items-center gap-1" onClick={(e) => e.stopPropagation()}>
          <input
            autoFocus
            className="flex-1 text-sm bg-slate-900 border border-userBubble rounded-md px-1.5 py-0.5 outline-none text-ink"
            value={draft}
            onChange={(e) => setDraft(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter')  commitRename()
              if (e.key === 'Escape') cancelEdit()
            }}
          />
          <button onClick={commitRename} className="text-green-400 hover:text-green-300 text-xs font-bold px-1">✓</button>
          <button onClick={cancelEdit}   className="text-slate-400 hover:text-slate-200 text-xs px-1">✕</button>
        </div>
      ) : (
        <>
          <span className="text-sm truncate pr-12 font-medium">
            {session.title || <span className="italic text-slate-500">Untitled</span>}
          </span>
          <span className="text-[11px] text-slate-500 mt-0.5">
            {fmtDate(session.updated_at)} · {session.message_count ?? 0} msgs
          </span>

          {/* hover actions */}
          <div className="absolute right-2 top-1.5 hidden group-hover:flex gap-0.5">
            <button
              onClick={startEdit}
              title="Rename"
              className="p-1 rounded-md hover:bg-white/10 text-slate-400 hover:text-userBubble transition-colors text-xs"
            >
              ✏
            </button>
            <button
              onClick={(e) => { e.stopPropagation(); onDelete(session.id) }}
              title="Delete"
              className="p-1 rounded-md hover:bg-white/10 text-slate-400 hover:text-red-400 transition-colors text-xs"
            >
              🗑
            </button>
          </div>
        </>
      )}
    </div>
  )
}
