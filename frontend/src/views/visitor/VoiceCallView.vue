<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useChatStore } from '@/stores/chat'
import { useUserStore } from '@/stores/user'
import Live2DCanvas from '@/components/live2d/Live2DCanvas.vue'

const router = useRouter()
const chatStore = useChatStore()
const userStore = useUserStore()
const live2dRef = ref(null)

// 通话状态: idle | listening | processing | speaking | connecting
const callState = ref('connecting')
const statusText = ref('正在连接...')
const isHolding = ref(false)

// 录音
let mediaRecorder = null
let audioChunks = []
let audioContext = null
let analyser = null
let animFrame = 0
const volumeLevel = ref(0)

// 口型同步
let _mouthRAF = 0

async function startRecording() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
    audioContext = new AudioContext()
    const source = audioContext.createMediaStreamSource(stream)
    analyser = audioContext.createAnalyser()
    analyser.fftSize = 256
    source.connect(analyser)

    mediaRecorder = new MediaRecorder(stream, { mimeType: 'audio/webm;codecs=opus' })
    audioChunks = []

    mediaRecorder.ondataavailable = (e) => {
      if (e.data.size > 0) audioChunks.push(e.data)
    }

    mediaRecorder.onstop = async () => {
      stream.getTracks().forEach(t => t.stop())
      if (audioContext) { audioContext.close(); audioContext = null }
      cancelAnimationFrame(animFrame)
      volumeLevel.value = 0

      if (audioChunks.length === 0) return

      const blob = new Blob(audioChunks, { type: 'audio/webm' })
      if (blob.size < 1000) {
        // 太短，忽略
        callState.value = 'idle'
        statusText.value = '点击开始对话'
        return
      }

      callState.value = 'processing'
      statusText.value = 'AI 思考中...'
      chatStore.sendVoiceMessage(blob, 'webm')
    }

    mediaRecorder.start(100) // 每 100ms 收集一次
    callState.value = 'listening'
    statusText.value = '正在聆听...'
    isHolding.value = true

    // 音量可视化
    const dataArray = new Uint8Array(analyser.frequencyBinCount)
    const tick = () => {
      if (!analyser) return
      analyser.getByteFrequencyData(dataArray)
      let sum = 0
      for (let i = 0; i < dataArray.length; i++) sum += dataArray[i]
      volumeLevel.value = Math.min(1, (sum / dataArray.length) / 128)
      animFrame = requestAnimationFrame(tick)
    }
    animFrame = requestAnimationFrame(tick)

  } catch (e) {
    console.error('录音失败:', e)
    statusText.value = '麦克风权限被拒绝'
  }
}

function stopRecording() {
  isHolding.value = false
  if (mediaRecorder && mediaRecorder.state !== 'inactive') {
    mediaRecorder.stop()
  }
}

// 监听 AI 回复完成 → 自动恢复监听
watch(() => chatStore.audioPlaying, (playing, oldPlaying) => {
  if (oldPlaying && !playing && callState.value === 'speaking') {
    // AI 语音播放完毕，自动恢复监听
    setTimeout(() => {
      if (callState.value === 'speaking') {
        startRecording()
      }
    }, 500)
  }
})

watch(() => chatStore.loading, (loading, oldLoading) => {
  if (oldLoading && !loading && callState.value === 'processing') {
    callState.value = 'speaking'
    statusText.value = 'AI 正在回答...'
  }
})

// 口型同步（复用 ChatView 的逻辑）
watch(() => chatStore.audioPlaying, (playing) => {
  if (_mouthRAF) { cancelAnimationFrame(_mouthRAF); _mouthRAF = 0 }
  if (playing) {
    const tick = () => {
      if (!live2dRef.value || !chatStore.audioPlaying) {
        live2dRef.value?.setLipSync(0)
        _mouthRAF = 0
        return
      }
      const open = 0.1 + 0.9 * Math.abs(Math.sin(performance.now() / 1000 * 6))
      live2dRef.value.setLipSync(open)
      _mouthRAF = requestAnimationFrame(tick)
    }
    _mouthRAF = requestAnimationFrame(tick)
  } else {
    live2dRef.value?.setLipSync(0)
  }
})

function endCall() {
  stopRecording()
  if (_mouthRAF) { cancelAnimationFrame(_mouthRAF); _mouthRAF = 0 }
  live2dRef.value?.setLipSync(0)
  chatStore.audioPlayer?.stop()
  callState.value = 'idle'
  statusText.value = '通话已结束'
  router.push('/chat')
}

onMounted(async () => {
  await userStore.fetchMe()
  chatStore.initWebSocket()

  // 等待 WebSocket 连接
  const waitForWs = () => new Promise((resolve) => {
    if (chatStore.isWsConnected) return resolve()
    const unwatch = watch(() => chatStore.isWsConnected, (connected) => {
      if (connected) { unwatch(); resolve() }
    })
    setTimeout(() => { unwatch(); resolve() }, 5000) // 最多等5秒
  })
  await waitForWs()
  callState.value = 'idle'
  statusText.value = '点击开始对话'
})

onUnmounted(() => {
  stopRecording()
  if (_mouthRAF) { cancelAnimationFrame(_mouthRAF); _mouthRAF = 0 }
})
</script>

<template>
  <div class="voice-call">
    <!-- Live2D 数字人 -->
    <div class="avatar-area">
      <Live2DCanvas ref="live2dRef" class="live2d" />
    </div>

    <!-- 状态提示 -->
    <div class="status-bar" :class="callState">
      <div class="status-dot" :class="callState"></div>
      <span>{{ statusText }}</span>
    </div>

    <!-- 音量波纹 -->
    <div class="volume-ring" :style="{ transform: `scale(${1 + volumeLevel * 0.5})`, opacity: 0.3 + volumeLevel * 0.7 }">
      <div class="ring-inner"></div>
    </div>

    <!-- 控制按钮 -->
    <div class="controls">
      <button
        v-if="callState === 'idle' || callState === 'speaking'"
        class="call-btn start"
        @click="startRecording"
      >
        <span class="btn-icon">🎤</span>
        <span>按住说话</span>
      </button>

      <button
        v-else-if="callState === 'listening'"
        class="call-btn listening"
        @mousedown.prevent="stopRecording"
        @touchstart.prevent="stopRecording"
      >
        <span class="btn-icon pulse">⏺</span>
        <span>松手发送</span>
      </button>

      <button
        v-else-if="callState === 'processing'"
        class="call-btn processing"
        disabled
      >
        <span class="btn-icon spin">⏳</span>
        <span>思考中...</span>
      </button>

      <button
        v-else-if="callState === 'connecting'"
        class="call-btn processing"
        disabled
      >
        <span class="btn-icon spin">⏳</span>
        <span>连接中...</span>
      </button>

      <button class="end-btn" @click="endCall">
        <el-icon :size="18"><Close /></el-icon>
        结束通话
      </button>
    </div>
  </div>
</template>

<style scoped>
.voice-call {
  height: calc(100vh - 60px);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(180deg, #e8f4f8 0%, #d4e9d7 40%, #f0ebe3 100%);
  gap: 20px;
  position: relative;
  overflow: hidden;
}

/* Live2D */
.avatar-area {
  flex: 1;
  width: 100%;
  max-width: 500px;
  min-height: 300px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.live2d {
  width: 100%;
  height: 100%;
}

/* Status */
.status-bar {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 20px;
  border-radius: 20px;
  font-size: 14px;
  color: #5a6577;
  background: rgba(255,255,255,0.8);
  backdrop-filter: blur(8px);
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #a0aec0;
}

.status-dot.listening { background: #5a8a6a; animation: pulse 1s ease infinite; }
.status-dot.processing { background: #c4956a; animation: pulse 0.8s ease infinite; }
.status-dot.speaking { background: #6a9fb5; }

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.3); }
}

/* Volume ring */
.volume-ring {
  width: 120px;
  height: 120px;
  border-radius: 50%;
  border: 3px solid rgba(90, 138, 106, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  transition: transform 0.1s, opacity 0.1s;
  position: absolute;
  bottom: 160px;
}

.ring-inner {
  width: 80px;
  height: 80px;
  border-radius: 50%;
  background: rgba(90, 138, 106, 0.1);
}

/* Controls */
.controls {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding-bottom: 32px;
}

.call-btn {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 16px 40px;
  border: none;
  border-radius: 50px;
  font-size: 16px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  color: #fff;
  min-width: 200px;
  justify-content: center;
}

.call-btn.start {
  background: linear-gradient(135deg, #5a8a6a, #4d7a5e);
  box-shadow: 0 4px 20px rgba(90, 138, 106, 0.4);
}

.call-btn.start:hover {
  transform: scale(1.05);
  box-shadow: 0 6px 24px rgba(90, 138, 106, 0.5);
}

.call-btn.listening {
  background: linear-gradient(135deg, #c0705a, #a85a48);
  box-shadow: 0 4px 20px rgba(192, 112, 90, 0.4);
}

.call-btn.processing {
  background: #a0aec0;
  cursor: not-allowed;
}

.btn-icon { font-size: 20px; }

.btn-icon.pulse { animation: pulse 0.8s ease infinite; }
.btn-icon.spin { animation: spin 1s linear infinite; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.end-btn {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 8px 20px;
  border: 1px solid #d5d2cc;
  border-radius: 20px;
  background: rgba(255,255,255,0.6);
  color: #8d95a3;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.end-btn:hover {
  border-color: #c0705a;
  color: #c0705a;
  background: rgba(255,255,255,0.9);
}
</style>
