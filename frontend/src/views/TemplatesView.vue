<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">🗂</span> Шаблоны документов</h1>
      <button class="btn btn-primary" @click="openCreate()">+ Добавить шаблон</button>
    </div>
    <p class="page-desc">
      Шаблоны заключений (DOCX) используются для автоматического формирования документа по статье.
      Остальные шаблоны — образцы сопроводительных документов к ПО, их можно скачать и заполнить.
    </p>

    <details class="card help">
      <summary>Как подготовить шаблон заключения</summary>
      <p class="text-sm text-muted mt-2">Вставьте в DOCX-файл метки — при формировании они заменятся данными статьи:</p>
      <div class="help-grid">
        <code>[название_статьи]</code><span>название статьи</span>
        <code>[ФИО_авторов]</code><span>авторы: Иванов И.И., Петров П.П.</span>
        <code>[окончание_автор]</code><span>«а» для одного автора, «ов» — для нескольких (автор[окончание_автор])</span>
        <code>[главный_автор]</code><span>главный автор (или первый)</span>
        <code>[месяц_загрузки]</code><span>месяц в родительном падеже: «апреля»</span>
        <code>[год_загрузки]</code><span>год: 2026</span>
      </div>
    </details>

    <div v-if="loadError" class="alert alert-error">⚠️ {{ loadError }}</div>

    <section v-for="group in grouped" :key="group.type" class="tgroup">
      <div class="tgroup__head">
        <span class="badge badge-blue">{{ typeLabel(group.type) }}</span>
        <span class="text-muted text-sm">{{ pluralize(group.items.length, 'вариант', 'варианта', 'вариантов') }}</span>
        <button class="btn btn-ghost btn-sm ml-auto" @click="openCreate(group.type)">+ Добавить</button>
      </div>
      <div class="card card--flush">
        <div class="table-wrap">
          <table>
            <thead><tr><th>Название</th><th>Файл</th><th>Статус</th><th class="hide-sm">Создан</th><th class="col-actions"></th></tr></thead>
            <tbody>
              <tr v-for="t in group.items" :key="t.id">
                <td>
                  <div style="font-weight:500">{{ t.name }}</div>
                  <div v-if="t.description" class="cell-sub" style="max-width:420px">{{ t.description }}</div>
                </td>
                <td>
                  <span v-if="t.has_file" class="text-ok text-sm">● загружен</span>
                  <span v-else class="text-dim text-sm">○ нет файла</span>
                </td>
                <td>
                  <button class="badge" :class="t.is_active ? 'badge-green' : 'badge-gray'" style="border:none;cursor:pointer"
                    :title="t.is_active ? 'Отключить' : 'Включить'" @click="toggleActive(t)">
                    {{ t.is_active ? 'Активен' : 'Отключён' }}
                  </button>
                </td>
                <td class="hide-sm text-muted text-sm">{{ formatDate(t.created_at) }}</td>
                <td>
                  <div class="cell-actions">
                    <button v-if="t.has_file" class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="preview(t)">👁</button>
                    <a v-if="t.has_file" :href="templatesApi.download(t.id)" class="btn btn-ghost btn-sm btn-icon" title="Скачать" download>↓</a>
                    <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(t)">✏️</button>
                    <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(t)">🗑</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </section>

    <div v-if="!templates.length && !loadError" class="card">
      <div class="empty-state">
        <div class="empty-state__icon">🗂</div>
        <div class="empty-state__text">Шаблонов пока нет</div>
      </div>
    </div>

    <Modal v-model="showForm" :title="editing ? 'Редактировать шаблон' : 'Новый шаблон'">
      <form id="tmpl-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <input v-model="form.name" class="input" required maxlength="500" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Тип документа <span class="req">*</span></label>
            <select v-model="form.doc_type" class="select" required>
              <option value="" disabled>— выбрать —</option>
              <option v-for="t in types" :key="t.key" :value="t.key">{{ t.label }}</option>
            </select>
          </div>
          <div class="form-group">
            <label class="form-label">Статус</label>
            <label class="checkbox" style="height:38px"><input v-model="form.is_active" type="checkbox" /> Активен</label>
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Описание</label>
          <textarea v-model="form.description" class="textarea"></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Файл шаблона</label>
          <FileUpload v-model="form.file" :accept="form.doc_type === 'conclusion' ? '.docx' : '.docx,.doc,.pdf,.odt,.rtf'"
            :hint="form.doc_type === 'conclusion' ? 'только DOCX (нужен для автозаполнения)' : 'DOCX, DOC, PDF, ODT'" icon="🗂"
            :existing-name="editing?.has_file ? 'файл загружен' : null"
            :download-url="editing?.has_file ? templatesApi.download(editing.id) : null" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="tmpl-form" :disabled="saving">{{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}</button>
      </template>
    </Modal>

    <FilePreviewModal v-model="showPreview" v-bind="previewData" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { templatesApi, buildFormData } from '@/utils/api'
import { formatDate, pluralize } from '@/utils/format'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import FileUpload from '@/components/common/FileUpload.vue'
import FilePreviewModal from '@/components/common/FilePreviewModal.vue'

const toast = useToast()
const templates = ref([])
const types = ref([])
const loadError = ref('')

const typeLabel = k => types.value.find(t => t.key === k)?.label || k
const grouped = computed(() => {
  const order = types.value.map(t => t.key)
  const map = {}
  templates.value.forEach(t => { (map[t.doc_type] ||= []).push(t) })
  return Object.keys(map)
    .sort((a, b) => (order.indexOf(a) + 1 || 99) - (order.indexOf(b) + 1 || 99))
    .map(type => ({ type, items: map[type] }))
})

async function load() {
  loadError.value = ''
  try {
    const [t, ty] = await Promise.all([templatesApi.list(), templatesApi.types()])
    templates.value = t.data
    types.value = ty.data
  } catch (e) { loadError.value = e.message }
}
onMounted(load)

const showPreview = ref(false)
const previewData = ref({})
function preview(t) {
  previewData.value = { previewUrl: templatesApi.preview(t.id), downloadUrl: templatesApi.download(t.id), filename: `${t.name}.docx`, title: t.name }
  showPreview.value = true
}

const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})
function openCreate(type = '') {
  editing.value = null
  form.value = { name: '', doc_type: type, description: '', is_active: true, file: null }
  showForm.value = true
}
function openEdit(t) {
  editing.value = t
  form.value = { name: t.name, doc_type: t.doc_type, description: t.description || '', is_active: t.is_active, file: null }
  showForm.value = true
}
async function save() {
  const f = form.value
  if (!f.name.trim()) return toast.error('Введите название')
  if (!f.doc_type) return toast.error('Выберите тип документа')
  saving.value = true
  try {
    const fd = buildFormData({ name: f.name.trim(), doc_type: f.doc_type, description: f.description, is_active: f.is_active, file: f.file })
    if (editing.value) { await templatesApi.update(editing.value.id, fd); toast.success('Сохранено') }
    else { await templatesApi.create(fd); toast.success('Шаблон добавлен') }
    showForm.value = false
    await load()
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function toggleActive(t) {
  try { await templatesApi.update(t.id, buildFormData({ is_active: !t.is_active })); await load() }
  catch (e) { toast.error(e.message) }
}
async function remove(t) {
  if (!await confirmDialog({ title: 'Удалить шаблон?', message: `«${t.name}»` })) return
  try { await templatesApi.delete(t.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}
</script>

<style scoped>
.help { margin-bottom: 20px; padding: 14px 18px; }
.help summary { cursor: pointer; font-weight: 500; font-size: 13px; }
.help-grid { display: grid; grid-template-columns: auto 1fr; gap: 6px 16px; margin-top: 10px; font-size: 13px; align-items: baseline; }
.help-grid code { font-family: var(--font-mono); font-size: 12px; background: var(--c-bg3); padding: 1px 6px; border-radius: 4px; color: var(--c-accent); }
.tgroup { margin-bottom: 20px; }
.tgroup__head { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
</style>
