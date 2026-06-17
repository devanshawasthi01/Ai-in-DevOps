import SessionItem from './SessionItem'

export default function Sidebar({ sessions, activeSessionId, onSelect, onNew, onRename, onDelete }) {
  return (
    <div className="w-64 shrink-0 bg-sidebar border-r border-white/10 flex flex-col h-full">
      {/* Header / brand */}
      <div className="p-3 shrink-0">
        <div className="flex items-center gap-2 px-1 pb-3">
          <span className="grid h-7 w-7 place-items-center rounded-lg bg-userBubble text-sm">📄</span>
          <h1 className="font-semibold text-ink text-[15px] tracking-tight">Talk To Docs</h1>
        </div>
        <button
          onClick={onNew}
          className="w-full flex items-center gap-2 border border-white/15 hover:bg-white/5 text-ink text-sm font-medium py-2.5 px-3 rounded-xl transition-colors"
        >
          <PlusIcon />
          New Chat
        </button>
      </div>

      {/* Conversation history */}
      <div className="flex-1 overflow-y-auto scroll-dark px-2 pb-2">
        <p className="px-2 pt-2 pb-1 text-[11px] font-semibold uppercase tracking-wider text-slate-500">
          Conversations
        </p>
        {sessions.length === 0 ? (
          <p className="text-xs text-slate-500 text-center mt-6 px-3 leading-relaxed">
            No conversations yet. Click <span className="text-slate-300">New Chat</span> to start.
          </p>
        ) : (
          sessions.map((s) => (
            <SessionItem
              key={s.id}
              session={s}
              isActive={s.id === activeSessionId}
              onSelect={onSelect}
              onRename={onRename}
              onDelete={onDelete}
            />
          ))
        )}
      </div>

      {/* Footer */}
      <div className="p-3 border-t border-white/10 shrink-0 text-[11px] text-slate-500 text-center">
        {sessions.length} session{sessions.length !== 1 ? 's' : ''}
      </div>
    </div>
  )
}

function PlusIcon() {
  return (
    <svg className="h-4 w-4 shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round">
      <path d="M12 5v14M5 12h14" />
    </svg>
  )
}
