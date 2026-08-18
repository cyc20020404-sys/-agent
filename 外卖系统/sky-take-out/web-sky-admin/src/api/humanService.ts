import axios from 'axios'

/**
 * Human agent handoff service APIs.
 * Calls Python FastAPI (:8000) directly — CORS is enabled on the Python side.
 */

const AI_BASE = process.env.VUE_APP_AI_URL || 'http://localhost:8000'

const http = axios.create({
  baseURL: AI_BASE,
  timeout: 15000,
  withCredentials: false
})

export interface HandoffSession {
  session_id: string
  user_id: string
  status: string
  message_count: number
  agent_id: string
  agent_name: string
  created_at: string
  accepted_at: string
  resolved_at: string
}

export interface HandoffMessage {
  role: string
  content: string
  timestamp: string
}

export const listHumanQueue = () =>
  http.get('/api/human-queue')

export const acceptSession = (sessionId: string, agentId?: string, agentName?: string) =>
  http.post(`/api/human-queue/${sessionId}/accept`, {
    agent_id: agentId || 'admin',
    agent_name: agentName || '管理员'
  })

export const agentReply = (sessionId: string, message: string) =>
  http.post(`/api/human-queue/${sessionId}/reply`, { message })

export const getSessionMessages = (sessionId: string, since?: number) =>
  http.get(`/api/human-queue/${sessionId}/messages`, {
    params: { since: since || 0 }
  })
