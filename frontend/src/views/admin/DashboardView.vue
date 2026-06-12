<script setup>
import { ref, onMounted, onUnmounted } from 'vue'
import * as echarts from 'echarts'
import { getOverview, getSentiment, getTrends, getConversations, getTopQuestions } from '@/api/dashboard'

const overview = ref({ todaySessions: 0, todayMessages: 0, totalSessions: 0, totalMessages: 0 })
const sentimentData = ref([])
const trendData = ref({ sessions: [], messages: [] })
const conversations = ref([])
const topQuestions = ref([])

let sentimentChart = null
let trendChart = null
let questionsChart = null

const sentimentColors = { positive: '#67c23a', neutral: '#909399', negative: '#f56c6c' }
const sentimentLabels = { positive: '正面', neutral: '中性', negative: '负面' }

async function fetchData() {
  try {
    const [ov, sent, trend, conv, top] = await Promise.all([
      getOverview(), getSentiment(), getTrends(), getConversations(), getTopQuestions(),
    ])
    overview.value = ov || overview.value
    sentimentData.value = sent?.distribution || []
    trendData.value = trend || trendData.value
    conversations.value = conv?.conversations || []
    topQuestions.value = top?.questions || []
    renderCharts()
  } catch (e) {
    console.error('获取数据大屏数据失败:', e)
  }
}

function renderCharts() {
  // 情感分布饼图
  const sentEl = document.getElementById('sentiment-chart')
  if (sentEl) {
    if (!sentimentChart) sentimentChart = echarts.init(sentEl)
    sentimentChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
      legend: { bottom: 0 },
      series: [{
        type: 'pie', radius: ['40%', '70%'],
        label: { show: true, formatter: '{b}\n{d}%' },
        data: sentimentData.value.map(d => ({
          name: sentimentLabels[d.sentiment] || d.sentiment,
          value: d.count,
          itemStyle: { color: sentimentColors[d.sentiment] || '#409eff' },
        })),
      }],
    })
  }

  // 趋势折线图
  const trendEl = document.getElementById('trend-chart')
  if (trendEl) {
    if (!trendChart) trendChart = echarts.init(trendEl)
    const dates = trendData.value.sessions?.map(d => d.date) || []
    const sessionCounts = trendData.value.sessions?.map(d => d.count) || []
    const msgCounts = trendData.value.messages?.map(d => d.count) || []
    trendChart.setOption({
      tooltip: { trigger: 'axis' },
      legend: { data: ['会话数', '消息数'], bottom: 0 },
      xAxis: { type: 'category', data: dates },
      yAxis: { type: 'value' },
      series: [
        { name: '会话数', type: 'line', smooth: true, data: sessionCounts, itemStyle: { color: '#409eff' } },
        { name: '消息数', type: 'line', smooth: true, data: msgCounts, itemStyle: { color: '#67c23a' } },
      ],
    })
  }

  // 热门问题柱状图
  const qEl = document.getElementById('questions-chart')
  if (qEl) {
    if (!questionsChart) questionsChart = echarts.init(qEl)
    const labels = topQuestions.value.map((_, i) => `Q${i + 1}`)
    const values = topQuestions.value.map(q => q.count)
    questionsChart.setOption({
      tooltip: {
        trigger: 'axis',
        formatter: (params) => {
          const idx = params[0].dataIndex
          const q = topQuestions.value[idx]
          return `${q?.content || ''}<br/>提问次数: ${q?.count || 0}`
        },
      },
      xAxis: { type: 'category', data: labels },
      yAxis: { type: 'value' },
      series: [{
        type: 'bar', data: values, barWidth: '60%',
        itemStyle: { color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: '#667eea' }, { offset: 1, color: '#764ba2' },
        ]) },
      }],
    })
  }
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

onMounted(() => {
  fetchData()
  window.addEventListener('resize', () => {
    sentimentChart?.resize(); trendChart?.resize(); questionsChart?.resize()
  })
})
onUnmounted(() => {
  sentimentChart?.dispose(); trendChart?.dispose(); questionsChart?.dispose()
})
</script>

<template>
  <div class="dashboard">
    <h2>📊 数据大屏</h2>

    <div class="overview-cards">
      <div class="card"><div class="card-value">{{ overview.todaySessions }}</div><div class="card-label">今日会话</div></div>
      <div class="card"><div class="card-value">{{ overview.todayMessages }}</div><div class="card-label">今日消息</div></div>
      <div class="card"><div class="card-value">{{ overview.totalSessions }}</div><div class="card-label">总会话数</div></div>
      <div class="card"><div class="card-value">{{ overview.totalMessages }}</div><div class="card-label">总消息数</div></div>
    </div>

    <div class="charts-row">
      <div class="chart-card"><h3>📈 近7天趋势</h3><div id="trend-chart" class="chart"></div></div>
      <div class="chart-card"><h3>😊 情感分布</h3><div id="sentiment-chart" class="chart"></div></div>
    </div>

    <div class="charts-row single">
      <div class="chart-card"><h3>🔥 热门问题 Top10</h3><div id="questions-chart" class="chart"></div></div>
    </div>

    <div class="conversations-card">
      <h3>💬 最近对话</h3>
      <el-table :data="conversations" stripe>
        <el-table-column prop="title" label="会话主题" min-width="150" show-overflow-tooltip />
        <el-table-column prop="first_user_message" label="首条消息" min-width="200" show-overflow-tooltip />
        <el-table-column prop="last_ai_reply" label="最新回复" min-width="200" show-overflow-tooltip />
        <el-table-column prop="message_count" label="消息数" width="80" align="center" />
        <el-table-column label="时间" width="150" align="center">
          <template #default="{ row }">{{ formatTime(row.session_time) }}</template>
        </el-table-column>
      </el-table>
    </div>
  </div>
</template>

<style scoped>
.dashboard { padding: 20px; max-width: 1200px; margin: 0 auto; }
.dashboard h2 { margin-bottom: 20px; font-size: 22px; color: #303133; }

.overview-cards { display: grid; grid-template-columns: repeat(4, 1fr); gap: 16px; margin-bottom: 20px; }
.card { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-radius: 12px; padding: 24px; text-align: center; color: #fff; box-shadow: 0 4px 12px rgba(102,126,234,0.3); }
.card-value { font-size: 36px; font-weight: 700; margin-bottom: 8px; }
.card-label { font-size: 14px; opacity: 0.9; }

.charts-row { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 20px; }
.charts-row.single { grid-template-columns: 1fr; }
.chart-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.chart-card h3 { font-size: 15px; color: #303133; margin-bottom: 16px; }
.chart { width: 100%; height: 300px; }

.conversations-card { background: #fff; border-radius: 12px; padding: 20px; box-shadow: 0 2px 12px rgba(0,0,0,0.06); }
.conversations-card h3 { font-size: 15px; color: #303133; margin-bottom: 16px; }

@media (max-width: 900px) { .overview-cards { grid-template-columns: repeat(2, 1fr); } .charts-row { grid-template-columns: 1fr; } }
</style>
