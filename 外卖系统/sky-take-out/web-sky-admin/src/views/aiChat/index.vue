<template>
  <div class="ai-chat-container">
    <!-- Session Sidebar -->
    <div class="chat-sidebar">
      <div class="sidebar-header">
        <el-button type="primary" size="small" icon="el-icon-plus" @click="newSession">
          新建会话
        </el-button>
      </div>
      <div class="session-list">
        <div
          v-for="(session, idx) in sessions"
          :key="session.id"
          class="session-item"
          :class="{ active: session.id === activeSessionId }"
          @click="switchSession(session.id)"
        >
          <span class="session-title">{{ session.title }}</span>
          <i
            class="el-icon-delete session-delete"
            title="删除会话"
            @click.stop="deleteSession(session.id)"
          />
        </div>
      </div>
    </div>

    <!-- Main Chat Area -->
    <div class="chat-main">
      <div class="chat-header">
        <span class="chat-title">AI 客服助手</span>
        <span v-if="activeSession" class="chat-meta">
          Session: {{ activeSession.id.slice(0, 8) }}...
          <el-tag v-if="lastIntent" size="mini" type="info" class="intent-tag">
            {{ lastIntent }}
          </el-tag>
        </span>
      </div>

      <div ref="messageList" class="chat-messages">
        <div v-if="activeMessages.length === 0" class="chat-empty">
          <i class="el-icon-chat-dot-round" style="font-size:48px;color:#ccc" />
          <p>向 AI 客服提问，例如：</p>
          <div class="quick-actions">
            <el-button size="small" @click="quickSend('帮我查一下最近的订单')">查最近订单</el-button>
            <el-button size="small" @click="quickSend('今天的营业数据怎么样')">今日营业数据</el-button>
            <el-button size="small" @click="quickSend('有什么菜品和套餐')">查菜单</el-button>
            <el-button size="small" @click="quickSend('店铺现在营业吗')">店铺状态</el-button>
          </div>
        </div>

        <div
          v-for="(msg, idx) in activeMessages"
          :key="idx"
          class="message-row"
          :class="msg.role"
        >
          <div class="message-bubble">
            <div class="message-content" v-html="formatContent(msg.content)" />
            <div class="message-meta" v-if="msg.intent">
              <el-tag size="mini" :type="msg.compliancePassed ? 'success' : 'danger'">
                {{ msg.compliancePassed ? '合规通过' : '存在风险' }}
              </el-tag>
            </div>
          </div>
        </div>

        <div v-if="loading" class="message-row assistant">
          <div class="message-bubble typing">
            <span class="dot" />
            <span class="dot" />
            <span class="dot" />
          </div>
        </div>
      </div>

      <div class="chat-input">
        <el-input
          v-model="inputText"
          type="textarea"
          :rows="2"
          placeholder="输入消息，Enter 发送..."
          :disabled="loading"
          @keyup.enter.native="sendMessage"
        />
        <el-button
          type="primary"
          :loading="loading"
          :disabled="!inputText.trim()"
          @click="sendMessage"
        >
          发送
        </el-button>
        <el-button :disabled="activeMessages.length === 0" @click="clearSession">
          清空
        </el-button>
      </div>
    </div>
  </div>
</template>

<script lang="ts">
import { Component, Vue, Watch } from 'vue-property-decorator'
import { aiChat, aiChatHistory, ChatResponse } from '@/api/aiChat'

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  intent?: string
  compliancePassed?: boolean
}

interface ChatSession {
  id: string
  title: string
  messages: ChatMessage[]
  updatedAt: string
}

@Component({ name: 'AiChat' })
export default class extends Vue {
  private sessions: ChatSession[] = []
  private activeSessionId = ''
  private inputText = ''
  private loading = false
  private lastIntent = ''

  get activeSession(): ChatSession | undefined {
    return this.sessions.find((s) => s.id === this.activeSessionId)
  }

  get activeMessages(): ChatMessage[] {
    const s = this.activeSession
    return s ? s.messages : []
  }

  created() {
    this.newSession()
  }

  newSession() {
    const id = 'cs-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8)
    const session: ChatSession = {
      id,
      title: '新会话',
      messages: [],
      updatedAt: new Date().toLocaleString()
    }
    this.sessions.unshift(session)
    this.activeSessionId = id
    this.lastIntent = ''
    this.$nextTick(() => this.scrollToBottom())
  }

  switchSession(id: string) {
    this.activeSessionId = id
    this.lastIntent = ''
    this.$nextTick(() => this.scrollToBottom())
  }

  deleteSession(id: string) {
    if (this.sessions.length <= 1) {
      this.$message.warning('至少保留一个会话')
      return
    }
    const idx = this.sessions.findIndex((s) => s.id === id)
    this.sessions.splice(idx, 1)
    if (this.activeSessionId === id) {
      this.activeSessionId = this.sessions[0].id
    }
  }

  clearSession() {
    if (this.activeSession) {
      this.activeSession.messages = []
      this.activeSession.title = '新会话'
      this.lastIntent = ''
    }
  }

  quickSend(text: string) {
    this.inputText = text
    this.sendMessage()
  }

  async sendMessage() {
    const text = this.inputText.trim()
    if (!text || !this.activeSession || this.loading) return

    const session = this.activeSession
    session.messages.push({ role: 'user', content: text })

    // Auto-title: first user message sets session title
    if (session.title === '新会话') {
      session.title = text.length > 15 ? text.slice(0, 15) + '...' : text
    }

    this.inputText = ''
    this.loading = true
    this.$nextTick(() => this.scrollToBottom())

    try {
      const res = await aiChat({
        message: text,
        user_id: 'admin',
        session_id: session.id
      })
      const data = res.data as ChatResponse
      session.messages.push({
        role: 'assistant',
        content: data.response,
        intent: data.intent,
        compliancePassed: data.compliance_passed
      })
      this.lastIntent = data.intent
    } catch (err: any) {
      const errMsg = (err && err.response && err.response.data && err.response.data.detail) || (err && err.message) || '请求失败'
      session.messages.push({
        role: 'assistant',
        content: '请求失败：' + errMsg + '\n\n请确认 AI 客服服务 (localhost:8000) 已启动且 API Key 已配置。'
      })
    } finally {
      this.loading = false
      session.updatedAt = new Date().toLocaleString()
      this.$nextTick(() => this.scrollToBottom())
    }
  }

  formatContent(text: string): string {
    if (!text) return ''
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\n/g, '<br>')
      .replace(/\*\*(.+?)\*\*/g, '<b>$1</b>')
  }

  scrollToBottom() {
    const el = this.$refs.messageList as HTMLElement | undefined
    if (el) {
      el.scrollTop = el.scrollHeight
    }
  }

  @Watch('activeMessages', { deep: true })
  onMessagesChange() {
    this.$nextTick(() => this.scrollToBottom())
  }
}
</script>

<style scoped lang="scss">
.ai-chat-container {
  display: flex;
  height: calc(100vh - 120px);
  background: #fff;
  border-radius: 8px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
}

// Sidebar
.chat-sidebar {
  width: 220px;
  border-right: 1px solid #eee;
  display: flex;
  flex-direction: column;
  background: #fafafa;
}
.sidebar-header {
  padding: 12px;
  border-bottom: 1px solid #eee;
}
.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 8px;
}
.session-item {
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 13px;
  color: #333;
  transition: background 0.2s;

  &:hover {
    background: #e8e8e8;
  }
  &.active {
    background: #ffc100;
    color: #333;
    font-weight: 600;
  }
}
.session-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex: 1;
}
.session-delete {
  opacity: 0;
  transition: opacity 0.2s;
  color: #999;
  font-size: 14px;
}
.session-item:hover .session-delete {
  opacity: 1;
}

// Main area
.chat-main {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-width: 0;
}
.chat-header {
  padding: 12px 20px;
  border-bottom: 1px solid #eee;
  display: flex;
  align-items: center;
  gap: 12px;
  background: #fff;
}
.chat-title {
  font-size: 16px;
  font-weight: 700;
  color: #333;
}
.chat-meta {
  font-size: 12px;
  color: #999;
}
.intent-tag {
  margin-left: 6px;
}

// Messages
.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 20px;
  background: #f5f6fa;
}
.chat-empty {
  text-align: center;
  padding: 60px 20px;
  color: #999;

  p {
    margin: 16px 0 12px;
    font-size: 14px;
  }
}
.quick-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  justify-content: center;
}

// Message bubbles
.message-row {
  margin-bottom: 16px;
  display: flex;

  &.user {
    justify-content: flex-end;
    .message-bubble {
      background: #ffc100;
      color: #333;
      border-bottom-right-radius: 4px;
    }
  }
  &.assistant {
    justify-content: flex-start;
    .message-bubble {
      background: #fff;
      border: 1px solid #e8e8e8;
      border-bottom-left-radius: 4px;
    }
  }
}
.message-bubble {
  max-width: 75%;
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
.message-meta {
  margin-top: 6px;
  font-size: 11px;
}

// Typing indicator
.typing {
  padding: 14px 20px;
  display: flex;
  gap: 4px;

  .dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: #ccc;
    animation: typingBounce 1.4s infinite both;

    &:nth-child(2) {
      animation-delay: 0.2s;
    }
    &:nth-child(3) {
      animation-delay: 0.4s;
    }
  }
}
@keyframes typingBounce {
  0%, 80%, 100% {
    transform: scale(0.6);
    opacity: 0.4;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

// Input area
.chat-input {
  padding: 12px 20px;
  border-top: 1px solid #eee;
  display: flex;
  gap: 8px;
  align-items: flex-end;
  background: #fff;
}
</style>
