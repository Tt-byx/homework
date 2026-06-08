<script setup>
import { onMounted, onUnmounted } from 'vue'
import { useChatStore } from '@/stores/chat'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()

function handleSendText(message) {
  chatStore.sendTextMessage(message)
}

function handleSendVoice(audioBlob, format) {
  chatStore.sendVoiceMessage(audioBlob, format)
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
    <!-- 连接状态指示 -->
    <div v-if="!chatStore.isWsConnected" class="connection-status">
      <el-icon class="is-loading"><Loading /></el-icon>
      <span>正在连接服务器...</span>
    </div>

    <div class="chat-container">
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
        @send-voice="handleSendVoice"
      />
    </div>
  </div>
</template>

<style scoped>
.chat-view {
  width: 100%;
  max-width: 800px;
  height: calc(100vh - 60px);
  padding: 20px;
  display: flex;
  flex-direction: column;
}

.connection-status {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  background: #fdf6ec;
  border-radius: 8px;
  color: #e6a23c;
  font-size: 13px;
  margin-bottom: 12px;
}

.chat-container {
  flex: 1;
  display: flex;
  flex-direction: column;
  background: #fff;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.06);
  overflow: hidden;
}
</style>
