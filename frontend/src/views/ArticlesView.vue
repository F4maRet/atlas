<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">📄</span> Научные статьи</h1>
      <div class="page-header__actions">
        <button class="btn btn-primary" @click="openCreate">+ Добавить статью</button>
      </div>
    </div>

    <div v-if="loadError" class="alert alert-error">
      ⚠️ {{ loadError }}
      <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button>
    </div>

    <div class="toolbar">
      <div class="search-bar">
        <span>🔍</span>
        <input v-model="search" placeholder="Название, автор, каталог…" />
        <button v-if="search" class="search-bar__clear" title="Очистить" @click="search = ''">✕</button>
      </div>
      <select v-model="filterCollection" class="select" aria-label="Сборник">
        <option value="">Все сборники</option>
        <option value="__none__">— без сборника —</option>
        <option v-for="c in collections" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
      </select>
      <select v-model="filterType" class="select" aria-label="Тип">
        <option value="">Все типы</option>
        <option v-for="t in typeOptions" :key="t" :value="t">{{ t }}</option>
      </select>
      <select v-model="filterConclusion" class="select" aria-label="Заключение">
        <option value="">Заключение: все</option>
        <option value="yes">✓ Есть заключение</option>
        <option value="no">✗ Нет заключения</option>
      </select>
    </div>

    <div class="layout-with-sidebar">
      <CatalogSidebar ref="sidebar" v-model="activeCatalog" scope="articles" :items="articles" all-label="Все статьи" @changed="load" />

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
                  <SortTh k="collection" v-bind="sortProps" class="hide-sm">Сборник</SortTh>
                  <SortTh k="conclusion" v-bind="sortProps" title="Заключение">Закл.</SortTh>
                  <SortTh k="created" v-bind="sortProps" class="hide-sm">Добавлена</SortTh>
                  <th class="col-actions"></th>
                </tr>
              </thead>
              <tbody>
                <tr v-if="loading && !articles.length"><td colspan="8"><div class="skeleton" v-for="i in 4" :key="i" style="margin:10px 0"></div></td></tr>
                <tr v-else-if="!sorted.length">
                  <td colspan="8">
                    <div class="empty-state">
                      <div class="empty-state__icon">📄</div>
                      <div class="empty-state__text">{{ articles.length ? 'Ничего не найдено' : 'Статей пока нет' }}</div>
                      <button v-if="!articles.length" class="btn btn-primary btn-sm" @click="openCreate">+ Добавить первую статью</button>
                      <button v-else class="btn btn-ghost btn-sm" @click="resetFilters">Сбросить фильтры</button>
                    </div>
                  </td>
                </tr>
                <tr v-for="a in sorted" :key="a.id" class="row-click" draggable="true"
                  @dragstart="dragStart(a, $event)" @click="openDetail(a)">
                  <td @click.stop><input v-model="selected" type="checkbox" :value="a.id" :aria-label="`Выбрать ${a.title}`" /></td>
                  <td style="max-width:360px">
                    <div class="cell-title" :title="a.title">{{ a.title }}</div>
                    <div class="cell-sub">
                      <span v-if="a.catalog">📁 {{ a.catalog }}</span>
                      <span v-if="!a.has_file" class="text-warn"> · без файла</span>
                    </div>
                  </td>
                  <td class="hide-sm">
                    <div class="tags">
                      <span v-for="au in a.authors" :key="au.id" class="tag" :title="au.full_name">
                        {{ authorLabel(au) }}<span v-if="au.id === a.lead_author_id" class="text-warn">★</span>
                      </span>
                    </div>
                  </td>
                  <td><span v-if="a.article_type" class="badge badge-blue">{{ a.article_type }}</span></td>
                  <td class="hide-sm"><span v-if="a.collection" class="truncate" style="max-width:160px;display:block" :title="a.collection.name">{{ a.collection.name }}</span></td>
                  <td class="num">
                    <span v-if="a.has_conclusion" class="text-ok" title="Заключение есть">✓</span>
                    <span v-else class="text-dim" title="Заключения нет">—</span>
                  </td>
                  <td class="hide-sm text-muted text-sm nowrap">{{ formatDate(a.created_at) }}</td>
                  <td @click.stop>
                    <div class="cell-actions">
                      <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(a)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(a)">🗑</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
        <div class="results-count">Показано {{ sorted.length }} из {{ articles.length }}</div>
      </div>
    </div>

    <!-- ── Карточка статьи ── -->
    <Modal v-model="showDetail" size="xl" flush>
      <template #header>
        <div style="min-width:0;flex:1">
          <span v-if="detail?.article_type" class="badge badge-blue">{{ detail.article_type }}</span>
          <h2 class="modal-title mt-2">{{ detail?.title }}</h2>
        </div>
        <button class="btn btn-ghost btn-sm" @click="showDetail = false; openEdit(detail)">✏️ Редактировать</button>
      </template>
      <div v-if="detail" class="detail">
        <div class="detail__meta">
          <div class="detail-section">
            <div class="detail-label">Авторы</div>
            <div v-if="detail.authors.length" class="flex flex-wrap gap-2">
              <span v-for="au in detail.authors" :key="au.id" class="author-chip"
                :class="{ 'author-chip--lead': au.id === detail.lead_author_id }"
                :title="au.id === detail.lead_author_id ? 'Главный автор' : ''">
                {{ au.full_name }}<span v-if="au.id === detail.lead_author_id" class="text-warn">★</span>
              </span>
            </div>
            <span v-else class="text-muted text-sm">—</span>
          </div>
          <div class="detail-section detail-grid">
            <div><div class="detail-label">Сборник</div><div class="detail-val">{{ detail.collection?.name || '—' }}</div></div>
            <div><div class="detail-label">Добавлена</div><div class="detail-val">{{ formatDate(detail.created_at) }}</div></div>
            <div v-if="detail.catalog"><div class="detail-label">Каталог</div><div class="detail-val">📁 {{ detail.catalog }}</div></div>
          </div>

          <div class="detail-section">
            <div class="detail-label">Файл статьи</div>
            <div v-if="detail.has_file" class="file-card" :class="{ active: previewTarget === 'article' }">
              <span class="file-card__icon">{{ fileIcon(detail.original_filename) }}</span>
              <div class="file-card__info">
                <div class="file-card__name">{{ detail.original_filename }}</div>
                <div class="file-card__sub">
                  {{ formatBytes(detail.file_size_original) }}
                  <span v-if="ratio(detail)" class="compress-badge">{{ ratio(detail) }}</span>
                </div>
              </div>
              <div class="file-card__actions">
                <button class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="previewTarget = 'article'">👁</button>
                <a :href="articlesApi.download(detail.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
              </div>
            </div>
            <div v-else class="text-muted text-sm">
              Не прикреплён · <a href="#" @click.prevent="showDetail = false; openEdit(detail)">загрузить</a>
            </div>
          </div>

          <div class="detail-section">
            <div class="detail-label">Заключение об открытом опубликовании</div>
            <template v-if="detail.has_conclusion">
              <div v-if="detail.conclusion_has_file" class="file-card" :class="{ active: previewTarget === 'conclusion' }">
                <span class="file-card__icon">✅</span>
                <div class="file-card__info">
                  <div class="file-card__name">{{ conclusion?.original_filename || 'Заключение' }}</div>
                  <div class="file-card__sub">{{ detail.conclusion_generated ? 'Сформировано по шаблону' : 'Загружено вручную' }}</div>
                </div>
                <div class="file-card__actions">
                  <button class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="previewTarget = 'conclusion'">👁</button>
                  <a :href="articlesApi.downloadConclusion(detail.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
                </div>
              </div>
              <div v-if="conclusion?.notes && !detail.conclusion_generated" class="text-sm text-muted mt-2">📝 {{ conclusion.notes }}</div>
              <div class="flex gap-2 mt-2">
                <button class="btn btn-ghost btn-sm" @click="openConclusion(detail)">↺ Заменить</button>
                <button class="btn btn-danger btn-sm" @click="removeConclusion(detail)">🗑 Удалить</button>
              </div>
            </template>
            <div v-else>
              <div class="text-muted text-sm" style="margin-bottom:8px">Не сформировано</div>
              <button class="btn btn-primary btn-sm" @click="openConclusion(detail)">✨ Сформировать</button>
            </div>
          </div>
        </div>

        <div class="detail__preview">
          <div class="detail__preview-bar">
            <span class="grow">{{ previewTarget === 'conclusion' ? 'Заключение' : detail.original_filename || 'Предпросмотр' }}</span>
            <div v-if="detail.has_file && detail.conclusion_has_file" class="btn-group">
              <button class="btn btn-ghost btn-sm" :class="{ 'btn-active': previewTarget === 'article' }" @click="previewTarget = 'article'">Статья</button>
              <button class="btn btn-ghost btn-sm" :class="{ 'btn-active': previewTarget === 'conclusion' }" @click="previewTarget = 'conclusion'">Заключение</button>
            </div>
          </div>
          <DocumentViewer v-bind="previewProps" empty-text="Файл статьи не прикреплён" />
        </div>
      </div>
    </Modal>

    <!-- ── Создание / редактирование ── -->
    <Modal v-model="showForm" :title="editing ? 'Редактировать статью' : 'Новая статья'" persistent>
      <form id="article-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <textarea v-model="form.title" class="textarea" rows="2" style="min-height:60px" placeholder="Полное название статьи" required maxlength="1000"></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Тип статьи</label>
            <input v-model="form.article_type" class="input" list="article-types" placeholder="ВАК, РИНЦ…" maxlength="100" />
            <datalist id="article-types"><option v-for="t in typeOptions" :key="t" :value="t" /></datalist>
          </div>
          <div class="form-group">
            <label class="form-label">Сборник</label>
            <select v-model="form.collection_id" class="select">
              <option value="">— без сборника —</option>
              <option v-for="c in collections" :key="c.id" :value="String(c.id)">{{ c.name }}</option>
            </select>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Каталог хранения</label>
          <input v-model="form.catalog" class="input" list="article-catalogs" placeholder="Без каталога" maxlength="500" />
          <datalist id="article-catalogs"><option v-for="c in sidebar?.catalogs || []" :key="c.name" :value="c.name" /></datalist>
        </div>
        <div class="form-group">
          <label class="form-label">Авторы</label>
          <AuthorPicker v-model="form.author_ids" :all-authors="authors" @created="authors.push($event)" />
          <div class="form-hint">Порядок авторов сохраняется (кнопка ↑ поднимает автора выше)</div>
        </div>
        <div v-if="form.author_ids.length > 1" class="form-group">
          <label class="form-label">Главный автор</label>
          <select v-model="form.lead_author_id" class="select">
            <option value="">— первый из списка —</option>
            <option v-for="id in form.author_ids" :key="id" :value="String(id)">{{ authorsById.get(id)?.full_name || id }}</option>
          </select>
        </div>
        <div class="form-group">
          <label class="form-label">Файл статьи</label>
          <FileUpload v-model="form.file" accept=".pdf,.doc,.docx,.odt,.rtf,.txt" hint="PDF, DOC, DOCX, ODT, RTF" icon="📄"
            :existing-name="editing?.original_filename"
            :existing-size-original="editing?.file_size_original"
            :existing-size-compressed="editing?.file_size_compressed"
            :download-url="editing?.has_file ? articlesApi.download(editing.id) : null" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="article-form" :disabled="saving">
          {{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}
        </button>
      </template>
    </Modal>

    <!-- ── Заключение ── -->
    <Modal v-model="showConclusion" title="Заключение об открытом опубликовании">
      <div class="text-muted text-sm" style="margin-bottom:16px">
        Статья: <strong style="color:var(--c-text)">{{ conclusionArticle?.title }}</strong>
      </div>
      <div class="tab-bar">
        <button class="tab-btn" :class="{ active: conclusionMode === 'auto' }" @click="conclusionMode = 'auto'">✨ Сформировать по шаблону</button>
        <button class="tab-btn" :class="{ active: conclusionMode === 'manual' }" @click="conclusionMode = 'manual'">📎 Загрузить своё</button>
      </div>

      <div v-if="conclusionMode === 'auto'" class="auto-box">
        <div class="auto-row"><span class="auto-label">Название</span><span>{{ conclusionArticle?.title }}</span></div>
        <div class="auto-row">
          <span class="auto-label">Автор{{ conclusionArticle?.authors?.length === 1 ? 'а' : 'ов' }}</span>
          <span v-if="conclusionArticle?.authors?.length">{{ conclusionArticle.authors.map(a => abbreviateName(a.full_name)).join(', ') }}</span>
          <span v-else class="text-warn">⚠ авторы не указаны — в документе будет «—»</span>
        </div>
        <div class="auto-row"><span class="auto-label">Главный автор</span><span>{{ conclusionLead ? abbreviateName(conclusionLead.full_name) : '—' }}</span></div>
        <div class="auto-row"><span class="auto-label">Дата</span><span>{{ autoDateLabel }}</span></div>
        <div class="auto-row">
          <span class="auto-label">Шаблон</span>
          <div style="flex:1">
            <select v-model="conclusionTemplateId" class="select">
              <option value="">Автоматически (последний активный)</option>
              <option v-for="t in conclusionTemplates" :key="t.id" :value="String(t.id)">
                {{ t.name }}{{ t.is_active ? '' : ' (отключён)' }}
              </option>
            </select>
            <div class="form-hint mt-2">
              Шаблоны настраиваются в разделе <RouterLink to="/templates" @click="showConclusion = false">«Шаблоны документов»</RouterLink>.
            </div>
          </div>
        </div>
        <div class="auto-row"><span class="auto-label">Имя файла</span><span class="text-mono text-sm">{{ conclusionFilename }}</span></div>
      </div>

      <div v-else>
        <div class="form-group">
          <label class="form-label">Файл заключения</label>
          <FileUpload v-model="conclusionFile" accept=".pdf,.doc,.docx,.odt,.rtf,.jpg,.jpeg,.png" hint="PDF, DOC, DOCX или скан" icon="📋" />
        </div>
        <div class="form-group">
          <label class="form-label">Примечание</label>
          <textarea v-model="conclusionNotes" class="textarea" placeholder="Номер, дата, кем выдано…"></textarea>
        </div>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="showConclusion = false">Отмена</button>
        <button class="btn btn-primary" :disabled="savingConclusion" @click="saveConclusion">
          {{ savingConclusion ? '⏳ Подождите…' : conclusionMode === 'auto' ? '✨ Сформировать' : '📎 Прикрепить' }}
        </button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { articlesApi, collectionsApi, authorsApi, templatesApi, catalogsApi, buildFormData } from '@/utils/api'
import { formatDate, formatBytes, compressionRatio, abbreviateName, authorLabel, fileIcon } from '@/utils/format'
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
const DEFAULT_TYPES = ['ВАК', 'РИНЦ', 'Scopus', 'Web of Science', 'Прочее']
const MONTHS = ['января', 'февраля', 'марта', 'апреля', 'мая', 'июня', 'июля', 'августа', 'сентября', 'октября', 'ноября', 'декабря']

const articles = ref([])
const collections = ref([])
const authors = ref([])
const conclusionTemplates = ref([])
const loading = ref(false)
const loadError = ref('')
const sidebar = ref(null)

const search = ref('')
const filterCollection = ref('')
const filterType = ref('')
const filterConclusion = ref('')
const activeCatalog = ref('')
const selected = ref([])

const authorsById = computed(() => new Map(authors.value.map(a => [a.id, a])))
const typeOptions = computed(() => [...new Set([...DEFAULT_TYPES, ...articles.value.map(a => a.article_type).filter(Boolean)])])
const ratio = a => compressionRatio(a.file_size_original, a.file_size_compressed)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return articles.value.filter(a => {
    if (q && !(a.title.toLowerCase().includes(q) || (a.catalog || '').toLowerCase().includes(q) ||
      a.authors.some(au => au.full_name.toLowerCase().includes(q)))) return false
    if (filterCollection.value === '__none__' ? a.collection_id : filterCollection.value && a.collection_id !== Number(filterCollection.value)) return false
    if (filterType.value && a.article_type !== filterType.value) return false
    if (filterConclusion.value === 'yes' && !a.has_conclusion) return false
    if (filterConclusion.value === 'no' && a.has_conclusion) return false
    if (activeCatalog.value === '__none__') return !a.catalog
    if (activeCatalog.value) return a.catalog === activeCatalog.value
    return true
  })
})
const { sortKey, sortDir, toggle, sorted } = useSort(filtered, {
  title: a => a.title,
  authors: a => a.authors[0]?.full_name,
  type: a => a.article_type,
  collection: a => a.collection?.name,
  conclusion: a => (a.has_conclusion ? 1 : 0),
  created: a => a.created_at,
}, { key: 'created', dir: 'desc' })
const sortProps = computed(() => ({ sortKey: sortKey.value, sortDir: sortDir.value, toggle }))

const allSelected = computed(() => sorted.value.length > 0 && sorted.value.every(a => selected.value.includes(a.id)))
function toggleAll() {
  selected.value = allSelected.value ? [] : sorted.value.map(a => a.id)
}
watch([search, filterCollection, filterType, filterConclusion, activeCatalog], () => { selected.value = [] })

function resetFilters() {
  search.value = ''; filterCollection.value = ''; filterType.value = ''; filterConclusion.value = ''; activeCatalog.value = ''
}

async function load() {
  loading.value = true
  loadError.value = ''
  try {
    const [art, col, auth, tmpl] = await Promise.all([
      articlesApi.list(), collectionsApi.list(), authorsApi.list(), templatesApi.list(),
    ])
    articles.value = art.data
    collections.value = col.data
    authors.value = auth.data
    conclusionTemplates.value = tmpl.data.filter(t => t.doc_type === 'conclusion' && t.has_file)
    if (detail.value) detail.value = articles.value.find(a => a.id === detail.value.id) || null
    selected.value = selected.value.filter(id => articles.value.some(a => a.id === id))
  } catch (e) {
    loadError.value = e.message
  } finally {
    loading.value = false
  }
}
onMounted(load)

// ── Drag & drop / групповые действия ─────────────────────────────────────────
function dragStart(a, e) {
  const ids = selected.value.includes(a.id) ? selected.value : [a.id]
  e.dataTransfer.setData('application/x-atlas-ids', JSON.stringify(ids))
  e.dataTransfer.effectAllowed = 'move'
}
async function bulkMove(e) {
  const target = e.target.value
  e.target.value = ''
  if (!target) return
  try {
    await catalogsApi.move('articles', selected.value, target === '__none__' ? null : target)
    toast.success('Перемещено')
    selected.value = []
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (err) { toast.error(err.message) }
}
async function bulkDelete() {
  const n = selected.value.length
  if (!await confirmDialog({ title: 'Удалить статьи?', message: `Будут удалены статьи (${n}) вместе с файлами и заключениями. Действие необратимо.` })) return
  let ok = 0
  for (const id of selected.value) {
    try { await articlesApi.delete(id); ok++ } catch (e) { toast.error(e.message) }
  }
  toast.success(`Удалено: ${ok}`)
  selected.value = []
  await load()
}

// ── Карточка ─────────────────────────────────────────────────────────────────
const showDetail = ref(false)
const detail = ref(null)
const conclusion = ref(null)
const previewTarget = ref('article')

async function openDetail(a) {
  detail.value = a
  conclusion.value = null
  previewTarget.value = a.has_file ? 'article' : (a.conclusion_has_file ? 'conclusion' : 'article')
  showDetail.value = true
  if (a.has_conclusion) {
    try { conclusion.value = (await articlesApi.getConclusion(a.id)).data } catch { /* нет — не страшно */ }
  }
}

const previewProps = computed(() => {
  const a = detail.value
  if (!a) return {}
  if (previewTarget.value === 'conclusion' && a.conclusion_has_file) {
    return { src: articlesApi.previewConclusion(a.id), filename: conclusion.value?.original_filename || 'conclusion.docx', downloadUrl: articlesApi.downloadConclusion(a.id) }
  }
  if (!a.has_file) return {}
  return { src: articlesApi.preview(a.id), filename: a.original_filename, downloadUrl: articlesApi.download(a.id) }
})

// ── Форма ────────────────────────────────────────────────────────────────────
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const emptyForm = () => ({ title: '', article_type: '', collection_id: '', catalog: '', author_ids: [], lead_author_id: '', file: null })
const form = ref(emptyForm())

function openCreate() {
  editing.value = null
  form.value = { ...emptyForm(), catalog: activeCatalog.value && activeCatalog.value !== '__none__' ? activeCatalog.value : '' }
  showForm.value = true
}
function openEdit(a) {
  editing.value = a
  form.value = {
    title: a.title, article_type: a.article_type || '', collection_id: a.collection_id ? String(a.collection_id) : '',
    catalog: a.catalog || '', author_ids: a.authors.map(x => x.id),
    lead_author_id: a.lead_author_id ? String(a.lead_author_id) : '', file: null,
  }
  showForm.value = true
}

async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const f = form.value
    // Пустые строки отправляются намеренно: сервер очистит поле
    const fd = buildFormData({
      title: f.title.trim(), article_type: f.article_type.trim(), collection_id: f.collection_id, catalog: f.catalog.trim(),
      author_ids: f.author_ids, lead_author_id: f.author_ids.includes(Number(f.lead_author_id)) ? f.lead_author_id : '',
      file: f.file,
    })
    if (editing.value) {
      await articlesApi.update(editing.value.id, fd)
      toast.success('Статья сохранена')
    } else {
      await articlesApi.create(fd)
      toast.success('Статья добавлена')
    }
    showForm.value = false
    await Promise.all([load(), sidebar.value?.reload()])
  } catch (e) {
    toast.error(e.message)
  } finally {
    saving.value = false
  }
}

async function remove(a) {
  if (!await confirmDialog({ title: 'Удалить статью?', message: `«${a.title}»\n\nФайл статьи и заключение тоже будут удалены.` })) return
  try {
    await articlesApi.delete(a.id)
    toast.success('Статья удалена')
    await load()
  } catch (e) { toast.error(e.message) }
}

// ── Заключение ───────────────────────────────────────────────────────────────
const showConclusion = ref(false)
const conclusionArticle = ref(null)
const conclusionMode = ref('auto')
const conclusionTemplateId = ref('')
const conclusionFile = ref(null)
const conclusionNotes = ref('')
const savingConclusion = ref(false)

const conclusionLead = computed(() => {
  const a = conclusionArticle.value
  if (!a?.authors?.length) return null
  return a.authors.find(x => x.id === a.lead_author_id) || a.authors[0]
})
const autoDateLabel = computed(() => {
  const d = conclusionArticle.value?.created_at ? new Date(conclusionArticle.value.created_at) : new Date()
  return `${MONTHS[d.getMonth()]} ${d.getFullYear()} г.`
})
const conclusionFilename = computed(() => {
  const a = conclusionArticle.value
  if (!a) return ''
  const parts = ['Заключение']
  if (conclusionLead.value) parts.push(abbreviateName(conclusionLead.value.full_name).replace(/\s/g, '_').replace(/\./g, ''))
  parts.push(formatDate(a.created_at, 'yyyy-MM-dd'))
  return parts.join('_') + '.docx'
})

function openConclusion(a) {
  conclusionArticle.value = a
  conclusionMode.value = 'auto'
  conclusionTemplateId.value = ''
  conclusionFile.value = null
  conclusionNotes.value = ''
  showConclusion.value = true
}

async function saveConclusion() {
  const id = conclusionArticle.value.id
  if (conclusionMode.value === 'manual' && !conclusionFile.value && !conclusionNotes.value.trim()) {
    return toast.error('Выберите файл или укажите примечание')
  }
  savingConclusion.value = true
  try {
    if (conclusionMode.value === 'auto') {
      await articlesApi.generateConclusion(id, conclusionTemplateId.value || undefined)
      toast.success('Заключение сформировано')
    } else {
      await articlesApi.uploadConclusion(id, buildFormData({ notes: conclusionNotes.value, file: conclusionFile.value }))
      toast.success('Заключение прикреплено')
    }
    showConclusion.value = false
    await load()
    if (showDetail.value && detail.value?.id === id) {
      await openDetail(detail.value)
      previewTarget.value = 'conclusion'
    }
  } catch (e) {
    toast.error(e.message)
  } finally {
    savingConclusion.value = false
  }
}

async function removeConclusion(a) {
  if (!await confirmDialog({ title: 'Удалить заключение?', message: `Заключение к статье «${a.title}» будет удалено.` })) return
  try {
    await articlesApi.deleteConclusion(a.id)
    toast.success('Заключение удалено')
    await load()
    if (detail.value) openDetail(detail.value)
  } catch (e) { toast.error(e.message) }
}

// в конце setup: к этому моменту все ref-ы формы и карточки уже объявлены
useOpenFromQuery(articles, openDetail, () => openCreate())
</script>

<style scoped>
.auto-box { background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: var(--radius); padding: 6px 16px; }
.auto-row { display: flex; gap: 12px; padding: 9px 0; border-bottom: 1px solid var(--c-border); font-size: 13px; align-items: baseline; }
.auto-row:last-child { border-bottom: none; }
.auto-label { flex-shrink: 0; width: 120px; color: var(--c-text3); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; }
</style>
