<template>
  <view class="chat-page">
    <!-- 导航栏 -->
    <navBar
      :title="'AI客服助手'"
      :backUrl="backUrl"
      :background="'#333333'"
      :color="'#ffffff'"
    />

    <!-- 消息区域 -->
    <scroll-view
      class="chat-messages"
      scroll-y
      :scroll-top="scrollTop"
      :scroll-with-animation="true"
      @scrolltolower="onScrollToLower"
    >
      <view v-if="messages.length === 0" class="chat-empty">
        <image src="/static/chat-icon.png" mode="aspectFit" class="empty-icon" />
        <text class="empty-text">您好！我是苍穹外卖的AI客服助手</text>
        <text class="empty-sub">您可以问我关于订单、菜品、配送等问题</text>

        <view class="quick-actions">
          <view class="quick-btn" @click="quickSend('我的订单到哪了？')">
            📋 查我的订单
          </view>
          <view class="quick-btn" @click="quickSend('有什么好吃的推荐？')">
            🍽️ 美食推荐
          </view>
          <view class="quick-btn" @click="quickSend('怎么退款？')">
            💰 退款咨询
          </view>
          <view class="quick-btn" @click="quickSend('店铺几点关门？')">
            🕐 营业时间
          </view>
        </view>
      </view>

      <view
        v-for="(msg, idx) in messages"
        :key="idx"
        class="msg-row"
        :class="msg.role"
      >
        <view class="msg-bubble">
          <text class="msg-content">{{ msg.content }}</text>
          <text v-if="msg.intent" class="msg-tag">{{ msg.intent }}</text>
        </view>
      </view>

      <view v-if="loading" class="msg-row assistant">
        <view class="msg-bubble typing">
          <view class="dot" />
          <view class="dot" />
          <view class="dot" />
        </view>
      </view>
    </scroll-view>

    <!-- 输入区 -->
    <view class="chat-input-bar">
      <input
        v-model="inputText"
        class="chat-input"
        type="text"
        placeholder="输入消息..."
        :disabled="loading"
        confirm-type="send"
        @confirm="sendMessage"
      />
      <view class="send-btn" :class="{ disabled: !inputText.trim() || loading }" @click="sendMessage">
        发送
      </view>
    </view>
  </view>
</template>

<script>
import { aiChat } from '../api/chatApi.js'

export default {
  data() {
    return {
      messages: [],
      inputText: '',
      loading: false,
      sessionId: '',
      scrollTop: 0,
      backUrl: '/pages/my/my'
    }
  },

  onLoad(options) {
    // 从 options 获取初始消息（例如订单页跳转带过来的订单ID）
    const prefill = options.prefill || ''
    this.sessionId = uni.getStorageSync('chat_session_id') || ('cs-' + Date.now().toString(36) + '-' + Math.random().toString(36).slice(2, 8))
    uni.setStorageSync('chat_session_id', this.sessionId)

    if (prefill) {
      this.sendMessage(prefill)
    }
  },

  methods: {
    quickSend(text) {
      this.inputText = text
      this.$nextTick(() => {
        this.sendMessage()
      })
    },

    sendMessage(prefillText) {
      const text = prefillText || this.inputText.trim()
      if (!text || this.loading) return

      this.messages.push({ role: 'user', content: text, intent: '' })
      if (!prefillText) this.inputText = ''
      this.loading = true
      this.scrollToBottom()

      aiChat({
        message: text,
        user_id: 'consumer',
        session_id: this.sessionId
      }).then((data) => {
        this.messages.push({
          role: 'assistant',
          content: data.response || '暂无回复',
          intent: data.intent || ''
        })
      }).catch((err) => {
        this.messages.push({
          role: 'assistant',
          content: '抱歉，AI客服暂时无法响应。请确认客服服务已启动。\n\n(' + (err.detail || err.errMsg || '网络错误') + ')',
          intent: ''
        })
      }).finally(() => {
        this.loading = false
        this.scrollToBottom()
      })
    },

    scrollToBottom() {
      this.$nextTick(() => {
        this.scrollTop = 99999
      })
    },

    onScrollToLower() {
      // 预留：加载历史消息
    }
  }
}
</script>

<style scoped>
.chat-page {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f5f5f5;
}

/* 消息区域 */
.chat-messages {
  flex: 1;
  padding: 20rpx 24rpx;
  overflow-y: auto;
}

.chat-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding-top: 120rpx;
}
.empty-icon {
  width: 120rpx;
  height: 120rpx;
  margin-bottom: 24rpx;
}
.empty-text {
  font-size: 32rpx;
  color: #333;
  font-weight: 600;
  margin-bottom: 12rpx;
}
.empty-sub {
  font-size: 26rpx;
  color: #999;
  margin-bottom: 40rpx;
}

.quick-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 16rpx;
  padding: 0 40rpx;
}
.quick-btn {
  background: #fff;
  border: 2rpx solid #e5e4e4;
  border-radius: 40rpx;
  padding: 16rpx 32rpx;
  font-size: 26rpx;
  color: #333;
}
.quick-btn:active {
  background: #ffc200;
  border-color: #ffc200;
}

/* 消息气泡 */
.msg-row {
  display: flex;
  margin-bottom: 24rpx;
}
.msg-row.user {
  justify-content: flex-end;
}
.msg-row.assistant {
  justify-content: flex-start;
}

.msg-bubble {
  max-width: 80%;
  padding: 16rpx 24rpx;
  border-radius: 16rpx;
  font-size: 28rpx;
  line-height: 1.6;
}
.msg-row.user .msg-bubble {
  background: #ffc200;
  color: #333;
  border-bottom-right-radius: 4rpx;
}
.msg-row.assistant .msg-bubble {
  background: #fff;
  border: 1px solid #e8e8e8;
  border-bottom-left-radius: 4rpx;
}

.msg-content {
  white-space: pre-wrap;
  word-break: break-all;
}

.msg-tag {
  display: block;
  margin-top: 8rpx;
  font-size: 22rpx;
  color: #999;
}

/* 输入中动画 */
.typing {
  display: flex;
  gap: 8rpx;
  padding: 20rpx 28rpx;
}
.typing .dot {
  width: 12rpx;
  height: 12rpx;
  border-radius: 50%;
  background: #ccc;
  animation: bounce 1.4s infinite both;
}
.typing .dot:nth-child(2) { animation-delay: 0.2s; }
.typing .dot:nth-child(3) { animation-delay: 0.4s; }
@keyframes bounce {
  0%, 80%, 100% { transform: scale(0.6); opacity: 0.4; }
  40% { transform: scale(1); opacity: 1; }
}

/* 输入栏 */
.chat-input-bar {
  display: flex;
  align-items: center;
  gap: 16rpx;
  padding: 16rpx 24rpx;
  padding-bottom: calc(16rpx + env(safe-area-inset-bottom));
  background: #fff;
  border-top: 1px solid #efefef;
}
.chat-input {
  flex: 1;
  height: 72rpx;
  border: 1px solid #e5e4e4;
  border-radius: 36rpx;
  padding: 0 28rpx;
  font-size: 28rpx;
  background: #f5f5f5;
}
.send-btn {
  padding: 14rpx 32rpx;
  background: #ffc200;
  color: #333;
  font-size: 28rpx;
  font-weight: 600;
  border-radius: 36rpx;
}
.send-btn.disabled {
  background: #eee;
  color: #ccc;
}
</style>
