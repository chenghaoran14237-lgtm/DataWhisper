import client from './client'
import type { ExcelUploadResponse, MessagesPage, Artifact } from './types'

export const uploadExcel = (file: File, sessionId?: string) => {
  const formData = new FormData()
  formData.append('file', file)
  if (sessionId) formData.append('session_id', sessionId)
  return client.post<any, ExcelUploadResponse>('/api/excel/upload', formData)
}

export const chatExcel = (data: { session_id: string; upload_id: string; message: string }) => {
  return client.post<any, { reply: string; artifacts: Artifact[] }>('/api/excel/chat', data)
}

export const listMessages = (sessionId: string) => {
  return client.get<any, MessagesPage>(`/api/sessions/${sessionId}/messages`)
}