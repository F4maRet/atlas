<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">🗂</span> Шаблоны документов</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить шаблон</button>
    </div>

    <div class="text-muted text-sm" style="margin-bottom:20px">
      Шаблоны используются при формировании документов: заключений об открытом публиковании и сопроводительных документов к ПО.
    </div>

    <!-- Group by doc_type -->
    <div v-for="group in groupedTemplates" :key="group.type" class="template-group">
      <div class="template-group__header">
        <span class="badge" :class="typeBadge(group.type)">{{ typeLabel(group.type) }}</span>
        <span class="text-muted text-sm" style="margin-left:8px">{{ group.items.length }} {{ pluralize(group.items.length, 'вариант', 'варианта', 'вариантов') }}</span>
      </div>
      <div class="card" style="padding:0;overflow:hidden;margin-bottom:16px">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Название</th>
                <th>Файл</th>
                <th>Статус</th>
                <th>Загружен</th>
                <th>Создан</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="t in group.items" :key="t.id">
                <td style="font-weight:500">
                  {{ t.name }}
                  <div v-if="t.description" class="text-muted text-sm truncate" style="max-width:260px;font-weight:400;margin-top:2px">{{ t.description }}</div>
                </td>
                <td>
                  <div v-if="t.file_path" class="file-status file-status--ok">
                    <span class="file-status__dot"></span>
                    <span class="text-sm">Загружен</span>
                  </div>
                  <div v-else class="file-status file-status--missing">
                    <span class="file-status__dot"></span>
                    <span class="text-sm text-muted">Нет файла</span>
                  </div>
                </td>
                <td>
                  <span class="badge" :class="t.is_active ? 'badge-green' : 'badge-gray'">
                    {{ t.is_active ? 'Активен' : 'Отключён' }}
                  </span>
                </td>
                <td class="text-muted text-sm">
                  <span v-if="t.file_path">✓</span>
                  <span v-else class="text-muted">—</span>
                </td>
                <td class="text-muted text-sm">{{ formatDate(t.created_at) }}</td>
                <td>
                  <div class="flex-center gap-2">
                    <button v-if="t.file_path" class="btn btn-ghost btn-sm btn-icon" title="Просмотр" @click="previewTemplate(t)">👁</button>
                    <a v-if="t.file_path" :href="templatesApi.download(t.id)" class="btn btn-ghost btn-sm btn-icon" target="_blank" title="Скачать">↓</a>
                    <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(t)">✏️</button>
                    <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="del(t)">🗑</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>

    <div v-if="!templates.length" class="card">
      <div class="empty-state" style="padding:48px">
        <div class="empty-state__icon">🗂</div>
        <div class="empty-state__text">Шаблонов пока нет</div>
        <button class="btn btn-primary" style="margin-top:16px" @click="openCreate">+ Добавить первый шаблон</button>
      </div>
    </div>

    <!-- Create/Edit Modal -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать шаблон' : 'Новый шаблон' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.name" placeholder="Название шаблона" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Тип документа *</label>
              <select class="select" v-model="form.doc_type">
                <option value="">— выбрать —</option>
                <option value="conclusion">Заключение об открытом публиковании</option>
                <option value="annotation">Аннотация программы</option>
                <option value="registration">Заявление на регистрацию</option>
                <option value="description">Описание программы</option>
                <option value="manual">Руководство пользователя</option>
                <option value="act">Акт приёма и ввода в эксплуатацию</option>
                <option value="abstract">Реферат по исходникам</option>
                <option value="listing">Листинг по исходникам</option>
              </select>
            </div>
            <div class="form-group">
              <label class="form-label">Статус</label>
              <select class="select" v-model="form.is_active">
                <option :value="true">Активен</option>
                <option :value="false">Отключён</option>
              </select>
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Описание</label>
            <textarea class="textarea" v-model="form.description" placeholder="Краткое описание шаблона (необязательно)"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Файл шаблона (DOCX)</label>
            <FileUpload
              v-model="form.file" accept=".doc,.docx" icon="🗂"
              :existing-name="editing?.file_path ? 'Шаблон загружен' : null"
              :download-url="editing?.file_path ? templatesApi.download(editing.id) : null"
            />
          </div>

          <!-- File status indicator in edit mode -->
          <div v-if="editing" class="template-file-status-row">
            <div v-if="editing.file_path" class="file-status-card file-status-card--ok">
              <span style="font-size:18px">✅</span>
              <div>
                <div style="font-weight:600;font-size:13px">Файл загружен</div>
                <div class="text-muted text-sm">Шаблон доступен для формирования документов</div>
              </div>
              <a :href="templatesApi.download(editing.id)" class="btn btn-ghost btn-sm" target="_blank">↓ Скачать</a>
              <button class="btn btn-ghost btn-sm" @click="previewTemplate(editing); showModal=false">👁 Просмотр</button>
            </div>
            <div v-else class="file-status-card file-status-card--missing">
              <span style="font-size:18px">⚠️</span>
              <div>
                <div style="font-weight:600;font-size:13px">Файл не загружен</div>
                <div class="text-muted text-sm">Загрузите файл шаблона для использования в формировании документов</div>
              </div>
            </div>
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

    <!-- Preview Modal -->
    <FilePreviewModal
      v-model="showPreview"
      :preview-url="previewTemplate_.previewUrl"
      :download-url="previewTemplate_.downloadUrl"
      :filename="previewTemplate_.filename"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useToast } from 'vue-toastification'
import { templatesApi, buildFormData } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'
import FilePreviewModal from '@/components/common/FilePreviewModal.vue'

const toast = useToast()
const templates = ref([])
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ name: '', doc_type: '', description: '', is_active: true, file: null })

const showPreview = ref(false)
const previewTemplate_ = ref({ previewUrl: '', downloadUrl: '', filename: '' })

const TYPE_LABELS = {
  conclusion: 'Заключение',
  annotation: 'Аннотация',
  registration: 'Заявление',
  description: 'Описание',
  manual: 'Руководство',
  act: 'Акт',
  abstract: 'Реферат',
  listing: 'Листинг'
}
const TYPE_BADGE = {
  conclusion: 'badge-blue',
  annotation: 'badge-purple',
  registration: 'badge-amber',
  description: 'badge-teal',
  manual: 'badge-green',
  act: 'badge-red',
  abstract: 'badge-gray',
  listing: 'badge-gray'
}
const TYPE_ORDER = ['conclusion', 'annotation', 'registration', 'description', 'manual', 'act', 'abstract', 'listing']

const typeLabel = k => TYPE_LABELS[k] || k
const typeBadge = k => TYPE_BADGE[k] || 'badge-gray'
const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''

function pluralize(n, one, few, many) {
  const mod10 = n % 10, mod100 = n % 100
  if (mod100 >= 11 && mod100 <= 14) return `${n} ${many}`
  if (mod10 === 1) return `${n} ${one}`
  if (mod10 >= 2 && mod10 <= 4) return `${n} ${few}`
  return `${n} ${many}`
}

// Group templates by doc_type preserving type order
const groupedTemplates = computed(() => {
  const map = {}
  for (const t of templates.value) {
    if (!map[t.doc_type]) map[t.doc_type] = []
    map[t.doc_type].push(t)
  }
  const result = []
  // First add types in defined order
  for (const type of TYPE_ORDER) {
    if (map[type]) result.push({ type, items: map[type] })
  }
  // Then any unknown types
  for (const type of Object.keys(map)) {
    if (!TYPE_ORDER.includes(type)) result.push({ type, items: map[type] })
  }
  return result
})

function previewTemplate(t) {
  const downloadUrl = templatesApi.download(t.id)
  const previewUrl = templatesApi.preview(t.id)
  previewTemplate_.value = {
    previewUrl,
    downloadUrl,
    filename: `${t.name}.docx`
  }
  showPreview.value = true
}

function openCreate() {
  editing.value = null
  form.value = { name: '', doc_type: '', description: '', is_active: true, file: null }
  showModal.value = true
}

function openEdit(t) {
  editing.value = t
  form.value = { name: t.name, doc_type: t.doc_type, description: t.description || '', is_active: t.is_active, file: null }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return toast.error('Введите название')
  if (!form.value.doc_type) return toast.error('Выберите тип документа')
  saving.value = true
  try {
    const fd = buildFormData({
      name: form.value.name,
      doc_type: form.value.doc_type,
      description: form.value.description || undefined,
      is_active: form.value.is_active,
      file: form.value.file
    })
    if (editing.value) { await templatesApi.update(editing.value.id, fd); toast.success('Обновлено') }
    else { await templatesApi.create(fd); toast.success('Шаблон добавлен') }
    showModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}

async function del(t) {
  if (!confirm(`Удалить шаблон «${t.name}»?`)) return
  try { await templatesApi.delete(t.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}

async function load() {
  try {
    const r = await templatesApi.list()
    templates.value = r.data
  } catch (e) {
    toast.error('Ошибка загрузки шаблонов: ' + e.message)
  }
}
onMounted(load)
</script>

<style scoped>
.template-group__header {
  display: flex;
  align-items: center;
  margin-bottom: 8px;
}

.file-status {
  display: flex;
  align-items: center;
  gap: 6px;
}
.file-status__dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.file-status--ok .file-status__dot { background: var(--c-green, #22c55e); }
.file-status--missing .file-status__dot { background: var(--c-border2, #555); }

.template-file-status-row {
  margin-bottom: 16px;
}
.file-status-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 14px;
  border-radius: var(--radius);
  border: 1px solid;
  flex-wrap: wrap;
}
.file-status-card--ok {
  background: rgba(34,197,94,0.07);
  border-color: rgba(34,197,94,0.3);
}
.file-status-card--missing {
  background: rgba(255,180,0,0.07);
  border-color: rgba(255,180,0,0.3);
}
.file-status-card > div:nth-child(2) { flex: 1; min-width: 0; }
</style>
