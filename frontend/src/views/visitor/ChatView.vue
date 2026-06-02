<script setup>
import { useChatStore } from '@/stores/chat'
import ChatMessage from '@/components/chat/ChatMessage.vue'
import MessageList from '@/components/chat/MessageList.vue'
import ChatInput from '@/components/chat/ChatInput.vue'

const chatStore = useChatStore()

function handleSend(message) {
  chatStore.sendMessage(message)
}
</script>

<template>
  <div class="chat-view">
    <div class="chat-container">
      <MessageList :messages="chatStore.messages" :loading="chatStore.loading">
        <ChatMessage
          v-for="(msg, index) in chatStore.messages"
          :key="index"
          :message="msg"
        />
      </MessageList>
      <ChatInput :loading="chatStore.loading" @send="handleSend" />
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
