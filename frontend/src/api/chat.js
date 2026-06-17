import client from './client'

export const ingestUrl = (url) =>
  client.post('/ingest', { url })

export const sendMessage = (documentId, question, sessionId) =>
  client.post('/chat', {
    document_id: documentId,
    question,
    session_id: sessionId,
  })
