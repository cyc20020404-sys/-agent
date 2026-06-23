import request from '@/utils/request'

/**
 * AI customer service chat APIs.
 * Calls Python FastAPI (port 8000) directly with full URL.
 * CORS is enabled on the FastAPI side (allow_origins=["*"]).
 * The axios interceptor in request.ts automatically attaches the `token` header
 * for JWT passthrough to the Spring Boot backend.
 *
 * Use VUE_APP_AI_URL from env, fallback to http://localhost:8000
 */

const AI_BASE = process.env.VUE_APP_AI_URL || 'http://localhost:8000'

export interface ChatResponse {
  response: string
  session_id: string
  intent: string
  compliance_passed: boolean
}

export const aiChat = (data: {
  message: string
  user_id: string
  session_id?: string
}) =>
  request({
    baseURL: AI_BASE,
    url: '/api/chat',
    method: 'post',
    data
  }) as Promise<{ data: ChatResponse }>

export const aiChatHistory = (sessionId: string) =>
  request({
    baseURL: AI_BASE,
    url: `/api/history/${sessionId}`,
    method: 'get'
  })

export const aiTools = () =>
  request({
    baseURL: AI_BASE,
    url: '/api/tools',
    method: 'get'
  })
