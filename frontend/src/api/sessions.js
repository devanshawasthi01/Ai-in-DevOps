import client from './client'

export const getSessions  = ()         => client.get('/sessions')
export const createSession = (title)   => client.post('/sessions/create', title ? { title } : {})
export const getSession   = (id)       => client.get(`/sessions/${id}`)
export const getMessages  = (id)       => client.get(`/sessions/${id}/messages`)
export const renameSession = (id, title) => client.patch(`/sessions/${id}`, { title })
export const deleteSession = (id)      => client.delete(`/sessions/${id}`)
