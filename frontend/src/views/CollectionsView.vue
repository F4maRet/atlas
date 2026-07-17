<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">📚</span> Сборники</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить сборник</button>
    </div>

    <div class="collections-grid">
      <div v-if="!collections.length" class="empty-state">
        <div class="empty-state__icon">📚</div>
        <div class="empty-state__text">Сборников пока нет</div>
      </div>
      <div v-for="c in collections" :key="c.id" class="collection-card">
        <div class="collection-card__photo" :style="c.photo_path ? `background-image:url(${photoUrl(c)})` : ''">
          <span v-if="!c.photo_path" style="font-size:32px">📚</span>
        </div>
        <div class="collection-card__body">
          <div class="collection-card__title">{{ c.name }}</div>
          <div v-if="c.university" class="collection-card__uni">🏛 {{ c.university }}</div>
          <div class="collection-card__dates" v-if="c.date_start || c.date_end">
            📅 {{ c.date_start || '?' }} — {{ c.date_end || '?' }}
          </div>
          <div class="collection-card__status">
            <span v-if="c.is_past === true" class="badge badge-gray">Завершён</span>
            <span v-else-if="c.is_past === false" class="badge badge-green">Активен</span>
            <span v-else class="badge badge-amber">Дата не указана</span>
          </div>
          <a v-if="c.url" :href="c.url" target="_blank" class="collection-card__link">🔗 Ссылка</a>
          <div class="collection-card__actions">
            <button class="btn btn-ghost btn-sm" @click="openEdit(c)">✏️ Редактировать</button>
            <button class="btn btn-danger btn-sm" @click="del(c)">🗑</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modal -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать сборник' : 'Новый сборник' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">Название *</label>
            <input class="input" v-model="form.name" placeholder="Название сборника / конференции" />
          </div>
          <div class="form-group">
            <label class="form-label">Университет / организатор</label>
            <input class="input" v-model="form.university" placeholder="Наименование организации" />
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
            <label class="form-label">Ссылка (URL)</label>
            <input class="input" v-model="form.url" placeholder="https://..." />
          </div>
          <div class="form-group">
            <label class="form-label">Описание</label>
            <textarea class="textarea" v-model="form.description" placeholder="Краткое описание"></textarea>
          </div>
          <div class="form-group">
            <label class="form-label">Обложка / фото</label>
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
import { ref, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { collectionsApi, buildFormData } from '@/utils/api'
import FileUpload from '@/components/common/FileUpload.vue'

const toast = useToast()
const collections = ref([])
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ name: '', university: '', date_start: '', date_end: '', url: '', description: '', photo: null })

const photoUrl = c => c.photo_path ? `/uploads/${c.photo_path.split('/uploads/')[1] || c.photo_path}` : ''

function openCreate() {
  editing.value = null
  form.value = { name: '', university: '', date_start: '', date_end: '', url: '', description: '', photo: null }
  showModal.value = true
}
function openEdit(c) {
  editing.value = c
  form.value = { name: c.name, university: c.university || '', date_start: c.date_start || '', date_end: c.date_end || '', url: c.url || '', description: c.description || '', photo: null }
  showModal.value = true
}

async function save() {
  if (!form.value.name.trim()) return toast.error('Введите название')
  saving.value = true
  try {
    const fd = buildFormData({ name: form.value.name, university: form.value.university || undefined, date_start: form.value.date_start || undefined, date_end: form.value.date_end || undefined, url: form.value.url || undefined, description: form.value.description || undefined, photo: form.value.photo })
    if (editing.value) { await collectionsApi.update(editing.value.id, fd); toast.success('Обновлено') }
    else { await collectionsApi.create(fd); toast.success('Сборник создан') }
    showModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}

async function del(c) {
  if (!confirm(`Удалить сборник «${c.name}»?`)) return
  try { await collectionsApi.delete(c.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}

async function load() {
  try {
    const r = await collectionsApi.list()
    collections.value = r.data
  } catch (e) {
    console.error(e)
  }
}
onMounted(load)
</script>

<style scoped>
.collections-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
}
.collection-card {
  background: var(--c-bg2); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); overflow: hidden;
}
.collection-card__photo {
  height: 120px; background: var(--c-bg3);
  display: flex; align-items: center; justify-content: center;
  background-size: cover; background-position: center;
}
.collection-card__body { padding: 16px; display: flex; flex-direction: column; gap: 6px; }
.collection-card__title { font-size: 15px; font-weight: 600; }
.collection-card__uni, .collection-card__dates { font-size: 12px; color: var(--c-text2); }
.collection-card__link { font-size: 12px; color: var(--c-accent); }
.collection-card__actions { display: flex; gap: 8px; margin-top: 8px; }
.collection-card__status { margin-top: 2px; }
</style>
