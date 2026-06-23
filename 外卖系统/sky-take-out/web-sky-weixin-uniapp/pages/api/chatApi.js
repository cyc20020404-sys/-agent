import { agentBaseUrl } from './env-chat.js'
import store from '../../store'

/**
 * AI 客服聊天 API
 * 调用 Python FastAPI Agent (:8000)
 * 用户 JWT 通过 authentication header 透传
 */
export function aiChat({ message, user_id, session_id }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: agentBaseUrl + '/api/chat',
      method: 'POST',
      header: {
        'Content-Type': 'application/json',
        'authentication': store.state.token || ''
      },
      data: { message, user_id, session_id },
      success: (res) => {
        if (res.data && res.data.response !== undefined) {
          resolve(res.data)
        } else {
          reject(res.data || { detail: '未知错误' })
        }
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}

export function aiChatHistory(sessionId) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: agentBaseUrl + `/api/history/${sessionId}`,
      method: 'GET',
      header: {
        'authentication': store.state.token || ''
      },
      success: (res) => {
        resolve(res.data)
      },
      fail: (err) => {
        reject(err)
      }
    })
  })
}
