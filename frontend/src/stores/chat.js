import { defineStore } from 'pinia'
import { ref } from 'vue'
import { chatWs } from '@/api/websocket'
import { AudioPlayer } from '@/components/chat/AudioPlayer'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const sessionId = ref(null)
  const loading = ref(false)
  const isRecording = ref(false)
  const isWsConnected = ref(false)

  // 音频播放器
  const audioPlayer = new AudioPlayer()

  // 当前正在流式接收的助手消息索引
  let currentAssistantIndex = -1

  /**
   * 初始化 WebSocket 连接
   */
  function initWebSocket() {
    chatWs.onConnect = () => {
      isWsConnected.value = true
      // 初始化 AudioContext（在用户交互后）
      audioPlayer.init()
    }

    chatWs.onDisconnect = () => {
      isWsConnected.value = false
    }

    chatWs.onAsrResult = (text) => {
      // ASR 识别结果：替换最后一条用户消息的内容（如果有占位）
      const lastUserMsg = [...messages.value].reverse().find(m => m.role === 'user')
      if (lastUserMsg && lastUserMsg.isVoice) {
        lastUserMsg.content = `🎤 ${text}`
      }
    }

    chatWs.onTextChunk = (text) => {
      // 流式文字：追加到当前助手消息
      if (currentAssistantIndex === -1) {
        // 创建新的助手消息
        currentAssistantIndex = messages.value.length
        messages.value.push({
          role: 'assistant',
          content: '',
          timestamp: Date.now(),
        })
      }
      messages.value[currentAssistantIndex].content += text
    }

    chatWs.onAudioChunk = (audioBase64, format) => {
      // 音频片段：加入播放队列
      audioPlayer.enqueue(audioBase64, format || 'wav')
    }

    chatWs.onDone = (data) => {
      loading.value = false
      if (data.session_id) {
        sessionId.value = data.session_id
      }
      currentAssistantIndex = -1
    }

    chatWs.onError = (errMsg) => {
      loading.value = false
      // 如果当前没有助手消息，创建一个错误消息
      if (currentAssistantIndex === -1) {
        messages.value.push({
          role: 'assistant',
          content: `抱歉，${errMsg || '暂时无法回答，请稍后再试。'}`,
          timestamp: Date.now(),
          isError: true,
        })
      } else {
        messages.value[currentAssistantIndex].content += `\n\n[错误: ${errMsg}]`
      }
      currentAssistantIndex = -1
    }

    chatWs.connect()
  }

  /**
   * 发送文字消息
   */
  function sendTextMessage(content) {
    if (!content.trim() || loading.value) return

    messages.value.push({
      role: 'user',
      content,
      timestamp: Date.now(),
      isVoice: false,
    })

    loading.value = true
    currentAssistantIndex = -1

    chatWs.sendText(content, sessionId.value)
  }

  /**
   * 发送语音消息
   */
  function sendVoiceMessage(audioBlob, format) {
    if (!audioBlob || loading.value) return

    // 先添加一条占位用户消息
    messages.value.push({
      role: 'user',
      content: '🎤 正在识别...',
      timestamp: Date.now(),
      isVoice: true,
    })

    loading.value = true
    currentAssistantIndex = -1

    chatWs.sendAudio(audioBlob, format, sessionId.value)
  }

  /**
   * 清空消息
   */
  function clearMessages() {
    messages.value = []
    sessionId.value = null
    currentAssistantIndex = -1
    audioPlayer.stop()
  }

  /**
   * 销毁
   */
  function destroy() {
    chatWs.disconnect()
    audioPlayer.destroy()
  }

  return {
    messages,
    sessionId,
    loading,
    isRecording,
    isWsConnected,
    initWebSocket,
    sendTextMessage,
    sendVoiceMessage,
    clearMessages,
    destroy,
  }
})
