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
  0: { label: '未处理', type: 'info' },
  1: { label: '处理中', type: 'warning' },
  2: { label: '已完成', type: 'success' },
  3: { label: '失败', type: 'danger' },
}

const fileTypeStyle = {
  docx: { color: '#5a8a6a', bg: '#e8f0eb' },
  xlsx: { color: '#c4956a', bg: '#f5ede4' },
  pdf:  { color: '#c0705a', bg: '#f5e8e4' },
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
  if (!time) return '—'
  const d = new Date(time)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function startPolling() {
  pollTimer = setInterval(() => {
    if (isProcessing.value) fetchList()
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
  <div class="page">
    <!-- Upload panel -->
    <div class="panel">
      <div class="panel-head">
        <el-icon :size="16"><Upload /></el-icon>
        上传景区资料
      </div>
      <div class="upload-body">
        <el-input
          v-model="uploadTitle"
          placeholder="文档标题（如：灵山胜境游览指南）"
          class="title-input"
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
        <div class="upload-actions">
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
    </div>

    <!-- Document list panel -->
    <div class="panel">
      <div class="panel-head">
        <el-icon :size="16"><FolderOpened /></el-icon>
        已上传文档
        <span class="count-badge" v-if="documents.length">{{ documents.length }}</span>
      </div>

      <el-table
        v-if="documents.length"
        :data="documents"
        class="data-table"
        stripe
        size="default"
      >
        <el-table-column prop="title" label="文档标题" min-width="180">
          <template #default="{ row }">
            <div class="doc-name">
              <el-icon :size="14" :style="{ color: (fileTypeStyle[row.fileType] || fileTypeStyle.docx).color }">
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
              class="type-chip"
              :style="{
                color: (fileTypeStyle[row.fileType] || fileTypeStyle.docx).color,
                background: (fileTypeStyle[row.fileType] || fileTypeStyle.docx).bg,
              }"
            >
              {{ (row.fileType || '').toUpperCase() }}
            </span>
          </template>
        </el-table-column>

        <el-table-column prop="chunkCount" label="切片数" width="90" align="center">
          <template #default="{ row }">
            <span class="mono-num">{{ row.chunkCount ?? '—' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="vectorStatus" label="向量化状态" width="120" align="center">
          <template #default="{ row }">
            <el-tag
              :type="statusConfig[row.vectorStatus]?.type || 'info'"
              size="small"
              effect="light"
              round
              :class="{ 'tag-pulse': row.vectorStatus === 1 }"
            >
              <el-icon v-if="row.vectorStatus === 1" class="spin-icon"><Loading /></el-icon>
              {{ statusConfig[row.vectorStatus]?.label || '未知' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="createdAt" label="上传时间" width="160" align="center">
          <template #default="{ row }">
            <span class="time-cell">{{ formatTime(row.createdAt) }}</span>
          </template>
        </el-table-column>

        <el-table-column label="操作" width="120" align="center" fixed="right">
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

      <div v-else class="empty">
        <el-empty description="暂无文档">
          <template #description>
            <span class="empty-desc">上传景区资料，让数字人拥有专业知识</span>
          </template>
        </el-empty>
      </div>
    </div>
  </div>
</template>

<style scoped>
.page {
  max-width: 960px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

/* ── Panel ── */
.panel {
  background: var(--bg-card);
  border-radius: 10px;
  border: 1px solid var(--border-light);
  padding: 20px;
}

.panel-head {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary);
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
}

.count-badge {
  font-size: 11px;
  font-weight: 500;
  color: var(--text-tertiary);
  background: var(--bg-page);
  padding: 1px 8px;
  border-radius: 10px;
  margin-left: 4px;
}

/* ── Upload ── */
.upload-body {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.title-input :deep(.el-input__wrapper) {
  border-radius: 8px;
  box-shadow: 0 0 0 1px var(--border-medium) inset;
  transition: box-shadow 0.2s;
}

.title-input :deep(.el-input__wrapper:focus-within) {
  box-shadow: 0 0 0 2px var(--accent-sage) inset;
}

.upload-area :deep(.el-upload-dragger) {
  border: 2px dashed var(--border-medium);
  border-radius: 10px;
  background: var(--bg-page);
  padding: 28px 20px;
  transition: all 0.2s ease;
}

.upload-area :deep(.el-upload-dragger:hover) {
  border-color: var(--accent-sage);
  background: var(--accent-sage-light);
}

.upload-inner {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 6px;
}

.upload-icon {
  font-size: 36px;
  color: var(--text-tertiary);
  transition: color 0.2s;
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
  color: var(--text-tertiary);
}

.upload-actions {
  display: flex;
  justify-content: flex-end;
}

.submit-btn {
  border-radius: 8px;
  background: var(--accent-sage);
  border-color: var(--accent-sage);
  padding: 10px 24px;
  font-weight: 500;
}

.submit-btn:hover {
  background: #4d7a5c;
  border-color: #4d7a5c;
}

/* ── Table ── */
.data-table {
  --el-table-border-color: var(--border-light);
  --el-table-header-bg-color: var(--bg-page);
}

.doc-name {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
  color: var(--text-primary);
}

.type-chip {
  display: inline-block;
  padding: 2px 10px;
  border-radius: 10px;
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.5px;
}

.mono-num {
  font-variant-numeric: tabular-nums;
  font-weight: 600;
  color: var(--text-primary);
}

.time-cell {
  font-size: 13px;
  color: var(--text-tertiary);
  font-variant-numeric: tabular-nums;
}

.spin-icon {
  animation: spin 1s linear infinite;
  margin-right: 4px;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.tag-pulse {
  animation: pulse 2s ease-in-out infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.7; }
}

/* ── Empty ── */
.empty {
  padding: 32px 0;
}

.empty-desc {
  color: var(--text-tertiary);
  font-size: 13px;
}
</style>
