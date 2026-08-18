<template>
  <div class="human-service-container">
    <!-- Queue Sidebar -->
    <div class="queue-sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">升级队列</span>
        <el-button type="primary" size="mini" icon="el-icon-refresh" circle :loading="queueLoading" @click="refreshQueue" />
      </div>
      <div v-if="queueError" class="queue-error">
        <i class="el-icon-warning" /> {{ queueError }}
      </div>
      <div class="queue-list">
        <div v-if="queueLoading && sessions.length === 0" class="queue-empty">
          <i class="el-icon-loading" style="font-size:32px;color:#ccc" />
          <p>加载中...</p>
        </div>
        <div v-else-if="!queueError && sessions.length === 0" class="queue-empty">
          <i class="el-icon-chat-line-round" style="font-size:32px;color:#ccc" />
          <p>暂无待处理会话</p>
        </div>
        <div
          v-for="s in sessions"
          :key="s.session_id"
          class="queue-item"
          :class="{ active: s.session_id === activeSessionId }"
          @click="selectSession(s)"
        >
          <div class="queue-item-top">
            <span class="queue-user">{{ s.user_id }}</span>
            <el-tag
              size="mini"
              :type="s.status === 'active' ? 'success' : 'warning'"
            >
              {{ s.status === 'active' ? '已接管' : '等待中' }}
            </el-tag>
          </div>
          <div class="queue-item-meta">
            <span class="queue-time">{{ formatTime(s.created_at) }}</span>
            <span v-if="s.agent_name" class="queue-agent">{{ s.agent_name }}</span>
          </div>
        </div>
      </div>
      <div class="sidebar-footer">
        <div class="footer-row">
          <el-button type="text" size="mini" @click="refreshQueue">
            <i class="el-icon-refresh" /> 手动刷新
          </el-button>
          <span class="footer-debug">{{ debugInfo }}</span>
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <!-- Empty state -->
      <div v-if="!activeSession" class="chat-empty-full">
        <i class="el-icon-headset" style="font-size:64px;color:#ddd" />
        <h3>人工客服工作台</h3>
        <p>选择左侧的升级会话开始处理</p>
      </div>

      <!-- Active chat -->
      <template v-else>
        <div class="chat-header">
          <div class="chat-header-left">
            <span class="chat-title">{{ activeSession.user_id }} 的会话</span>
            <el-tag
              size="mini"
              :type="activeSession.status === 'active' ? 'success' : 'warning'"
            >
              {{ activeSession.status === 'active' ? '已接管' : '待接管' }}
            </el-tag>
            <span class="chat-id">ID: {{ activeSession.session_id.slice(0, 8) }}...</span>
          </div>
          <div class="chat-header-right">
            <el-button
              v-if="activeSession.status === 'queued'"
              type="primary"
              size="small"
              @click="acceptCurrent"
            >
              接管会话
            </el-button>
            <el-button
              v-if="activeSession.status === 'active'"
              type="warning"
              size="small"
              @click="resolveCurrent"
            >
              标记已解决
            </el-button>
          </div>
        </div>

        <div ref="messageList" class="chat-messages">
          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message-row"
            :class="msg.role === 'agent' ? 'agent' : msg.role"
          >
            <div class="message-label">
              {{ msg.role === 'agent' ? '我' : msg.role === 'user' ? '用户' : msg.role === 'assistant' ? '机器人' : '系统' }}
            </div>
            <div class="message-bubble" :class="msg.role">
              <div class="message-content">{{ msg.content }}</div>
              <div class="message-time">{{ formatTime(msg.timestamp) }}</div>
            </div>
          </div>

          <div v-if="loading" class="message-row system">
            <div class="message-bubble typing">
              <span class="dot" /><span class="dot" /><span class="dot" />
            </div>
          </div>
        </div>

        <div class="chat-input" v-if="activeSession.status === 'active'">
          <el-input
            v-model="inputText"
            type="textarea"
            :rows="2"
            placeholder="输入回复，Enter 发送..."
            :disabled="sending"
            @keyup.enter.native="sendReply"
          />
          <el-button
            type="primary"
            :loading="sending"
            :disabled="!inputText.trim()"
            @click="sendReply"
          >
            发送
          </el-button>
        </div>
        <div v-else class="chat-input-disabled">
          <span>请先"接管会话"后再发送消息</span>
        </div>
      </template>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator'
import {
  listHumanQueue,
  acceptSession as apiAccept,
  agentReply as apiReply,
  getSessionMessages,
  HandoffSession,
  HandoffMessage
} from '@/api/humanService'

const AI_BASE = process.env.VUE_APP_AI_URL || 'http://localhost:8000'
const WS_BASE = AI_BASE.replace(/^http/, 'ws')

@Component({ name: 'HumanService' })
export default class extends Vue {
  private sessions: HandoffSession[] = []
  private activeSessionId = ''
  private messages: HandoffMessage[] = []
  private inputText = ''
  private loading = false
  private sending = false
  private queueLoading = false
  private queueError = ''
  private queueTimer: any = null
  private wsAdmin: WebSocket | null = null
  private _wsHeartbeat: any = null
  private lastPollTime = ''

  get activeSession(): HandoffSession | undefined {
    return this.sessions.find((s) => s.session_id === this.activeSessionId)
  }

  get debugInfo(): string {
    const parts = [this.sessions.length + '个会话']
    if (this.queueError) parts.push('❌ ' + this.queueError.substring(0, 20))
    if (this.lastPollTime) parts.push('上次刷新:' + this.lastPollTime)
    const wsState = this.wsAdmin ? (this.wsAdmin.readyState === 1 ? 'WS已连' : 'WS重连中') : 'WS未连'
    parts.push(wsState)
    return parts.join(' | ')
  }

  created() {
    this.refreshQueue()
    this.queueTimer = setInterval(() => {
      this.refreshQueue()
    }, 10000)
  }

  beforeDestroy() {
    if (this.queueTimer) clearInterval(this.queueTimer)
    this.disconnectWS()
  }

  // ── HTTP 队列刷新 ──────────────────────────────────────

  async refreshQueue() {
    this.queueLoading = true
    try {
      const res = await listHumanQueue()
      const data: HandoffSession[] = (res as any).data
      console.log('[人工客服] 队列刷新: ' + (Array.isArray(data) ? data.length + '个会话' : '非数组响应'), data)
      this.lastPollTime = new Date().toLocaleTimeString()
      if (!Array.isArray(data)) {
        console.error('humanService: unexpected queue response', res)
        this.queueError = '返回数据格式异常'
        return
      }
      this.queueError = ''
      this.sessions = data
      if (this.activeSessionId) {
        const updated = this.sessions.find((s) => s.session_id === this.activeSessionId)
        if (!updated) {
          this.activeSessionId = ''
          this.messages = []
        } else if (updated.status === 'resolved') {
          this.activeSessionId = ''
          this.messages = []
          this.$message.info('会话已解决')
        }
      }
    } catch (e) {
      console.error('humanService: refreshQueue failed', e)
      this.queueError = '无法连接人工客服服务 (localhost:8000)，请检查服务是否已启动'
    } finally {
      this.queueLoading = false
    }
  }

  // ── WebSocket 实时通道 ──────────────────────────────────

  connectWS(sessionId: string) {
    this.disconnectWS()
    const url = WS_BASE + '/ws/admin/' + sessionId
    this.wsAdmin = new WebSocket(url)

    this.wsAdmin.onopen = () => {
      console.log('[人工客服] WS connected:', sessionId)
      this._wsHeartbeat = setInterval(() => {
        try { this.wsAdmin!.send(JSON.stringify({ type: 'pong' })) } catch (e) {}
      }, 25000)
    }

    this.wsAdmin.onmessage = (event: MessageEvent) => {
      try {
        const data = JSON.parse(event.data)
        this.wsOnMessage(data)
      } catch (e) {}
    }

    this.wsAdmin.onerror = () => {
      console.warn('[人工客服] WS error, retrying...')
    }

    this.wsAdmin.onclose = () => {
      if (this._wsHeartbeat) clearInterval(this._wsHeartbeat)
      if (this.activeSessionId === sessionId) {
        // 断线 3 秒后重连
        setTimeout(() => {
          if (this.activeSessionId === sessionId) this.connectWS(sessionId)
        }, 3000)
      }
    }
  }

  disconnectWS() {
    if (this._wsHeartbeat) { clearInterval(this._wsHeartbeat); this._wsHeartbeat = null }
    if (this.wsAdmin) {
      try { this.wsAdmin.close() } catch (e) {}
      this.wsAdmin = null
    }
  }

  wsOnMessage(data: any) {
    switch (data.type) {
      case 'user_message':
        this.messages.push({
          role: 'user',
          content: data.content,
          timestamp: data.timestamp || ''
        })
        this.$nextTick(() => this.scrollToBottom())
        break
      case 'user_connected':
        console.log('[人工客服] 用户上线:', data.session_id)
        break
      case 'ping':
        try { this.wsAdmin!.send(JSON.stringify({ type: 'pong' })) } catch (e) {}
        break
    }
  }

  sendWsMessage(content: string) {
    if (!this.wsAdmin || this.wsAdmin.readyState !== 1) return
    this.wsAdmin.send(JSON.stringify({ type: 'agent_message', content }))
  }

  // ── 会话控制 ────────────────────────────────────────────

  selectSession(session: HandoffSession) {
    this.activeSessionId = session.session_id
    this.inputText = ''
    this.connectWS(session.session_id)
    // 加载初始消息
    this.loadInitialMessages(session.session_id)
  }

  async loadInitialMessages(sessionId: string) {
    try {
      const res = await getSessionMessages(sessionId, 0)
      const msgs: HandoffMessage[] = (res as any).data
      if (Array.isArray(msgs)) {
        this.messages = msgs
      }
    } catch (e) {
      console.error('loadInitialMessages failed', e)
    }
  }

  async acceptCurrent() {
    if (!this.activeSession) return
    try {
      this.loading = true
      await apiAccept(this.activeSessionId)
      // Also send via WebSocket
      if (this.wsAdmin && this.wsAdmin.readyState === 1) {
        this.wsAdmin.send(JSON.stringify({ type: 'accept', agent_id: 'admin', agent_name: '管理员' }))
      }
      this.$message.success('已接管会话')
      await this.refreshQueue()
    } catch (e) {
      console.error('humanService: accept failed', e)
      this.$message.error('接管失败: ' + ((e as any).message || '网络错误'))
    } finally {
      this.loading = false
    }
  }

  async resolveCurrent() {
    if (!this.activeSession) return
    this.$confirm('确认标记该会话为已解决？', '提示', { type: 'warning' })
      .then(async () => {
        try {
          if (this.wsAdmin && this.wsAdmin.readyState === 1) {
            this.wsAdmin.send(JSON.stringify({ type: 'resolve' }))
          }
          await this.$message.success('已标记为解决')
          this.activeSessionId = ''
          this.messages = []
          this.disconnectWS()
          await this.refreshQueue()
        } catch (e) {
          console.error('humanService: resolve failed', e)
          this.$message.error('操作失败')
        }
      })
      .catch(() => {})
  }

  async sendReply() {
    const text = this.inputText.trim()
    if (!text || !this.activeSessionId || this.sending) return

    this.inputText = ''
    this.sending = true

    // 立即在本地显示
    this.messages.push({
      role: 'agent',
      content: text,
      timestamp: new Date().toISOString()
    })
    this.$nextTick(() => this.scrollToBottom())

    // 通过 WebSocket 发送
    this.sendWsMessage(text)

    // 同时保留 HTTP fallback
    try {
      await apiReply(this.activeSessionId, text)
    } catch (e) {
      console.error('HTTP reply failed (WS may have succeeded):', e)
    } finally {
      this.sending = false
    }
  }

  formatTime(iso: string): string {
    if (!iso) return ''
    try {
      const d = new Date(iso)
      const pad = (n: number) => String(n).padStart(2, '0')
      return `${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`
    } catch {
      return iso
    }
  }

  scrollToBottom() {
    const el = this.$refs.messageList as HTMLElement | undefined
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }

  @Watch('messages', { deep: true })
  onMessagesChange() {
    this.$nextTick(() => this.scrollToBottom())
  }
}
</script>

<style scoped lang="scss">
.human-service-container {
  display: flex;
  height: calc(100vh - 120px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

// Queue sidebar
.queue-sidebar {
  width: 260px;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}
.sidebar-header {
  padding: 14px 16px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.sidebar-title {
  font-size: 15px;
  font-weight: 700;
  color: #333;
}
.queue-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.queue-error {
  margin: 8px;
  padding: 10px 12px;
  background: #fef0f0;
  border: 1px solid #fde2e2;
  border-radius: 6px;
  color: #f56c6c;
  font-size: 12px;
  line-height: 1.5;
}
.queue-empty {
  text-align: center;
  padding: 40px 16px;
  color: #999;
  font-size: 13px;
}
.queue-item {
  padding: 12px 14px;
  margin-bottom: 4px;
  border-radius: 8px;
  cursor: pointer;
  background: #fff;
  border: 1px solid #eee;
  transition: all 0.2s;

  &:hover {
    border-color: #ffc100;
    background: #fffef5;
  }
  &.active {
    border-color: #ffc100;
    background: #fffbe6;
  }
}
.queue-item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}
.queue-user {
  font-weight: 600;
  font-size: 14px;
  color: #333;
}
.queue-item-meta {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #999;
}
.sidebar-footer {
  padding: 10px 16px;
  border-top: 1px solid #eee;
}
.footer-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  align-items: flex-start;
}
.footer-debug {
  font-size: 11px;
  color: #999;
  line-height: 1.4;
}

// Chat main
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-empty-full {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #999;

  h3 { margin: 16px 0 8px; color: #666; }
  p { font-size: 14px; }
}
.chat-header {
  padding: 12px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.chat-header-left {
  display: flex;
  align-items: center;
  gap: 10px;
}
.chat-header-right {
  display: flex;
  gap: 8px;
}
.chat-title {
  font-size: 16px;
  font-weight: 700;
  color: #333;
}
.chat-id {
  font-size: 12px;
  color: #999;
}

// Messages
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f6fa;
}
.message-row {
  margin-bottom: 16px;

  &.user .message-bubble {
    background: #fff;
    border: 1px solid #e8e8e8;
    margin-left: 0;
    margin-right: auto;
  }
  &.assistant .message-bubble {
    background: #e8f4fd;
    border: 1px solid #cce5ff;
    margin-left: 0;
    margin-right: auto;
  }
  &.agent .message-bubble {
    background: #ffc100;
    color: #333;
    margin-left: auto;
    margin-right: 0;
  }
  &.system .message-bubble {
    background: #f0f0f0;
    color: #999;
    margin: 0 auto;
    font-size: 12px;
    text-align: center;
  }
}
.message-label {
  font-size: 12px;
  color: #999;
  margin-bottom: 4px;

  .agent & { text-align: right; }
  .user & { text-align: left; }
}
.message-bubble {
  max-width: 70%;
  padding: 10px 16px;
  border-radius: 12px;
  font-size: 14px;
  line-height: 1.6;
  word-break: break-word;
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.06);
}
.message-content {
  white-space: pre-wrap;
}
.message-time {
  font-size: 11px;
  color: #aaa;
  margin-top: 4px;
  text-align: right;
}

// Typing indicator
.typing {
  padding: 10px 20px;
  display: flex;
  gap: 4px;
  .dot {
    width: 8px; height: 8px;
    border-radius: 50%;
    background: #ccc;
    animation: typingBounce 1.4s infinite both;
    &:nth-child(2) { animation-delay: 0.2s; }
    &:nth-child(3) { animation-delay: 0.4s; }
  }
}
@keyframes typingBounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

// Input
.chat-input {
  padding: 12px 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: #fff;
}
.chat-input-disabled {
  padding: 14px 20px;
  border-top: 1px solid #eee;
  text-align: center;
  background: #fafafa;
  color: #999;
  font-size: 13px;
}
</style>
