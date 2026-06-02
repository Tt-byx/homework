<script setup>
import { ref } from 'vue'

const emit = defineEmits(['send'])

const props = defineProps({
  loading: {
    type: Boolean,
    default: false,
  },
})

const inputText = ref('')

function handleSend() {
  const text = inputText.value.trim()
  if (!text || props.loading) return
  emit('send', text)
  inputText.value = ''
}

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}
</script>

<template>
  <div class="chat-input">
    <el-input
      v-model="inputText"
      type="textarea"
      :rows="2"
      placeholder="输入你的问题..."
      resize="none"
      :disabled="loading"
      @keydown="handleKeydown"
    />
    <el-button
      type="primary"
      :loading="loading"
      :disabled="!inputText.trim()"
      @click="handleSend"
    >
      发送
    </el-button>
  </div>
</template>

<style scoped>
.chat-input {
  display: flex;
  gap: 10px;
  padding: 16px 20px;
  border-top: 1px solid #e4e7ed;
  background: #fff;
  align-items: flex-end;
}

.chat-input .el-textarea {
  flex: 1;
}

.chat-input .el-button {
  height: 54px;
  min-width: 80px;
}
</style>
