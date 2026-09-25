<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">📚</span> Сборники</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить сборник</button>
    </div>

    <div v-if="loadError" class="alert alert-error">⚠️ {{ loadError }} <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button></div>

    <div class="toolbar">
      <div class="search-bar">
        <span>🔍</span>
        <input v-model="search" placeholder="Название или организатор…" />
        <button v-if="search" class="search-bar__clear" @click="search = ''">✕</button>
      </div>
      <select v-model="status" class="select" aria-label="Статус">
        <option value="">Все</option>
        <option value="active">Активные</option>
        <option value="past">Завершённые</option>
      </select>
    </div>

    <div v-if="!filtered.length" class="card">
      <div class="empty-state">
        <div class="empty-state__icon">📚</div>
        <div class="empty-state__text">{{ collections.length ? 'Ничего не найдено' : 'Сборников пока нет' }}</div>
        <button v-if="!collections.length" class="btn btn-primary btn-sm" @click="openCreate">+ Добавить сборник</button>
      </div>
    </div>

    <div class="collections-grid">
      <article v-for="c in filtered" :key="c.id" class="collection-card" :class="{ highlight: highlightId === c.id }" :id="`col-${c.id}`">
        <div class="collection-card__photo" :style="c.photo_url ? { backgroundImage: `url(${c.photo_url})` } : null">
          <span v-if="!c.photo_url">📚</span>
          <span class="collection-card__status badge" :class="c.is_past === true ? 'badge-gray' : c.is_past === false ? 'badge-green' : 'badge-amber'">
            {{ c.is_past === true ? 'Завершён' : c.is_past === false ? 'Активен' : 'Без даты' }}
          </span>
        </div>
        <div class="collection-card__body">
          <div class="collection-card__title">{{ c.name }}</div>
          <div v-if="c.university" class="collection-card__meta">🏛 {{ c.university }}</div>
          <div v-if="c.date_start || c.date_end" class="collection-card__meta">📅 {{ formatRange(c.date_start, c.date_end) }}</div>
          <div v-if="c.description" class="collection-card__desc">{{ c.description }}</div>
          <div class="collection-card__footer">
            <button class="btn btn-ghost btn-sm" :disabled="!c.articles_count" @click="openArticles(c)">📄 {{ pluralize(c.articles_count, 'статья', 'статьи', 'статей') }}</button>
            <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer" class="btn btn-ghost btn-sm" title="Сайт">🔗</a>
            <span class="ml-auto"></span>
            <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(c)">✏️</button>
            <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(c)">🗑</button>
          </div>
        </div>
      </article>
    </div>

    <!-- Статьи сборника -->
    <Modal v-model="showArticles" :title="`Статьи сборника «${articlesOf?.name || ''}»`" size="lg">
      <div v-if="articlesLoading" class="flex-center" style="justify-content:center;padding:30px"><div class="spinner"></div></div>
      <div v-else-if="!collArticles.length" class="text-muted">Статей нет</div>
      <RouterLink v-for="a in collArticles" :key="a.id" :to="{ name: 'Articles', query: { open: a.id } }" class="list-link" @click="showArticles = false">
        <span class="grow">{{ a.title }}</span>
        <span class="text-dim text-sm">{{ a.authors.map(x => x.short_name || x.full_name).join(', ') }}</span>
      </RouterLink>
    </Modal>

    <!-- Форма -->
    <Modal v-model="showForm" :title="editing ? 'Редактировать сборник' : 'Новый сборник'" persistent>
      <form id="col-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">Название <span class="req">*</span></label>
          <input v-model="form.name" class="input" placeholder="Название сборника / конференции" required maxlength="500" />
        </div>
        <div class="form-group">
          <label class="form-label">Организатор (вуз, организация)</label>
          <input v-model="form.university" class="input" maxlength="500" />
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
          <label class="form-label">Ссылка</label>
          <input v-model="form.url" class="input" type="url" placeholder="https://…" />
        </div>
        <div class="form-group">
          <label class="form-label">Описание</label>
          <textarea v-model="form.description" class="textarea"></textarea>
        </div>
        <div class="form-group">
          <label class="form-label">Обложка</label>
          <div v-if="editing?.photo_url && !form.photo && !form.remove_photo" class="flex-center gap-3" style="margin-bottom:8px">
            <img :src="editing.photo_url" alt="" class="thumb" />
            <button type="button" class="btn btn-ghost btn-sm" @click="form.remove_photo = true">Убрать обложку</button>
          </div>
          <FileUpload v-model="form.photo" accept=".jpg,.jpeg,.png,.gif,.webp" hint="JPG, PNG, WEBP" icon="🖼" :max-mb="10" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="col-form" :disabled="saving">{{ saving ? 'Сохранение…' : (editing ? 'Сохранить' : 'Создать') }}</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, nextTick } from 'vue'
import { useToast } from 'vue-toastification'
import { collectionsApi, articlesApi, buildFormData } from '@/utils/api'
import { formatRange, pluralize } from '@/utils/format'
import { useOpenFromQuery } from '@/composables/useOpenFromQuery'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import FileUpload from '@/components/common/FileUpload.vue'

const toast = useToast()
const collections = ref([])
const loadError = ref('')
const search = ref('')
const status = ref('')
const highlightId = ref(null)

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  return collections.value.filter(c => {
    if (q && !(c.name.toLowerCase().includes(q) || (c.university || '').toLowerCase().includes(q))) return false
    if (status.value === 'active' && c.is_past === true) return false
    if (status.value === 'past' && c.is_past !== true) return false
    return true
  })
})

async function load() {
  loadError.value = ''
  try { collections.value = (await collectionsApi.list()).data } catch (e) { loadError.value = e.message }
}
onMounted(load)

useOpenFromQuery(collections, c => {
  highlightId.value = c.id
  nextTick(() => document.getElementById(`col-${c.id}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' }))
  setTimeout(() => { highlightId.value = null }, 2500)
})

// ── Статьи сборника ──────────────────────────────────────────────────────────
const showArticles = ref(false)
const articlesOf = ref(null)
const collArticles = ref([])
const articlesLoading = ref(false)
async function openArticles(c) {
  articlesOf.value = c
  showArticles.value = true
  articlesLoading.value = true
  try { collArticles.value = (await articlesApi.list({ collection_id: c.id })).data } catch (e) { toast.error(e.message) }
  finally { articlesLoading.value = false }
}

// ── Форма ────────────────────────────────────────────────────────────────────
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})
function openCreate() {
  editing.value = null
  form.value = { name: '', university: '', date_start: '', date_end: '', url: '', description: '', photo: null, remove_photo: false }
  showForm.value = true
}
function openEdit(c) {
  editing.value = c
  form.value = { name: c.name, university: c.university || '', date_start: c.date_start || '', date_end: c.date_end || '',
    url: c.url || '', description: c.description || '', photo: null, remove_photo: false }
  showForm.value = true
}
async function save() {
  const f = form.value
  if (!f.name.trim()) return toast.error('Введите название')
  if (f.date_start && f.date_end && f.date_end < f.date_start) return toast.error('Дата окончания раньше даты начала')
  saving.value = true
  try {
    const fd = buildFormData({ name: f.name.trim(), university: f.university, date_start: f.date_start, date_end: f.date_end,
      url: f.url, description: f.description, photo: f.photo, remove_photo: f.remove_photo || undefined })
    if (editing.value) { await collectionsApi.update(editing.value.id, fd); toast.success('Сохранено') }
    else { await collectionsApi.create(fd); toast.success('Сборник создан') }
    showForm.value = false
    await load()
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function remove(c) {
  const msg = c.articles_count
    ? `«${c.name}»\n\nСтатьи сборника (${c.articles_count}) не удалятся, но будут откреплены от него.`
    : `«${c.name}»`
  if (!await confirmDialog({ title: 'Удалить сборник?', message: msg })) return
  try { await collectionsApi.delete(c.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}
</script>

<style scoped>
.collections-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); gap: 18px; }
.collection-card { background: var(--c-bg2); border: 1px solid var(--c-border); border-radius: var(--radius-lg); overflow: hidden; display: flex; flex-direction: column; transition: box-shadow 0.3s, border-color 0.3s; }
.collection-card.highlight { border-color: var(--c-accent); box-shadow: 0 0 0 3px rgba(79,124,255,0.3); }
.collection-card__photo { position: relative; height: 120px; background: var(--c-bg3) center / cover; display: flex; align-items: center; justify-content: center; font-size: 32px; }
.collection-card__status { position: absolute; top: 10px; right: 10px; backdrop-filter: blur(6px); }
.collection-card__body { padding: 14px 16px; display: flex; flex-direction: column; gap: 5px; flex: 1; }
.collection-card__title { font-size: 15px; font-weight: 600; line-height: 1.35; }
.collection-card__meta { font-size: 12px; color: var(--c-text2); }
.collection-card__desc { font-size: 12px; color: var(--c-text3); display: -webkit-box; -webkit-line-clamp: 3; -webkit-box-orient: vertical; overflow: hidden; }
.collection-card__footer { display: flex; align-items: center; gap: 6px; margin-top: auto; padding-top: 10px; }
.thumb { width: 90px; height: 56px; object-fit: cover; border-radius: 6px; border: 1px solid var(--c-border); }
.list-link { display: flex; gap: 10px; align-items: center; padding: 8px 10px; border-radius: 7px; color: var(--c-text); font-size: 13px; }
.list-link:hover { background: var(--c-bg3); text-decoration: none; }
.list-link .grow { flex: 1; min-width: 0; }
</style>
