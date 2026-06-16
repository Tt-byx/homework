<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import { getConversations, getConversationMessages } from '@/api/auth'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import Live2DCanvas from '@/components/live2d/Live2DCanvas.vue'
import { ElMessage } from 'element-plus'

const chatStore = useChatStore()
const userStore = useUserStore()
const live2dRef = ref(null)
const isLive2DReady = ref(false)

// 历史对话
const conversations = ref([])
const activeConvId = ref(null)

const interestTags = [
  { icon: '🏛️', label: '历史文化', prompt: '我对历史文化感兴趣，请推荐一条游览路线', type: '' },
  { icon: '🌿', label: '自然风光', prompt: '我喜欢自然风光，请推荐一条游览路线', type: 'success' },
  { icon: '👨‍👩‍👧', label: '亲子互动', prompt: '我带小朋友来玩，推荐一条亲子路线', type: 'warning' },
  { icon: '📸', label: '摄影打卡', prompt: '我想拍照打卡，推荐一条摄影路线', type: 'danger' },
  { icon: '🍜', label: '美食禅意', prompt: '我想品尝美食和体验禅意文化，推荐一条路线', type: 'info' },
]

let fullReplyText = ''
let textLipSyncStarted = false

function handleSendText(message) {
  activeConvId.value = null
  chatStore.sendTextMessage(message)
}

// 加载历史对话列表
async function loadConversations() {
  try {
    const data = await getConversations()
    conversations.value = Array.isArray(data) ? data : []
  } catch {
    conversations.value = []
  }
}

// 点击历史对话加载消息
async function loadConversation(conv) {
  try {
    activeConvId.value = conv.id
    const msgs = await getConversationMessages(conv.id)
    chatStore.clearMessages()
    // 直接设置 messages
    if (Array.isArray(msgs)) {
      chatStore.messages.splice(0, chatStore.messages.length,
        ...msgs.map(m => ({
          role: m.role,
          content: m.content,
          timestamp: new Date(m.createdAt).getTime(),
        }))
      )
      chatStore.sessionId = conv.sessionId
    }
  } catch (err) {
    ElMessage.error('加载对话失败')
  }
}

// 新建对话
function newConversation() {
  activeConvId.value = null
  chatStore.clearMessages()
}

// 对话完成后刷新列表
watch(() => chatStore.loading, (loading, oldLoading) => {
  if (oldLoading && !loading) {
    loadConversations()
  }
})

// 数字人口型同步
watch(() => chatStore.loading, (loading) => {
  if (loading) {
    live2dRef.value?.setExpression('Smile')
    fullReplyText = ''
    textLipSyncStarted = false
  }
})

watch(() => chatStore.currentExpression, (expr) => {
  if (expr && live2dRef.value) {
    live2dRef.value.setExpression(expr)
  }
})

watch(
  () => {
    const msgs = chatStore.messages
    if (msgs.length === 0) return ''
    const last = msgs[msgs.length - 1]
    if (last.role === 'assistant') return last.content
    return ''
  },
  (text) => {
    if (!text || !live2dRef.value) return
    fullReplyText = text
    if (!textLipSyncStarted && text.length > 0) {
      textLipSyncStarted = true
    }
    if (textLipSyncStarted) {
      live2dRef.value.startTextLipSync(fullReplyText)
    }
  }
)

watch(() => chatStore.audioPlaying, (playing) => {
  if (playing) live2dRef.value?.stopTextLipSync()
})

if (chatStore.audioPlayer) {
  chatStore.audioPlayer.onPlayStart = (analyser) => {
    if (analyser && live2dRef.value) {
      textLipSyncStarted = false
      live2dRef.value.startLipSyncFromAnalyser(analyser)
    }
  }
  chatStore.audioPlayer.onPlayEnd = () => {
    live2dRef.value?.stopLipSync()
    if (chatStore.loading && fullReplyText) {
      live2dRef.value?.startTextLipSync(fullReplyText)
      textLipSyncStarted = true
    }
  }
}

function onLive2DReady() {
  isLive2DReady.value = true
  live2dRef.value?.setExpression('Normal')
}

function formatTime(time) {
  if (!time) return ''
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(async () => {
  chatStore.initWebSocket()
  await userStore.fetchMe()
  loadConversations()
})

onUnmounted(() => {
  chatStore.destroy()
})
</script>

<template>
  <div class="chat-view">
    <div class="chat-layout">
      <!-- 左侧：数字人 -->
      <div class="avatar-panel">
        <Live2DCanvas
          ref="live2dRef"
          class="live2d-wrapper"
          @ready="onLive2DReady"
        />
      </div>

      <!-- 中间：聊天 -->
      <div class="chat-panel">
        <div v-if="!chatStore.isWsConnected" class="connection-hint">
          <span class="dot"></span>
          聊天服务未连接
        </div>

        <div class="chat-container">
          <div v-if="chatStore.messages.length === 0 && !activeConvId" class="interest-tags">
            <p class="tags-title">🎯 我感兴趣的方向</p>
            <div class="tags-row">
              <el-tag
                v-for="tag in interestTags"
                :key="tag.label"
                :type="tag.type"
                class="interest-tag"
                effect="plain"
                @click="handleSendText(tag.prompt)"
              >
                {{ tag.icon }} {{ tag.label }}
              </el-tag>
            </div>
          </div>

          <MessageList :messages="chatStore.messages" :loading="chatStore.loading">
            <ChatMessage
              v-for="(msg, index) in chatStore.messages"
              :key="index"
              :message="msg"
            />
          </MessageList>
          <ChatInput
            :loading="chatStore.loading"
            @send-text="handleSendText"
          />
        </div>
      </div>

      <!-- 右侧：历史对话 -->
      <div class="history-panel">
        <div class="history-header">
          <span class="history-title">💬 历史对话</span>
          <el-button size="small" text type="primary" @click="newConversation">
            <el-icon><Plus /></el-icon> 新对话
          </el-button>
        </div>

        <div class="history-list">
          <div
            v-for="conv in conversations"
            :key="conv.id"
            class="history-item"
            :class="{ active: activeConvId === conv.id }"
            @click="loadConversation(conv)"
          >
            <div class="conv-title">{{ conv.title || '新对话' }}</div>
            <div class="conv-time">{{ formatTime(conv.updatedAt) }}</div>
          </div>

          <div v-if="conversations.length === 0" class="history-empty">
            暂无历史对话
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  width: 100%;
  height: calc(100vh - 60px);
  padding: 12px;
  display: flex;
  flex-direction: column;
}

.chat-layout {
  flex: 1;
  display: flex;
  gap: 12px;
  min-height: 0;
}

/* 数字人面板 */
.avatar-panel {
  width: 360px;
  min-width: 280px;
  display: flex;
  flex-direction: column;
  background: linear-gradient(180deg, #e8f4f8 0%, #d4e9d7 40%, #f0ebe3 100%);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

.live2d-wrapper {
  flex: 1;
  min-height: 0;
}

/* 聊天面板 */
.chat-panel {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.connection-hint {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 14px;
  background: #fdf6ec;
  border-radius: 6px;
  color: #e6a23c;
  font-size: 12px;
  flex-shrink: 0;
}

.connection-hint .dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #e6a23c;
  animation: blink 1.5s ease-in-out infinite;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.3; }
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
  min-height: 0;
}

.interest-tags {
  padding: 20px;
  border-bottom: 1px solid #f0f0f0;
  flex-shrink: 0;
}

.tags-title {
  font-size: 14px;
  color: #606266;
  margin-bottom: 12px;
}

.tags-row {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.interest-tag {
  cursor: pointer;
  font-size: 13px;
  padding: 8px 16px;
  border-radius: 20px;
  transition: all 0.2s;
}

.interest-tag:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
}

/* 历史对话面板 */
.history-panel {
  width: 220px;
  min-width: 200px;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.history-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  border-bottom: 1px solid #f0f0f0;
}

.history-title {
  font-size: 14px;
  font-weight: 600;
  color: #333;
}

.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 6px;
}

.history-item {
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background 0.15s;
  margin-bottom: 2px;
}

.history-item:hover {
  background: #f5f7fa;
}

.history-item.active {
  background: #e8f5e9;
}

.conv-title {
  font-size: 13px;
  color: #333;
  font-weight: 500;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.conv-time {
  font-size: 11px;
  color: #999;
  margin-top: 3px;
}

.history-empty {
  text-align: center;
  color: #ccc;
  font-size: 13px;
  padding: 32px 0;
}

/* 响应式 */
@media (max-width: 1100px) {
  .history-panel {
    display: none;
  }
}

@media (max-width: 900px) {
  .chat-layout {
    flex-direction: column;
  }
  .avatar-panel {
    width: 100%;
    height: 300px;
    min-width: unset;
  }
}
</style>
