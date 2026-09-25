<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">💾</span> Программное обеспечение</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить ПО</button>
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
      <select v-model="filterDocs" class="select" aria-label="Комплект документов">
        <option value="">Документы: все</option>
        <option value="full">✓ Полный комплект</option>
        <option value="partial">⚠ Неполный комплект</option>
      </select>
    </div>

    <div class="layout-with-sidebar">
      <CatalogSidebar ref="sidebar" v-model="activeCatalog" scope="software" :items="software" all-label="Всё ПО" @changed="load" />

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
                  <SortTh k="docs" v-bind="sortProps">Документы</SortTh>
                  <SortTh k="created" v-bind="sortProps" class="hide-sm">Добавлено</SortTh>
                  <th class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading && !software.length"><td colspan="7"><div v-for="i in 4" :key="i" class="skeleton" style="margin:10px 0"></div></td></tr>
                <tr v-else-if="!sorted.length">
                  <td colspan="7">
                    <div class="empty-state">
                      <div class="empty-state__icon">💾</div>
                      <div class="empty-state__text">{{ software.length ? 'Ничего не найдено' : 'ПО пока нет' }}</div>
                      <button v-if="!software.length" class="btn btn-primary btn-sm" @click="openCreate">+ Добавить ПО</button>
                    </div>
                  </td>
                </tr>
                <tr v-for="s in sorted" :key="s.id" class="row-click" draggable="true" @dragstart="dragStart(s, $event)" @click="openDetail(s)">
                  <td @click.stop><input v-model="selected" type="checkbox" :value="s.id" /></td>
                  <td style="max-width:340px">
                    <div class="cell-title" :title="s.title">{{ s.title }}</div>
                    <div class="cell-sub">
                      <span v-if="s.catalog">📁 {{ s.catalog }}</span>
                      <span v-if="s.has_file"> · 🗜 {{ s.files_count ?? '?' }} файл.</span>
                      <span v-else class="text-warn"> · без архива</span>
                    </div>
                  </td>
                  <td class="hide-sm"><div class="tags"><span v-for="a in s.authors" :key="a.id" class="tag" :title="a.full_name">{{ authorLabel(a) }}</span></div></td>
                  <td><span v-if="s.software_type" class="badge badge-teal">{{ s.software_type }}</span></td>
                  <td>
                    <div class="doc-progress" :title="`${s.documents.length} из ${docTypes.length} документов`">
                      <div class="doc-progress__bar"><div :style="{ width: (s.documents.length / docTypes.length * 100) + '%' }" :class="{ full: s.documents.length >= docTypes.length }"></div></div>
                      <span class="text-sm text-muted">{{ s.documents.length }}/{{ docTypes.length }}</span>
                    </div>
                  </td>
                  <td class="hide-sm text-muted text-sm nowrap">{{ formatDate(s.created_at) }}</td>
                  <td @click.stop>
                    <div class="cell-actions">
                      <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(s)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(s)">🗑</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="results-count">Показано {{ sorted.length }} из {{ software.length }}</div>
      </div>
    </div>

    <!-- ── Карточка ПО ── -->
    <Modal v-model="showDetail" size="xl" flush>
      <template #header>
        <div style="min-width:0;flex:1">
          <span v-if="detail?.software_type" class="badge badge-teal">{{ detail.software_type }}</span>
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
            <div class="detail-label">Архив с исходниками</div>
            <div v-if="detail.has_file" class="file-card" :class="{ active: pane === 'archive' }">
              <span class="file-card__icon">🗜</span>
              <div class="file-card__info">
                <div class="file-card__name">{{ detail.original_filename }}</div>
                <div class="file-card__sub">{{ formatBytes(detail.file_size_original) }} · {{ detail.files_count ?? '?' }} файл.</div>
              </div>
              <div class="file-card__actions">
                <button class="btn btn-ghost btn-sm btn-icon" title="Структура архива" @click="openArchive">🗂</button>
                <a :href="softwareApi.download(detail.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
              </div>
            </div>
            <div v-else class="text-muted text-sm">Не загружен</div>
          </div>

          <div class="detail-section">
            <div class="detail-label flex-center">
              Комплект документов
              <span class="ml-auto badge" :class="detail.documents.length >= docTypes.length ? 'badge-green' : 'badge-amber'">{{ detail.documents.length }}/{{ docTypes.length }}</span>
            </div>
            <div class="doc-list">
              <div v-for="dt in docTypes" :key="dt.key" class="doc-row"
                :class="{ active: pane === 'doc' && docKey === dt.key, missing: !getDoc(dt.key) }"
                @click="getDoc(dt.key) ? showDoc(dt.key) : null">
                <span class="doc-row__status">{{ getDoc(dt.key) ? '✓' : '○' }}</span>
                <span class="doc-row__label" :title="getDoc(dt.key)?.original_filename || 'Не загружен'">{{ dt.label }}</span>
                <span class="doc-row__actions" @click.stop>
                  <label class="btn btn-ghost btn-sm btn-icon" :title="getDoc(dt.key) ? 'Заменить' : 'Загрузить'">
                    {{ uploadingKey === dt.key ? '⏳' : getDoc(dt.key) ? '↻' : '＋' }}
                    <input type="file" hidden accept=".pdf,.doc,.docx,.odt,.rtf,.txt,.jpg,.jpeg,.png" :disabled="!!uploadingKey" @change="uploadDoc(dt.key, $event)" />
                  </label>
                  <a v-if="getDoc(dt.key)" :href="softwareApi.downloadDoc(detail.id, getDoc(dt.key).id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
                  <button v-if="getDoc(dt.key)" class="btn btn-ghost btn-sm btn-icon text-danger" title="Удалить" @click="deleteDoc(dt)">✕</button>
                </span>
              </div>
            </div>
            <a v-if="detail.documents.length" :href="softwareApi.docsArchive(detail.id)" class="btn btn-ghost btn-sm w-full mt-2" download>
              📦 Скачать комплект одним архивом
            </a>
          </div>
        </div>

        <!-- Правая панель: документ или архив -->
        <div class="detail__preview">
          <template v-if="pane === 'archive'">
            <div class="detail__preview-bar">
              <span class="grow">🗂 {{ archivePath || 'Структура архива' }}</span>
              <a v-if="archivePath" :href="softwareApi.fileDownload(detail.id, archivePath)" class="btn btn-ghost btn-sm" download>↓ Файл</a>
            </div>
            <div class="archive">
              <div class="archive__tree">
                <div v-if="treeLoading" class="text-muted text-sm" style="padding:10px">Чтение архива…</div>
                <div v-else-if="treeError" class="text-danger text-sm" style="padding:10px">{{ treeError }}</div>
                <FileTree v-else :nodes="tree" :selected="archivePath" @select="loadFileContent" />
              </div>
              <div class="archive__content">
                <div v-if="!archivePath" class="text-muted text-sm" style="padding:16px">Выберите файл слева</div>
                <div v-else-if="fileLoading" class="text-muted text-sm" style="padding:16px">Загрузка…</div>
                <div v-else-if="fileInfo?.binary" class="text-muted text-sm" style="padding:16px">
                  Двоичный файл ({{ formatBytes(fileInfo.size) }}) — просмотр невозможен, его можно скачать.
                </div>
                <template v-else-if="fileInfo">
                  <div v-if="fileInfo.truncated" class="alert alert-warn" style="margin:8px">Показан первый 1 МБ из {{ formatBytes(fileInfo.size) }}</div>
                  <pre class="code">{{ fileInfo.content }}</pre>
                </template>
              </div>
            </div>
          </template>
          <template v-else>
            <div class="detail__preview-bar">
              <span class="grow">{{ currentDoc ? docLabel(docKey) + ' · ' + currentDoc.original_filename : 'Предпросмотр документов' }}</span>
            </div>
            <DocumentViewer v-bind="docPreviewProps" empty-text="Выберите загруженный документ слева" />
          </template>
        </div>
      </div>
    </Modal>

    <!-- ── Форма ── -->
    <Modal v-model="showForm" :title="editing ? 'Редактировать ПО' : 'Добавить ПО'" persistent>
      <form id="sw-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <input v-model="form.title" class="input" placeholder="Название программы" required maxlength="1000" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Тип ПО</label>
            <input v-model="form.software_type" class="input" list="sw-types" placeholder="Прикладное, веб-приложение…" maxlength="100" />
            <datalist id="sw-types"><option v-for="t in typeOptions" :key="t" :value="t" /></datalist>
          </div>
          <div class="form-group">
            <label class="form-label">Каталог хранения</label>
            <input v-model="form.catalog" class="input" list="sw-catalogs" placeholder="Без каталога" maxlength="500" />
            <datalist id="sw-catalogs"><option v-for="c in sidebar?.catalogs || []" :key="c.name" :value="c.name" /></datalist>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Авторы</label>
          <AuthorPicker v-model="form.author_ids" :all-authors="authors" @created="authors.push($event)" />
        </div>
        <div class="form-group">
          <label class="form-label">ZIP-архив с исходниками</label>
          <FileUpload v-model="form.file" accept=".zip" hint="ZIP" icon="🗜"
            :existing-name="editing?.original_filename"
            :existing-size-original="editing?.file_size_original"
            :download-url="editing?.has_file ? softwareApi.download(editing.id) : null" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="sw-form" :disabled="saving">
          {{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { softwareApi, authorsApi, catalogsApi, buildFormData } from '@/utils/api'
import { formatDate, formatBytes, authorLabel } from '@/utils/format'
import { useSort } from '@/composables/useSort'
import { useOpenFromQuery } from '@/composables/useOpenFromQuery'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'
import DocumentViewer from '@/components/common/DocumentViewer.vue'
import CatalogSidebar from '@/components/common/CatalogSidebar.vue'
import FileTree from '@/components/common/FileTree.vue'
import SortTh from '@/components/common/SortTh.vue'

const toast = useToast()
const DEFAULT_TYPES = ['Прикладное', 'Системное', 'Веб-приложение', 'Мобильное', 'Библиотека', 'Прочее']

const software = ref([])
const authors = ref([])
const docTypes = ref([
  { key: 'annotation', label: 'Аннотация программы' },
  { key: 'registration', label: 'Заявление на регистрацию' },
  { key: 'description', label: 'Описание программы' },
  { key: 'manual', label: 'Руководство пользователя' },
  { key: 'act', label: 'Акт приёма и ввода в эксплуатацию' },
  { key: 'abstract', label: 'Реферат по исходникам' },
  { key: 'listing', label: 'Листинг по исходникам' },
  { key: 'certificate', label: 'Свидетельство о регистрации' },
])
const loading = ref(false)
const loadError = ref('')
const sidebar = ref(null)
const search = ref('')
const filterType = ref('')
const filterDocs = ref('')
const activeCatalog = ref('')
const selected = ref([])

const typeOptions = computed(() => [...new Set([...DEFAULT_TYPES, ...software.value.map(s => s.software_type).filter(Boolean)])])
const docLabel = key => docTypes.value.find(d => d.key === key)?.label || key

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const total = docTypes.value.length
  return software.value.filter(s => {
    if (q && !(s.title.toLowerCase().includes(q) || (s.catalog || '').toLowerCase().includes(q) ||
      s.authors.some(a => a.full_name.toLowerCase().includes(q)))) return false
    if (filterType.value && s.software_type !== filterType.value) return false
    if (filterDocs.value === 'full' && s.documents.length < total) return false
    if (filterDocs.value === 'partial' && s.documents.length >= total) return false
    if (activeCatalog.value === '__none__') return !s.catalog
    if (activeCatalog.value) return s.catalog === activeCatalog.value
    return true
  })
})
const { sortKey, sortDir, toggle, sorted } = useSort(filtered, {
  title: s => s.title,
  authors: s => s.authors[0]?.full_name,
  type: s => s.software_type,
  docs: s => s.documents.length,
  created: s => s.created_at,
}, { key: 'created', dir: 'desc' })
const sortProps = computed(() => ({ sortKey: sortKey.value, sortDir: sortDir.value, toggle }))
const allSelected = computed(() => sorted.value.length > 0 && sorted.value.every(s => selected.value.includes(s.id)))
function toggleAll() { selected.value = allSelected.value ? [] : sorted.value.map(s => s.id) }
watch([search, filterType, filterDocs, activeCatalog], () => { selected.value = [] })

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [sw, au] = await Promise.all([softwareApi.list(), authorsApi.list()])
    software.value = sw.data
    authors.value = au.data
    if (detail.value) detail.value = software.value.find(s => s.id === detail.value.id) || null
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(async () => {
  load()
  try { docTypes.value = (await softwareApi.docTypes()).data } catch { /* используем встроенный список */ }
})

function dragStart(s, e) {
  const ids = selected.value.includes(s.id) ? selected.value : [s.id]
  e.dataTransfer.setData('application/x-atlas-ids', JSON.stringify(ids))
}
async function bulkMove(e) {
  const target = e.target.value
  e.target.value = ''
  if (!target) return
  try {
    await catalogsApi.move('software', selected.value, target === '__none__' ? null : target)
    toast.success('Перемещено')
    selected.value = []
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (err) { toast.error(err.message) }
}
async function bulkDelete() {
  if (!await confirmDialog({ title: 'Удалить ПО?', message: `Будут удалены записи (${selected.value.length}) вместе с архивами и документами.` })) return
  for (const id of selected.value) {
    try { await softwareApi.delete(id) } catch (e) { toast.error(e.message) }
  }
  toast.success('Удалено')
  selected.value = []
  await load()
}

// ── Карточка ─────────────────────────────────────────────────────────────────
const showDetail = ref(false)
const detail = ref(null)
const pane = ref('doc') // doc | archive
const docKey = ref('')
const uploadingKey = ref('')

const getDoc = key => detail.value?.documents.find(d => d.doc_type === key)
const currentDoc = computed(() => (docKey.value ? getDoc(docKey.value) : null))
const docPreviewProps = computed(() => {
  const d = currentDoc.value
  if (!d) return {}
  return { src: softwareApi.previewDoc(detail.value.id, d.id), filename: d.original_filename, downloadUrl: softwareApi.downloadDoc(detail.value.id, d.id) }
})

function openDetail(s) {
  detail.value = s
  pane.value = 'doc'
  docKey.value = docTypes.value.find(dt => s.documents.some(d => d.doc_type === dt.key))?.key || ''
  tree.value = []
  archivePath.value = ''
  fileInfo.value = null
  showDetail.value = true
}

function showDoc(key) { pane.value = 'doc'; docKey.value = key }

async function uploadDoc(key, event) {
  const file = event.target.files[0]
  event.target.value = ''
  if (!file) return
  uploadingKey.value = key
  try {
    await softwareApi.uploadDoc(detail.value.id, buildFormData({ doc_type: key, file }))
    toast.success(`«${docLabel(key)}» загружен`)
    await load()
    showDoc(key)
  } catch (e) { toast.error(e.message) } finally { uploadingKey.value = '' }
}
async function deleteDoc(dt) {
  const d = getDoc(dt.key)
  if (!await confirmDialog({ title: 'Удалить документ?', message: `${dt.label}\n${d.original_filename}` })) return
  try {
    await softwareApi.deleteDoc(detail.value.id, d.id)
    toast.success('Документ удалён')
    if (docKey.value === dt.key) docKey.value = ''
    await load()
  } catch (e) { toast.error(e.message) }
}

// ── Архив ────────────────────────────────────────────────────────────────────
const tree = ref([])
const treeLoading = ref(false)
const treeError = ref('')
const archivePath = ref('')
const fileInfo = ref(null)
const fileLoading = ref(false)

async function openArchive() {
  pane.value = 'archive'
  if (tree.value.length) return
  treeLoading.value = true
  treeError.value = ''
  try { tree.value = (await softwareApi.structure(detail.value.id)).data.tree }
  catch (e) { treeError.value = e.message }
  finally { treeLoading.value = false }
}
async function loadFileContent(node) {
  archivePath.value = node.path
  fileLoading.value = true
  fileInfo.value = null
  try { fileInfo.value = (await softwareApi.fileContent(detail.value.id, node.path)).data }
  catch (e) { fileInfo.value = { content: `Ошибка: ${e.message}` } }
  finally { fileLoading.value = false }
}

// ── Форма ────────────────────────────────────────────────────────────────────
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})

function openCreate() {
  editing.value = null
  form.value = { title: '', software_type: '', catalog: activeCatalog.value && activeCatalog.value !== '__none__' ? activeCatalog.value : '', author_ids: [], file: null }
  showForm.value = true
}
function openEdit(s) {
  editing.value = s
  form.value = { title: s.title, software_type: s.software_type || '', catalog: s.catalog || '', author_ids: s.authors.map(x => x.id), file: null }
  showForm.value = true
}
async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const f = form.value
    const fd = buildFormData({ title: f.title.trim(), software_type: f.software_type.trim(), catalog: f.catalog.trim(), author_ids: f.author_ids, file: f.file })
    if (editing.value) { await softwareApi.update(editing.value.id, fd); toast.success('Сохранено') }
    else { await softwareApi.create(fd); toast.success('ПО добавлено') }
    showForm.value = false
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function remove(s) {
  if (!await confirmDialog({ title: 'Удалить ПО?', message: `«${s.title}»\n\nАрхив и все документы комплекта тоже будут удалены.` })) return
  try { await softwareApi.delete(s.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}

// в конце setup: к этому моменту все ref-ы формы и карточки уже объявлены
useOpenFromQuery(software, openDetail, () => openCreate())
</script>

<style scoped>
.doc-progress { display: flex; align-items: center; gap: 8px; min-width: 110px; }
.doc-progress__bar { flex: 1; height: 6px; background: var(--c-bg3); border-radius: 3px; overflow: hidden; }
.doc-progress__bar > div { height: 100%; background: var(--c-amber); border-radius: 3px; }
.doc-progress__bar > div.full { background: var(--c-green); }

.doc-list { display: flex; flex-direction: column; gap: 2px; }
.doc-row { display: flex; align-items: center; gap: 8px; padding: 5px 6px; border-radius: 7px; border: 1px solid transparent; font-size: 12px; cursor: pointer; }
.doc-row:hover { background: var(--c-bg3); }
.doc-row.active { background: rgba(79,124,255,0.1); border-color: rgba(79,124,255,0.3); }
.doc-row.missing { cursor: default; }
.doc-row.missing .doc-row__label { color: var(--c-text3); }
.doc-row__status { width: 14px; text-align: center; color: var(--c-green); font-weight: 700; }
.doc-row.missing .doc-row__status { color: var(--c-text3); }
.doc-row__label { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.doc-row__actions { display: flex; gap: 2px; }
.doc-row__actions .btn { padding: 2px 6px; min-width: 24px; }

.archive { display: grid; grid-template-columns: 260px minmax(0, 1fr); flex: 1; min-height: 0; }
.archive__tree { overflow: auto; border-right: 1px solid var(--c-border); padding: 6px; background: var(--c-bg2); }
.archive__content { overflow: auto; background: var(--c-bg); }
.code { margin: 0; padding: 12px 16px; font-family: var(--font-mono); font-size: 12px; white-space: pre; color: var(--c-text); tab-size: 4; }
@media (max-width: 700px) { .archive { grid-template-columns: 1fr; grid-template-rows: 40% 60%; } }
</style>
