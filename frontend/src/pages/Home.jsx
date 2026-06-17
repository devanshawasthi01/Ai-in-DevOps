import { useEffect, useState } from 'react'
import Sidebar from '../components/Sidebar'
import ChatWindow from '../components/ChatWindow'
import {
  getSessions,
  createSession,
  renameSession,
  deleteSession,
} from '../api/sessions'

const LS_SESSION = 'ttd_active_session'
const LS_DOC     = 'ttd_doc_id'
const LS_DOC_URL = 'ttd_doc_url'

export default function Home() {
  const [sessions,        setSessions]        = useState([])
  const [activeSessionId, setActiveSessionId] = useState(() => localStorage.getItem(LS_SESSION) || null)
  const [docId,           setDocId]           = useState(() => localStorage.getItem(LS_DOC) || null)
  const [docUrl,          setDocUrl]          = useState(() => localStorage.getItem(LS_DOC_URL) || null)

  // Persist active session + docId + doc url across reloads.
  useEffect(() => {
    activeSessionId ? localStorage.setItem(LS_SESSION, activeSessionId) : localStorage.removeItem(LS_SESSION)
  }, [activeSessionId])

  useEffect(() => {
    docId ? localStorage.setItem(LS_DOC, docId) : localStorage.removeItem(LS_DOC)
  }, [docId])

  useEffect(() => {
    docUrl ? localStorage.setItem(LS_DOC_URL, docUrl) : localStorage.removeItem(LS_DOC_URL)
  }, [docUrl])

  const loadSessions = () =>
    getSessions().then((r) => setSessions(r.data)).catch(console.error)

  useEffect(() => { loadSessions() }, [])

  const handleNew = async () => {
    try {
      const r = await createSession()
      setSessions((prev) => [r.data, ...prev])
      setActiveSessionId(r.data.id)
    } catch (e) { console.error(e) }
  }

  const handleSelect = (id) => setActiveSessionId(id)

  const handleRename = async (id, title) => {
    try {
      await renameSession(id, title)
      setSessions((prev) => prev.map((s) => (s.id === id ? { ...s, title } : s)))
    } catch (e) { console.error(e) }
  }

  const handleDelete = async (id) => {
    if (!window.confirm('Delete this conversation and all its messages?')) return
    try {
      await deleteSession(id)
      setSessions((prev) => prev.filter((s) => s.id !== id))
      if (activeSessionId === id) setActiveSessionId(null)
    } catch (e) { console.error(e) }
  }

  const handleDocLoaded = (id, url) => {
    setDocId(id)
    if (url) setDocUrl(url)
  }

  return (
    <div className="flex h-screen overflow-hidden bg-canvas text-ink font-sans">
      <Sidebar
        sessions={sessions}
        activeSessionId={activeSessionId}
        onSelect={handleSelect}
        onNew={handleNew}
        onRename={handleRename}
        onDelete={handleDelete}
      />
      <ChatWindow
        sessionId={activeSessionId}
        docId={docId}
        docUrlLabel={docUrl}
        onDocLoaded={handleDocLoaded}
        onSessionUpdated={loadSessions}
      />
    </div>
  )
}
