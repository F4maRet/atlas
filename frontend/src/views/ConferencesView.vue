<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">🗓</span> Календарь конференций</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить конференцию</button>
    </div>

    <!-- Filters -->
    <div style="display:flex;gap:12px;margin-bottom:20px;align-items:center;flex-wrap:wrap">
      <div class="search-bar" style="flex:1;min-width:220px;margin-bottom:0;height:40px;box-sizing:border-box">
        <span>🔍</span>
        <input v-model="search" placeholder="Поиск по названию..." />
      </div>
      <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;height:40px">
        <label style="font-size:13px;font-weight:500;color:var(--c-text2);white-space:nowrap">С:</label>
        <input class="input" type="date" v-model="dateFrom" style="width:150px;height:40px;box-sizing:border-box" />
        <label style="font-size:13px;font-weight:500;color:var(--c-text2);white-space:nowrap">По:</label>
        <input class="input" type="date" v-model="dateTo" style="width:150px;height:40px;box-sizing:border-box" />
        <button class="btn btn-ghost btn-sm btn-icon" style="height:40px;width:40px;box-sizing:border-box" @click="clearDates" title="Сбросить">✕</button>
      </div>
    </div>

    <!-- Timeline view -->
    <div class="conf-list">
      <div v-if="!filtered.length" class="empty-state">
        <div class="empty-state__icon">🗓</div>
        <div class="empty-state__text">Конференций не найдено</div>
      </div>

      <div v-for="c in filtered" :key="c.id" class="conf-card">
        <div class="conf-card__date-col">
          <div class="conf-card__month">{{ monthLabel(c.date_start) }}</div>
          <div class="conf-card__day">{{ dayLabel(c.date_start) }}</div>
          <div class="conf-card__status-dot" :class="statusClass(c)"></div>
        </div>
        <div class="conf-card__body">
          <div class="conf-card__title">{{ c.title }}</div>
          <div class="conf-card__meta">
            <span v-if="c.organizer">🏛 {{ c.organizer }}</span>
            <span v-if="c.location" class="conf-location">
              📍 {{ c.location }}
              <a :href="yandexMapUrl(c.location)" target="_blank" class="map-link" title="Открыть на Яндекс Картах">🗺</a>
            </span>
            <span v-if="c.is_online" class="badge badge-blue">🌐 Онлайн</span>
            <span v-if="c.date_end && c.date_end !== c.date_start"> — {{ c.date_end }}</span>
          </div>
          <div v-if="c.participants && c.participants.length" class="conf-card__participants">
            <span class="conf-participants-label">👥 Участники:</span>
            <span v-for="p in c.participants" :key="p.id" class="tag">{{ p.short_name || p.full_name }}</span>
          </div>
          <div v-if="c.description" class="conf-card__desc">{{ c.description }}</div>
          <div class="conf-card__actions">
            <a v-if="c.url" :href="c.url" target="_blank" class="btn btn-ghost btn-sm">🔗 Сайт</a>
            <a v-if="c.location" :href="yandexMapUrl(c.location)" target="_blank" class="btn btn-ghost btn-sm">🗺 Карта</a>
            <button class="btn btn-ghost btn-sm" @click="openEdit(c)">✏️</button>
            <button class="btn btn-danger btn-sm" @click="del(c)">🗑</button>
          </div>
        </div>
        <div v-if="c.photo_path" class="conf-card__photo"
             :style="`background-image:url(/uploads/${c.photo_path.split('/uploads/')[1] || c.photo_path})`"></div>
      </div>
    </div>

    <!-- Modal -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать конференцию' : 'Новая конференция' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>

          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.title" placeholder="Название конференции" />
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Организатор</label>
              <input class="input" v-model="form.organizer" placeholder="Организация" />
            </div>
            <div class="form-group">
              <label class="form-label">Адрес</label>
              <div class="input-with-btn">
                <input class="input" v-model="form.location" placeholder="Город, улица, площадка" />
                <a v-if="form.location" :href="yandexMapUrl(form.location)" target="_blank"
                   class="btn btn-ghost btn-sm map-inline-btn" title="Открыть на Яндекс Картах">🗺</a>
              </div>
            </div>
          </div>

          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Дата начала</label>
              <input class="input" type="date" v-model="form.date_start" />
            </div>
            <div class="form-group">
              <label class="form-label">Дата окончания</label>
              <input class="input" type="date" v-model="form.date_end" />
            </div>
          </div>

          <div class="form-group">
            <label class="form-label">Ссылка</label>
            <input class="input" v-model="form.url" placeholder="https://..." />
          </div>

          <div class="form-group">
            <label class="form-label">Участники</label>
            <AuthorPicker
              v-model="form.participant_ids"
              :all-authors="allAuthors"
              @created="allAuthors.push($event)"
            />
          </div>

          <div class="form-group">
            <label class="form-label">Описание</label>
            <textarea class="textarea" v-model="form.description"></textarea>
          </div>

          <div class="form-group">
            <label style="display:flex;align-items:center;gap:8px;cursor:pointer;font-size:13px">
              <input type="checkbox" v-model="form.is_online" />
              Онлайн-формат
            </label>
          </div>

          <div class="form-group">
            <label class="form-label">Фото / баннер</label>
            <FileUpload v-model="form.photo" accept="image/*" icon="🖼" />
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
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { useToast } from 'vue-toastification'
import { conferencesApi, authorsApi, buildFormData } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'
import AuthorPicker from '@/components/common/AuthorPicker.vue'

const toast = useToast()
const conferences = ref([])
const allAuthors = ref([])
const search = ref('')
const dateFrom = ref('')
const dateTo = ref('')
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({
  title: '', organizer: '', location: '', date_start: '', date_end: '',
  url: '', description: '', is_online: false, photo: null, participant_ids: []
})

const filtered = computed(() => {
  let list = conferences.value
  const q = search.value.toLowerCase()
  if (q) list = list.filter(c => c.title.toLowerCase().includes(q) || (c.organizer || '').toLowerCase().includes(q))
  if (dateFrom.value) list = list.filter(c => !c.date_start || c.date_start >= dateFrom.value)
  if (dateTo.value) list = list.filter(c => !c.date_start || c.date_start <= dateTo.value)
  return list
})

const monthLabel = d => d ? format(parseISO(d), 'MMM', { locale: ru }).toUpperCase() : '?'
const dayLabel = d => d ? format(parseISO(d), 'd') : '?'
const statusClass = c => {
  if (!c.date_end) return ''
  const today = new Date().toISOString().slice(0, 10)
  if (c.date_end < today) return 'dot-past'
  if (c.date_start <= today) return 'dot-active'
  return 'dot-future'
}

const yandexMapUrl = location =>
  `https://yandex.ru/maps/?text=${encodeURIComponent(location)}`

function clearDates() { dateFrom.value = ''; dateTo.value = '' }

function openCreate() {
  editing.value = null
  form.value = {
    title: '', organizer: '', location: '', date_start: '', date_end: '',
    url: '', description: '', is_online: false, photo: null, participant_ids: []
  }
  showModal.value = true
}

function openEdit(c) {
  editing.value = c
  form.value = {
    title: c.title, organizer: c.organizer || '', location: c.location || '',
    date_start: c.date_start || '', date_end: c.date_end || '',
    url: c.url || '', description: c.description || '', is_online: c.is_online,
    photo: null,
    participant_ids: (c.participants || []).map(p => p.id)
  }
  showModal.value = true
}

async function save() {
  if (!form.value.title.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const fd = buildFormData({
      title: form.value.title,
      organizer: form.value.organizer || undefined,
      location: form.value.location || undefined,
      date_start: form.value.date_start || undefined,
      date_end: form.value.date_end || undefined,
      url: form.value.url || undefined,
      description: form.value.description || undefined,
      is_online: form.value.is_online,
      photo: form.value.photo,
      participant_ids: form.value.participant_ids,
    })
    if (editing.value) { await conferencesApi.update(editing.value.id, fd); toast.success('Обновлено') }
    else { await conferencesApi.create(fd); toast.success('Конференция добавлена') }
    showModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}

async function del(c) {
  if (!confirm(`Удалить «${c.title}»?`)) return
  try { await conferencesApi.delete(c.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}

async function load() {
  try {
    const [r, au] = await Promise.all([conferencesApi.list(), authorsApi.list()])
    conferences.value = r.data
    allAuthors.value = au.data
  } catch (e) {
    console.error(e)
    try { const r = await conferencesApi.list(); conferences.value = r.data } catch {}
    try { const r = await authorsApi.list(); allAuthors.value = r.data } catch {}
  }
}
onMounted(load)
</script>

<style scoped>
/* Filters layout fix */
.conf-filters {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}
.date-range-group {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.date-range-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--c-text2);
  white-space: nowrap;
  margin: 0;
}
.date-input {
  width: 150px;
}

/* Location with map link */
.conf-location { display: inline-flex; align-items: center; gap: 4px; }
.map-link {
  font-size: 14px;
  text-decoration: none;
  opacity: 0.7;
  transition: opacity 0.15s;
}
.map-link:hover { opacity: 1; }

/* Address field with map button */
.input-with-btn {
  display: flex;
  align-items: center;
  gap: 8px;
}
.input-with-btn .input { flex: 1; }
.map-inline-btn { flex-shrink: 0; }

/* Participants in card */
.conf-card__participants {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 6px;
  margin-top: 2px;
}
.conf-participants-label {
  font-size: 12px;
  color: var(--c-text2);
}

.conf-list { display: flex; flex-direction: column; gap: 12px; }
.conf-card {
  display: flex; gap: 0;
  background: var(--c-bg2); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); overflow: hidden;
}
.conf-card__date-col {
  width: 72px; flex-shrink: 0;
  background: var(--c-bg3); border-right: 1px solid var(--c-border);
  display: flex; flex-direction: column; align-items: center;
  justify-content: center; padding: 16px 8px; gap: 2px;
}
.conf-card__month { font-size: 10px; font-weight: 600; color: var(--c-text3); letter-spacing: 1px; }
.conf-card__day { font-size: 28px; font-weight: 700; color: var(--c-text); line-height: 1; }
.conf-card__status-dot { width: 8px; height: 8px; border-radius: 50%; background: var(--c-border2); margin-top: 4px; }
.dot-past   { background: var(--c-text3); }
.dot-active { background: var(--c-green); }
.dot-future { background: var(--c-accent); }
.conf-card__body { flex: 1; padding: 14px 18px; display: flex; flex-direction: column; gap: 6px; }
.conf-card__title { font-size: 15px; font-weight: 600; }
.conf-card__meta { display: flex; gap: 12px; flex-wrap: wrap; font-size: 12px; color: var(--c-text2); }
.conf-card__desc { font-size: 13px; color: var(--c-text2); }
.conf-card__actions { display: flex; gap: 8px; margin-top: 4px; }
.conf-card__photo {
  width: 100px; flex-shrink: 0;
  background-size: cover; background-position: center;
}
</style>
