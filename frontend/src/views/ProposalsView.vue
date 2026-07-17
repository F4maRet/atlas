<template>
  <div class="page" @click="closeContextMenu">
    <div class="page-header">
      <h1><span class="page-title-icon">💡</span> Рационализаторские предложения</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить</button>
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
          <span class="catalog-item__icon">📋</span><span class="catalog-item__name">Все</span>
          <span class="catalog-item__count">{{ proposals.length }}</span>
        </div>
        <div class="catalog-item" :class="{ active: activeCatalog === '__none__' }"
          @click.stop="activeCatalog = '__none__'"
          @dragover.prevent="dragOverCatalog = '__none__'" @dragleave="dragOverCatalog = null"
          @drop.stop="dropOnCatalog('__none__', $event)"
          :style="dragOverCatalog==='__none__'?'background:var(--c-surface);':''">
          <span class="catalog-item__icon">📂</span><span class="catalog-item__name">Без каталога</span>
          <span class="catalog-item__count">{{ proposals.filter(p => !p.catalog).length }}</span>
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
          <span class="catalog-item__count">{{ proposals.filter(p => p.catalog === cat).length }}</span>
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
                <tr><th>Название</th><th>Авторы</th><th>Тип</th><th>Загружено</th><th></th></tr>
              </thead>
              <tbody>
                <tr v-if="!filtered.length">
                  <td colspan="5" style="text-align:center;padding:40px">
                    <div class="empty-state" style="padding:32px">
                      <div class="empty-state__icon">💡</div>
                      <div class="empty-state__text">Рац. предложений пока нет</div>
                    </div>
                  </td>
                </tr>
                <tr v-for="p in filtered" :key="p.id" class="table-row-clickable"
                  draggable="true" @dragstart="dragStart(p, $event)" @dragend="dragEnd"
                  @click="openDetail(p)">
                  <td style="max-width:300px">
                    <div class="truncate" style="font-weight:500">{{ p.title }}</div>
                    <div v-if="p.catalog" class="text-muted" style="font-size:11px;margin-top:2px">📁 {{ p.catalog }}</div>
                  </td>
                  <td>
                    <div class="flex" style="flex-wrap:wrap;gap:4px">
                      <span v-for="a in p.authors" :key="a.id" class="tag">{{ a.short_name || a.full_name }}</span>
                    </div>
                  </td>
                  <td><span v-if="p.proposal_type" class="badge badge-amber">{{ p.proposal_type }}</span></td>
                  <td class="text-muted text-sm">{{ formatDate(p.created_at) }}</td>
                  <td @click.stop>
                    <div class="flex-center gap-2">
                      <button class="btn btn-ghost btn-sm btn-icon" @click.stop="openEdit(p)">✏️</button>
                      <button class="btn btn-danger btn-sm btn-icon" @click.stop="del(p)">🗑</button>
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
        <div class="modal modal-detail modal-detail--narrow">
          <div class="modal-header">
            <h2 class="detail-title">{{ detailProposal?.title }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showDetail=false">✕</button>
          </div>

          <div class="detail-body detail-body--single">
            <!-- Meta -->
            <div class="detail-meta">
              <div class="detail-section">
                <div class="detail-label">Тип</div>
                <div class="detail-value">
                  <span v-if="detailProposal?.proposal_type" class="badge badge-amber">{{ detailProposal.proposal_type }}</span>
                  <span v-else class="text-muted text-sm">—</span>
                </div>
              </div>
              <div class="detail-section">
                <div class="detail-label">Авторы</div>
                <div class="detail-value">
                  <div v-if="detailProposal?.authors?.length" style="display:flex;flex-wrap:wrap;gap:6px">
                    <span v-for="au in detailProposal.authors" :key="au.id" class="tag">{{ au.full_name }}</span>
                  </div>
                  <span v-else class="text-muted text-sm">—</span>
                </div>
              </div>
              <div class="detail-section">
                <div class="detail-label">Каталог</div>
                <div class="detail-value text-mono" style="font-size:12px">{{ detailProposal?.catalog || '—' }}</div>
              </div>
              <div class="detail-section">
                <div class="detail-label">Дата добавления</div>
                <div class="detail-value">{{ detailProposal ? formatDate(detailProposal.created_at) : '—' }}</div>
              </div>
              <div class="detail-section" v-if="detailProposal?.original_filename">
                <div class="detail-label">Файл</div>
                <div class="detail-value">
                  <div class="file-info-block">
                    <div class="file-info-block__name">📄 {{ detailProposal.original_filename }}</div>
                    <div style="display:flex;gap:8px;align-items:center;margin-top:8px;flex-wrap:wrap">
                      <a :href="downloadUrl(detailProposal.id)" class="btn btn-ghost btn-sm" target="_blank">↓ Скачать</a>
                      <button class="btn btn-ghost btn-sm" @click="openPreviewModal(detailProposal)">👁 Предпросмотр</button>
                      <span v-if="ratio(detailProposal)" class="compress-badge">{{ ratio(detailProposal) }}</span>
                    </div>
                    <div class="text-muted text-sm" style="margin-top:4px">
                      {{ formatBytes(detailProposal.file_size_original) }} → {{ formatBytes(detailProposal.file_size_compressed) }}
                    </div>
                  </div>
                </div>
              </div>
              <div class="detail-section" v-else>
                <div class="detail-label">Файл</div>
                <div class="detail-value text-muted text-sm">Не прикреплён</div>
              </div>

              <!-- Certificate block -->
              <div class="detail-section">
                <div class="detail-label">Свидетельство</div>
                <div v-if="detailProposal?.certificate" class="file-info-block">
                  <div class="file-info-block__name">🏆 {{ detailProposal.certificate.original_filename }}</div>
                  <div style="display:flex;gap:6px;align-items:center;margin-top:8px;flex-wrap:wrap">
                    <a :href="proposalsApi.downloadCertificate(detailProposal.id)"
                      class="btn btn-ghost btn-sm" download>↓ Скачать</a>
                    <button class="btn btn-ghost btn-sm"
                      @click="openCertPreviewModal(detailProposal)">👁 Предпросмотр</button>
                    <label class="btn btn-ghost btn-sm" style="cursor:pointer">
                      ↑ Заменить
                      <input type="file" style="display:none" accept=".pdf,.doc,.docx"
                        @change="uploadCertificate(detailProposal.id, $event)" />
                    </label>
                    <button class="btn btn-danger btn-sm"
                      @click="deleteCertificate(detailProposal.id)">🗑</button>
                  </div>
                </div>
                <div v-else class="detail-value">
                  <div class="text-muted text-sm" style="margin-bottom:8px">Не прикреплено</div>
                  <label class="btn btn-ghost btn-sm" style="cursor:pointer">
                    + Загрузить свидетельство
                    <input type="file" style="display:none" accept=".pdf,.doc,.docx"
                      @change="uploadCertificate(detailProposal.id, $event)" />
                  </label>
                </div>
              </div>
            </div>

          </div>

          <div class="modal-footer">
            <button class="btn btn-secondary" @click="showDetail=false">Закрыть</button>
            <button class="btn btn-ghost" @click="showDetail=false; openEdit(detailProposal)">✏️ Редактировать</button>
          </div>
        </div>
      </div>
    </Transition>

    <!-- ── Create/Edit Modal ── -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать' : 'Новое рац. предложение' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.title" placeholder="Полное название" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Тип</label>
              <select class="select" v-model="form.proposal_type">
                <option value="">— выбрать —</option>
                <option>ВАС</option><option>ОГВ(С)</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Каталог хранения</label>
              <div style="display:flex;gap:8px">
                <input class="input" v-model="form.catalog" placeholder="/proposals/2024" />
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
            <label class="form-label">Файл (PDF / DOCX)</label>
            <FileUpload v-model="form.file" accept=".pdf,.doc,.docx" icon="💡"
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
  </div>

    <!-- ── File Preview Modal ── -->
    <FilePreviewModal
      v-model="showPreviewModal"
      :preview-url="previewModalUrl"
      :download-url="previewDownloadUrl"
      :filename="previewFilename"
    />
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useToast } from 'vue-toastification'
import { proposalsApi, authorsApi, buildFormData, formatBytes } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'
import FilePreviewModal from '@/components/common/FilePreviewModal.vue'

const toast = useToast()
const proposals = ref([])
const authors = ref([])
const search = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ title: '', proposal_type: '', catalog: '', author_ids: [], file: null })

const showDetail = ref(false)
const detailProposal = ref(null)
const showPreview = ref(false)
const showPreviewModal = ref(false)
const previewModalUrl = ref('')
const previewDownloadUrl = ref('')
const previewFilename = ref('')

const catalogs = ref([])
const activeCatalog = ref('')
const creatingCatalog = ref(false)
const newCatalogName = ref('')
const newCatalogInput = ref(null)
const renamingCatalog = ref(null)
const renameValue = ref('')
const renameInputs = ref({})
const dragOverCatalog = ref(null)
const draggingProposal = ref(null)
const contextMenu = ref({ visible: false, x: 0, y: 0, catalog: '' })

const filtered = computed(() => {
  const q = search.value.toLowerCase()
  let list = proposals.value.filter(p => p.title.toLowerCase().includes(q) || p.authors.some(a => a.full_name.toLowerCase().includes(q)))
  if (activeCatalog.value === '__none__') list = list.filter(p => !p.catalog)
  else if (activeCatalog.value !== '') list = list.filter(p => p.catalog === activeCatalog.value)
  return list
})

const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''
const downloadUrl = id => proposalsApi.download(id)
const absoluteDownloadUrl = id => `${window.location.origin}${proposalsApi.download(id)}`
const isPdf = name => name?.toLowerCase().endsWith('.pdf')
const ratio = p => {
  if (!p.file_size_original || !p.file_size_compressed) return null
  const s = ((1 - p.file_size_compressed / p.file_size_original) * 100).toFixed(0)
  return s > 2 ? `-${s}%` : null
}
function togglePreview() { showPreview.value = !showPreview.value }
function openPreviewModal(proposal) {
  previewModalUrl.value = proposalsApi.preview(proposal.id)
  previewDownloadUrl.value = downloadUrl(proposal.id)
  previewFilename.value = proposal.original_filename || 'file'
  showPreviewModal.value = true
}

function openCertPreviewModal(proposal) {
  previewModalUrl.value = proposalsApi.previewCertificate(proposal.id)
  previewDownloadUrl.value = proposalsApi.downloadCertificate(proposal.id)
  previewFilename.value = proposal.certificate?.original_filename || 'certificate'
  showPreviewModal.value = true
}

async function uploadCertificate(pid, event) {
  const file = event.target.files[0]
  if (!file) return
  try {
    const fd = new FormData()
    fd.append('file', file)
    await proposalsApi.uploadCertificate(pid, fd)
    toast.success('Свидетельство загружено')
    await load()
    detailProposal.value = proposals.value.find(p => p.id === pid) || detailProposal.value
  } catch (e) { toast.error(e.message) }
  event.target.value = ''
}

async function deleteCertificate(pid) {
  if (!confirm('Удалить свидетельство?')) return
  try {
    await proposalsApi.deleteCertificate(pid)
    toast.success('Свидетельство удалено')
    await load()
    detailProposal.value = proposals.value.find(p => p.id === pid) || detailProposal.value
  } catch (e) { toast.error(e.message) }
}

function syncCatalogsFromData(list) {
  list.filter(p => p.catalog).forEach(p => { if (!catalogs.value.includes(p.catalog)) catalogs.value.push(p.catalog) })
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
  for (const p of proposals.value.filter(p => p.catalog === oldName))
    await proposalsApi.update(p.id, buildFormData({ title: p.title, catalog: newName, author_ids: p.authors.map(x => x.id) }))
  const idx = catalogs.value.indexOf(oldName); if (idx !== -1) { catalogs.value[idx] = newName; catalogs.value.sort() }
  if (activeCatalog.value === oldName) activeCatalog.value = newName
  await load(); toast.success(`Каталог переименован в «${newName}»`)
}
async function deleteCatalog(cat) {
  contextMenu.value.visible = false
  if (!confirm(`Удалить каталог «${cat}»?\nУ всех предложений каталог будет откреплён.`)) return
  for (const p of proposals.value.filter(p => p.catalog === cat))
    await proposalsApi.update(p.id, buildFormData({ title: p.title, catalog: '', author_ids: p.authors.map(x => x.id) }))
  catalogs.value = catalogs.value.filter(c => c !== cat)
  if (activeCatalog.value === cat) activeCatalog.value = ''
  await load(); toast.success(`Каталог «${cat}» удалён`)
}
function openContextMenu(cat, e) { contextMenu.value = { visible: true, x: e.clientX, y: e.clientY, catalog: cat } }
function closeContextMenu() { contextMenu.value.visible = false }

function dragStart(p, e) { draggingProposal.value = p; e.dataTransfer.effectAllowed = 'move' }
function dragEnd() { draggingProposal.value = null; dragOverCatalog.value = null }
async function dropOnCatalog(catName, e) {
  e.preventDefault(); dragOverCatalog.value = null
  const p = draggingProposal.value; if (!p) return
  const newCatalog = catName === '__none__' ? '' : (catName || '')
  if (p.catalog === newCatalog) return
  await proposalsApi.update(p.id, buildFormData({ title: p.title, catalog: newCatalog, author_ids: p.authors.map(x => x.id) }))
  await load(); toast.success(newCatalog ? `Перемещено в «${newCatalog}»` : 'Каталог откреплён')
}

function openDetail(p) { detailProposal.value = p; showPreview.value = false; showDetail.value = true }
function openCreate() {
  editing.value = null
  form.value = { title: '', proposal_type: '', catalog: activeCatalog.value !== '' && activeCatalog.value !== '__none__' ? activeCatalog.value : '', author_ids: [], file: null }
  showModal.value = true
}
function openEdit(p) { editing.value = p; form.value = { title: p.title, proposal_type: p.proposal_type || '', catalog: p.catalog || '', author_ids: p.authors.map(x => x.id), file: null }; showModal.value = true }

async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const fd = buildFormData({ title: form.value.title, proposal_type: form.value.proposal_type || undefined, catalog: form.value.catalog || undefined, author_ids: form.value.author_ids, file: form.value.file })
    if (editing.value) { await proposalsApi.update(editing.value.id, fd); toast.success('Обновлено') }
    else { await proposalsApi.create(fd); toast.success('Добавлено') }
    showModal.value = false; await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}
async function del(p) {
  if (!confirm(`Удалить «${p.title}»?`)) return
  try { await proposalsApi.delete(p.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}
async function load() {
  try {
    const [pr, au] = await Promise.all([proposalsApi.list(), authorsApi.list()])
    proposals.value = pr.data; authors.value = au.data
    syncCatalogsFromData(pr.data)
  } catch (e) {
    console.error(e)
    try { const r = await proposalsApi.list(); proposals.value = r.data; syncCatalogsFromData(r.data) } catch {}
    try { const r = await authorsApi.list(); authors.value = r.data } catch {}
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
/* Detail */
.modal-detail { max-width: 900px; width: 96vw; }
.modal-detail--narrow { max-width: 560px; }
.detail-title { font-size: 15px; line-height: 1.4; max-width: 780px; }
.detail-body { display: grid; grid-template-columns: 280px 1fr; gap: 20px; min-height: 300px; }
.detail-body--single { display: block; }
.detail-meta { display: flex; flex-direction: column; }
.detail-section { padding: 10px 0; border-bottom: 1px solid var(--c-border); }
.detail-section:last-child { border-bottom: none; }
.detail-label { font-size: 10px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.06em; color: var(--c-text3); margin-bottom: 5px; }
.detail-value { font-size: 13px; color: var(--c-text); }
.file-info-block { background: var(--c-bg3); border-radius: 8px; padding: 10px 12px; }
.file-info-block__name { font-size: 12px; font-weight: 500; word-break: break-all; }
.text-mono { font-family: var(--font-mono); }
.detail-preview { display: flex; flex-direction: column; border: 1px solid var(--c-border); border-radius: var(--radius); overflow: hidden; }
.detail-preview-placeholder { display: flex; align-items: center; justify-content: center; border: 1px dashed var(--c-border); border-radius: var(--radius); min-height: 300px; }
.preview-toolbar { display: flex; align-items: center; justify-content: space-between; padding: 6px 10px; background: var(--c-bg3); border-bottom: 1px solid var(--c-border); }
.preview-frame-wrap { flex: 1; background: var(--c-bg); min-height: 400px; }
.preview-frame { width: 100%; height: 100%; min-height: 400px; border: none; display: block; }
@media (max-width: 1000px) { .detail-body { grid-template-columns: 1fr; } .layout-with-sidebar { grid-template-columns: 1fr; } .catalog-sidebar { position: static; } }
</style>
