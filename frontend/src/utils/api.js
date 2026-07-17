import axios from 'axios'
import router from '@/router'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL
    ? `${import.meta.env.VITE_API_URL}/api/v1`
    : '/api/v1',
  timeout: 60000,
  withCredentials: true, // отправлять cookie сессии на другой порт/домен
})

api.interceptors.response.use(
  r => r,
  err => {
    if (err.response?.status === 401 && router.currentRoute.value.name !== 'Login') {
      router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    const msg = err.response?.data?.detail || err.message || 'Ошибка запроса'
    return Promise.reject(new Error(Array.isArray(msg) ? msg.map(m => m.msg).join('; ') : msg))
  }
)

export default api

export const authApi = {
  login: password => api.post('/auth/login', { password }),
  logout: () => api.post('/auth/logout'),
  check: () => api.get('/auth/check'),
}

// ── Helpers ──────────────────────────────────────────────────────────────────

export function buildFormData(obj) {
  const fd = new FormData()
  for (const [k, v] of Object.entries(obj)) {
    if (v === undefined || v === null) continue
    if (v instanceof File) fd.append(k, v)
    else if (Array.isArray(v)) fd.append(k, JSON.stringify(v))
    else fd.append(k, String(v))
  }
  return fd
}

export function formatBytes(bytes) {
  if (!bytes) return '0 Б'
  const units = ['Б', 'КБ', 'МБ', 'ГБ']
  let i = 0
  while (bytes >= 1024 && i < units.length - 1) { bytes /= 1024; i++ }
  return `${bytes.toFixed(1)} ${units[i]}`
}

export function compressionRatio(original, compressed) {
  if (!original || !compressed) return null
  const saved = ((1 - compressed / original) * 100).toFixed(0)
  return saved > 0 ? `-${saved}%` : null
}

// ── API methods ───────────────────────────────────────────────────────────────

export const authorsApi = {
  list: () => api.get('/authors/'),
  stats: () => api.get('/authors/stats'),
  create: d => api.post('/authors/', d),
  update: (id, d) => api.put(`/authors/${id}`, d),
  delete: id => api.delete(`/authors/${id}`),
}

export const collectionsApi = {
  list: () => api.get('/collections/'),
  create: fd => api.post('/collections/', fd),
  update: (id, fd) => api.put(`/collections/${id}`, fd),
  delete: id => api.delete(`/collections/${id}`),
}

export const articlesApi = {
  list: params => api.get('/articles/', { params }),
  get: id => api.get(`/articles/${id}`),
  create: fd => api.post('/articles/', fd),
  update: (id, fd) => api.put(`/articles/${id}`, fd),
  delete: id => api.delete(`/articles/${id}`),
  download: id => `${api.defaults.baseURL}/articles/${id}/download`,
  uploadConclusion: (articleId, fd) => api.post(`/documents/conclusion/${articleId}`, fd),
  generateConclusion: (articleId, templateId) => api.post(`/documents/conclusion/${articleId}/generate${templateId ? '?template_id=' + templateId : ''}`),
  getConclusion: id => api.get(`/documents/conclusion/${id}`),
  downloadConclusion: id => `${api.defaults.baseURL}/documents/conclusion/${id}/download`,
  downloadGeneratedConclusion: id => `${api.defaults.baseURL}/documents/conclusion/${id}/download-generated`,
}

export const proposalsApi = {
  list: () => api.get('/proposals/'),
  create: fd => api.post('/proposals/', fd),
  update: (id, fd) => api.put(`/proposals/${id}`, fd),
  delete: id => api.delete(`/proposals/${id}`),
  download: id => `${api.defaults.baseURL}/proposals/${id}/download`,
  preview: id => `${api.defaults.baseURL}/proposals/${id}/preview`,
  // Certificate
  uploadCertificate: (id, fd) => api.post(`/proposals/${id}/certificate`, fd),
  deleteCertificate: id => api.delete(`/proposals/${id}/certificate`),
  downloadCertificate: id => `${api.defaults.baseURL}/proposals/${id}/certificate/download`,
  previewCertificate: id => `${api.defaults.baseURL}/proposals/${id}/certificate/preview`,
}

export const softwareApi = {
  list: () => api.get('/software/'),
  get: id => api.get(`/software/${id}`),
  create: fd => api.post('/software/', fd),
  update: (id, fd) => api.put(`/software/${id}`, fd),
  delete: id => api.delete(`/software/${id}`),
  download: id => `${api.defaults.baseURL}/software/${id}/download`,
  fileContent: (id, path) => api.get(`/software/${id}/file-content`, { params: { path } }),
  uploadDoc: (id, fd) => api.post(`/software/${id}/documents`, fd),
  deleteDoc: (sid, did) => api.delete(`/software/${sid}/documents/${did}`),
  downloadDoc: (sid, did) => `${api.defaults.baseURL}/software/${sid}/documents/${did}/download`,
  previewDoc: (sid, did) => `${api.defaults.baseURL}/software/${sid}/documents/${did}/preview`,
}

export const conferencesApi = {
  list: params => api.get('/conferences/', { params }),
  create: fd => api.post('/conferences/', fd),
  update: (id, fd) => api.put(`/conferences/${id}`, fd),
  delete: id => api.delete(`/conferences/${id}`),
}

export const reportsApi = {
  plan: () => api.get('/reports/publication-plan'),
  collectionsList: () => api.get('/reports/collections-list'),
  dashboard: () => api.get('/reports/dashboard'),
}

export const templatesApi = {
  list: () => api.get('/templates/'),
  create: fd => api.post('/templates/', fd),
  update: (id, fd) => api.put(`/templates/${id}`, fd),
  delete: id => api.delete(`/templates/${id}`),
  download: id => `${api.defaults.baseURL}/templates/${id}/download`,
  preview: id => `${api.defaults.baseURL}/templates/${id}/preview`,
}
