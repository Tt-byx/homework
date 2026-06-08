import request from './request'

export function uploadKnowledge(file, title) {
  const formData = new FormData()
  formData.append('file', file)
  formData.append('title', title)
  return request.post('/api/knowledge/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  })
}

export function getKnowledgeList() {
  return request.get('/api/knowledge/list')
}

export function deleteKnowledge(id) {
  return request.delete(`/api/knowledge/${id}`)
}

export function reprocessKnowledge(id) {
  return request.post(`/api/knowledge/reprocess/${id}`)
}
