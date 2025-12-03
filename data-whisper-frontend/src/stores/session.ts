import { defineStore } from 'pinia'
import { ref } from 'vue'
import type { ExcelProfile } from '../api/types'

export const useSessionStore = defineStore('session', () => {
  const sessionId = ref<string | null>(localStorage.getItem('dw_session_id'))
  const uploadId = ref<string | null>(localStorage.getItem('dw_upload_id'))
  const filename = ref<string | null>(localStorage.getItem('dw_filename'))
  const profileStr = localStorage.getItem('dw_profile')
  const profile = ref<ExcelProfile | null>(profileStr ? JSON.parse(profileStr) : null)

  function saveSessionInfo(sid: string, uid: string, fname: string, prof: ExcelProfile) {
    sessionId.value = sid; uploadId.value = uid; filename.value = fname; profile.value = prof;
    localStorage.setItem('dw_session_id', sid)
    localStorage.setItem('dw_upload_id', uid)
    localStorage.setItem('dw_filename', fname)
    localStorage.setItem('dw_profile', JSON.stringify(prof))
  }

  function clearSession() {
    sessionId.value = null; uploadId.value = null; filename.value = null; profile.value = null;
    localStorage.removeItem('dw_session_id'); localStorage.removeItem('dw_upload_id');
    localStorage.removeItem('dw_filename'); localStorage.removeItem('dw_profile');
  }

  return { sessionId, uploadId, filename, profile, saveSessionInfo, clearSession }
})