import { agentBaseUrl } from './env-chat.js'
import store from '../../store'

/**
 * AI 客服聊天 API（非流式，兼容保留）
 */
export function aiChat({ message, user_id, session_id }) {
  return new Promise((resolve, reject) => {
    uni.request({
      url: agentBaseUrl + '/api/chat',
      method: 'POST',
      dataType: 'json',
      header: {
        'content-type': 'application/json',
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

/**
 * AI 客服聊天 API（SSE 流式）
 *
 * 用法：
 *   aiChatStream({
 *     message, user_id, session_id,
 *     onStatus: (text) => {},      // 状态更新（"正在分析..."）
 *     onContent: (chunk) => {},    // 内容增量
 *     onMeta: (meta) => {},        // 元数据（intent, compliance）
 *     onDone: (fullText) => {},    // 完成
 *     onError: (err) => {},        // 错误
 *   })
 */
export function aiChatStream({ message, user_id, session_id, onStatus, onContent, onMeta, onDone, onError }) {
  // uni-app H5 环境用 fetch + ReadableStream
  // #ifdef H5
  return _h5Stream({ message, user_id, session_id, onStatus, onContent, onMeta, onDone, onError })
  // #endif

  // #ifndef H5
  // 小程序环境用 uni.request + 轮询（暂不支持 SSE，回退到非流式）
  return aiChat({ message, user_id, session_id })
    .then((data) => {
      onStatus && onStatus('正在生成回复...')
      onContent && onContent(data.response || '')
      onMeta && onMeta({ intent: data.intent, compliance_passed: data.compliance_passed })
      onDone && onDone(data.response)
    })
    .catch((err) => {
      onError && onError(err)
    })
  // #endif
}

/**
 * H5 环境：用 fetch API 消费 SSE 流
 */
function _h5Stream({ message, user_id, session_id, onStatus, onContent, onMeta, onDone, onError }) {
  const url = agentBaseUrl + '/api/chat/stream'

  fetch(url, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      'authentication': store.state.token || ''
    },
    body: JSON.stringify({ message, user_id, session_id })
  }).then(async (response) => {
    if (!response.ok) {
      const errText = await response.text()
      onError && onError(new Error(errText || 'HTTP ' + response.status))
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''
    let fullText = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // SSE 事件以 \n\n 分隔
      const parts = buffer.split('\n\n')
      buffer = parts.pop()  // 最后一段可能不完整，留着下次拼

      for (const part of parts) {
        const line = part.trim()
        if (!line.startsWith('data: ')) continue

        try {
          const event = JSON.parse(line.slice(6))  // 去掉 "data: " 前缀

          switch (event.type) {
            case 'status':
              onStatus && onStatus(event.text)
              break
            case 'content':
              fullText += event.text
              onContent && onContent(fullText)
              break
            case 'meta':
              onMeta && onMeta(event)
              break
            case 'error':
              onError && onError(new Error(event.text))
              return
            case 'done':
              onDone && onDone(fullText)
              return
          }
        } catch (e) {
          // 解析失败，跳过
        }
      }
    }

    // 流结束但没有收到 done 事件
    onDone && onDone(fullText)
  }).catch((err) => {
    onError && onError(err)
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