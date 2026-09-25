import axios from 'axios'
import router from '@/router'

// По умолчанию — относительный путь: nginx проксирует /api на backend, cookie
// сессии остаётся same-origin. Раньше в сборку «зашивался» http://localhost:8000,
// и при открытии системы с другого компьютера в сети браузер стучался в свой localhost.
const API_ROOT = (import.meta.env.VITE_API_URL || '').replace(/\/$/, '')
export const API_BASE = `${API_ROOT}/api/v1`

const api = axios.create({
  baseURL: API_BASE,
  timeout: 120000,
  withCredentials: true,
})

api.interceptors.response.use(
  r => r,
  err => {
    const status = err.response?.status
    if (status === 401 && router.currentRoute.value.name !== 'Login') {
      router.push({ name: 'Login', query: { redirect: router.currentRoute.value.fullPath } })
    }
    let msg = err.response?.data?.detail
    if (Array.isArray(msg)) msg = msg.map(m => m.msg).join('; ')
    if (!msg) {
      if (err.code === 'ECONNABORTED') msg = 'Превышено время ожидания ответа сервера'
      else if (!err.response) msg = 'Нет связи с сервером'
      else msg = `Ошибка сервера (${status})`
    }
    const e = new Error(msg)
    e.status = status
    return Promise.reject(e)
  }
)

export default api

// ── Helpers ──────────────────────────────────────────────────────────────────

/**
 * FormData из объекта. undefined/null пропускаются (поле не меняется),
 * пустая строка отправляется — это «очистить значение» на сервере.
 */
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

const url = path => `${API_BASE}${path}`

/** Скачать ответ API как файл (для экспорта, где нужны параметры). */
export async function downloadFile(path, params = {}) {
  const r = await api.get(path, { params, responseType: 'blob' })
  const cd = r.headers['content-disposition'] || ''
  const m = cd.match(/filename\*=UTF-8''([^;]+)/i) || cd.match(/filename="?([^";]+)"?/i)
  const name = m ? decodeURIComponent(m[1]) : 'file'
  const href = URL.createObjectURL(r.data)
  const a = document.createElement('a')
  a.href = href
  a.download = name
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(href), 1000)
}

// ── API methods ───────────────────────────────────────────────────────────────

export const authApi = {
  login: password => api.post('/auth/login', { password }),
  logout: () => api.post('/auth/logout'),
  check: () => api.get('/auth/check'),
}

export const authorsApi = {
  list: () => api.get('/authors/'),
  stats: () => api.get('/authors/stats'),
  works: id => api.get(`/authors/${id}/works`),
  create: d => api.post('/authors/', d),
  update: (id, d) => api.put(`/authors/${id}`, d),
  merge: (id, intoId) => api.post(`/authors/${id}/merge`, { into_id: intoId }),
  delete: id => api.delete(`/authors/${id}`),
}

export const collectionsApi = {
  list: () => api.get('/collections/'),
  create: fd => api.post('/collections/', fd),
  update: (id, fd) => api.put(`/collections/${id}`, fd),
  delete: id => api.delete(`/collections/${id}`),
}

export const catalogsApi = {
  list: scope => api.get(`/catalogs/${scope}`),
  create: (scope, name) => api.post(`/catalogs/${scope}`, { name }),
  rename: (scope, oldName, newName) => api.put(`/catalogs/${scope}/rename`, { old_name: oldName, new_name: newName }),
  delete: (scope, name) => api.delete(`/catalogs/${scope}`, { params: { name } }),
  move: (scope, ids, catalog) => api.post(`/catalogs/${scope}/move`, { ids, catalog }),
}

export const articlesApi = {
  list: params => api.get('/articles/', { params }),
  get: id => api.get(`/articles/${id}`),
  create: fd => api.post('/articles/', fd),
  update: (id, fd) => api.put(`/articles/${id}`, fd),
  delete: id => api.delete(`/articles/${id}`),
  download: id => url(`/articles/${id}/download`),
  preview: id => url(`/articles/${id}/preview`),
  uploadConclusion: (articleId, fd) => api.post(`/documents/conclusion/${articleId}`, fd),
  generateConclusion: (articleId, templateId) =>
    api.post(`/documents/conclusion/${articleId}/generate`, null, { params: templateId ? { template_id: templateId } : {} }),
  getConclusion: id => api.get(`/documents/conclusion/${id}`),
  deleteConclusion: id => api.delete(`/documents/conclusion/${id}`),
  downloadConclusion: id => url(`/documents/conclusion/${id}/download`),
  previewConclusion: id => url(`/documents/conclusion/${id}/preview`),
}

export const proposalsApi = {
  list: () => api.get('/proposals/'),
  get: id => api.get(`/proposals/${id}`),
  create: fd => api.post('/proposals/', fd),
  update: (id, fd) => api.put(`/proposals/${id}`, fd),
  delete: id => api.delete(`/proposals/${id}`),
  download: id => url(`/proposals/${id}/download`),
  preview: id => url(`/proposals/${id}/preview`),
  uploadCertificate: (id, fd) => api.post(`/proposals/${id}/certificate`, fd),
  deleteCertificate: id => api.delete(`/proposals/${id}/certificate`),
  downloadCertificate: id => url(`/proposals/${id}/certificate/download`),
  previewCertificate: id => url(`/proposals/${id}/certificate/preview`),
}

export const softwareApi = {
  list: () => api.get('/software/'),
  get: id => api.get(`/software/${id}`),
  docTypes: () => api.get('/software/doc-types'),
  structure: id => api.get(`/software/${id}/structure`),
  create: fd => api.post('/software/', fd),
  update: (id, fd) => api.put(`/software/${id}`, fd),
  delete: id => api.delete(`/software/${id}`),
  download: id => url(`/software/${id}/download`),
  fileContent: (id, path) => api.get(`/software/${id}/file-content`, { params: { path } }),
  fileDownload: (id, path) => url(`/software/${id}/file-download?path=${encodeURIComponent(path)}`),
  uploadDoc: (id, fd) => api.post(`/software/${id}/documents`, fd),
  deleteDoc: (sid, did) => api.delete(`/software/${sid}/documents/${did}`),
  downloadDoc: (sid, did) => url(`/software/${sid}/documents/${did}/download`),
  previewDoc: (sid, did) => url(`/software/${sid}/documents/${did}/preview`),
  docsArchive: sid => url(`/software/${sid}/documents/archive`),
}

export const conferencesApi = {
  list: params => api.get('/conferences/', { params }),
  create: fd => api.post('/conferences/', fd),
  update: (id, fd) => api.put(`/conferences/${id}`, fd),
  delete: id => api.delete(`/conferences/${id}`),
  ics: id => url(`/conferences/${id}/ics`),
}

export const reportsApi = {
  plan: params => api.get('/reports/publication-plan', { params }),
  collectionsList: () => api.get('/reports/collections-list'),
  dashboard: () => api.get('/reports/dashboard'),
  search: q => api.get('/reports/search', { params: { q } }),
  exportPlan: params => downloadFile('/reports/publication-plan/export', params),
  exportRating: format => downloadFile('/reports/authors-rating/export', { format }),
  exportCollections: format => downloadFile('/reports/collections-list/export', { format }),
}

export const templatesApi = {
  list: () => api.get('/templates/'),
  types: () => api.get('/templates/types'),
  create: fd => api.post('/templates/', fd),
  update: (id, fd) => api.put(`/templates/${id}`, fd),
  delete: id => api.delete(`/templates/${id}`),
  download: id => url(`/templates/${id}/download`),
  preview: id => url(`/templates/${id}/preview`),
}

export async function healthCheck() {
  const r = await fetch(`${API_ROOT}/health`, { credentials: 'include' })
  return r.ok
}
