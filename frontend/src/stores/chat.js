import { defineStore } from 'pinia'
import { ref } from 'vue'
import { sendChatMessage } from '@/api/chat'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const sessionId = ref(null)
  const loading = ref(false)

  async function sendMessage(content) {
    messages.value.push({ role: 'user', content, timestamp: Date.now() })

    loading.value = true
    try {
      const reply = await sendChatMessage(content, sessionId.value)
      sessionId.value = reply.sessionId
      messages.value.push({
        role: 'assistant',
        content: reply.reply,
        timestamp: Date.now(),
      })
    } catch (err) {
      messages.value.push({
        role: 'assistant',
        content: '抱歉，暂时无法回答，请稍后再试。',
        timestamp: Date.now(),
      })
    } finally {
      loading.value = false
    }
  }

  function clearMessages() {
    messages.value = []
    sessionId.value = null
  }

  return { messages, sessionId, loading, sendMessage, clearMessages }
})
