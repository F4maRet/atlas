<template>
  <div class="page" @click="closeContextMenu">
    <div class="page-header">
      <h1><span class="page-title-icon">📄</span> Научные статьи</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить статью</button>
    </div>

    <div v-if="loadError" class="load-error-banner">
      ⚠️ {{ loadError }}
      <button class="btn btn-ghost btn-sm" @click="load()">↺ Повторить</button>
    </div>

    <div style="display:flex;gap:12px;margin-bottom:16px;align-items:center">
      <div class="search-bar" style="flex:1;margin-bottom:0;height:40px;box-sizing:border-box">
        <span>🔍</span>
        <input v-model="search" placeholder="Поиск по названию или автору..." />
      </div>
      <select class="select" style="width:200px;height:40px;flex-shrink:0" v-model="filterCollection">
        <option value="">Все сборники</option>
        <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
      </select>
    </div>

    <div class="layout-with-sidebar">
      <!-- Sidebar -->
      <div class="catalog-sidebar">
        <div class="catalog-sidebar__head">
          <span class="catalog-sidebar__title">📁 Каталоги</span>
          <button class="btn btn-ghost btn-sm btn-icon" @click.stop="startCreateCatalog">＋</button>
        </div>
        <div v-if="creatingCatalog" class="catalog-new-input">
          <input ref="newCatalogInput" v-model="newCatalogName" class="input input-sm"
            placeholder="Название каталога"
            @keyup.enter="confirmCreateCatalog" @keyup.esc="creatingCatalog=false" @click.stop />
          <div style="display:flex;gap:4px;margin-top:6px">
            <button class="btn btn-primary btn-sm" @click.stop="confirmCreateCatalog">OK</button>
            <button class="btn btn-secondary btn-sm" @click.stop="creatingCatalog=false">✕</button>
          </div>
        </div>
        <div class="catalog-item" :class="{ active: activeCatalog === '' }"
          @click.stop="activeCatalog = ''"
          @dragover.prevent="dragOverCatalog = '__all__'" @dragleave="dragOverCatalog = null"
          @drop.stop="dropOnCatalog(null, $event)"
          :style="dragOverCatalog==='__all__'?'background:var(--c-surface);':''">
          <span class="catalog-item__icon">📋</span>
          <span class="catalog-item__name">Все статьи</span>
          <span class="catalog-item__count">{{ articles.length }}</span>
        </div>
        <div class="catalog-item" :class="{ active: activeCatalog === '__none__' }"
          @click.stop="activeCatalog = '__none__'"
          @dragover.prevent="dragOverCatalog = '__none__'" @dragleave="dragOverCatalog = null"
          @drop.stop="dropOnCatalog('__none__', $event)"
          :style="dragOverCatalog==='__none__'?'background:var(--c-surface);':''">
          <span class="catalog-item__icon">📂</span>
          <span class="catalog-item__name">Без каталога</span>
          <span class="catalog-item__count">{{ articles.filter(a => !a.catalog).length }}</span>
        </div>
        <div v-for="cat in catalogs" :key="cat"
          class="catalog-item" :class="{ active: activeCatalog === cat }"
          @click.stop="activeCatalog = cat"
          @contextmenu.prevent="openContextMenu(cat, $event)"
          @dragover.prevent="dragOverCatalog = cat" @dragleave="dragOverCatalog = null"
          @drop.stop="dropOnCatalog(cat, $event)"
          :style="dragOverCatalog===cat?'background:var(--c-surface);border-color:var(--c-accent);':''">
          <span class="catalog-item__icon">📁</span>
          <div v-if="renamingCatalog === cat" style="flex:1" @click.stop>
            <input :ref="el => { if(el) renameInputs[cat] = el }" v-model="renameValue" class="input input-sm"
              @keyup.enter="confirmRename(cat)" @keyup.esc="renamingCatalog = null" />
          </div>
          <span v-else class="catalog-item__name">{{ cat }}</span>
          <span class="catalog-item__count">{{ articles.filter(a => a.catalog === cat).length }}</span>
        </div>
      </div>

      <!-- Context menu -->
      <div v-if="contextMenu.visible" class="context-menu"
        :style="{ top: contextMenu.y + 'px', left: contextMenu.x + 'px' }" @click.stop>
        <div class="context-menu__item" @click="startRenameCatalog(contextMenu.catalog)">✏️ Переименовать</div>
        <div class="context-menu__item context-menu__item--new" @click="startCreateCatalogFromMenu">📁 Новый каталог</div>
        <div class="context-menu__divider"></div>
        <div class="context-menu__item context-menu__item--danger" @click="deleteCatalog(contextMenu.catalog)">🗑 Удалить каталог</div>
      </div>

      <!-- Table -->
      <div class="catalog-content">
        <div class="card" style="padding:0;overflow:hidden">
          <div class="table-wrap">
            <table>
              <thead>
                <tr><th>Название</th><th>Авторы</th><th>Тип</th><th>Сборник</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-if="filtered.length === 0">
                  <td colspan="5" style="text-align:center;padding:40px">
                    <div class="empty-state" style="padding:32px">
                      <div class="empty-state__icon">📄</div>
                      <div class="empty-state__text">Статей пока нет</div>
                    </div>
                  </td>
                </tr>
                <tr v-for="a in filtered" :key="a.id" class="table-row-clickable"
                  draggable="true" @dragstart="dragStart(a, $event)" @dragend="dragEnd"
                  @click="openDetail(a)">
                  <td style="max-width:320px">
                    <div class="truncate" style="font-weight:500">{{ a.title }}</div>
                    <div v-if="a.catalog" class="text-muted" style="font-size:11px;margin-top:2px">📁 {{ a.catalog }}</div>
                  </td>
                  <td>
                    <div class="flex" style="flex-wrap:wrap;gap:4px">
                      <span v-for="au in a.authors" :key="au.id" class="tag">{{ au.short_name || au.full_name }}</span>
                    </div>
                  </td>
                  <td><span v-if="a.article_type" class="badge badge-blue">{{ a.article_type }}</span></td>
                  <td><span v-if="a.collection" class="truncate" style="max-width:140px;display:block;font-size:13px">{{ a.collection.name }}</span></td>
                  <td @click.stop>
                    <div class="flex-center gap-2">
                      <button class="btn btn-ghost btn-sm btn-icon" @click.stop="openEdit(a)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" @click.stop="confirmDelete(a)">🗑</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Detail Modal (redesigned) ── -->
    <Transition name="fade">
      <div v-if="showDetail" class="modal-overlay" @click.self="showDetail=false">
        <div class="modal modal-detail-v2">

          <!-- Header -->
          <div class="detail-v2-header">
            <div class="detail-v2-header__left">
              <span class="detail-v2-badge" v-if="detailArticle?.article_type">{{ detailArticle.article_type }}</span>
              <h2 class="detail-v2-title">{{ detailArticle?.title }}</h2>
            </div>
            <div class="detail-v2-header__actions">
              <button class="btn btn-ghost btn-sm" @click="showDetail=false; openEdit(detailArticle)">✏️ Редактировать</button>
              <button class="btn btn-ghost btn-sm btn-icon" @click="showDetail=false">✕</button>
            </div>
          </div>

          <!-- Body: 2-column -->
          <div class="detail-v2-body">

            <!-- LEFT: meta + actions -->
            <div class="detail-v2-meta">

              <!-- Authors -->
              <div class="detail-v2-section">
                <div class="detail-v2-label">Авторы</div>
                <div v-if="detailArticle?.authors?.length" class="detail-v2-authors">
                  <span v-for="au in detailArticle.authors" :key="au.id"
                    class="author-chip"
                    :class="au.id === detailArticle.lead_author_id ? 'author-chip--lead' : ''">
                    {{ au.full_name }}
                    <span v-if="au.id === detailArticle.lead_author_id" class="lead-star">★</span>
                  </span>
                </div>
                <span v-else class="text-muted text-sm">—</span>
              </div>

              <!-- Meta grid -->
              <div class="detail-v2-grid">
                <div class="detail-v2-cell">
                  <div class="detail-v2-label">Сборник</div>
                  <div class="detail-v2-val">{{ detailArticle?.collection?.name || '—' }}</div>
                </div>
                <div class="detail-v2-cell">
                  <div class="detail-v2-label">Дата добавления</div>
                  <div class="detail-v2-val">{{ detailArticle ? formatDate(detailArticle.created_at) : '—' }}</div>
                </div>
                <div class="detail-v2-cell" v-if="detailArticle?.catalog">
                  <div class="detail-v2-label">Каталог</div>
                  <div class="detail-v2-val text-mono" style="font-size:11px">{{ detailArticle.catalog }}</div>
                </div>
              </div>

              <!-- File block -->
              <div class="detail-v2-section">
                <div class="detail-v2-label">Файл статьи</div>
                <div v-if="detailArticle?.original_filename" class="detail-v2-file">
                  <div class="detail-v2-file__icon">{{ isPdf(detailArticle.original_filename) ? '📕' : '📘' }}</div>
                  <div class="detail-v2-file__info">
                    <div class="detail-v2-file__name">{{ detailArticle.original_filename }}</div>
                    <div class="detail-v2-file__size text-muted" style="font-size:11px" v-if="detailArticle.file_size_original">
                      {{ formatBytes(detailArticle.file_size_original) }}
                      <span v-if="ratio(detailArticle)" class="compress-badge" style="margin-left:4px">{{ ratio(detailArticle) }}</span>
                    </div>
                  </div>
                  <div class="detail-v2-file__actions">
                    <a :href="downloadUrl(detailArticle.id)" class="btn btn-ghost btn-sm" download>↓</a>
                    <button class="btn btn-ghost btn-sm"
                      :class="detailPreview ? 'btn-active' : ''"
                      @click="toggleDetailPreview(detailArticle)"
                      :title="detailPreview ? 'Скрыть предпросмотр' : 'Предпросмотр'">
                      {{ detailPreview ? '🙈' : '👁' }}
                    </button>
                  </div>
                </div>
                <div v-else class="text-muted text-sm">Не прикреплён</div>
              </div>

              <!-- Conclusion block -->
              <div class="detail-v2-section">
                <div class="detail-v2-label">Заключение об открытом публиковании</div>
                <div v-if="detailArticle?.has_conclusion" class="detail-v2-conclusion detail-v2-conclusion--ok">
                  <span class="badge badge-green">✓ Прикреплено</span>
                  <div style="display:flex;gap:6px;margin-top:8px;flex-wrap:wrap">
                    <a :href="articlesApi.downloadGeneratedConclusion(detailArticle.id)" class="btn btn-ghost btn-sm" target="_blank">↓ Скачать</a>
                    <button class="btn btn-ghost btn-sm" style="color:var(--c-red)" @click="showDetail=false; openConclusion(detailArticle)">↺ Заменить</button>
                  </div>
                </div>
                <div v-else class="detail-v2-conclusion">
                  <div class="text-muted text-sm" style="margin-bottom:8px">Не сформировано</div>
                  <button class="btn btn-primary btn-sm" @click="showDetail=false; openConclusion(detailArticle)">✨ Сформировать</button>
                </div>
              </div>

            </div>

            <!-- RIGHT: inline preview -->
            <div class="detail-v2-preview">
              <div v-if="!detailArticle?.original_filename" class="detail-v2-preview__empty">
                <div style="font-size:40px;margin-bottom:10px">📎</div>
                <div class="text-muted text-sm">Файл не прикреплён</div>
              </div>
              <div v-else-if="!detailPreview" class="detail-v2-preview__empty">
                <div style="font-size:36px;margin-bottom:10px">{{ isPdf(detailArticle.original_filename) ? '📕' : '📘' }}</div>
                <div style="font-weight:500;margin-bottom:6px;font-size:13px">{{ detailArticle.original_filename }}</div>
                <div class="text-muted text-sm" style="margin-bottom:16px">Нажмите 👁 для предпросмотра</div>
                <button class="btn btn-ghost btn-sm" @click="toggleDetailPreview(detailArticle)">👁 Открыть предпросмотр</button>
              </div>
              <div v-else-if="detailPreviewLoading" class="detail-v2-preview__empty">
                <div class="detail-preview-spinner"></div>
                <div class="text-muted text-sm" style="margin-top:12px">Загрузка...</div>
              </div>
              <div v-else-if="detailPreviewError" class="detail-v2-preview__empty">
                <div style="font-size:32px;margin-bottom:10px">⚠️</div>
                <div class="text-muted text-sm">{{ detailPreviewError }}</div>
              </div>
              <!-- PDF -->
              <object v-else-if="detailPreview && isPdf(detailArticle.original_filename)"
                :data="downloadUrl(detailArticle.id)"
                type="application/pdf"
                class="detail-v2-preview__frame">
                <div class="detail-v2-preview__empty">
                  <div class="text-muted text-sm">PDF не отображается браузером</div>
                  <a :href="downloadUrl(detailArticle.id)" class="btn btn-ghost btn-sm" style="margin-top:8px" download>↓ Скачать</a>
                </div>
              </object>
              <!-- DOCX rendered as HTML -->
              <iframe v-else-if="detailPreview && detailPreviewHtml"
                :srcdoc="detailPreviewHtml"
                class="detail-v2-preview__frame"
                sandbox="allow-same-origin"
                title="Document preview">
              </iframe>
            </div>

          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Create/Edit Modal ── -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать статью' : 'Новая статья' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.title" placeholder="Полное название статьи" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Тип статьи</label>
              <select class="select" v-model="form.article_type">
                <option value="">— выбрать —</option>
                <option>ВАК</option><option>РИНЦ</option><option>Scopus</option>
                <option>Web of Science</option><option>Прочее</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Сборник</label>
              <select class="select" v-model="form.collection_id">
                <option value="">— без сборника —</option>
                <option v-for="c in collections" :key="c.id" :value="c.id">{{ c.name }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Каталог хранения</label>
            <div style="display:flex;gap:8px">
              <input class="input" v-model="form.catalog" placeholder="/articles/2024" />
              <select v-if="catalogs.length" class="select" style="width:160px" @change="e => { if(e.target.value) form.catalog = e.target.value }">
                <option value="">📁 Каталоги</option>
                <option v-for="c in catalogs" :key="c" :value="c">{{ c }}</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Авторы</label>
            <AuthorPicker v-model="form.author_ids" :all-authors="authors" @created="authors.push($event)" />
          </div>
          <div class="form-group" v-if="form.author_ids.length > 0">
            <label class="form-label">Главный автор</label>
            <select class="select" v-model="form.lead_author_id">
              <option value="">— первый из списка —</option>
              <option v-for="id in form.author_ids" :key="id" :value="id">
                {{ authors.find(a => a.id === id)?.full_name || id }}
              </option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Файл статьи (PDF / DOCX)</label>
            <FileUpload v-model="form.file" accept=".pdf,.doc,.docx" icon="📄"
              :existing-name="editing?.original_filename"
              :existing-size-original="editing?.file_size_original"
              :existing-size-compressed="editing?.file_size_compressed"
              :download-url="editing ? downloadUrl(editing.id) : null" />
          </div>
          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showModal=false">Отмена</button>
            <button class="btn btn-primary" @click="save" :disabled="saving">
              {{ saving ? 'Сохранение...' : (editing ? 'Сохранить' : 'Создать') }}
            </button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Conclusion Modal ── -->
    <Transition name="fade">
      <div v-if="showConclusionModal" class="modal-overlay" @click.self="showConclusionModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>Заключение об открытом публиковании</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showConclusionModal=false">✕</button>
          </div>

          <div class="conclusion-article-name text-muted text-sm" style="margin-bottom:20px">
            Статья: <strong style="color:var(--c-text)">{{ conclusionArticle?.title }}</strong>
          </div>

          <!-- Mode tabs -->
          <div class="conclusion-tabs">
            <button class="conclusion-tab" :class="{ active: conclusionMode === 'auto' }" @click="conclusionMode = 'auto'">
              ✨ Сгенерировать автоматически
            </button>
            <button class="conclusion-tab" :class="{ active: conclusionMode === 'manual' }" @click="conclusionMode = 'manual'">
              📎 Загрузить своё
            </button>
          </div>

          <!-- Auto mode -->
          <div v-if="conclusionMode === 'auto'" class="conclusion-mode-body">
            <div class="auto-preview-box">
              <div class="auto-preview-box__title">📄 Будет сгенерировано заключение</div>
              <div class="auto-preview-row">
                <span class="auto-preview-label">Название статьи</span>
                <span class="auto-preview-value">{{ conclusionArticle?.title }}</span>
              </div>
              <div class="auto-preview-row">
                <span class="auto-preview-label">Автор[а/ов]</span>
                <span class="auto-preview-value">
                  <span v-if="conclusionArticle?.authors?.length">
                    {{ conclusionArticle.authors.map(a => abbreviateName(a.full_name)).join(', ') }}
                    <span class="text-muted text-sm" style="margin-left:4px">
                      ({{ conclusionArticle.authors.length === 1 ? 'автора' : 'авторов' }})
                    </span>
                  </span>
                  <span v-else class="text-muted">—</span>
                </span>
              </div>
              <div class="auto-preview-row">
                <span class="auto-preview-label">Главный автор</span>
                <span class="auto-preview-value">
                  <span v-if="conclusionLeadAuthor">
                    {{ abbreviateName(conclusionLeadAuthor.full_name) }}
                    <span class="text-muted text-sm" style="margin-left:4px">({{ conclusionLeadAuthor.full_name }})</span>
                  </span>
                  <span v-else class="text-muted">— первый из списка</span>
                </span>
              </div>
              <div class="auto-preview-row">
                <span class="auto-preview-label">Дата загрузки</span>
                <span class="auto-preview-value">{{ autoDateLabel }}</span>
              </div>

              <!-- Template selector -->
              <div class="auto-preview-row" style="align-items:flex-start;padding-top:10px">
                <span class="auto-preview-label" style="padding-top:6px">Шаблон документа</span>
                <span class="auto-preview-value">
                  <div v-if="conclusionTemplates.length > 0" style="display:flex;flex-direction:column;gap:6px">
                    <select class="select select-sm" v-model="conclusionForm.template_id" style="font-size:13px">
                      <option value="">— встроенный шаблон —</option>
                      <option v-for="t in conclusionTemplates" :key="t.id" :value="t.id">
                        {{ t.name }}{{ !t.is_active ? ' (неактивен)' : '' }}
                      </option>
                    </select>
                    <div v-if="conclusionSelectedTemplate" style="display:flex;gap:6px;align-items:center">
                      <a :href="templatesApi.preview(conclusionSelectedTemplate.id)"
                        target="_blank" class="template-link text-sm">👁 Просмотреть шаблон</a>
                      <span class="text-muted text-sm">·</span>
                      <a :href="templatesApi.download(conclusionSelectedTemplate.id)"
                        target="_blank" class="template-link text-sm">↓ Скачать</a>
                    </div>
                    <div v-else class="text-muted text-sm">
                      Будет использован встроенный шаблон. Изменить шаблоны можно в разделе <strong>Шаблоны документов</strong>.
                    </div>
                  </div>
                  <div v-else class="text-muted text-sm">
                    Встроенный шаблон.
                    <a href="#" class="template-link" @click.prevent="showConclusionModal=false">Добавить свой в «Шаблонах»</a>
                  </div>
                </span>
              </div>

              <div class="auto-preview-row">
                <span class="auto-preview-label">Имя файла</span>
                <span class="auto-preview-value text-mono" style="font-size:12px">{{ conclusionFilename }}</span>
              </div>
            </div>
          </div>

          <!-- Manual mode -->
          <div v-if="conclusionMode === 'manual'" class="conclusion-mode-body">
            <div class="form-group">
              <label class="form-label">Файл заключения (PDF / DOCX)</label>
              <FileUpload v-model="conclusionForm.file" accept=".pdf,.doc,.docx" icon="📋" />
            </div>
            <div class="form-group">
              <label class="form-label">Примечания</label>
              <textarea class="textarea" v-model="conclusionForm.notes" placeholder="Дополнительная информация..."></textarea>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showConclusionModal=false">Отмена</button>
            <button class="btn btn-primary" @click="saveConclusion" :disabled="savingConclusion">
              <span v-if="savingConclusion">⏳ Генерация...</span>
              <span v-else-if="conclusionMode === 'auto'">✨ Сгенерировать</span>
              <span v-else>📎 Прикрепить</span>
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useToast } from 'vue-toastification'
import { articlesApi, collectionsApi, authorsApi, templatesApi, buildFormData, formatBytes } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'

const toast = useToast()
const articles = ref([])
const collections = ref([])
const authors = ref([])
const conclusionTemplates = ref([])
const search = ref('')
const filterCollection = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const showConclusionModal = ref(false)
const conclusionArticle = ref(null)
const savingConclusion = ref(false)

const showDetail = ref(false)
const detailArticle = ref(null)
const detailPreview = ref(false)
const detailPreviewHtml = ref('')
const detailPreviewLoading = ref(false)
const detailPreviewError = ref('')

const catalogs = ref([])
const activeCatalog = ref('')
const creatingCatalog = ref(false)
const newCatalogName = ref('')
const newCatalogInput = ref(null)
const renamingCatalog = ref(null)
const renameValue = ref('')
const renameInputs = ref({})
const dragOverCatalog = ref(null)
const draggingArticle = ref(null)
const contextMenu = ref({ visible: false, x: 0, y: 0, catalog: '' })

const form = ref({ title: '', article_type: '', collection_id: '', catalog: '', author_ids: [], lead_author_id: '', file: null })
const conclusionForm = ref({ file: null, notes: '', template_id: '' })
const conclusionMode = ref('auto')

const MONTHS_RU = ['января','февраля','марта','апреля','мая','июня','июля','августа','сентября','октября','ноября','декабря']
const autoDateLabel = computed(() => {
  if (!conclusionArticle.value?.created_at) return '—'
  const d = new Date(conclusionArticle.value.created_at)
  return `${MONTHS_RU[d.getMonth()]} ${d.getFullYear()} г.`
})

function abbreviateName(fullName) {
  if (!fullName) return ''
  const parts = fullName.trim().split(/\s+/)
  if (parts.length === 0) return fullName
  const surname = parts[0]
  const initials = parts.slice(1).filter(Boolean).map(p => p[0].toUpperCase() + '.').join('')
  return initials ? `${surname} ${initials}` : surname
}

const conclusionLeadAuthor = computed(() => {
  const a = conclusionArticle.value
  if (!a?.authors?.length) return null
  if (a.lead_author_id) return a.authors.find(au => au.id === a.lead_author_id) || a.authors[0]
  return a.authors[0]
})

// All conclusion templates (active and inactive) for selection
const conclusionSelectedTemplate = computed(() => {
  if (!conclusionForm.value.template_id) return null
  return conclusionTemplates.value.find(t => t.id === conclusionForm.value.template_id) || null
})

const conclusionFilename = computed(() => {
  const a = conclusionArticle.value
  if (!a) return 'Заключение.docx'
  const lead = conclusionLeadAuthor.value
  const abbr = lead ? abbreviateName(lead.full_name).replace(/\s/g, '_').replace(/\./g, '') : ''
  const d = a.created_at ? new Date(a.created_at) : new Date()
  const dateStr = d.toISOString().slice(0, 10)
  const parts = ['Заключение']
  if (abbr) parts.push(abbr)
  if (dateStr) parts.push(dateStr)
  return parts.join('_') + '.docx'
})

const filtered = computed(() => {
  let list = articles.value
  if (search.value) {
    const q = search.value.toLowerCase()
    list = list.filter(a => a.title.toLowerCase().includes(q) || a.authors.some(au => au.full_name.toLowerCase().includes(q)))
  }
  if (filterCollection.value) list = list.filter(a => a.collection_id === Number(filterCollection.value))
  if (activeCatalog.value === '__none__') list = list.filter(a => !a.catalog)
  else if (activeCatalog.value !== '') list = list.filter(a => a.catalog === activeCatalog.value)
  return list
})

const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''
const downloadUrl = id => articlesApi.download(id)
const previewUrl  = id => `${articlesApi.download(id).replace('/download', '/preview')}`
const isPdf = name => name?.toLowerCase().endsWith('.pdf')
const ratio = a => {
  if (!a.file_size_original || !a.file_size_compressed) return null
  const saved = ((1 - a.file_size_compressed / a.file_size_original) * 100).toFixed(0)
  return saved > 2 ? `-${saved}%` : null
}

// ── Detail preview (inline, local) ──────────────────────────────────────────
async function toggleDetailPreview(article) {
  if (detailPreview.value) {
    detailPreview.value = false
    detailPreviewHtml.value = ''
    detailPreviewError.value = ''
    return
  }
  detailPreview.value = true
  if (isPdf(article.original_filename)) return  // PDF renders via <object>

  // DOCX: fetch HTML from backend /preview endpoint (local, no internet)
  detailPreviewLoading.value = true
  detailPreviewError.value = ''
  try {
    // Articles preview endpoint mirrors the download url with /preview
    const url = `${import.meta.env.VITE_API_URL || ''}/api/v1/articles/${article.id}/preview`
    const resp = await fetch(url)
    if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
    detailPreviewHtml.value = await resp.text()
  } catch (e) {
    detailPreviewError.value = `Не удалось загрузить предпросмотр: ${e.message}`
  } finally {
    detailPreviewLoading.value = false
  }
}

// ── Sync catalogs ────────────────────────────────────────────────────────────
function syncCatalogsFromData(articleList) {
  const fromData = new Set(articleList.filter(a => a.catalog).map(a => a.catalog))
  fromData.forEach(c => { if (!catalogs.value.includes(c)) catalogs.value.push(c) })
  catalogs.value.sort()
}

// ── Catalog management ───────────────────────────────────────────────────────
function startCreateCatalog() {
  contextMenu.value.visible = false
  creatingCatalog.value = true
  newCatalogName.value = ''
  nextTick(() => newCatalogInput.value?.focus())
}
function startCreateCatalogFromMenu() { contextMenu.value.visible = false; startCreateCatalog() }

async function confirmCreateCatalog() {
  const name = newCatalogName.value.trim()
  creatingCatalog.value = false
  if (!name) return
  if (!catalogs.value.includes(name)) { catalogs.value.push(name); catalogs.value.sort() }
  activeCatalog.value = name
  toast.success(`Каталог «${name}» создан`)
}

function startRenameCatalog(cat) {
  contextMenu.value.visible = false
  renamingCatalog.value = cat
  renameValue.value = cat
  nextTick(() => renameInputs.value[cat]?.focus())
}

async function confirmRename(oldName) {
  const newName = renameValue.value.trim()
  renamingCatalog.value = null
  if (!newName || newName === oldName) return
  for (const a of articles.value.filter(a => a.catalog === oldName))
    await articlesApi.update(a.id, buildFormData({ title: a.title, catalog: newName, author_ids: a.authors.map(x => x.id) }))
  const idx = catalogs.value.indexOf(oldName)
  if (idx !== -1) { catalogs.value[idx] = newName; catalogs.value.sort() }
  if (activeCatalog.value === oldName) activeCatalog.value = newName
  await load()
  toast.success(`Каталог переименован в «${newName}»`)
}

async function deleteCatalog(cat) {
  contextMenu.value.visible = false
  if (!confirm(`Удалить каталог «${cat}»?\nУ всех статей каталог будет откреплён.`)) return
  for (const a of articles.value.filter(a => a.catalog === cat))
    await articlesApi.update(a.id, buildFormData({ title: a.title, catalog: '', author_ids: a.authors.map(x => x.id) }))
  catalogs.value = catalogs.value.filter(c => c !== cat)
  if (activeCatalog.value === cat) activeCatalog.value = ''
  await load()
  toast.success(`Каталог «${cat}» удалён`)
}

function openContextMenu(cat, e) { contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, catalog: cat } }
function closeContextMenu() { contextMenu.value.visible = false }

// ── Drag & drop ──────────────────────────────────────────────────────────────
function dragStart(article, e) { draggingArticle.value = article; e.dataTransfer.effectAllowed = 'move' }
function dragEnd() { draggingArticle.value = null; dragOverCatalog.value = null }
async function dropOnCatalog(catName, e) {
  e.preventDefault(); dragOverCatalog.value = null
  const a = draggingArticle.value; if (!a) return
  const newCatalog = catName === '__none__' ? '' : (catName || '')
  if (a.catalog === newCatalog) return
  await articlesApi.update(a.id, buildFormData({ title: a.title, catalog: newCatalog, author_ids: a.authors.map(x => x.id) }))
  await load()
  toast.success(newCatalog ? `Перемещено в «${newCatalog}»` : 'Каталог откреплён')
}

// ── Detail ───────────────────────────────────────────────────────────────────
function openDetail(a) {
  detailArticle.value = a
  detailPreview.value = false
  detailPreviewHtml.value = ''
  detailPreviewError.value = ''
  showDetail.value = true
}

// ── CRUD ─────────────────────────────────────────────────────────────────────
function openCreate() {
  editing.value = null
  form.value = { title: '', article_type: '', collection_id: '', catalog: activeCatalog.value !== '' && activeCatalog.value !== '__none__' ? activeCatalog.value : '', author_ids: [], lead_author_id: '', file: null }
  showModal.value = true
}
function openEdit(a) {
  editing.value = a
  form.value = { title: a.title, article_type: a.article_type || '', collection_id: a.collection_id || '', catalog: a.catalog || '', author_ids: a.authors.map(x => x.id), lead_author_id: a.lead_author_id || '', file: null }
  showModal.value = true
}
function openConclusion(a) {
  conclusionArticle.value = a
  conclusionForm.value = { file: null, notes: '', template_id: '' }
  conclusionMode.value = 'auto'
  showConclusionModal.value = true
}

async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const fd = buildFormData({ title: form.value.title, article_type: form.value.article_type || undefined, collection_id: form.value.collection_id || undefined, catalog: form.value.catalog || undefined, author_ids: form.value.author_ids, lead_author_id: form.value.lead_author_id || undefined, file: form.value.file })
    if (editing.value) { await articlesApi.update(editing.value.id, fd); toast.success('Статья обновлена') }
    else { await articlesApi.create(fd); toast.success('Статья добавлена') }
    showModal.value = false; await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}

async function saveConclusion() {
  savingConclusion.value = true
  try {
    if (conclusionMode.value === 'auto') {
      // Pass selected template_id if chosen
      const templateId = conclusionForm.value.template_id || undefined
      await articlesApi.generateConclusion(conclusionArticle.value.id, templateId)
      toast.success('Заключение сгенерировано')
    } else {
      if (!conclusionForm.value.file) return toast.error('Выберите файл')
      await articlesApi.uploadConclusion(
        conclusionArticle.value.id,
        buildFormData({ notes: conclusionForm.value.notes, file: conclusionForm.value.file })
      )
      toast.success('Заключение прикреплено')
    }
    showConclusionModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
  finally { savingConclusion.value = false }
}

async function confirmDelete(a) {
  if (!confirm(`Удалить статью «${a.title}»?`)) return
  try { await articlesApi.delete(a.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}

const loadError = ref('')

async function load() {
  loadError.value = ''
  try {
    const [art, col, auth, tmpl] = await Promise.all([
      articlesApi.list(),
      collectionsApi.list(),
      authorsApi.list(),
      templatesApi.list(),
    ])
    articles.value = art.data
    collections.value = col.data
    authors.value = auth.data
    conclusionTemplates.value = tmpl.data.filter(t => t.doc_type === 'conclusion')
    syncCatalogsFromData(art.data)
  } catch (e) {
    loadError.value = e.message || 'Ошибка загрузки данных'
    toast.error('Ошибка загрузки: ' + loadError.value)
  }
}

onMounted(load)
</script>

<style scoped>
.load-error-banner {
  background: rgba(239,68,68,0.12);
  border: 1px solid rgba(239,68,68,0.3);
  color: var(--c-red);
  border-radius: var(--radius);
  padding: 10px 14px;
  margin-bottom: 16px;
  display: flex; align-items: center; gap: 12px; font-size: 13px;
}
.layout-with-sidebar { display: grid; grid-template-columns: 220px 1fr; gap: 16px; align-items: start; position: relative; }
.catalog-sidebar { background: var(--c-bg2); border: 1px solid var(--c-border); border-radius: var(--radius); padding: 10px 8px; position: sticky; top: 16px; }
.catalog-sidebar__head { display: flex; align-items: center; justify-content: space-between; padding: 0 4px 8px; border-bottom: 1px solid var(--c-border); margin-bottom: 6px; }
.catalog-sidebar__title { font-size: 12px; font-weight: 600; color: var(--c-text2); text-transform: uppercase; letter-spacing: 0.04em; }
.catalog-item { display: flex; align-items: center; gap: 7px; padding: 7px 8px; border-radius: 7px; cursor: pointer; font-size: 13px; transition: background 0.15s; border: 1px solid transparent; margin-bottom: 2px; user-select: none; }
.catalog-item:hover { background: var(--c-bg3); }
.catalog-item.active { background: rgba(79,124,255,0.12); color: var(--c-accent); border-color: rgba(79,124,255,0.25); }
.catalog-item__icon { font-size: 14px; flex-shrink: 0; }
.catalog-item__name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.catalog-item__count { font-size: 11px; color: var(--c-text3); background: var(--c-bg3); padding: 1px 6px; border-radius: 10px; }
.catalog-new-input { padding: 6px 4px; }
.input-sm { height: 30px; font-size: 12px; padding: 4px 8px; }
.context-menu { position: fixed; z-index: 9999; background: var(--c-surface); border: 1px solid var(--c-border2); border-radius: var(--radius); padding: 4px; min-width: 190px; box-shadow: 0 8px 24px rgba(0,0,0,0.4); }
.context-menu__item { padding: 8px 12px; font-size: 13px; border-radius: 6px; cursor: pointer; color: var(--c-text); }
.context-menu__item:hover { background: var(--c-bg3); }
.context-menu__item--danger { color: var(--c-red); }
.context-menu__item--new { color: var(--c-accent); }
.context-menu__divider { height: 1px; background: var(--c-border); margin: 4px 0; }
.catalog-content { min-width: 0; }
.table-row-clickable { cursor: pointer; }
.table-row-clickable:hover td { background: var(--c-bg3); }
.text-mono { font-family: var(--font-mono); }
.compress-badge { font-size:10px; background:rgba(34,211,160,0.15); color:var(--c-green); padding:1px 5px; border-radius:4px; font-family:var(--font-mono); }

/* ── Detail v2 ── */
.modal-detail-v2 {
  max-width: 1100px;
  width: 96vw;
  max-height: 88vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}
.detail-v2-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px 14px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg3);
  flex-shrink: 0;
}
.detail-v2-header__left { display: flex; flex-direction: column; gap: 6px; min-width: 0; flex: 1; }
.detail-v2-header__actions { display: flex; gap: 6px; flex-shrink: 0; align-items: center; }
.detail-v2-badge { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; background: rgba(79,124,255,0.15); color: var(--c-accent); border: 1px solid rgba(79,124,255,0.3); border-radius: 5px; padding: 2px 8px; width: fit-content; }
.detail-v2-title { font-size: 15px; font-weight: 600; line-height: 1.4; color: var(--c-text); }

.detail-v2-body {
  display: grid;
  grid-template-columns: 320px 1fr;
  flex: 1;
  overflow: hidden;
}

.detail-v2-meta {
  overflow-y: auto;
  padding: 16px 18px;
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  gap: 0;
}
.detail-v2-section {
  padding: 12px 0;
  border-bottom: 1px solid var(--c-border);
}
.detail-v2-section:last-child { border-bottom: none; }
.detail-v2-label {
  font-size: 10px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.07em;
  color: var(--c-text3);
  margin-bottom: 7px;
}
.detail-v2-val { font-size: 13px; color: var(--c-text); }
.detail-v2-authors { display: flex; flex-direction: column; gap: 5px; }
.author-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  background: var(--c-bg3);
  border: 1px solid var(--c-border);
  border-radius: 6px;
  padding: 4px 10px;
  font-size: 12px;
  color: var(--c-text);
}
.author-chip--lead {
  background: rgba(79,124,255,0.12);
  border-color: rgba(79,124,255,0.3);
  color: var(--c-accent);
}
.lead-star { font-size: 10px; color: var(--c-amber); }
.detail-v2-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0;
  border-top: 1px solid var(--c-border);
}
.detail-v2-cell {
  padding: 10px 0;
  border-bottom: 1px solid var(--c-border);
}
.detail-v2-cell:nth-child(odd) { padding-right: 12px; border-right: 1px solid var(--c-border); }
.detail-v2-cell:nth-child(even) { padding-left: 12px; }
.detail-v2-cell:last-child:nth-child(odd) { grid-column: span 2; border-right: none; }

.detail-v2-file {
  display: flex;
  align-items: center;
  gap: 10px;
  background: var(--c-bg3);
  border: 1px solid var(--c-border);
  border-radius: 8px;
  padding: 10px 12px;
}
.detail-v2-file__icon { font-size: 22px; flex-shrink: 0; }
.detail-v2-file__info { flex: 1; min-width: 0; }
.detail-v2-file__name { font-size: 12px; font-weight: 500; word-break: break-all; color: var(--c-text); }
.detail-v2-file__actions { display: flex; gap: 4px; flex-shrink: 0; }
.btn-active { background: var(--c-surface) !important; color: var(--c-accent) !important; border-color: var(--c-accent) !important; }

.detail-v2-conclusion { padding: 4px 0; }
.detail-v2-conclusion--ok {}

/* Right panel: preview */
.detail-v2-preview {
  overflow: hidden;
  display: flex;
  flex-direction: column;
  background: #e8e8e8;
  position: relative;
}
.detail-v2-preview__empty {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: var(--c-bg2);
  color: var(--c-text);
  padding: 40px;
  text-align: center;
  height: 100%;
}
.detail-v2-preview__frame {
  width: 100%;
  height: 100%;
  border: none;
  display: block;
  flex: 1;
}
.detail-preview-spinner {
  width: 32px; height: 32px;
  border: 3px solid var(--c-border2);
  border-top-color: var(--c-accent);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }

/* Conclusion */
.tag-lead { background: rgba(79,124,255,0.18); border-color: rgba(79,124,255,0.4); color: var(--c-accent); }
.lead-badge { font-size: 10px; font-weight: 700; margin-left: 4px; opacity: 0.8; }
.template-link { color: var(--c-accent); text-decoration: underline; text-underline-offset: 2px; cursor: pointer; }
.template-link:hover { opacity: 0.8; }
.conclusion-tabs { display: flex; gap: 0; border: 1px solid var(--c-border); border-radius: var(--radius); overflow: hidden; margin-bottom: 20px; }
.conclusion-tab { flex: 1; padding: 9px 12px; background: var(--c-bg3); color: var(--c-text2); border: none; cursor: pointer; font-size: 13px; font-family: var(--font); font-weight: 500; transition: background 0.15s, color 0.15s; }
.conclusion-tab:first-child { border-right: 1px solid var(--c-border); }
.conclusion-tab.active { background: var(--c-accent); color: #fff; }
.conclusion-tab:not(.active):hover { background: var(--c-surface); color: var(--c-text); }
.conclusion-mode-body { min-height: 120px; }
.auto-preview-box { background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: var(--radius); padding: 14px 16px; }
.auto-preview-box__title { font-size: 13px; font-weight: 600; margin-bottom: 12px; color: var(--c-text); }
.auto-preview-row { display: flex; gap: 12px; padding: 8px 0; border-bottom: 1px solid var(--c-border); font-size: 13px; }
.auto-preview-row:last-child { border-bottom: none; }
.auto-preview-label { flex-shrink: 0; width: 130px; color: var(--c-text3); font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.04em; padding-top: 2px; }
.auto-preview-value { flex: 1; color: var(--c-text); line-height: 1.5; }
.select-sm { padding: 5px 8px; font-size: 12px; height: 32px; }

@media (max-width: 1000px) {
  .detail-v2-body { grid-template-columns: 1fr; }
  .detail-v2-meta { border-right: none; border-bottom: 1px solid var(--c-border); max-height: 40vh; }
  .detail-v2-preview { min-height: 300px; }
  .layout-with-sidebar { grid-template-columns: 1fr; }
  .catalog-sidebar { position: static; }
}
</style>
