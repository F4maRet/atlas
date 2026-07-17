<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">👤</span> Авторы</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить автора</button>
    </div>

    <!-- Rating / Оценочная ведомость -->
    <div class="card" style="margin-bottom:24px">
      <h3 style="margin-bottom:16px">📊 Оценочная ведомость</h3>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>#</th>
              <th>Автор</th>
              <th>Организация</th>
              <th style="text-align:center">Статьи</th>
              <th style="text-align:center">Рац. предл.</th>
              <th style="text-align:center">ПО</th>
              <th style="text-align:center">Итого</th>
            </tr>
          </thead>
          <tbody>
            <tr v-if="!stats.length">
              <td colspan="7" style="text-align:center;padding:24px" class="text-muted">Нет данных</td>
            </tr>
            <tr v-for="(a, i) in stats" :key="a.id">
              <td>
                <span class="rank-badge" :class="rankClass(i)">{{ i + 1 }}</span>
              </td>
              <td>
                <div style="font-weight:500">{{ a.full_name }}</div>
                <div v-if="a.email" class="text-muted text-sm">{{ a.email }}</div>
              </td>
              <td class="text-muted text-sm">{{ a.organization || '—' }}</td>
              <td style="text-align:center">
                <span class="badge badge-blue">{{ a.articles_count }}</span>
              </td>
              <td style="text-align:center">
                <span class="badge badge-amber">{{ a.proposals_count }}</span>
              </td>
              <td style="text-align:center">
                <span class="badge badge-teal">{{ a.software_count }}</span>
              </td>
              <td style="text-align:center">
                <strong>{{ a.total }}</strong>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- All authors table -->
    <div class="card" style="padding:0;overflow:hidden">
      <div style="padding:16px 20px;border-bottom:1px solid var(--c-border)">
        <h3>Справочник авторов</h3>
      </div>
      <div class="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ФИО</th><th>Краткое имя</th><th>Email</th><th>Организация</th><th>Должность</th><th></th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="a in authors" :key="a.id">
              <td style="font-weight:500">{{ a.full_name }}</td>
              <td class="text-muted text-sm">{{ a.short_name || '—' }}</td>
              <td class="text-muted text-sm">{{ a.email || '—' }}</td>
              <td class="text-muted text-sm">{{ a.organization || '—' }}</td>
              <td class="text-muted text-sm">{{ a.position || '—' }}</td>
              <td>
                <div class="flex-center gap-2">
                  <button class="btn btn-ghost btn-sm btn-icon" @click="openEdit(a)">✏️</button>
                  <button class="btn btn-danger btn-sm btn-icon" @click="del(a)">🗑</button>
                </div>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Modal -->
    <Transition name="fade">
      <div v-if="showModal" class="modal-overlay" @click.self="showModal=false">
        <div class="modal">
          <div class="modal-header">
            <h2>{{ editing ? 'Редактировать автора' : 'Новый автор' }}</h2>
            <button class="btn btn-ghost btn-sm btn-icon" @click="showModal=false">✕</button>
          </div>
          <div class="form-group">
            <label class="form-label">ФИО *</label>
            <input class="input" v-model="form.full_name" placeholder="Фамилия Имя Отчество" />
          </div>
          <div class="form-row">
            <div class="form-group">
              <label class="form-label">Краткое имя</label>
              <input class="input" v-model="form.short_name" placeholder="Фамилия И.О." />
            </div>
            <div class="form-group">
              <label class="form-label">Email</label>
              <input class="input" type="email" v-model="form.email" placeholder="email@example.com" />
            </div>
          </div>
          <div class="form-group">
            <label class="form-label">Организация</label>
            <input class="input" v-model="form.organization" placeholder="Место работы / учёбы" />
          </div>
          <div class="form-group">
            <label class="form-label">Должность</label>
            <input class="input" v-model="form.position" placeholder="Должность / звание" />
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
import { authorsApi } from '@/utils/api'

const toast = useToast()
const authors = ref([])
const stats = ref([])
const showModal = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({ full_name: '', short_name: '', email: '', organization: '', position: '' })

const rankClass = i => i === 0 ? 'rank-gold' : i === 1 ? 'rank-silver' : i === 2 ? 'rank-bronze' : ''

function openCreate() {
  editing.value = null
  form.value = { full_name: '', short_name: '', email: '', organization: '', position: '' }
  showModal.value = true
}
function openEdit(a) {
  editing.value = a
  form.value = { full_name: a.full_name, short_name: a.short_name || '', email: a.email || '', organization: a.organization || '', position: a.position || '' }
  showModal.value = true
}
async function save() {
  if (!form.value.full_name.trim()) return toast.error('Введите ФИО')
  saving.value = true
  try {
    if (editing.value) { await authorsApi.update(editing.value.id, form.value); toast.success('Обновлено') }
    else { await authorsApi.create(form.value); toast.success('Автор добавлен') }
    showModal.value = false
    await load()
  } catch (e) { toast.error(e.message) }
  finally { saving.value = false }
}
async function del(a) {
  if (!confirm(`Удалить автора «${a.full_name}»?`)) return
  try { await authorsApi.delete(a.id); toast.success('Удалено'); await load() }
  catch (e) { toast.error(e.message) }
}
async function load() {
  try {
    const [au, st] = await Promise.all([authorsApi.list(), authorsApi.stats()])
    authors.value = au.data
    stats.value = st.data
  } catch (e) {
    console.error(e)
    try { const r = await authorsApi.list(); authors.value = r.data } catch {}
    try { const r = await authorsApi.stats(); stats.value = r.data } catch {}
  }
}
onMounted(load)
</script>

<style scoped>
.rank-badge {
  display: inline-flex; align-items: center; justify-content: center;
  width: 26px; height: 26px; border-radius: 50%;
  font-size: 12px; font-weight: 700;
  background: var(--c-surface); color: var(--c-text2);
}
.rank-gold   { background: rgba(245,158,11,0.2); color: #f59e0b; }
.rank-silver { background: rgba(139,149,181,0.2); color: #a0aabf; }
.rank-bronze { background: rgba(160,100,60,0.2); color: #c87941; }
</style>
