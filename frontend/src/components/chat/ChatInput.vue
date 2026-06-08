<script setup>
import { ref, onUnmounted } from 'vue'
import { VoiceRecorder } from './VoiceRecorder.js'

const emit = defineEmits(['sendText', 'sendVoice'])

const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
})

const inputText = ref('')
const isRecording = ref(false)
const recordingError = ref('')
const recordingDuration = ref(0)

const recorder = new VoiceRecorder()
let durationTimer = null

// --- 文字发送 ---
function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  emit('sendText', text)
  inputText.value = ''
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

// --- 语音录制 ---
async function startRecording() {
  if (props.loading || isRecording.value) return

  recordingError.value = ''
  recordingDuration.value = 0

  try {
    await recorder.start()
    isRecording.value = true

    // 计时器：显示录音时长
    durationTimer = setInterval(() => {
      recordingDuration.value = Math.floor((Date.now() - recorder.startTime) / 1000)
    }, 200)
  } catch (err) {
    recordingError.value = err.message || '录音失败'
    setTimeout(() => { recordingError.value = '' }, 3000)
  }
}

async function stopRecording() {
  if (!isRecording.value) return
  isRecording.value = false

  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }

  try {
    const result = await recorder.stop()
    if (result && result.blob && result.blob.size > 1000) {
      // 录音时长 > 0.5s 才发送
      if (result.duration >= 500) {
        emit('sendVoice', result.blob, result.format)
      } else {
        recordingError.value = '录音时间太短'
        setTimeout(() => { recordingError.value = '' }, 2000)
      }
    }
  } catch (err) {
    recordingError.value = err.message || '录音失败'
    setTimeout(() => { recordingError.value = '' }, 3000)
  }
}

function cancelRecording() {
  if (!isRecording.value) return
  isRecording.value = false
  recorder.cancel()
  if (durationTimer) {
    clearInterval(durationTimer)
    durationTimer = null
  }
}

function formatDuration(seconds) {
  const m = Math.floor(seconds / 60)
  const s = seconds % 60
  return `${m}:${s.toString().padStart(2, '0')}`
}

onUnmounted(() => {
  recorder.destroy()
  if (durationTimer) clearInterval(durationTimer)
})
</script>

<template>
  <div class="chat-input">
    <!-- 文字输入框 -->
    <el-input
      v-model="inputText"
      type="textarea"
      :rows="2"
      placeholder="输入你的问题..."
      resize="none"
      :disabled="loading || isRecording"
      @keydown="handleKeydown"
    />

    <!-- 按钮区域 -->
    <div class="button-group">
      <!-- 发送文字按钮 -->
      <el-button
        type="primary"
        :loading="loading"
        :disabled="!inputText.trim() || isRecording"
        @click="handleSend"
      >
        发送
      </el-button>

      <!-- 按住说话按钮 -->
      <el-button
        :type="isRecording ? 'danger' : 'success'"
        :disabled="loading"
        @mousedown.prevent="startRecording"
        @mouseup.prevent="stopRecording"
        @mouseleave="cancelRecording"
        @touchstart.prevent="startRecording"
        @touchend.prevent="stopRecording"
        @touchcancel="cancelRecording"
      >
        <el-icon v-if="!isRecording"><Microphone /></el-icon>
        <span v-if="isRecording">松开结束</span>
        <span v-else>按住说话</span>
      </el-button>
    </div>

    <!-- 录音状态指示器 -->
    <div v-if="isRecording" class="recording-indicator">
      <div class="wave-animation">
        <span></span><span></span><span></span><span></span><span></span>
      </div>
      <span class="duration">{{ formatDuration(recordingDuration) }}</span>
    </div>

    <!-- 错误提示 -->
    <div v-if="recordingError" class="recording-error">
      {{ recordingError }}
    </div>
  </div>
</template>

<style scoped>
.chat-input {
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
}

.button-group {
  display: flex;
  gap: 10px;
  margin-top: 10px;
  align-items: center;
}

.button-group .el-button {
  height: 40px;
  min-width: 80px;
}

/* 录音指示器 */
.recording-indicator {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 8px;
  padding: 8px 12px;
  background: #fef0f0;
  border-radius: 8px;
  color: #f56c6c;
  font-size: 14px;
}

.duration {
  font-weight: 600;
  font-variant-numeric: tabular-nums;
}

/* 波浪动画 */
.wave-animation {
  display: flex;
  align-items: center;
  gap: 3px;
  height: 20px;
}

.wave-animation span {
  display: block;
  width: 3px;
  height: 8px;
  background: #f56c6c;
  border-radius: 2px;
  animation: wave 1s ease-in-out infinite;
}

.wave-animation span:nth-child(2) { animation-delay: 0.1s; }
.wave-animation span:nth-child(3) { animation-delay: 0.2s; }
.wave-animation span:nth-child(4) { animation-delay: 0.3s; }
.wave-animation span:nth-child(5) { animation-delay: 0.4s; }

@keyframes wave {
  0%, 100% { height: 8px; }
  50% { height: 20px; }
}

/* 错误提示 */
.recording-error {
  margin-top: 6px;
  padding: 4px 8px;
  color: #f56c6c;
  font-size: 12px;
  background: #fef0f0;
  border-radius: 4px;
}
</style>
