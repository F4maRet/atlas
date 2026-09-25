<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">💡</span> Рационализаторские предложения</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить</button>
    </div>

    <div v-if="loadError" class="alert alert-error">
      ⚠️ {{ loadError }} <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <span>🔍</span>
        <input v-model="search" placeholder="Название, автор, каталог…" />
        <button v-if="search" class="search-bar__clear" @click="search = ''">✕</button>
      </div>
      <select v-model="filterType" class="select" aria-label="Тип">
        <option value="">Все типы</option>
        <option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filterCert" class="select" aria-label="Свидетельство">
        <option value="">Свидетельство: все</option>
        <option value="yes">✓ Есть</option>
        <option value="no">✗ Нет</option>
      </select>
    </div>

    <div class="layout-with-sidebar">
      <CatalogSidebar ref="sidebar" v-model="activeCatalog" scope="proposals" :items="proposals" all-label="Все предложения" @changed="load" />

      <div>
        <div v-if="selected.length" class="bulk-bar">
          <strong>Выбрано: {{ selected.length }}</strong>
          <select class="select" @change="bulkMove($event)">
            <option value="">Переместить в каталог…</option>
            <option value="__none__">— без каталога —</option>
            <option v-for="c in sidebar?.catalogs || []" :key="c.name" :value="c.name">{{ c.name }}</option>
          </select>
          <button class="btn btn-danger btn-sm" @click="bulkDelete">🗑 Удалить</button>
          <button class="btn btn-ghost btn-sm ml-auto" @click="selected = []">Снять выделение</button>
        </div>

        <div class="card card--flush">
          <div class="table-wrap">
            <table>
              <thead>
                <tr>
                  <th class="col-actions"><input type="checkbox" :checked="allSelected" aria-label="Выбрать все" @change="toggleAll" /></th>
                  <SortTh k="title" v-bind="sortProps">Название</SortTh>
                  <SortTh k="authors" v-bind="sortProps" class="hide-sm">Авторы</SortTh>
                  <SortTh k="type" v-bind="sortProps">Тип</SortTh>
                  <SortTh k="cert" v-bind="sortProps" title="Свидетельство">Свид.</SortTh>
                  <SortTh k="created" v-bind="sortProps" class="hide-sm">Добавлено</SortTh>
                  <th class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading && !proposals.length"><td colspan="7"><div v-for="i in 4" :key="i" class="skeleton" style="margin:10px 0"></div></td></tr>
                <tr v-else-if="!sorted.length">
                  <td colspan="7">
                    <div class="empty-state">
                      <div class="empty-state__icon">💡</div>
                      <div class="empty-state__text">{{ proposals.length ? 'Ничего не найдено' : 'Рац. предложений пока нет' }}</div>
                      <button v-if="!proposals.length" class="btn btn-primary btn-sm" @click="openCreate">+ Добавить</button>
                    </div>
                  </td>
                </tr>
                <tr v-for="p in sorted" :key="p.id" class="row-click" draggable="true" @dragstart="dragStart(p, $event)" @click="openDetail(p)">
                  <td @click.stop><input v-model="selected" type="checkbox" :value="p.id" /></td>
                  <td style="max-width:380px">
                    <div class="cell-title" :title="p.title">{{ p.title }}</div>
                    <div class="cell-sub">
                      <span v-if="p.catalog">📁 {{ p.catalog }}</span>
                      <span v-if="!p.has_file" class="text-warn"> · без файла</span>
                    </div>
                  </td>
                  <td class="hide-sm"><div class="tags"><span v-for="a in p.authors" :key="a.id" class="tag" :title="a.full_name">{{ authorLabel(a) }}</span></div></td>
                  <td><span v-if="p.proposal_type" class="badge badge-amber">{{ p.proposal_type }}</span></td>
                  <td class="num"><span v-if="p.certificate" class="text-ok" title="Свидетельство есть">🏆</span><span v-else class="text-dim">—</span></td>
                  <td class="hide-sm text-muted text-sm nowrap">{{ formatDate(p.created_at) }}</td>
                  <td @click.stop>
                    <div class="cell-actions">
                      <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(p)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(p)">🗑</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="results-count">Показано {{ sorted.length }} из {{ proposals.length }}</div>
      </div>
    </div>

    <!-- ── Карточка ── -->
    <Modal v-model="showDetail" size="xl" flush>
      <template #header>
        <div style="min-width:0;flex:1">
          <span v-if="detail?.proposal_type" class="badge badge-amber">{{ detail.proposal_type }}</span>
          <h2 class="modal-title mt-2">{{ detail?.title }}</h2>
        </div>
        <button class="btn btn-ghost btn-sm" @click="showDetail = false; openEdit(detail)">✏️ Редактировать</button>
      </template>
      <div v-if="detail" class="detail">
        <div class="detail__meta">
          <div class="detail-section">
            <div class="detail-label">Авторы</div>
            <div v-if="detail.authors.length" class="flex flex-wrap gap-2">
              <span v-for="a in detail.authors" :key="a.id" class="author-chip">{{ a.full_name }}</span>
            </div>
            <span v-else class="text-muted text-sm">—</span>
          </div>
          <div class="detail-section detail-grid">
            <div><div class="detail-label">Каталог</div><div class="detail-val">{{ detail.catalog || '—' }}</div></div>
            <div><div class="detail-label">Добавлено</div><div class="detail-val">{{ formatDate(detail.created_at) }}</div></div>
          </div>
          <div class="detail-section">
            <div class="detail-label">Файл предложения</div>
            <div v-if="detail.has_file" class="file-card" :class="{ active: previewTarget === 'file' }">
              <span class="file-card__icon">{{ fileIcon(detail.original_filename) }}</span>
              <div class="file-card__info">
                <div class="file-card__name">{{ detail.original_filename }}</div>
                <div class="file-card__sub">{{ formatBytes(detail.file_size_original) }} <span v-if="ratio(detail)" class="compress-badge">{{ ratio(detail) }}</span></div>
              </div>
              <div class="file-card__actions">
                <button class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="previewTarget = 'file'">👁</button>
                <a :href="proposalsApi.download(detail.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
              </div>
            </div>
            <div v-else class="text-muted text-sm">Не прикреплён</div>
          </div>
          <div class="detail-section">
            <div class="detail-label">Свидетельство</div>
            <div v-if="detail.certificate" class="file-card" :class="{ active: previewTarget === 'cert' }">
              <span class="file-card__icon">🏆</span>
              <div class="file-card__info">
                <div class="file-card__name">{{ detail.certificate.original_filename }}</div>
                <div class="file-card__sub">загружено {{ formatDate(detail.certificate.created_at) }}</div>
              </div>
              <div class="file-card__actions">
                <button class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="previewTarget = 'cert'">👁</button>
                <a :href="proposalsApi.downloadCertificate(detail.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
              </div>
            </div>
            <div class="flex gap-2 mt-2">
              <label class="btn btn-ghost btn-sm" :class="{ 'btn-active': uploadingCert }">
                {{ uploadingCert ? '⏳ Загрузка…' : detail.certificate ? '↑ Заменить' : '+ Загрузить свидетельство' }}
                <input type="file" hidden accept=".pdf,.doc,.docx,.odt,.jpg,.jpeg,.png" :disabled="uploadingCert" @change="uploadCertificate($event)" />
              </label>
              <button v-if="detail.certificate" class="btn btn-danger btn-sm" @click="deleteCertificate">🗑</button>
            </div>
          </div>
        </div>
        <div class="detail__preview">
          <div class="detail__preview-bar">
            <span class="grow">{{ previewTarget === 'cert' ? 'Свидетельство' : detail.original_filename || 'Предпросмотр' }}</span>
            <div v-if="detail.has_file && detail.certificate" class="btn-group">
              <button class="btn btn-ghost btn-sm" :class="{ 'btn-active': previewTarget === 'file' }" @click="previewTarget = 'file'">Предложение</button>
              <button class="btn btn-ghost btn-sm" :class="{ 'btn-active': previewTarget === 'cert' }" @click="previewTarget = 'cert'">Свидетельство</button>
            </div>
          </div>
          <DocumentViewer v-bind="previewProps" empty-text="Файл не прикреплён" />
        </div>
      </div>
    </Modal>

    <!-- ── Форма ── -->
    <Modal v-model="showForm" :title="editing ? 'Редактировать рац. предложение' : 'Новое рац. предложение'" persistent>
      <form id="proposal-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <textarea v-model="form.title" class="textarea" rows="2" style="min-height:60px" required maxlength="1000"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Тип</label>
            <input v-model="form.proposal_type" class="input" list="proposal-types" placeholder="ВАС, ОГВ(С)…" maxlength="100" />
            <datalist id="proposal-types"><option v-for="t in typeOptions" :key="t" :value="t" /></datalist>
          </div>
          <div class="form-group">
            <label class="form-label">Каталог хранения</label>
            <input v-model="form.catalog" class="input" list="proposal-catalogs" placeholder="Без каталога" maxlength="500" />
            <datalist id="proposal-catalogs"><option v-for="c in sidebar?.catalogs || []" :key="c.name" :value="c.name" /></datalist>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Авторы</label>
          <AuthorPicker v-model="form.author_ids" :all-authors="authors" @created="authors.push($event)" />
        </div>
        <div class="form-group">
          <label class="form-label">Файл</label>
          <FileUpload v-model="form.file" accept=".pdf,.doc,.docx,.odt,.rtf,.txt" hint="PDF, DOC, DOCX, ODT, RTF" icon="💡"
            :existing-name="editing?.original_filename"
            :existing-size-original="editing?.file_size_original"
            :existing-size-compressed="editing?.file_size_compressed"
            :download-url="editing?.has_file ? proposalsApi.download(editing.id) : null" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="proposal-form" :disabled="saving">
          {{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { proposalsApi, authorsApi, catalogsApi, buildFormData } from '@/utils/api'
import { formatDate, formatBytes, compressionRatio, authorLabel, fileIcon } from '@/utils/format'
import { useSort } from '@/composables/useSort'
import { useOpenFromQuery } from '@/composables/useOpenFromQuery'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'
import DocumentViewer from '@/components/common/DocumentViewer.vue'
import CatalogSidebar from '@/components/common/CatalogSidebar.vue'
import SortTh from '@/components/common/SortTh.vue'

const toast = useToast()
const DEFAULT_TYPES = ['ВАС', 'ОГВ(С)']

const proposals = ref([])
const authors = ref([])
const loading = ref(false)
const loadError = ref('')
const sidebar = ref(null)
const search = ref('')
const filterType = ref('')
const filterCert = ref('')
const activeCatalog = ref('')
const selected = ref([])

const typeOptions = computed(() => [...new Set([...DEFAULT_TYPES, ...proposals.value.map(p => p.proposal_type).filter(Boolean)])])
const ratio = p => compressionRatio(p.file_size_original, p.file_size_compressed)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return proposals.value.filter(p => {
    if (q && !(p.title.toLowerCase().includes(q) || (p.catalog || '').toLowerCase().includes(q) ||
      p.authors.some(a => a.full_name.toLowerCase().includes(q)))) return false
    if (filterType.value && p.proposal_type !== filterType.value) return false
    if (filterCert.value === 'yes' && !p.certificate) return false
    if (filterCert.value === 'no' && p.certificate) return false
    if (activeCatalog.value === '__none__') return !p.catalog
    if (activeCatalog.value) return p.catalog === activeCatalog.value
    return true
  })
})
const { sortKey, sortDir, toggle, sorted } = useSort(filtered, {
  title: p => p.title,
  authors: p => p.authors[0]?.full_name,
  type: p => p.proposal_type,
  cert: p => (p.certificate ? 1 : 0),
  created: p => p.created_at,
}, { key: 'created', dir: 'desc' })
const sortProps = computed(() => ({ sortKey: sortKey.value, sortDir: sortDir.value, toggle }))
const allSelected = computed(() => sorted.value.length > 0 && sorted.value.every(p => selected.value.includes(p.id)))
function toggleAll() { selected.value = allSelected.value ? [] : sorted.value.map(p => p.id) }
watch([search, filterType, filterCert, activeCatalog], () => { selected.value = [] })

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [pr, au] = await Promise.all([proposalsApi.list(), authorsApi.list()])
    proposals.value = pr.data
    authors.value = au.data
    if (detail.value) detail.value = proposals.value.find(p => p.id === detail.value.id) || null
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(load)

function dragStart(p, e) {
  const ids = selected.value.includes(p.id) ? selected.value : [p.id]
  e.dataTransfer.setData('application/x-atlas-ids', JSON.stringify(ids))
}
async function bulkMove(e) {
  const target = e.target.value
  e.target.value = ''
  if (!target) return
  try {
    await catalogsApi.move('proposals', selected.value, target === '__none__' ? null : target)
    toast.success('Перемещено')
    selected.value = []
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (err) { toast.error(err.message) }
}
async function bulkDelete() {
  if (!await confirmDialog({ title: 'Удалить предложения?', message: `Будут удалены записи (${selected.value.length}) вместе с файлами и свидетельствами.` })) return
  for (const id of selected.value) {
    try { await proposalsApi.delete(id) } catch (e) { toast.error(e.message) }
  }
  toast.success('Удалено')
  selected.value = []
  await load()
}

// ── Карточка ─────────────────────────────────────────────────────────────────
const showDetail = ref(false)
const detail = ref(null)
const previewTarget = ref('file')
const uploadingCert = ref(false)

function openDetail(p) {
  detail.value = p
  previewTarget.value = p.has_file || !p.certificate ? 'file' : 'cert'
  showDetail.value = true
}

const previewProps = computed(() => {
  const p = detail.value
  if (!p) return {}
  if (previewTarget.value === 'cert' && p.certificate) {
    return { src: proposalsApi.previewCertificate(p.id), filename: p.certificate.original_filename, downloadUrl: proposalsApi.downloadCertificate(p.id) }
  }
  if (!p.has_file) return {}
  return { src: proposalsApi.preview(p.id), filename: p.original_filename, downloadUrl: proposalsApi.download(p.id) }
})

async function uploadCertificate(event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  uploadingCert.value = true
  try {
    await proposalsApi.uploadCertificate(detail.value.id, buildFormData({ file }))
    toast.success('Свидетельство загружено')
    await load()
    previewTarget.value = 'cert'
  } catch (e) { toast.error(e.message) } finally { uploadingCert.value = false }
}
async function deleteCertificate() {
  if (!await confirmDialog({ title: 'Удалить свидетельство?', message: detail.value.certificate.original_filename })) return
  try {
    await proposalsApi.deleteCertificate(detail.value.id)
    toast.success('Свидетельство удалено')
    previewTarget.value = 'file'
    await load()
  } catch (e) { toast.error(e.message) }
}

// ── Форма ────────────────────────────────────────────────────────────────────
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})

function openCreate() {
  editing.value = null
  form.value = { title: '', proposal_type: '', catalog: activeCatalog.value && activeCatalog.value !== '__none__' ? activeCatalog.value : '', author_ids: [], file: null }
  showForm.value = true
}
function openEdit(p) {
  editing.value = p
  form.value = { title: p.title, proposal_type: p.proposal_type || '', catalog: p.catalog || '', author_ids: p.authors.map(x => x.id), file: null }
  showForm.value = true
}
async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const f = form.value
    const fd = buildFormData({ title: f.title.trim(), proposal_type: f.proposal_type.trim(), catalog: f.catalog.trim(), author_ids: f.author_ids, file: f.file })
    if (editing.value) { await proposalsApi.update(editing.value.id, fd); toast.success('Сохранено') }
    else { await proposalsApi.create(fd); toast.success('Добавлено') }
    showForm.value = false
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function remove(p) {
  if (!await confirmDialog({ title: 'Удалить рац. предложение?', message: `«${p.title}»\n\nФайл и свидетельство тоже будут удалены.` })) return
  try { await proposalsApi.delete(p.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}

// в конце setup: к этому моменту все ref-ы формы и карточки уже объявлены
useOpenFromQuery(proposals, openDetail, () => openCreate())
</script>
