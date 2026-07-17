<template>
  <div class="page" @click="closeContextMenu">
    <div class="page-header">
      <h1><span class="page-title-icon">💾</span> Программное обеспечение</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить ПО</button>
    </div>

    <div class="search-bar">
      <span>🔍</span>
      <input v-model="search" placeholder="Поиск по названию или автору..." />
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
          <span class="catalog-item__icon">📋</span><span class="catalog-item__name">Всё ПО</span>
          <span class="catalog-item__count">{{ software.length }}</span>
        </div>
        <div class="catalog-item" :class="{ active: activeCatalog === '__none__' }"
          @click.stop="activeCatalog = '__none__'"
          @dragover.prevent="dragOverCatalog = '__none__'" @dragleave="dragOverCatalog = null"
          @drop.stop="dropOnCatalog('__none__', $event)"
          :style="dragOverCatalog==='__none__'?'background:var(--c-surface);':''">
          <span class="catalog-item__icon">📂</span><span class="catalog-item__name">Без каталога</span>
          <span class="catalog-item__count">{{ software.filter(s => !s.catalog).length }}</span>
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
          <span class="catalog-item__count">{{ software.filter(s => s.catalog === cat).length }}</span>
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
                <tr><th>Название</th><th>Авторы</th><th>Тип</th><th>Документы</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-if="filtered.length === 0">
                  <td colspan="5" style="text-align:center;padding:40px">
                    <div class="empty-state" style="padding:32px">
                      <div class="empty-state__icon">💾</div>
                      <div class="empty-state__text">ПО пока нет</div>
                    </div>
                  </td>
                </tr>
                <tr v-for="s in filtered" :key="s.id" class="table-row-clickable"
                  draggable="true" @dragstart="dragStart(s, $event)" @dragend="dragEnd"
                  @click="openDetail(s)">
                  <td style="max-width:280px">
                    <div class="truncate" style="font-weight:500">{{ s.title }}</div>
                    <div v-if="s.catalog" class="text-muted" style="font-size:11px;margin-top:2px">📁 {{ s.catalog }}</div>
                  </td>
                  <td>
                    <div class="flex" style="flex-wrap:wrap;gap:4px">
                      <span v-for="au in s.authors" :key="au.id" class="tag">{{ au.short_name || au.full_name }}</span>
                    </div>
                  </td>
                  <td><span v-if="s.software_type" class="badge badge-teal">{{ s.software_type }}</span></td>
                  <td>
                    <div class="doc-chips">
                      <span v-for="dt in docTypes" :key="dt.key"
                        class="doc-chip"
                        :class="getDoc(s, dt.key) ? 'doc-chip--ok' : 'doc-chip--miss'"
                        :title="dt.label">{{ dt.icon }}</span>
                    </div>
                  </td>
                  <td @click.stop>
                    <div class="flex-center gap-2">
                      <button class="btn btn-ghost btn-sm btn-icon" @click.stop="openEdit(s)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" @click.stop="del(s)">🗑</button>
                    </div>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>
      </div>
    </div>

    <!-- ── Detail Modal ── -->
    <Transition name="fade">
      <div v-if="showDetail" class="modal-overlay" @click.self="showDetail=false">
        <div class="modal modal-detail-sw">
          <div class="detail-sw-header">
            <div class="detail-sw-header__left">
              <span class="detail-sw-badge" v-if="detailSw?.software_type">{{ detailSw.software_type }}</span>
              <h2 class="detail-sw-title">{{ detailSw?.title }}</h2>
            </div>
            <div class="detail-sw-header__actions">
              <button class="btn btn-ghost btn-sm" @click="showDetail=false; openEdit(detailSw)">✏️ Редактировать</button>
              <button class="btn btn-ghost btn-sm btn-icon" @click="showDetail=false">✕</button>
            </div>
          </div>

          <div class="detail-sw-body">
            <!-- LEFT: meta -->
            <div class="detail-sw-meta">
              <div class="detail-sw-section">
                <div class="detail-sw-label">Авторы</div>
                <div v-if="detailSw?.authors?.length" style="display:flex;flex-direction:column;gap:4px">
                  <span v-for="au in detailSw.authors" :key="au.id" class="author-chip">{{ au.full_name }}</span>
                </div>
                <span v-else class="text-muted text-sm">—</span>
              </div>
              <div class="detail-sw-section">
                <div class="detail-sw-label">Дата добавления</div>
                <div class="detail-sw-val">{{ detailSw ? formatDate(detailSw.created_at) : '—' }}</div>
              </div>
              <div class="detail-sw-section" v-if="detailSw?.catalog">
                <div class="detail-sw-label">Каталог</div>
                <div class="detail-sw-val text-mono" style="font-size:11px">{{ detailSw.catalog }}</div>
              </div>
              <div class="detail-sw-section">
                <div class="detail-sw-label">ZIP-архив</div>
                <div v-if="detailSw?.original_filename" class="sw-file-block">
                  <span style="font-size:18px">🗜</span>
                  <div style="flex:1;min-width:0">
                    <div style="font-size:12px;font-weight:500;word-break:break-all">{{ detailSw.original_filename }}</div>
                    <div v-if="ratio(detailSw)" class="compress-badge" style="margin-top:2px">{{ ratio(detailSw) }}</div>
                  </div>
                  <div style="display:flex;gap:4px">
                    <a :href="downloadUrl(detailSw.id)" class="btn btn-ghost btn-sm" download>↓</a>
                    <button class="btn btn-ghost btn-sm" @click="showDetail=false; openViewer(detailSw)">🗂</button>
                  </div>
                </div>
                <div v-else class="text-muted text-sm">Не прикреплён</div>
              </div>

              <!-- Document checklist -->
              <div class="detail-sw-section">
                <div class="detail-sw-label detail-sw-label--toggle" @click="docListOpen = !docListOpen" style="margin-bottom:6px;cursor:pointer;user-select:none;display:flex;align-items:center;justify-content:space-between">
                  <span>Комплект документов</span>
                  <span style="display:flex;align-items:center;gap:6px">
                    <span class="doc-count-badge">{{ detailSw?.documents?.length || 0 }}/8</span>
                    <span style="font-size:11px;transition:transform 0.2s" :style="docListOpen ? 'transform:rotate(180deg)' : ''">▼</span>
                  </span>
                </div>
                <Transition name="doc-list">
                  <div v-show="docListOpen" class="sw-doc-checklist">
                    <div v-for="dt in docTypes" :key="dt.key"
                      class="sw-doc-row"
                      :class="{ 'sw-doc-row--active': docPreviewKey === dt.key && getDoc(detailSw, dt.key), 'sw-doc-row--clickable': !!getDoc(detailSw, dt.key) }"
                      @click="getDoc(detailSw, dt.key) && openDocPreview(dt.key)">
                      <span class="sw-doc-row__icon">{{ dt.icon }}</span>
                      <span class="sw-doc-row__label">{{ dt.label }}</span>
                      <div style="display:flex;align-items:center;gap:4px">
                        <a v-if="getDoc(detailSw, dt.key)"
                          :href="softwareApi.downloadDoc(detailSw.id, getDoc(detailSw, dt.key).id)"
                          class="btn btn-ghost btn-sm btn-icon doc-row-action"
                          title="Скачать" @click.stop download>↓</a>
                        <span v-if="getDoc(detailSw, dt.key)" class="sw-doc-row__status sw-doc-row__status--ok">✓</span>
                        <span v-else class="sw-doc-row__status sw-doc-row__status--miss">—</span>
                      </div>
                    </div>
                  </div>
                </Transition>
                <button class="btn btn-ghost btn-sm" style="margin-top:8px;width:100%" @click="showDetail=false; openDocs(detailSw)">
                  📋 Управлять документами
                </button>
              </div>
            </div>

            <!-- RIGHT: doc preview -->
            <div class="detail-sw-preview">
              <div v-if="!docPreviewKey" class="detail-sw-preview__empty">
                <div style="font-size:36px;margin-bottom:10px">📂</div>
                <div style="font-weight:500;margin-bottom:6px;font-size:13px">Предпросмотр документов</div>
                <div class="text-muted text-sm">Выберите документ из списка слева</div>
              </div>
              <div v-else-if="docPreviewLoading" class="detail-sw-preview__empty">
                <div class="detail-preview-spinner"></div>
                <div class="text-muted text-sm" style="margin-top:12px">Загрузка...</div>
              </div>
              <div v-else-if="docPreviewError" class="detail-sw-preview__empty">
                <div style="font-size:32px;margin-bottom:10px">⚠️</div>
                <div class="text-muted text-sm">{{ docPreviewError }}</div>
                <a v-if="docPreviewDoc" :href="softwareApi.downloadDoc(detailSw.id, docPreviewDoc.id)"
                  class="btn btn-ghost btn-sm" style="margin-top:10px" download>↓ Скачать</a>
              </div>
              <template v-else-if="docPreviewDoc">
                <!-- Preview toolbar -->
                <div class="doc-preview-toolbar">
                  <span style="font-size:16px">{{ docTypeMap[docPreviewKey]?.icon }}</span>
                  <span style="font-size:13px;font-weight:500;flex:1">{{ docTypeMap[docPreviewKey]?.label }}</span>
                  <span class="text-muted text-sm">{{ docPreviewDoc.original_filename }}</span>
                  <a :href="softwareApi.downloadDoc(detailSw.id, docPreviewDoc.id)"
                    class="btn btn-ghost btn-sm" download>↓ Скачать</a>
                  <button class="btn btn-ghost btn-sm btn-icon" @click="closeDocPreview">✕</button>
                </div>
                <!-- PDF — iframe через /preview endpoint (backend отдаёт inline PDF) -->
                <iframe v-if="isPdf(docPreviewDoc.original_filename)"
                  :src="softwareApi.downloadDoc(detailSw.id, docPreviewDoc.id) + '?inline=1'"
                  class="detail-sw-preview__frame"
                  title="PDF preview">
                </iframe>
                <!-- DOCX / DOC rendered as HTML -->
                <iframe v-else-if="docPreviewHtml"
                  :srcdoc="docPreviewHtml"
                  class="detail-sw-preview__frame"
                  sandbox="allow-same-origin"
                  title="Document preview">
                </iframe>
                <!-- DOC/DOCX loading (no html yet but key is set) -->
                <div v-else class="detail-sw-preview__empty">
                  <div class="detail-preview-spinner"></div>
                  <div class="text-muted text-sm" style="margin-top:12px">Загрузка документа...</div>
                </div>
              </template>
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
            <h2>{{ editing ? 'Редактировать ПО' : 'Добавить ПО' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.title" placeholder="Название программы" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Тип ПО</label>
              <select class="select" v-model="form.software_type">
                <option value="">— выбрать —</option>
                <option>Прикладное</option><option>Системное</option>
                <option>Веб-приложение</option><option>Мобильное</option>
                <option>Библиотека</option><option>Прочее</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Каталог хранения</label>
              <div style="display:flex;gap:8px">
                <input class="input" v-model="form.catalog" placeholder="/software/2024" />
                <select v-if="catalogs.length" class="select" style="width:160px" @change="e => { if(e.target.value) form.catalog = e.target.value }">
                  <option value="">📁 Каталоги</option>
                  <option v-for="c in catalogs" :key="c" :value="c">{{ c }}</option>
                </select>
              </div>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Авторы</label>
            <AuthorPicker v-model="form.author_ids" :all-authors="authors" @created="authors.push($event)" />
          </div>
          <div class="form-group">
            <label class="form-label">ZIP-архив</label>
            <FileUpload v-model="form.file" accept=".zip" icon="🗜"
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

    <!-- ── ZIP Viewer Modal ── -->
    <Transition name="fade">
      <div v-if="showViewer" class="modal-overlay" @click.self="showViewer=false">
        <div class="modal modal-wide">
          <div class="modal-header">
            <h2>🗂 Структура: {{ viewerSw?.title }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showViewer=false">✕</button>
          </div>
          <div style="display:grid;grid-template-columns:260px 1fr;gap:16px;height:460px">
            <div style="overflow-y:auto;border:1px solid var(--c-border);border-radius:var(--radius);padding:8px">
              <FileTree :nodes="viewerTree" @select="loadFileContent" />
            </div>
            <div style="overflow:auto;background:var(--c-bg3);border-radius:var(--radius);padding:12px">
              <div v-if="!fileContent && !loadingContent" class="text-muted text-sm" style="padding:16px">Выберите файл в дереве слева</div>
              <div v-if="loadingContent" class="text-muted text-sm" style="padding:16px">Загрузка...</div>
              <pre v-if="fileContent" style="font-family:var(--font-mono);font-size:12px;white-space:pre-wrap;color:var(--c-text)">{{ fileContent }}</pre>
            </div>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Documents Modal (with inline preview) ── -->
    <Transition name="fade">
      <div v-if="showDocsModal" class="modal-overlay" @click.self="showDocsModal=false">
        <div class="modal modal-docs">
          <div class="modal-header">
            <h2>📋 Документы ПО: {{ docsSw?.title }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showDocsModal=false">✕</button>
          </div>

          <div class="docs-layout">
            <!-- Doc list -->
            <div class="docs-list">
              <div v-for="dt in docTypes" :key="dt.key"
                class="doc-item-v2"
                :class="{ 'doc-item-v2--active': activeDocKey === dt.key }"
                @click="selectDocItem(dt.key)">
                <div class="doc-item-v2__header">
                  <span class="doc-item-v2__icon">{{ dt.icon }}</span>
                  <div class="doc-item-v2__info">
                    <div class="doc-item-v2__name">{{ dt.label }}</div>
                    <div v-if="getDoc(docsSw, dt.key)" class="doc-item-v2__file text-muted">
                      {{ getDoc(docsSw, dt.key).original_filename }}
                    </div>
                    <div v-else class="doc-item-v2__file text-muted">Не загружен</div>
                  </div>
                  <span v-if="getDoc(docsSw, dt.key)" class="doc-status doc-status--ok">✓</span>
                  <span v-else class="doc-status doc-status--miss">—</span>
                </div>
                <!-- Actions shown only for selected item -->
                <Transition name="doc-actions">
                  <div v-if="activeDocKey === dt.key" class="doc-item-v2__actions" @click.stop>
                    <div class="doc-item-v2__actions-row">
                      <label class="btn btn-ghost btn-sm doc-action-btn" style="cursor:pointer" title="Загрузить файл">
                        {{ getDoc(docsSw, dt.key) ? '↑ Заменить' : '+ Загрузить' }}
                        <input type="file" style="display:none" accept=".pdf,.doc,.docx" @change="uploadDoc(dt.key, $event)" />
                      </label>
                      <a v-if="getDoc(docsSw, dt.key)"
                        :href="softwareApi.downloadDoc(docsSw.id, getDoc(docsSw, dt.key).id)"
                        class="btn btn-ghost btn-sm doc-action-btn" download title="Скачать">↓ Скачать</a>
                    </div>
                    <div v-if="getDoc(docsSw, dt.key)" class="doc-item-v2__actions-row">
                      <button
                        class="btn btn-ghost btn-sm doc-action-btn"
                        :class="modalPreviewKey === dt.key ? 'btn-active' : ''"
                        @click="openModalDocPreview(dt.key)" title="Предпросмотр">👁 Просмотр</button>
                      <button
                        class="btn btn-danger btn-sm doc-action-btn" @click="deleteDoc(getDoc(docsSw, dt.key).id)" title="Удалить">🗑 Удалить</button>
                    </div>
                  </div>
                </Transition>
              </div>
            </div>

            <!-- Preview pane -->
            <div class="docs-preview-pane">
              <div v-if="!modalPreviewKey" class="docs-preview-empty">
                <div style="font-size:36px;margin-bottom:10px">👁</div>
                <div style="font-weight:500;margin-bottom:6px;font-size:13px">Предпросмотр</div>
                <div class="text-muted text-sm">Нажмите 👁 у документа</div>
              </div>
              <div v-else-if="modalPreviewLoading" class="docs-preview-empty">
                <div class="detail-preview-spinner"></div>
                <div class="text-muted text-sm" style="margin-top:12px">Загрузка...</div>
              </div>
              <div v-else-if="modalPreviewError" class="docs-preview-empty">
                <div style="font-size:32px;margin-bottom:10px">⚠️</div>
                <div class="text-muted text-sm">{{ modalPreviewError }}</div>
              </div>
              <template v-else-if="modalPreviewDoc">
                <div class="docs-preview-header">
                  <span>{{ docTypeMap[modalPreviewKey]?.icon }}</span>
                  <span style="font-size:12px;flex:1;font-weight:500">{{ docTypeMap[modalPreviewKey]?.label }}</span>
                  <a :href="softwareApi.downloadDoc(docsSw.id, modalPreviewDoc.id)"
                    class="btn btn-ghost btn-sm" download>↓</a>
                  <button class="btn btn-ghost btn-sm btn-icon" @click="closeModalPreview">✕</button>
                </div>
                <!-- PDF — iframe через /preview endpoint -->
                <iframe v-if="isPdf(modalPreviewDoc.original_filename)"
                  :src="softwareApi.downloadDoc(docsSw.id, modalPreviewDoc.id) + '?inline=1'"
                  class="docs-preview-frame"
                  title="PDF preview">
                </iframe>
                <!-- DOCX / DOC rendered as HTML -->
                <iframe v-else-if="modalPreviewHtml"
                  :srcdoc="modalPreviewHtml"
                  class="docs-preview-frame"
                  sandbox="allow-same-origin"
                  title="Document preview">
                </iframe>
                <!-- loading fallback -->
                <div v-else class="docs-preview-empty">
                  <div class="detail-preview-spinner"></div>
                  <div class="text-muted text-sm" style="margin-top:12px">Загрузка документа...</div>
                </div>
              </template>
            </div>
          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showDocsModal=false">Закрыть</button>
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
import { softwareApi, authorsApi, buildFormData, formatBytes } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'
import FileTree from '@/components/common/FileTree.vue'

const toast = useToast()
const software = ref([])
const authors = ref([])
const search = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ title: '', software_type: '', catalog: '', author_ids: [], file: null })

const showDetail = ref(false)
const detailSw = ref(null)
const docPreviewKey = ref('')
const docListOpen = ref(true)
const docPreviewLoading = ref(false)
const docPreviewHtml = ref('')
const docPreviewError = ref('')
const docPreviewDoc = computed(() => getDoc(detailSw.value, docPreviewKey.value))

const showViewer = ref(false)
const viewerSw = ref(null)
const viewerTree = ref([])
const fileContent = ref('')
const loadingContent = ref(false)

const showDocsModal = ref(false)
const docsSw = ref(null)
const modalPreviewKey = ref('')
const activeDocKey = ref('')
const modalPreviewLoading = ref(false)
const modalPreviewHtml = ref('')
const modalPreviewError = ref('')
const modalPreviewDoc = computed(() => getDoc(docsSw.value, modalPreviewKey.value))

const catalogs = ref([])
const activeCatalog = ref('')
const creatingCatalog = ref(false)
const newCatalogName = ref('')
const newCatalogInput = ref(null)
const renamingCatalog = ref(null)
const renameValue = ref('')
const renameInputs = ref({})
const dragOverCatalog = ref(null)
const draggingSw = ref(null)
const contextMenu = ref({ visible: false, x: 0, y: 0, catalog: '' })

const docTypes = [
  { key: 'annotation',   label: 'Аннотация программы',              icon: '📝' },
  { key: 'registration', label: 'Заявление на регистрацию',          icon: '📋' },
  { key: 'description',  label: 'Описание программы',                icon: '📖' },
  { key: 'manual',       label: 'Руководство пользователя',          icon: '📗' },
  { key: 'act',          label: 'Акт приёма и ввода в эксплуатацию', icon: '✅' },
  { key: 'abstract',     label: 'Реферат по исходникам',             icon: '📄' },
  { key: 'listing',      label: 'Листинг по исходникам',             icon: '💻' },
  { key: 'certificate',  label: 'Свидетельство',                     icon: '🏆' },
]

const docTypeMap = computed(() => Object.fromEntries(docTypes.map(d => [d.key, d])))

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  let list = software.value.filter(s =>
    s.title.toLowerCase().includes(q) || s.authors.some(a => a.full_name.toLowerCase().includes(q))
  )
  if (activeCatalog.value === '__none__') list = list.filter(s => !s.catalog)
  else if (activeCatalog.value !== '') list = list.filter(s => s.catalog === activeCatalog.value)
  return list
})

const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''
const downloadUrl = id => softwareApi.download(id)
const ratio = s => {
  if (!s.file_size_original || !s.file_size_compressed) return null
  const v = ((1 - s.file_size_compressed / s.file_size_original) * 100).toFixed(0)
  return v > 2 ? `-${v}%` : null
}
const getDoc = (sw, key) => sw?.documents?.find(d => d.doc_type === key)
const isPdf = name => name?.toLowerCase().endsWith('.pdf')

// ── Doc preview helpers ──────────────────────────────────────────────────────
// Все файлы, кроме PDF, загружаем через /preview (бэкенд сам вернёт HTML или
// страницу "Предпросмотр недоступен" для .doc и прочих форматов).
// PDF рендерим напрямую через /download?inline=1 в <iframe>.

async function fetchDocHtml(swId, docId) {
  const url = softwareApi.previewDoc(swId, docId)
  const resp = await fetch(url)
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`)
  return resp.text()
}

async function _loadPreview({ swId, docId, filename, setKey, setLoading, setHtml, setError }) {
  if (isPdf(filename)) { setKey(); return }
  setLoading(true)
  setHtml('')
  setError('')
  try {
    setHtml(await fetchDocHtml(swId, docId))
  } catch (e) {
    setError(`Ошибка загрузки: ${e.message}`)
  } finally {
    setLoading(false)
  }
}

async function openDocPreview(key) {
  if (docPreviewKey.value === key) { closeDocPreview(); return }
  const doc = getDoc(detailSw.value, key)
  if (!doc) return
  docPreviewKey.value = key
  await _loadPreview({
    swId: detailSw.value.id, docId: doc.id, filename: doc.original_filename,
    setKey: () => {}, // PDF: key already set, nothing extra needed
    setLoading: v => { docPreviewLoading.value = v },
    setHtml: v => { docPreviewHtml.value = v },
    setError: v => { docPreviewError.value = v },
  })
}

function closeDocPreview() {
  docPreviewKey.value = ''
  docPreviewHtml.value = ''
  docPreviewError.value = ''
}

function selectDocItem(key) {
  if (activeDocKey.value === key) {
    activeDocKey.value = ''
    closeModalPreview()
  } else {
    activeDocKey.value = key
    const doc = getDoc(docsSw.value, key)
    if (doc) openModalDocPreview(key)
    else closeModalPreview()
  }
}

async function openModalDocPreview(key) {
  if (modalPreviewKey.value === key) { closeModalPreview(); return }
  const doc = getDoc(docsSw.value, key)
  if (!doc) return
  modalPreviewKey.value = key
  await _loadPreview({
    swId: docsSw.value.id, docId: doc.id, filename: doc.original_filename,
    setKey: () => {},
    setLoading: v => { modalPreviewLoading.value = v },
    setHtml: v => { modalPreviewHtml.value = v },
    setError: v => { modalPreviewError.value = v },
  })
}

function closeModalPreview() {
  modalPreviewKey.value = ''
  modalPreviewHtml.value = ''
  modalPreviewError.value = ''
}

// ── Catalog management ───────────────────────────────────────────────────────
function syncCatalogsFromData(list) {
  list.filter(s => s.catalog).forEach(s => { if (!catalogs.value.includes(s.catalog)) catalogs.value.push(s.catalog) })
  catalogs.value.sort()
}
function startCreateCatalog() { contextMenu.value.visible = false; creatingCatalog.value = true; newCatalogName.value = ''; nextTick(() => newCatalogInput.value?.focus()) }
function startCreateCatalogFromMenu() { contextMenu.value.visible = false; startCreateCatalog() }
async function confirmCreateCatalog() {
  const name = newCatalogName.value.trim(); creatingCatalog.value = false; if (!name) return
  if (!catalogs.value.includes(name)) { catalogs.value.push(name); catalogs.value.sort() }
  activeCatalog.value = name; toast.success(`Каталог «${name}» создан`)
}
function startRenameCatalog(cat) { contextMenu.value.visible = false; renamingCatalog.value = cat; renameValue.value = cat; nextTick(() => renameInputs.value[cat]?.focus()) }
async function confirmRename(oldName) {
  const newName = renameValue.value.trim(); renamingCatalog.value = null; if (!newName || newName === oldName) return
  for (const s of software.value.filter(s => s.catalog === oldName))
    await softwareApi.update(s.id, buildFormData({ title: s.title, catalog: newName, author_ids: s.authors.map(x => x.id) }))
  const idx = catalogs.value.indexOf(oldName); if (idx !== -1) { catalogs.value[idx] = newName; catalogs.value.sort() }
  if (activeCatalog.value === oldName) activeCatalog.value = newName
  await load(); toast.success(`Переименовано в «${newName}»`)
}
async function deleteCatalog(cat) {
  contextMenu.value.visible = false
  if (!confirm(`Удалить каталог «${cat}»?\nУ всего ПО каталог будет откреплён.`)) return
  for (const s of software.value.filter(s => s.catalog === cat))
    await softwareApi.update(s.id, buildFormData({ title: s.title, catalog: '', author_ids: s.authors.map(x => x.id) }))
  catalogs.value = catalogs.value.filter(c => c !== cat)
  if (activeCatalog.value === cat) activeCatalog.value = ''
  await load(); toast.success(`Каталог «${cat}» удалён`)
}
function openContextMenu(cat, e) { contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, catalog: cat } }
function closeContextMenu() { contextMenu.value.visible = false }
function dragStart(s, e) { draggingSw.value = s; e.dataTransfer.effectAllowed = 'move' }
function dragEnd() { draggingSw.value = null; dragOverCatalog.value = null }
async function dropOnCatalog(catName, e) {
  e.preventDefault(); dragOverCatalog.value = null
  const s = draggingSw.value; if (!s) return
  const newCatalog = catName === '__none__' ? '' : (catName || '')
  if (s.catalog === newCatalog) return
  await softwareApi.update(s.id, buildFormData({ title: s.title, catalog: newCatalog, author_ids: s.authors.map(x => x.id) }))
  await load(); toast.success(newCatalog ? `Перемещено в «${newCatalog}»` : 'Каталог откреплён')
}

function openDetail(s) {
  detailSw.value = s
  docPreviewKey.value = ''
  docPreviewHtml.value = ''
  docPreviewError.value = ''
  docListOpen.value = true
  showDetail.value = true
}
function openCreate() {
  editing.value = null
  form.value = { title: '', software_type: '', catalog: activeCatalog.value !== '' && activeCatalog.value !== '__none__' ? activeCatalog.value : '', author_ids: [], file: null }
  showModal.value = true
}
function openEdit(s) { editing.value = s; form.value = { title: s.title, software_type: s.software_type || '', catalog: s.catalog || '', author_ids: s.authors.map(x => x.id), file: null }; showModal.value = true }
function openViewer(s) { viewerSw.value = s; viewerTree.value = s.file_structure || []; fileContent.value = ''; showViewer.value = true }
function openDocs(s) {
  docsSw.value = s
  modalPreviewKey.value = ''
  modalPreviewHtml.value = ''
  activeDocKey.value = ''
  showDocsModal.value = true
}

async function loadFileContent(path) {
  loadingContent.value = true; fileContent.value = ''
  try { const r = await softwareApi.fileContent(viewerSw.value.id, path); fileContent.value = r.data.content }
  catch (e) { fileContent.value = `Ошибка: ${e.message}` }
  finally { loadingContent.value = false }
}

async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const fd = buildFormData({ title: form.value.title, software_type: form.value.software_type || undefined, catalog: form.value.catalog || undefined, author_ids: form.value.author_ids, file: form.value.file })
    if (editing.value) { await softwareApi.update(editing.value.id, fd); toast.success('Обновлено') }
    else { await softwareApi.create(fd); toast.success('Добавлено') }
    showModal.value = false; await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}

async function del(s) {
  if (!confirm(`Удалить «${s.title}»?`)) return
  try { await softwareApi.delete(s.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}

async function uploadDoc(docType, event) {
  const file = event.target.files[0]; if (!file) return
  try {
    await softwareApi.uploadDoc(docsSw.value.id, buildFormData({ doc_type: docType, file }))
    toast.success('Документ загружен'); await load()
    docsSw.value = software.value.find(s => s.id === docsSw.value.id)
    // Auto-open preview for newly uploaded doc
    if (getDoc(docsSw.value, docType)) openModalDocPreview(docType)
  } catch (e) { toast.error(e.message) }
  event.target.value = ''
}

async function deleteDoc(docId) {
  if (!confirm('Удалить документ?')) return
  try {
    await softwareApi.deleteDoc(docsSw.value.id, docId)
    toast.success('Удалено'); await load()
    docsSw.value = software.value.find(s => s.id === docsSw.value.id)
    if (modalPreviewDoc.value?.id === docId) closeModalPreview()
    activeDocKey.value = ''
  } catch (e) { toast.error(e.message) }
}

async function load() {
  try {
    const [sw, au] = await Promise.all([softwareApi.list(), authorsApi.list()])
    software.value = sw.data; authors.value = au.data
    syncCatalogsFromData(sw.data)
  } catch (e) {
    console.error(e)
  }
}
onMounted(load)
</script>

<style scoped>
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
.doc-chips { display: flex; gap: 3px; flex-wrap: wrap; }
.doc-chip { font-size: 13px; opacity: 0.35; }
.doc-chip--ok { opacity: 1; }
.compress-badge { font-size:10px; background:rgba(34,211,160,0.15); color:var(--c-green); padding:1px 5px; border-radius:4px; font-family:var(--font-mono); }
.text-mono { font-family: var(--font-mono); }
.btn-active { background: var(--c-surface) !important; color: var(--c-accent) !important; border-color: var(--c-accent) !important; }

/* ── Detail SW ── */
.modal-detail-sw { max-width: 1100px; width: 96vw; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; }
.detail-sw-header { display: flex; align-items: flex-start; justify-content: space-between; gap: 16px; padding: 18px 20px 14px; border-bottom: 1px solid var(--c-border); background: var(--c-bg3); flex-shrink: 0; }
.detail-sw-header__left { display: flex; flex-direction: column; gap: 6px; min-width: 0; flex: 1; }
.detail-sw-header__actions { display: flex; gap: 6px; flex-shrink: 0; align-items: center; }
.detail-sw-badge { display: inline-block; font-size: 11px; font-weight: 700; letter-spacing: 0.05em; text-transform: uppercase; background: rgba(0,200,168,0.15); color: var(--c-teal); border: 1px solid rgba(0,200,168,0.3); border-radius: 5px; padding: 2px 8px; width: fit-content; }
.detail-sw-title { font-size: 15px; font-weight: 600; line-height: 1.4; color: var(--c-text); }
.detail-sw-body { display: grid; grid-template-columns: 300px 1fr; flex: 1; overflow: hidden; }
.detail-sw-meta { overflow-y: auto; padding: 16px 18px; border-right: 1px solid var(--c-border); display: flex; flex-direction: column; gap: 0; }
.detail-sw-section { padding: 12px 0; border-bottom: 1px solid var(--c-border); }
.detail-sw-section:last-child { border-bottom: none; }
.detail-sw-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.07em; color: var(--c-text3); margin-bottom: 7px; }
.detail-sw-val { font-size: 13px; color: var(--c-text); }
.author-chip { display: inline-flex; align-items: center; background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: 6px; padding: 4px 10px; font-size: 12px; color: var(--c-text); }
.sw-file-block { display: flex; align-items: center; gap: 10px; background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: 8px; padding: 10px 12px; }

/* checklist */
.sw-doc-checklist { display: flex; flex-direction: column; gap: 2px; }
.sw-doc-row { display: flex; align-items: center; gap: 8px; padding: 7px 8px; border-radius: 7px; border: 1px solid transparent; font-size: 12px; transition: background 0.12s; }
.sw-doc-row--clickable { cursor: pointer; }
.sw-doc-row--clickable:hover { background: var(--c-bg3); border-color: var(--c-border); }
.sw-doc-row--clickable:hover .doc-row-action { opacity: 1; }
.sw-doc-row:has(.sw-doc-row__status--ok) { cursor: pointer; }
.sw-doc-row:has(.sw-doc-row__status--ok):hover { background: var(--c-bg3); border-color: var(--c-border); }
.doc-row-action { opacity: 0; transition: opacity 0.15s; padding: 2px 5px; font-size: 12px; }
.doc-count-badge { font-size: 11px; background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: 10px; padding: 1px 7px; color: var(--c-text2); }
.doc-list-enter-active, .doc-list-leave-active { transition: max-height 0.25s ease, opacity 0.2s ease; overflow: hidden; max-height: 500px; }
.doc-list-enter-from, .doc-list-leave-to { max-height: 0; opacity: 0; }
.sw-doc-row--active { background: rgba(79,124,255,0.1) !important; border-color: rgba(79,124,255,0.25) !important; }
.sw-doc-row__icon { font-size: 14px; flex-shrink: 0; }
.sw-doc-row__label { flex: 1; color: var(--c-text2); }
.sw-doc-row__status { font-size: 11px; font-weight: 700; }
.sw-doc-row__status--ok { color: var(--c-green); }
.sw-doc-row__status--miss { color: var(--c-text3); }

/* Detail SW preview pane */
.detail-sw-preview { overflow: hidden; display: flex; flex-direction: column; background: #e8e8e8; position: relative; }
.detail-sw-preview__empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--c-bg2); color: var(--c-text); padding: 40px; text-align: center; height: 100%; }
.detail-sw-preview__frame { width: 100%; height: 100%; border: none; display: block; flex: 1; }
.doc-preview-toolbar { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--c-bg3); border-bottom: 1px solid var(--c-border); flex-shrink: 0; font-size: 13px; }
.detail-preview-spinner { width: 32px; height: 32px; border: 3px solid var(--c-border2); border-top-color: var(--c-accent); border-radius: 50%; animation: spin 0.8s linear infinite; }
@keyframes spin { to { transform: rotate(360deg); } }

/* ── Docs modal ── */
.modal-docs { max-width: 1050px; width: 96vw; max-height: 88vh; display: flex; flex-direction: column; overflow: hidden; }
.modal-docs .modal-header { flex-shrink: 0; }
.modal-docs .modal-footer { flex-shrink: 0; }
.docs-layout { display: grid; grid-template-columns: 380px 1fr; flex: 1; overflow: hidden; min-height: 0; }
.docs-list { overflow-y: auto; padding: 12px; display: flex; flex-direction: column; gap: 6px; border-right: 1px solid var(--c-border); min-height: 0; }
.doc-item-v2 { background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: var(--radius); transition: border-color 0.15s; }
.doc-item-v2--active { border-color: var(--c-accent); background: rgba(79,124,255,0.06); }
.doc-item-v2__header { display: flex; align-items: center; gap: 10px; padding: 10px 12px; cursor: pointer; border-radius: var(--radius) var(--radius) 0 0; }
.doc-item-v2__header:hover { background: rgba(255,255,255,0.03); }
.doc-item-v2__icon { font-size: 18px; flex-shrink: 0; }
.doc-item-v2__info { flex: 1; min-width: 0; }
.doc-item-v2__name { font-size: 12px; font-weight: 600; color: var(--c-text); }
.doc-item-v2__file { font-size: 11px; margin-top: 1px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.doc-status { font-size: 12px; font-weight: 700; flex-shrink: 0; }
.doc-status--ok { color: var(--c-green); }
.doc-status--miss { color: var(--c-text3); }
.doc-item-v2__actions { display: flex; flex-direction: column; gap: 6px; padding: 8px 10px 10px; border-top: 1px solid var(--c-border); background: rgba(79,124,255,0.04); box-sizing: border-box; width: 100%; border-radius: 0 0 var(--radius) var(--radius); }
.doc-item-v2__actions-row { display: flex; gap: 6px; width: 100%; }
.doc-action-btn { flex: 1 1 0; min-width: 0; white-space: nowrap; font-size: 12px; text-align: center; overflow: hidden; text-overflow: ellipsis; box-sizing: border-box; justify-content: center; }
.doc-actions-enter-active, .doc-actions-leave-active { transition: max-height 0.25s ease, opacity 0.2s ease; overflow: hidden; max-height: 160px; }
.doc-actions-enter-from, .doc-actions-leave-to { max-height: 0; opacity: 0; }

/* Preview pane in docs modal */
.docs-preview-pane { overflow: hidden; display: flex; flex-direction: column; background: #e8e8e8; }
.docs-preview-empty { flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; background: var(--c-bg2); color: var(--c-text); padding: 40px; text-align: center; height: 100%; }
.docs-preview-header { display: flex; align-items: center; gap: 8px; padding: 8px 12px; background: var(--c-bg3); border-bottom: 1px solid var(--c-border); flex-shrink: 0; font-size: 13px; }
.docs-preview-frame { width: 100%; flex: 1; border: none; display: block; min-height: 0; height: 100%; }

@media (max-width: 1000px) {
  /* Main table layout */
  .layout-with-sidebar { grid-template-columns: 1fr; }
  .catalog-sidebar { position: static; }

  /* Detail modal: stack meta above preview */
  .modal-detail-sw { max-width: 100vw; width: 100vw; max-height: 100vh; border-radius: 0; }
  .detail-sw-body { grid-template-columns: 1fr; }
  .detail-sw-meta { border-right: none; border-bottom: 1px solid var(--c-border); max-height: 40vh; overflow-y: auto; }
  .detail-sw-preview { min-height: 320px; }

  /* Docs modal: stack list above preview */
  .modal-docs { max-width: 100vw; width: 100vw; max-height: 100vh; border-radius: 0; }
  .docs-layout { grid-template-columns: 1fr; grid-template-rows: auto 1fr; }
  .docs-list { border-right: none; border-bottom: 1px solid var(--c-border); max-height: 42vh; }
  .docs-preview-pane { min-height: 300px; }
}

@media (max-width: 768px) {
  /* Detail modal header */
  .detail-sw-header { flex-direction: column; align-items: flex-start; gap: 10px; padding: 14px 14px 12px; }
  .detail-sw-header__actions { width: 100%; justify-content: flex-end; }
  .detail-sw-title { font-size: 14px; }

  /* Detail meta panel */
  .detail-sw-meta { padding: 10px 12px; max-height: 36vh; }
  .detail-sw-preview { min-height: 280px; }

  /* Docs modal header */
  .modal-docs .modal-header h2 { font-size: 13px; }
  .docs-list { max-height: 38vh; padding: 8px; }
  .doc-item-v2__header { padding: 8px 10px; gap: 8px; }
  .doc-item-v2__icon { font-size: 16px; }
  .doc-item-v2__name { font-size: 11px; }
  .doc-item-v2__file { font-size: 10px; }

  /* Action buttons wrap nicely */
  .doc-item-v2__actions { gap: 5px; padding: 6px 8px 8px; }
  .doc-item-v2__actions-row { gap: 5px; }
  .doc-action-btn { font-size: 11px; padding: 4px 8px; }

  /* Preview toolbar wraps */
  .doc-preview-toolbar { flex-wrap: wrap; gap: 6px; padding: 6px 10px; }
  .docs-preview-header { flex-wrap: wrap; gap: 6px; padding: 6px 10px; }

  /* Table: hide less important columns */
  table th:nth-child(3),
  table td:nth-child(3) { display: none; }

  /* Modal footer */
  .modal-footer { padding: 10px 14px; }
}

@media (max-width: 480px) {
  /* Full-screen modals */
  .modal-detail-sw,
  .modal-docs { max-height: 100dvh; height: 100dvh; }

  /* Detail meta: collapse more */
  .detail-sw-meta { max-height: 32vh; }
  .detail-sw-preview { min-height: 240px; }

  /* Docs list tighter */
  .docs-list { max-height: 35vh; padding: 6px; gap: 4px; }
  .doc-item-v2__header { padding: 7px 8px; }
  .doc-item-v2__actions { gap: 4px; padding: 6px 8px 8px; }
  .doc-item-v2__actions-row { gap: 4px; }
  .doc-action-btn { font-size: 11px; padding: 4px 6px; }

  /* Table: hide docs chips and authors on tiny screens */
  table th:nth-child(2),
  table td:nth-child(2),
  table th:nth-child(4),
  table td:nth-child(4) { display: none; }

  /* Sidebar search bar */
  .search-bar { padding: 6px 10px; }
  .page-header { flex-wrap: wrap; gap: 8px; }
  .page-header h1 { font-size: 16px; }

  /* Preview toolbar: icon+title on one line, actions wrap below */
  .doc-preview-toolbar { flex-direction: row; flex-wrap: wrap; }
  .docs-preview-header { flex-direction: row; flex-wrap: wrap; }
}

</style>
