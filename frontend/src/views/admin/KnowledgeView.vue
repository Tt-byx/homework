<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import {
  uploadKnowledge,
  getKnowledgeList,
  deleteKnowledge,
  reprocessKnowledge,
} from '@/api/knowledge'
import { ElMessage, ElMessageBox } from 'element-plus'

const documents = ref([])
const uploadTitle = ref('')
const uploading = ref(false)
const selectedFile = ref(null)
let pollTimer = null

const statusConfig = {
  0: { label: '未处理', type: 'info', icon: 'Clock' },
  1: { label: '处理中', type: 'warning', icon: 'Loading' },
  2: { label: '已完成', type: 'success', icon: 'CircleCheck' },
  3: { label: '失败', type: 'danger', icon: 'CircleClose' },
}

const fileTypeConfig = {
  docx: { color: '#4a7c59', bg: '#eef5f0' },
  xlsx: { color: '#7c6b4a', bg: '#f5f0ee' },
  pdf: { color: '#7c4a4a', bg: '#f5eeee' },
}

const isProcessing = computed(() =>
  documents.value.some((d) => d.vectorStatus === 1)
)

function handleFileChange(file) {
  selectedFile.value = file.raw
  if (!uploadTitle.value) {
    uploadTitle.value = file.name.replace(/\.[^.]+$/, '')
  }
}

function handleFileRemove() {
  selectedFile.value = null
}

async function handleUpload() {
  if (!selectedFile.value) {
    ElMessage.warning('请选择文件')
    return
  }
  if (!uploadTitle.value.trim()) {
    ElMessage.warning('请输入文档标题')
    return
  }

  uploading.value = true
  try {
    await uploadKnowledge(selectedFile.value, uploadTitle.value.trim())
    ElMessage.success('上传成功，正在处理中...')
    uploadTitle.value = ''
    selectedFile.value = null
    await fetchList()
  } catch (err) {
    ElMessage.error('上传失败: ' + (err.message || '未知错误'))
  } finally {
    uploading.value = false
  }
}

async function fetchList() {
  try {
    const data = await getKnowledgeList()
    documents.value = Array.isArray(data) ? data : []
  } catch (err) {
    console.error('获取文档列表失败:', err)
  }
}

async function handleDelete(doc) {
  try {
    await ElMessageBox.confirm(
      `确定删除文档「${doc.title}」？删除后相关向量数据也将被清除。`,
      '确认删除',
      { confirmButtonText: '删除', cancelButtonText: '取消', type: 'warning' }
    )
    await deleteKnowledge(doc.id)
    ElMessage.success('已删除')
    await fetchList()
  } catch (err) {
    if (err !== 'cancel') {
      ElMessage.error('删除失败: ' + (err.message || '未知错误'))
    }
  }
}

async function handleReprocess(doc) {
  try {
    await reprocessKnowledge(doc.id)
    ElMessage.info('重新处理中...')
    await fetchList()
  } catch (err) {
    ElMessage.error('重处理失败: ' + (err.message || '未知错误'))
  }
}

function formatTime(time) {
  if (!time) return '-'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function startPolling() {
  pollTimer = setInterval(() => {
    if (isProcessing.value) {
      fetchList()
    }
  }, 3000)
}

onMounted(() => {
  fetchList()
  startPolling()
})

onUnmounted(() => {
  if (pollTimer) {
    clearInterval(pollTimer)
    pollTimer = null
  }
})
</script>

<template>
  <div class="knowledge-page">
    <!-- Page header with decorative landscape line -->
    <div class="page-header">
      <div class="header-content">
        <h2>知识库管理</h2>
        <p class="header-subtitle">管理景区资料文档，构建数字人知识底座</p>
      </div>
      <svg class="header-deco" viewBox="0 0 320 40" fill="none">
        <path
          d="M0 32 Q40 8 80 24 Q120 40 160 20 Q200 0 240 16 Q280 32 320 12"
          stroke="var(--accent-sage)"
          stroke-width="2"
          fill="none"
          opacity="0.3"
        />
        <path
          d="M0 36 Q50 16 100 28 Q150 40 200 22 Q250 4 320 18"
          stroke="var(--accent-sage)"
          stroke-width="1"
          fill="none"
          opacity="0.15"
        />
      </svg>
    </div>

    <!-- Upload card -->
    <div class="upload-card">
      <div class="card-header">
        <el-icon class="card-icon"><Upload /></el-icon>
        <span>上传景区资料</span>
      </div>
      <div class="upload-body">
        <el-input
          v-model="uploadTitle"
          placeholder="文档标题（如：灵山胜境游览指南）"
          class="title-input"
          :prefix-icon="Edit"
          clearable
        />
        <el-upload
          class="upload-area"
          drag
          :auto-upload="false"
          :limit="1"
          accept=".docx,.xlsx"
          :on-change="handleFileChange"
          :on-remove="handleFileRemove"
        >
          <div class="upload-inner">
            <el-icon class="upload-icon"><UploadFilled /></el-icon>
            <div class="upload-text">拖拽文件到此处，或 <em>点击选择</em></div>
            <div class="upload-hint">支持 .docx、.xlsx 格式</div>
          </div>
        </el-upload>
        <el-button
          type="primary"
          :loading="uploading"
          class="submit-btn"
          @click="handleUpload"
        >
          <el-icon v-if="!uploading"><Check /></el-icon>
          {{ uploading ? '上传中...' : '上传并处理' }}
        </el-button>
      </div>
    </div>

    <!-- Document list card -->
    <div class="list-card">
      <div class="card-header">
        <el-icon class="card-icon"><FolderOpened /></el-icon>
        <span>已上传文档</span>
        <el-tag v-if="documents.length" class="count-tag" size="small" type="info">
          {{ documents.length }}
        </el-tag>
      </div>

      <el-table
        v-if="documents.length"
        :data="documents"
        class="doc-table"
        stripe
        :header-cell-style="{ background: '#fafbfc', color: '#4a5568', fontWeight: 600 }"
      >
        <el-table-column prop="title" label="文档标题" min-width="180">
          <template #default="{ row }">
            <div class="doc-title-cell">
              <el-icon class="doc-icon" :style="{ color: (fileTypeConfig[row.fileType] || fileTypeConfig.docx).color }">
                <Document />
              </el-icon>
              <span>{{ row.title }}</span>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="fileName" label="文件名" min-width="160" show-overflow-tooltip />

        <el-table-column prop="fileType" label="类型" width="90" align="center">
          <template #default="{ row }">
            <span
              class="filetype-badge"
              :style="{
                color: (fileTypeConfig[row.fileType] || fileTypeConfig.docx).color,
                background: (fileTypeConfig[row.fileType] || fileTypeConfig.docx).bg,
              }"
            >
              {{ (row.fileType || '').toUpperCase() }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="chunkCount" label="切片数" width="90" align="center">
          <template #default="{ row }">
            <span class="chunk-count">{{ row.chunkCount ?? '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="vectorStatus" label="向量化状态" width="130" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusConfig[row.vectorStatus]?.type || 'info'"
              size="small"
              effect="light"
              :class="{ 'pulse-tag': row.vectorStatus === 1 }"
            >
              <el-icon v-if="row.vectorStatus === 1" class="rotating-icon"><Loading /></el-icon>
              {{ statusConfig[row.vectorStatus]?.label || '未知' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="createdAt" label="上传时间" width="170" align="center">
          <template #default="{ row }">
            <span class="time-text">{{ formatTime(row.createdAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="140" align="center" fixed="right">
          <template #default="{ row }">
            <el-button
              v-if="row.vectorStatus === 3"
              type="warning"
              size="small"
              text
              @click="handleReprocess(row)"
            >
              <el-icon><RefreshRight /></el-icon> 重试
            </el-button>
            <el-button
              type="danger"
              size="small"
              text
              @click="handleDelete(row)"
            >
              <el-icon><Delete /></el-icon> 删除
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-else class="empty-state">
        <div class="empty-illustration">
          <svg viewBox="0 0 120 80" fill="none">
            <path d="M20 70 Q40 30 60 50 Q80 70 100 40" stroke="var(--accent-sage)" stroke-width="2" opacity="0.25" />
            <circle cx="60" cy="30" r="8" fill="var(--accent-sage)" opacity="0.12" />
            <path d="M50 55 L60 40 L70 55 Z" fill="var(--accent-sage)" opacity="0.15" />
          </svg>
        </div>
        <p class="empty-text">暂无文档</p>
        <p class="empty-hint">上传景区资料，让数字人拥有专业知识</p>
      </div>
    </div>
  </div>
</template>

<style scoped>
.knowledge-page {
  --accent-sage: #5a8a6a;
  --accent-sage-light: #e8f0eb;
  --accent-warm: #c4956a;
  --text-primary: #2d3748;
  --text-secondary: #718096;
  --card-shadow: 0 1px 3px rgba(0, 0, 0, 0.06), 0 1px 2px rgba(0, 0, 0, 0.04);
  --card-shadow-hover: 0 4px 12px rgba(0, 0, 0, 0.08), 0 2px 4px rgba(0, 0, 0, 0.04);

  max-width: 960px;
  margin: 0 auto;
  padding: 24px 0;
}

/* ── Page header ── */
.page-header {
  margin-bottom: 24px;
  position: relative;
}

.header-content h2 {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary);
  letter-spacing: -0.3px;
}

.header-subtitle {
  margin-top: 4px;
  font-size: 13px;
  color: var(--text-secondary);
}

.header-deco {
  position: absolute;
  right: 0;
  top: 50%;
  transform: translateY(-50%);
  width: 200px;
  height: 40px;
}

/* ── Cards ── */
.upload-card,
.list-card {
  background: #fff;
  border-radius: 10px;
  box-shadow: var(--card-shadow);
  padding: 24px;
  margin-bottom: 20px;
  transition: box-shadow 0.25s ease;
}

.upload-card:hover,
.list-card:hover {
  box-shadow: var(--card-shadow-hover);
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
  padding-bottom: 14px;
  border-bottom: 1px solid #f0f0f0;
}

.card-icon {
  color: var(--accent-sage);
  font-size: 18px;
}

.count-tag {
  margin-left: 6px;
  font-size: 11px;
}

/* ── Upload body ── */
.upload-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px #e2e8f0 inset;
  transition: box-shadow 0.2s;
}

.title-input :deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px var(--accent-sage) inset;
}

.upload-area :deep(.el-upload-dragger) {
  border: 2px dashed #d4dce6;
  border-radius: 10px;
  background: #fafbfc;
  padding: 32px 20px;
  transition: all 0.25s ease;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-sage);
  background: var(--accent-sage-light);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
}

.upload-icon {
  font-size: 40px;
  color: #c0c9d6;
  transition: color 0.25s;
}

.upload-area :deep(.el-upload-dragger:hover) .upload-icon {
  color: var(--accent-sage);
}

.upload-text {
  font-size: 14px;
  color: var(--text-secondary);
}

.upload-text em {
  color: var(--accent-sage);
  font-style: normal;
  font-weight: 500;
}

.upload-hint {
  font-size: 12px;
  color: #a0aec0;
}

.submit-btn {
  align-self: flex-end;
  border-radius: 8px;
  background: var(--accent-sage);
  border-color: var(--accent-sage);
  padding: 10px 28px;
  font-weight: 500;
  transition: all 0.2s;
}

.submit-btn:hover {
  background: #4d7a5c;
  border-color: #4d7a5c;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(90, 138, 106, 0.3);
}

/* ── Table ── */
.doc-table {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
}

.doc-table :deep(.el-table__inner-wrapper) {
  border-radius: 8px;
}

.doc-title-cell {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.doc-icon {
  font-size: 16px;
  flex-shrink: 0;
}

.filetype-badge {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 12px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.chunk-count {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
}

.time-text {
  font-size: 13px;
  color: var(--text-secondary);
  font-variant-numeric: tabular-nums;
}

/* ── Rotating icon for processing status ── */
.rotating-icon {
  animation: spin 1.2s linear infinite;
  margin-right: 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pulse-tag {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* ── Empty state ── */
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 48px 20px;
}

.empty-illustration svg {
  width: 120px;
  height: 80px;
  margin-bottom: 16px;
}

.empty-text {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 6px;
}

.empty-hint {
  font-size: 13px;
  color: var(--text-secondary);
}
</style>
