<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">🗓</span> Календарь конференций</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить конференцию</button>
    </div>

    <div v-if="loadError" class="alert alert-error">⚠️ {{ loadError }} <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button></div>

    <div class="toolbar">
      <div class="search-bar">
        <span>🔍</span>
        <input v-model="search" placeholder="Название, организатор, место…" />
        <button v-if="search" class="search-bar__clear" @click="search = ''">✕</button>
      </div>
      <div class="btn-group" role="group" aria-label="Статус">
        <button v-for="s in STATUSES" :key="s.key" class="btn btn-ghost btn-sm" :class="{ 'btn-active': status === s.key }" @click="status = s.key">{{ s.label }}</button>
      </div>
      <select v-model="participant" class="select" aria-label="Участник">
        <option value="">Все участники</option>
        <option v-for="a in participantsOptions" :key="a.id" :value="String(a.id)">{{ a.full_name }}</option>
      </select>
      <span class="toolbar__label">с</span>
      <input v-model="dateFrom" class="input" type="date" aria-label="С даты" />
      <span class="toolbar__label">по</span>
      <input v-model="dateTo" class="input" type="date" aria-label="По дату" />
      <button v-if="dateFrom || dateTo || participant" class="btn btn-ghost btn-sm" title="Сбросить фильтры" @click="clearFilters">✕</button>
    </div>

    <div v-if="!filtered.length" class="card">
      <div class="empty-state">
        <div class="empty-state__icon">🗓</div>
        <div class="empty-state__text">{{ conferences.length ? 'Конференций не найдено' : 'Календарь пуст' }}</div>
        <button v-if="!conferences.length" class="btn btn-primary btn-sm" @click="openCreate">+ Добавить конференцию</button>
      </div>
    </div>

    <div class="conf-list">
      <template v-for="(c, i) in filtered" :key="c.id">
        <div v-if="monthKey(c) !== monthKey(filtered[i - 1])" class="conf-month">{{ monthTitle(c) }}</div>
        <article class="conf-card" :class="[`conf-card--${stateOf(c)}`, { highlight: highlightId === c.id }]" :id="`conf-${c.id}`">
          <div class="conf-card__date">
            <div class="conf-card__month">{{ c.date_start ? formatDate(c.date_start, 'LLL').toUpperCase() : '—' }}</div>
            <div class="conf-card__day">{{ c.date_start ? formatDate(c.date_start, 'd') : '?' }}</div>
            <span class="conf-card__state">{{ STATE_LABEL[stateOf(c)] }}</span>
          </div>
          <div class="conf-card__body">
            <div class="conf-card__title">{{ c.title }}</div>
            <div class="conf-card__meta">
              <span v-if="c.date_end && c.date_end !== c.date_start">📅 {{ formatRange(c.date_start, c.date_end) }}</span>
              <span v-if="c.organizer">🏛 {{ c.organizer }}</span>
              <span v-if="c.location">📍 {{ c.location }}</span>
              <span v-if="c.is_online" class="badge badge-blue">🌐 Онлайн</span>
            </div>
            <div v-if="c.participants.length" class="tags">
              <span class="text-sm text-muted">👥</span>
              <span v-for="p in c.participants" :key="p.id" class="tag" :title="p.full_name">{{ authorLabel(p) }}</span>
            </div>
            <div v-if="c.description" class="conf-card__desc">{{ c.description }}</div>
            <div class="conf-card__actions">
              <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">🔗 Сайт</a>
              <a v-if="c.location" :href="mapUrl(c.location)" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm">🗺 Карта</a>
              <a v-if="c.date_start" :href="conferencesApi.ics(c.id)" class="btn btn-ghost btn-sm" title="Добавить в календарь (Outlook, телефон)" download>📆 В календарь</a>
              <span class="ml-auto"></span>
              <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(c)">✏️</button>
              <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(c)">🗑</button>
            </div>
          </div>
          <div v-if="c.photo_url" class="conf-card__photo" :style="{ backgroundImage: `url(${c.photo_url})` }"></div>
        </article>
      </template>
    </div>

    <Modal v-model="showForm" :title="editing ? 'Редактировать конференцию' : 'Новая конференция'" persistent>
      <form id="conf-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <input v-model="form.title" class="input" required maxlength="1000" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Организатор</label>
            <input v-model="form.organizer" class="input" maxlength="500" />
          </div>
          <div class="form-group">
            <label class="form-label">Место проведения</label>
            <input v-model="form.location" class="input" placeholder="Город, адрес" maxlength="500" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Дата начала</label>
            <input v-model="form.date_start" class="input" type="date" />
          </div>
          <div class="form-group">
            <label class="form-label">Дата окончания</label>
            <input v-model="form.date_end" class="input" type="date" :min="form.date_start || undefined" />
          </div>
        </div>
        <div class="form-group">
          <label class="checkbox"><input v-model="form.is_online" type="checkbox" /> Онлайн-формат</label>
        </div>
        <div class="form-group">
          <label class="form-label">Ссылка</label>
          <input v-model="form.url" class="input" type="url" placeholder="https://…" />
        </div>
        <div class="form-group">
          <label class="form-label">Участники</label>
          <AuthorPicker v-model="form.participant_ids" :all-authors="authors" :numbered="false" empty-text="Участники не выбраны" @created="authors.push($event)" />
        </div>
        <div class="form-group">
          <label class="form-label">Описание</label>
          <textarea v-model="form.description" class="textarea"></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Баннер / фото</label>
          <div v-if="editing?.photo_url && !form.photo && !form.remove_photo" class="flex-center gap-3" style="margin-bottom:8px">
            <img :src="editing.photo_url" alt="" class="thumb" />
            <button type="button" class="btn btn-ghost btn-sm" @click="form.remove_photo = true">Убрать фото</button>
          </div>
          <FileUpload v-model="form.photo" accept=".jpg,.jpeg,.png,.gif,.webp" hint="JPG, PNG, WEBP" icon="🖼" :max-mb="10" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="conf-form" :disabled="saving">{{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useToast } from 'vue-toastification'
import { conferencesApi, authorsApi, buildFormData } from '@/utils/api'
import { formatDate, formatRange, authorLabel, today } from '@/utils/format'
import { useOpenFromQuery } from '@/composables/useOpenFromQuery'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'

const toast = useToast()
const STATUSES = [
  { key: 'upcoming', label: 'Предстоящие' },
  { key: 'past', label: 'Прошедшие' },
  { key: '', label: 'Все' },
]
const STATE_LABEL = { ongoing: 'идёт', upcoming: 'скоро', past: 'прошла', nodate: 'без даты' }

const conferences = ref([])
const authors = ref([])
const loadError = ref('')
const search = ref('')
const status = ref('upcoming')
const participant = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const highlightId = ref(null)

function stateOf(c) {
  if (!c.date_start) return 'nodate'
  const t = today()
  const end = c.date_end || c.date_start
  if (end < t) return 'past'
  if (c.date_start <= t) return 'ongoing'
  return 'upcoming'
}

const participantsOptions = computed(() => {
  const m = new Map()
  conferences.value.forEach(c => c.participants.forEach(p => m.set(p.id, p)))
  return [...m.values()].sort((a, b) => a.full_name.localeCompare(b.full_name, 'ru'))
})

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  const list = conferences.value.filter(c => {
    const st = stateOf(c)
    if (status.value === 'upcoming' && st === 'past') return false
    if (status.value === 'past' && st !== 'past') return false
    if (q && ![c.title, c.organizer, c.location, c.description].some(v => (v || '').toLowerCase().includes(q))) return false
    if (participant.value && !c.participants.some(p => p.id === Number(participant.value))) return false
    const end = c.date_end || c.date_start
    if (dateFrom.value && end && end < dateFrom.value) return false
    if (dateTo.value && c.date_start && c.date_start > dateTo.value) return false
    return true
  })
  // Прошедшие — от свежих к старым, остальные — по возрастанию даты
  if (status.value === 'past') list.reverse()
  return list
})

const monthKey = c => (c ? (c.date_start || '').slice(0, 7) || 'none' : null)
const monthTitle = c => (c.date_start ? formatDate(c.date_start, 'LLLL yyyy') : 'Дата не указана')
function clearFilters() { dateFrom.value = ''; dateTo.value = ''; participant.value = '' }
const mapUrl = loc => `https://yandex.ru/maps/?text=${encodeURIComponent(loc)}`

async function load() {
  loadError.value = ''
  try {
    const [r, au] = await Promise.all([conferencesApi.list(), authorsApi.list()])
    conferences.value = r.data
    authors.value = au.data
  } catch (e) { loadError.value = e.message }
}
onMounted(load)

useOpenFromQuery(conferences, c => {
  status.value = ''
  highlightId.value = c.id
  nextTick(() => document.getElementById(`conf-${c.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  setTimeout(() => { highlightId.value = null }, 2500)
})

const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})
function openCreate() {
  editing.value = null
  form.value = { title: '', organizer: '', location: '', date_start: '', date_end: '', url: '', description: '', is_online: false, photo: null, remove_photo: false, participant_ids: [] }
  showForm.value = true
}
function openEdit(c) {
  editing.value = c
  form.value = {
    title: c.title, organizer: c.organizer || '', location: c.location || '', date_start: c.date_start || '', date_end: c.date_end || '',
    url: c.url || '', description: c.description || '', is_online: c.is_online, photo: null, remove_photo: false,
    participant_ids: c.participants.map(p => p.id),
  }
  showForm.value = true
}
async function save() {
  const f = form.value
  if (!f.title.trim()) return toast.error('Введите название')
  if (f.date_start && f.date_end && f.date_end < f.date_start) return toast.error('Дата окончания раньше даты начала')
  saving.value = true
  try {
    const fd = buildFormData({
      title: f.title.trim(), organizer: f.organizer, location: f.location, date_start: f.date_start, date_end: f.date_end,
      url: f.url, description: f.description, is_online: f.is_online, photo: f.photo,
      remove_photo: f.remove_photo || undefined, participant_ids: f.participant_ids,
    })
    if (editing.value) { await conferencesApi.update(editing.value.id, fd); toast.success('Сохранено') }
    else { await conferencesApi.create(fd); toast.success('Конференция добавлена') }
    showForm.value = false
    await load()
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function remove(c) {
  if (!await confirmDialog({ title: 'Удалить конференцию?', message: `«${c.title}»` })) return
  try { await conferencesApi.delete(c.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}
</script>

<style scoped>
.conf-list { display: flex; flex-direction: column; gap: 10px; }
.conf-month { font-size: 12px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; color: var(--c-text3); margin: 10px 0 2px; }
.conf-month::first-letter { text-transform: uppercase; }
.conf-card { display: flex; background: var(--c-bg2); border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; transition: box-shadow 0.3s, border-color 0.3s; }
.conf-card.highlight { border-color: var(--c-accent); box-shadow: 0 0 0 3px rgba(79,124,255,0.3); }
.conf-card--past { opacity: 0.72; }
.conf-card__date { width: 78px; flex-shrink: 0; background: var(--c-bg3); border-right: 1px solid var(--c-border); display: flex; flex-direction: column; align-items: center; justify-content: center; padding: 14px 6px; gap: 2px; }
.conf-card__month { font-size: 10px; font-weight: 600; color: var(--c-text3); letter-spacing: 1px; }
.conf-card__day { font-size: 28px; font-weight: 700; line-height: 1; }
.conf-card__state { font-size: 10px; margin-top: 6px; padding: 1px 6px; border-radius: 10px; background: var(--c-surface); color: var(--c-text2); }
.conf-card--ongoing .conf-card__state { background: rgba(34,211,160,0.18); color: var(--c-green); }
.conf-card--upcoming .conf-card__state { background: rgba(79,124,255,0.18); color: var(--c-accent); }
.conf-card__body { flex: 1; min-width: 0; padding: 12px 16px; display: flex; flex-direction: column; gap: 6px; }
.conf-card__title { font-size: 15px; font-weight: 600; }
.conf-card__meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--c-text2); align-items: center; }
.conf-card__desc { font-size: 13px; color: var(--c-text2); white-space: pre-line; }
.conf-card__actions { display: flex; gap: 6px; margin-top: 2px; flex-wrap: wrap; align-items: center; }
.conf-card__photo { width: 120px; flex-shrink: 0; background: center / cover; }
.thumb { width: 90px; height: 56px; object-fit: cover; border-radius: 6px; border: 1px solid var(--c-border); }
@media (max-width: 700px) { .conf-card__photo { display: none; } }
</style>
