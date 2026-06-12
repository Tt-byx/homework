<script setup>
import { ref, onMounted } from 'vue'
import { getConversations } from '@/api/dashboard'

const conversations = ref([])

async function fetchConversations() {
  try {
    const data = await getConversations()
    conversations.value = data?.conversations || []
  } catch (e) {
    console.error('获取对话记录失败:', e)
  }
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => fetchConversations())
</script>

<template>
  <div class="conversations-page">
    <h2>💬 对话记录</h2>

    <el-table :data="conversations" stripe>
      <el-table-column type="index" label="#" width="50" />
      <el-table-column prop="title" label="会话主题" min-width="150" show-overflow-tooltip />
      <el-table-column prop="first_user_message" label="首条消息" min-width="200" show-overflow-tooltip />
      <el-table-column prop="last_ai_reply" label="最新回复" min-width="250" show-overflow-tooltip />
      <el-table-column prop="message_count" label="消息数" width="80" align="center" />
      <el-table-column label="时间" width="170" align="center">
        <template #default="{ row }">{{ formatTime(row.session_time) }}</template>
      </el-table-column>
    </el-table>

    <el-empty v-if="conversations.length === 0" description="暂无对话记录" />
  </div>
</template>

<style scoped>
.conversations-page { padding: 20px; max-width: 1200px; margin: 0 auto; }
.conversations-page h2 { margin-bottom: 20px; font-size: 22px; color: #303133; }
</style>
