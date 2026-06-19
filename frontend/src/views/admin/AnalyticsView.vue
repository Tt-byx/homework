<script setup>
import { ref, onMounted, onUnmounted, nextTick } from 'vue'
import * as echarts from 'echarts'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  importAnalyticsData,
  getConsumptionTrend,
  getVisitorProfile,
  getSatisfaction,
  getPeakPeriods,
  getTopAttractions,
} from '@/api/analytics'

// ── State ──
const loading = ref(false)
const importing = ref(false)
const dataImported = ref(false)

// Chart instances
let consumptionChart = null
let ageChart = null
let genderChart = null
let satisfactionChart = null
let attractionsChart = null
let peakChart = null

// ── Color palette (extended from DashboardView) ──
const palette = {
  sage: '#5a8a6a',
  sageLight: '#7ba88a',
  warm: '#c4956a',
  stone: '#8a8578',
  teal: '#6a858a',
  rose: '#c0705a',
  lavender: '#8b7bb5',
  gold: '#bfa76a',
  coral: '#d4827a',
  sky: '#6a9fb5',
}

const consumptionColors = [
  palette.sage, palette.warm, palette.coral, palette.teal, palette.lavender,
]

// ── Data Import ──
async function handleImport() {
  try {
    await ElMessageBox.confirm(
      '将解析 xlsx 文件并导入到数据库，已有数据会被清空。确认继续？',
      '导入数据',
      { confirmButtonText: '开始导入', cancelButtonText: '取消', type: 'warning' }
    )
  } catch { return }

  importing.value = true
  try {
    const res = await importAnalyticsData()
    ElMessage.success(`导入成功：${res?.totalRows || 0} 条记录`)
    dataImported.value = true
    await fetchData()
  } catch (e) {
    ElMessage.error('导入失败: ' + (e?.message || '未知错误'))
  } finally {
    importing.value = false
  }
}

// ── Fetch all analytics data ──
async function fetchData() {
  loading.value = true
  try {
    const [consumption, profile, satisf, peak, attractions] = await Promise.all([
      getConsumptionTrend().catch(() => null),
      getVisitorProfile().catch(() => null),
      getSatisfaction().catch(() => null),
      getPeakPeriods().catch(() => null),
      getTopAttractions().catch(() => null),
    ])

    await nextTick()

    if (consumption?.data) renderConsumptionChart(consumption.data)
    if (profile) renderProfileCharts(profile)
    if (satisf?.data) renderSatisfactionChart(satisf.data)
    if (peak?.data) renderPeakChart(peak.data)
    if (attractions?.data) renderAttractionsChart(attractions.data)
  } catch (e) {
    console.error('获取分析数据失败:', e)
  } finally {
    loading.value = false
  }
}

// ── Chart Renderers ──

function renderConsumptionChart(data) {
  const el = document.getElementById('consumption-chart')
  if (!el || !data.length) return
  if (!consumptionChart) consumptionChart = echarts.init(el)

  const months = data.map(d => d.month)

  consumptionChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(45,52,64,0.92)',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => {
        let tip = `<div style="font-weight:600;margin-bottom:6px">${params[0].axisValue}</div>`
        params.forEach(p => {
          tip += `<div style="display:flex;align-items:center;gap:6px;margin:3px 0">
            <span style="width:8px;height:8px;border-radius:50%;background:${p.color};flex-shrink:0"></span>
            <span>${p.seriesName}</span>
            <span style="margin-left:auto;font-weight:600">¥${Number(p.value).toFixed(0)}</span>
          </div>`
        })
        return tip
      },
    },
    legend: {
      data: ['门票', '餐饮', '购物', '交通', '娱乐'],
      bottom: 0,
      itemGap: 16,
      textStyle: { fontSize: 12, color: '#8d95a3' },
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: { top: 16, right: 20, bottom: 48, left: 56 },
    xAxis: {
      type: 'category',
      data: months,
      axisLine: { lineStyle: { color: '#eae8e4' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      name: '元',
      nameTextStyle: { color: '#8d95a3', fontSize: 11, padding: [0, 30, 0, 0] },
      splitLine: { lineStyle: { color: '#f0efec', type: 'dashed' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
    },
    series: [
      { name: '门票', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: data.map(d => d.avg_ticket), itemStyle: { color: consumptionColors[0] }, lineStyle: { width: 2.5 }, areaStyle: gradientArea(consumptionColors[0]) },
      { name: '餐饮', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: data.map(d => d.avg_food), itemStyle: { color: consumptionColors[1] }, lineStyle: { width: 2.5 }, areaStyle: gradientArea(consumptionColors[1]) },
      { name: '购物', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: data.map(d => d.avg_shopping), itemStyle: { color: consumptionColors[2] }, lineStyle: { width: 2.5 }, areaStyle: gradientArea(consumptionColors[2]) },
      { name: '交通', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: data.map(d => d.avg_transport), itemStyle: { color: consumptionColors[3] }, lineStyle: { width: 2.5 }, areaStyle: gradientArea(consumptionColors[3]) },
      { name: '娱乐', type: 'line', smooth: true, symbol: 'circle', symbolSize: 5, data: data.map(d => d.avg_entertainment), itemStyle: { color: consumptionColors[4] }, lineStyle: { width: 2.5 }, areaStyle: gradientArea(consumptionColors[4]) },
    ],
  })
}

function renderProfileCharts(profile) {
  // Age distribution
  const ageEl = document.getElementById('age-chart')
  if (ageEl && profile.ageDistribution) {
    if (!ageChart) ageChart = echarts.init(ageEl)
    const ageOrder = ['18岁以下', '18-25岁', '26-35岁', '36-45岁', '46-55岁', '55岁以上']
    const ageData = ageOrder.map(label => {
      const found = profile.ageDistribution.find(d => d.age_group === label)
      return { name: label, value: found ? found.count : 0 }
    })

    ageChart.setOption({
      tooltip: { trigger: 'axis', backgroundColor: 'rgba(45,52,64,0.92)', borderColor: 'transparent', textStyle: { color: '#fff', fontSize: 12 } },
      grid: { top: 12, right: 16, bottom: 32, left: 68 },
      xAxis: {
        type: 'value',
        splitLine: { lineStyle: { color: '#f0efec', type: 'dashed' } },
        axisLabel: { color: '#8d95a3', fontSize: 11 },
      },
      yAxis: {
        type: 'category',
        data: ageData.map(d => d.name),
        axisLine: { show: false },
        axisTick: { show: false },
        axisLabel: { color: '#5a6577', fontSize: 12 },
      },
      series: [{
        type: 'bar',
        data: ageData.map((d, i) => ({
          value: d.value,
          itemStyle: {
            color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
              { offset: 0, color: blendColor(palette.sage, '#ffffff', 0.5 - i * 0.06) },
              { offset: 1, color: palette.sage },
            ]),
            borderRadius: [0, 4, 4, 0],
          },
        })),
        barWidth: '55%',
        barMaxWidth: 24,
      }],
    })
  }

  // Gender distribution
  const genderEl = document.getElementById('gender-chart')
  if (genderEl && profile.genderDistribution) {
    if (!genderChart) genderChart = echarts.init(genderEl)
    const genderLabels = { '男': '男性', '女': '女性' }
    const genderColors = { '男': palette.teal, '女': palette.rose }

    genderChart.setOption({
      tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)', backgroundColor: 'rgba(45,52,64,0.92)', borderColor: 'transparent', textStyle: { color: '#fff' } },
      legend: { bottom: 0, itemGap: 20, textStyle: { fontSize: 12, color: '#8d95a3' }, itemWidth: 10, itemHeight: 10 },
      series: [{
        type: 'pie',
        radius: ['48%', '72%'],
        center: ['50%', '42%'],
        avoidLabelOverlap: true,
        label: { show: true, formatter: '{b}\n{d}%', fontSize: 11, color: '#5a6577', lineHeight: 16 },
        data: profile.genderDistribution.map(d => ({
          name: genderLabels[d.gender] || d.gender,
          value: d.count,
          itemStyle: { color: genderColors[d.gender] || palette.stone },
        })),
      }],
    })
  }
}

function renderSatisfactionChart(data) {
  const el = document.getElementById('satisfaction-chart')
  if (!el || !data.length) return
  if (!satisfactionChart) satisfactionChart = echarts.init(el)

  const sorted = [...data].sort((a, b) => a.score - b.score)

  satisfactionChart.setOption({
    tooltip: { trigger: 'axis', backgroundColor: 'rgba(45,52,64,0.92)', borderColor: 'transparent', textStyle: { color: '#fff' } },
    grid: { top: 12, right: 16, bottom: 32, left: 44 },
    xAxis: {
      type: 'category',
      data: sorted.map(d => `${d.score}分`),
      axisLine: { lineStyle: { color: '#eae8e4' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0efec', type: 'dashed' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
    },
    series: [{
      type: 'bar',
      data: sorted.map(d => d.count),
      barWidth: '50%',
      barMaxWidth: 32,
      itemStyle: {
        color: (params) => {
          const score = sorted[params.dataIndex].score
          if (score >= 4) return palette.sage
          if (score >= 3) return palette.gold
          if (score >= 2) return palette.warm
          return palette.rose
        },
        borderRadius: [4, 4, 0, 0],
      },
    }],
  })
}

function renderPeakChart(data) {
  const el = document.getElementById('peak-chart')
  if (!el || !data.length) return
  if (!peakChart) peakChart = echarts.init(el)

  peakChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(45,52,64,0.92)',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => {
        const d = data[params[0].dataIndex]
        return `<div style="font-weight:600">${params[0].axisValue}</div>
          <div>总访问: ${d.visitor_count}</div>
          <div>独立游客: ${d.unique_visitors}</div>`
      },
    },
    legend: {
      data: ['总访问量', '独立游客'],
      bottom: 0,
      itemGap: 16,
      textStyle: { fontSize: 12, color: '#8d95a3' },
      itemWidth: 12,
      itemHeight: 8,
    },
    grid: { top: 16, right: 20, bottom: 48, left: 56 },
    xAxis: {
      type: 'category',
      data: data.map(d => d.month),
      axisLine: { lineStyle: { color: '#eae8e4' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0efec', type: 'dashed' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
    },
    series: [
      {
        name: '总访问量', type: 'bar',
        data: data.map(d => d.visitor_count),
        barWidth: '35%',
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: palette.sageLight },
            { offset: 1, color: palette.sage },
          ]),
          borderRadius: [4, 4, 0, 0],
        },
      },
      {
        name: '独立游客', type: 'line',
        data: data.map(d => d.unique_visitors),
        smooth: true,
        symbol: 'circle', symbolSize: 6,
        itemStyle: { color: palette.warm },
        lineStyle: { width: 2.5 },
      },
    ],
  })
}

function renderAttractionsChart(data) {
  const el = document.getElementById('attractions-chart')
  if (!el || !data.length) return
  if (!attractionsChart) attractionsChart = echarts.init(el)

  const sorted = [...data].reverse()

  attractionsChart.setOption({
    tooltip: {
      trigger: 'axis',
      backgroundColor: 'rgba(45,52,64,0.92)',
      borderColor: 'transparent',
      textStyle: { color: '#fff', fontSize: 12 },
      formatter: (params) => {
        const d = sorted[params[0].dataIndex]
        return `<div style="font-weight:600;margin-bottom:4px">${d.attraction_name}</div>
          <div style="font-size:11px;opacity:0.7">${d.attraction_type || ''}</div>
          <div>访问量: ${d.visit_count}</div>
          <div>满意度: ${Number(d.avg_satisfaction).toFixed(1)}</div>
          <div>人均消费: ¥${Number(d.avg_cost).toFixed(0)}</div>`
      },
    },
    grid: { top: 8, right: 80, bottom: 12, left: 110 },
    xAxis: {
      type: 'value',
      splitLine: { lineStyle: { color: '#f0efec', type: 'dashed' } },
      axisLabel: { color: '#8d95a3', fontSize: 11 },
    },
    yAxis: {
      type: 'category',
      data: sorted.map(d => truncate(d.attraction_name, 8)),
      axisLine: { show: false },
      axisTick: { show: false },
      axisLabel: { color: '#5a6577', fontSize: 12 },
    },
    series: [{
      type: 'bar',
      data: sorted.map((d, i) => ({
        value: d.visit_count,
        itemStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 1, 0, [
            { offset: 0, color: blendColor(palette.teal, '#ffffff', 0.4) },
            { offset: 1, color: palette.teal },
          ]),
          borderRadius: [0, 4, 4, 0],
        },
      })),
      barWidth: '55%',
      barMaxWidth: 20,
      label: {
        show: true,
        position: 'right',
        formatter: '{c}',
        fontSize: 11,
        color: '#8d95a3',
      },
    }],
  })
}

// ── Utilities ──
function gradientArea(color) {
  return {
    color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
      { offset: 0, color: hexToRgba(color, 0.15) },
      { offset: 1, color: hexToRgba(color, 0.02) },
    ]),
  }
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16)
  const g = parseInt(hex.slice(3, 5), 16)
  const b = parseInt(hex.slice(5, 7), 16)
  return `rgba(${r},${g},${b},${alpha})`
}

function blendColor(hex1, hex2, ratio) {
  const parse = h => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)]
  const c1 = parse(hex1), c2 = parse(hex2)
  const r = Math.round(c1[0] * (1 - ratio) + c2[0] * ratio)
  const g = Math.round(c1[1] * (1 - ratio) + c2[1] * ratio)
  const b = Math.round(c1[2] * (1 - ratio) + c2[2] * ratio)
  return `#${r.toString(16).padStart(2, '0')}${g.toString(16).padStart(2, '0')}${b.toString(16).padStart(2, '0')}`
}

function truncate(str, len) {
  if (!str) return ''
  return str.length > len ? str.slice(0, len) + '…' : str
}

// ── Lifecycle ──
const allCharts = () => [consumptionChart, ageChart, genderChart, satisfactionChart, attractionsChart, peakChart]

onMounted(() => {
  fetchData()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  allCharts().forEach(c => c?.dispose())
})

function handleResize() {
  allCharts().forEach(c => c?.resize())
}
</script>

<template>
  <div class="analytics" v-loading="loading">
    <!-- Header -->
    <div class="page-header">
      <div class="header-text">
        <h2 class="page-title">消费分析</h2>
        <p class="page-desc">基于游客行为数据的多维度分析，辅助运营决策</p>
      </div>
      <el-button
        type="primary"
        :loading="importing"
        @click="handleImport"
        class="import-btn"
      >
        <el-icon v-if="!importing" :size="16"><Upload /></el-icon>
        {{ importing ? '导入中...' : '导入 xlsx 数据' }}
      </el-button>
    </div>

    <!-- Empty state -->
    <div v-if="!loading && !dataImported" class="empty-state">
      <div class="empty-icon">
        <svg viewBox="0 0 80 80" fill="none">
          <rect x="12" y="20" width="56" height="44" rx="6" stroke="#d5d2cc" stroke-width="2"/>
          <path d="M24 36h32M24 44h20M24 52h24" stroke="#d5d2cc" stroke-width="1.5" stroke-linecap="round"/>
          <circle cx="60" cy="20" r="10" fill="#e8f0eb" stroke="#5a8a6a" stroke-width="1.5"/>
          <path d="M57 20h6M60 17v6" stroke="#5a8a6a" stroke-width="1.5" stroke-linecap="round"/>
        </svg>
      </div>
      <p class="empty-title">尚未导入分析数据</p>
      <p class="empty-desc">点击上方"导入 xlsx 数据"按钮，将游客行为分析数据导入系统</p>
    </div>

    <!-- Charts Grid -->
    <template v-if="dataImported || loading">
      <!-- Row 1: Consumption trend (wide) + Gender (small) -->
      <div class="charts-row">
        <div class="panel panel--wide">
          <div class="panel-head">
            <span class="panel-title">月度消费趋势</span>
            <span class="panel-hint">各消费类别的月均变化</span>
          </div>
          <div id="consumption-chart" class="chart-area chart-area--tall"></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title">性别比例</span>
          </div>
          <div id="gender-chart" class="chart-area"></div>
        </div>
      </div>

      <!-- Row 2: Age + Satisfaction + Peak -->
      <div class="charts-row charts-row--triple">
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title">年龄分布</span>
          </div>
          <div id="age-chart" class="chart-area"></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title">满意度分布</span>
          </div>
          <div id="satisfaction-chart" class="chart-area"></div>
        </div>
        <div class="panel">
          <div class="panel-head">
            <span class="panel-title">月度客流</span>
            <span class="panel-hint">访问量 vs 独立游客</span>
          </div>
          <div id="peak-chart" class="chart-area"></div>
        </div>
      </div>

      <!-- Row 3: Top Attractions (full width) -->
      <div class="panel">
        <div class="panel-head">
          <span class="panel-title">热门景点 Top 10</span>
          <span class="panel-hint">按访问量排序</span>
        </div>
        <div id="attractions-chart" class="chart-area chart-area--medium"></div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.analytics {
  max-width: 1200px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

/* ── Header ── */
.page-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.page-title {
  font-size: 20px;
  font-weight: 700;
  color: var(--text-primary, #2d3440);
  margin: 0;
  line-height: 1.3;
}

.page-desc {
  font-size: 13px;
  color: var(--text-tertiary, #8d95a3);
  margin: 4px 0 0;
}

.import-btn {
  flex-shrink: 0;
  background: #5a8a6a;
  border-color: #5a8a6a;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  height: 36px;
  padding: 0 18px;
  display: flex;
  align-items: center;
  gap: 6px;
}

.import-btn:hover {
  background: #4d7a5e;
  border-color: #4d7a5e;
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  background: var(--bg-card, #fff);
  border-radius: 10px;
  border: 1px solid var(--border-light, #eae8e4);
}

.empty-icon svg {
  width: 80px;
  height: 80px;
  opacity: 0.8;
}

.empty-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text-secondary, #5a6577);
  margin: 20px 0 8px;
}

.empty-desc {
  font-size: 13px;
  color: var(--text-tertiary, #8d95a3);
  text-align: center;
  max-width: 360px;
  line-height: 1.6;
}

/* ── Panels ── */
.panel {
  background: var(--bg-card, #ffffff);
  border-radius: 10px;
  border: 1px solid var(--border-light, #eae8e4);
  padding: 20px;
  transition: box-shadow 0.2s ease;
}

.panel:hover {
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.04);
}

.panel-head {
  display: flex;
  align-items: baseline;
  gap: 10px;
  margin-bottom: 16px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light, #eae8e4);
}

.panel-title {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #2d3440);
}

.panel-hint {
  font-size: 12px;
  color: var(--text-tertiary, #8d95a3);
}

/* ── Chart areas ── */
.chart-area {
  width: 100%;
  height: 280px;
}

.chart-area--tall {
  height: 320px;
}

.chart-area--medium {
  height: 360px;
}

/* ── Grid layouts ── */
.charts-row {
  display: grid;
  grid-template-columns: 3fr 2fr;
  gap: 16px;
}

.charts-row--triple {
  grid-template-columns: 1fr 1fr 1fr;
}

@media (max-width: 900px) {
  .charts-row,
  .charts-row--triple {
    grid-template-columns: 1fr;
  }
  .page-header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
