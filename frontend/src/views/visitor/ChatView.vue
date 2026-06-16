<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'
import Live2DCanvas from '@/components/live2d/Live2DCanvas.vue'
import SettingsPanel from '@/components/live2d/SettingsPanel.vue'

const chatStore = useChatStore()
const live2dRef = ref(null)
const isLive2DReady = ref(false)
const lookFactor = ref(8)
const breathFactor = ref(1)
const eyeFactor = ref(1.5)
const bodyFactor = ref(3)

const interestTags = [
  { icon: '🏛️', label: '历史文化', prompt: '我对历史文化感兴趣，请推荐一条游览路线', type: '' },
  { icon: '🌿', label: '自然风光', prompt: '我喜欢自然风光，请推荐一条游览路线', type: 'success' },
  { icon: '👨‍👩‍👧', label: '亲子互动', prompt: '我带小朋友来玩，推荐一条亲子路线', type: 'warning' },
  { icon: '📸', label: '摄影打卡', prompt: '我想拍照打卡，推荐一条摄影路线', type: 'danger' },
  { icon: '🍜', label: '美食禅意', prompt: '我想品尝美食和体验禅意文化，推荐一条路线', type: 'info' },
]

// 收集 AI 回复的完整文字，用于文字口型同步
let fullReplyText = ''
let textLipSyncStarted = false

function handleSendText(message) {
  chatStore.sendTextMessage(message)
}

// 当 AI 开始回复时重置口型状态
watch(() => chatStore.loading, (loading) => {
  if (loading) {
    live2dRef.value?.setExpression('Smile')
    fullReplyText = ''
    textLipSyncStarted = false
  }
})

// 监听后端返回的表情，自动切换数字人表情
watch(() => chatStore.currentExpression, (expr) => {
  if (expr && live2dRef.value) {
    live2dRef.value.setExpression(expr)
  }
})

// 监听文字块 — 累积文字并驱动口型
const originalOnTextChunk = chatStore._onTextChunk
chatStore._onTextChunk = null

// 使用 watch 监听 messages 变化，检测新文字块
watch(() => chatStore.messages.length, () => {})
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

    // 每收到新文字，更新口型序列
    if (!textLipSyncStarted && text.length > 0) {
      textLipSyncStarted = true
    }
    if (textLipSyncStarted) {
      // 重新启动口型，包含全部已收到文字
      live2dRef.value.startTextLipSync(fullReplyText)
    }
  }
)

// 监听音频播放状态 — 音频优先，覆盖文字口型
watch(() => chatStore.audioPlaying, (playing) => {
  if (playing) {
    // 音频开始播放时停止文字口型，改用音频口型
    live2dRef.value?.stopTextLipSync()
  }
})

// AudioPlayer 回调 — 音频口型同步
if (chatStore.audioPlayer) {
  chatStore.audioPlayer.onPlayStart = (analyser) => {
    if (analyser && live2dRef.value) {
      textLipSyncStarted = false
      live2dRef.value.startLipSyncFromAnalyser(analyser)
    }
  }
  chatStore.audioPlayer.onPlayEnd = () => {
    live2dRef.value?.stopLipSync()
    // 音频播完后如果还有文字在流式接收，恢复文字口型
    if (chatStore.loading && fullReplyText) {
      live2dRef.value?.startTextLipSync(fullReplyText)
      textLipSyncStarted = true
    }
  }
}

// 监听参数变化，动态更新数字人
watch([lookFactor, eyeFactor, bodyFactor], ([l, e, b]) => {
  live2dRef.value?.updateLookSensitivity?.(e, l, b)
})
watch(breathFactor, (v) => {
  live2dRef.value?.updateBreathIntensity?.(v)
})

function resetSettings() {
  lookFactor.value = 8
  breathFactor.value = 1
  eyeFactor.value = 1.5
  bodyFactor.value = 3
}

function onLive2DReady() {
  isLive2DReady.value = true
  live2dRef.value?.setExpression('Normal')
}

onMounted(() => {
  chatStore.initWebSocket()
})

onUnmounted(() => {
  chatStore.destroy()
})
</script>

<template>
  <div class="chat-view">
    <div class="chat-layout">
      <!-- 左侧：数字人（独立于 WebSocket） -->
      <div class="avatar-panel">
        <Live2DCanvas
          ref="live2dRef"
          class="live2d-wrapper"
          @ready="onLive2DReady"
          @error="(msg) => console.error('Live2D:', msg)"
        />
        <!-- 设置面板 -->
        <SettingsPanel
          v-model:lookFactor="lookFactor"
          v-model:breathFactor="breathFactor"
          v-model:eyeFactor="eyeFactor"
          v-model:bodyFactor="bodyFactor"
          @reset="resetSettings"
        />
        <!-- 表情 + 姿势按钮 -->
        <div class="expression-bar">
          <div class="btn-group">
            <span class="group-label">表情</span>
            <el-button size="small" @click="live2dRef?.setExpression('Normal')">😊 普通</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Smile')">😄 微笑</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Star')">⭐ 星星眼</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Circle')">🌀 圈圈眼</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Cry')">😢 哭泣</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Angry')">😠 生气</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Pucker')">😙 嘟嘴</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Chew')">😗 咀嚼</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('SideMouth')">😏 歪嘴</el-button>
          </div>
          <div class="btn-group">
            <span class="group-label">姿势</span>
            <el-button size="small" @click="live2dRef?.setExpression('PokeFace')">👉 戳脸</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Mic')">🎤 话筒</el-button>
            <el-button size="small" @click="live2dRef?.setExpression('Controller')">🎮 手柄</el-button>
          </div>
        </div>
      </div>

      <!-- 右侧：聊天 -->
      <div class="chat-panel">
        <!-- 连接状态（小提示，不遮挡） -->
        <div v-if="!chatStore.isWsConnected" class="connection-hint">
          <span class="dot"></span>
          聊天服务未连接，请启动 Java 后端
        </div>

        <div class="chat-container">
          <!-- 兴趣标签（仅在没有消息时显示） -->
          <div v-if="chatStore.messages.length === 0" class="interest-tags">
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
  width: 400px;
  min-width: 320px;
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

.expression-bar {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 8px;
  background: rgba(255, 255, 255, 0.6);
  backdrop-filter: blur(10px);
}

.btn-group {
  display: flex;
  align-items: center;
  gap: 3px;
  flex-wrap: wrap;
}

.group-label {
  font-size: 10px;
  color: #666;
  flex: 0 0 auto;
  margin-right: 2px;
}

.expression-bar .el-button {
  font-size: 11px;
  padding: 3px 6px;
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

/* 兴趣标签 */
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

/* 响应式 */
@media (max-width: 900px) {
  .chat-layout {
    flex-direction: column;
  }
  .avatar-panel {
    width: 100%;
    height: 350px;
    min-width: unset;
  }
}
</style>
