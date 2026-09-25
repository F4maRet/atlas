<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">👤</span> Авторы</h1>
      <button class="btn btn-primary" @click="openCreate">+ Добавить автора</button>
    </div>

    <div class="tab-bar">
      <button class="tab-btn" :class="{ active: tab === 'list' }" @click="tab = 'list'">📇 Справочник ({{ stats.length }})</button>
      <button class="tab-btn" :class="{ active: tab === 'rating' }" @click="tab = 'rating'">📊 Оценочная ведомость</button>
    </div>

    <div v-if="loadError" class="alert alert-error">⚠️ {{ loadError }} <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button></div>

    <!-- Справочник -->
    <template v-if="tab === 'list'">
      <div class="toolbar">
        <div class="search-bar">
          <span>🔍</span>
          <input v-model="search" placeholder="ФИО, организация, email…" />
          <button v-if="search" class="search-bar__clear" @click="search = ''">✕</button>
        </div>
      </div>
      <div class="card card--flush">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <SortTh k="name" v-bind="sortProps">ФИО</SortTh>
                <SortTh k="org" v-bind="sortProps" class="hide-sm">Организация</SortTh>
                <SortTh k="position" v-bind="sortProps" class="hide-sm">Должность</SortTh>
                <SortTh k="total" v-bind="sortProps" class="num">Работ</SortTh>
                <th class="col-actions"></th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!sorted.length">
                <td colspan="5">
                  <div class="empty-state">
                    <div class="empty-state__icon">👤</div>
                    <div class="empty-state__text">{{ stats.length ? 'Ничего не найдено' : 'Справочник пуст' }}</div>
                  </div>
                </td>
              </tr>
              <tr v-for="a in sorted" :key="a.id" class="row-click" @click="openCard(a)">
                <td>
                  <div style="font-weight:500">{{ a.full_name }}</div>
                  <div class="cell-sub">{{ [a.short_name, a.email].filter(Boolean).join(' · ') }}</div>
                </td>
                <td class="hide-sm text-muted text-sm">{{ a.organization || '—' }}</td>
                <td class="hide-sm text-muted text-sm">{{ a.position || '—' }}</td>
                <td class="num">
                  <span v-if="a.total || a.conferences_count" class="flex-center gap-2" style="justify-content:center">
                    <span v-if="a.articles_count" class="badge badge-blue" title="Статьи">📄 {{ a.articles_count }}</span>
                    <span v-if="a.proposals_count" class="badge badge-amber" title="Рац. предложения">💡 {{ a.proposals_count }}</span>
                    <span v-if="a.software_count" class="badge badge-teal" title="ПО">💾 {{ a.software_count }}</span>
                    <span v-if="a.conferences_count" class="badge badge-gray" title="Конференции">🗓 {{ a.conferences_count }}</span>
                  </span>
                  <span v-else class="text-dim">—</span>
                </td>
                <td @click.stop>
                  <div class="cell-actions">
                    <button class="btn btn-ghost btn-sm btn-icon" title="Редактировать" @click="openEdit(a)">✏️</button>
                    <button class="btn btn-ghost btn-sm btn-icon" title="Объединить с другим автором" @click="openMerge(a)">⇄</button>
                    <button class="btn btn-danger btn-sm btn-icon" title="Удалить" @click="remove(a)">🗑</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="results-count">Показано {{ sorted.length }} из {{ stats.length }}</div>
    </template>

    <!-- Оценочная ведомость -->
    <template v-else>
      <div class="toolbar">
        <span class="text-muted text-sm">Итог — сумма статей, рац. предложений и ПО. Участие в конференциях показано отдельно.</span>
        <div class="ml-auto flex gap-2">
          <button class="btn btn-secondary btn-sm" @click="exportRating('docx')">⬇ DOCX</button>
          <button class="btn btn-secondary btn-sm" @click="exportRating('csv')">⬇ Excel (CSV)</button>
          <button class="btn btn-secondary btn-sm" @click="print">🖨 Печать</button>
        </div>
      </div>
      <div class="print-title">Оценочная ведомость авторов на {{ formatDate(new Date()) }}</div>
      <div class="card card--flush">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Автор</th><th class="hide-sm">Организация</th>
                <th class="num">Статьи</th><th class="num">Рац. предл.</th><th class="num">ПО</th><th class="num">Конф.</th><th class="num">Итого</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!stats.length"><td colspan="8" class="text-muted" style="text-align:center;padding:24px">Нет данных</td></tr>
              <tr v-for="(a, i) in stats" :key="a.id" class="row-click" @click="openCard(a)">
                <td><span class="rank" :class="`rank-${i}`">{{ i + 1 }}</span></td>
                <td style="font-weight:500">{{ a.full_name }}</td>
                <td class="hide-sm text-muted text-sm">{{ a.organization || '—' }}</td>
                <td class="num">{{ a.articles_count }}</td>
                <td class="num">{{ a.proposals_count }}</td>
                <td class="num">{{ a.software_count }}</td>
                <td class="num text-muted">{{ a.conferences_count }}</td>
                <td class="num"><strong>{{ a.total }}</strong></td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </template>

    <!-- Карточка автора -->
    <Modal v-model="showCard" size="lg" :title="card?.author.full_name">
      <div v-if="cardLoading" class="flex-center" style="justify-content:center;padding:40px"><div class="spinner"></div></div>
      <template v-else-if="card">
        <div class="detail-grid" style="margin-bottom:16px">
          <div><div class="detail-label">Краткое имя</div><div class="detail-val">{{ card.author.short_name || '—' }}</div></div>
          <div><div class="detail-label">Email</div><div class="detail-val">
            <a v-if="card.author.email" :href="`mailto:${card.author.email}`">{{ card.author.email }}</a><span v-else>—</span>
          </div></div>
          <div><div class="detail-label">Организация</div><div class="detail-val">{{ card.author.organization || '—' }}</div></div>
          <div><div class="detail-label">Должность</div><div class="detail-val">{{ card.author.position || '—' }}</div></div>
        </div>
        <div v-for="g in workGroups" :key="g.key" class="works">
          <div class="works__head">{{ g.icon }} {{ g.label }} <span class="badge badge-gray">{{ card[g.key].length }}</span></div>
          <div v-if="!card[g.key].length" class="text-dim text-sm">—</div>
          <RouterLink v-for="w in card[g.key]" :key="w.id" :to="{ name: g.route, query: { open: w.id } }" class="works__item" @click="showCard = false">
            <span class="works__title">{{ w.title }}</span>
            <span v-if="w.subtitle" class="badge badge-gray">{{ w.subtitle }}</span>
            <span class="text-dim text-sm nowrap">{{ formatDate(w.date) }}</span>
          </RouterLink>
        </div>
      </template>
      <template #footer>
        <button class="btn btn-ghost" @click="showCard = false; openEdit(card.author)">✏️ Редактировать</button>
        <button class="btn btn-secondary" @click="showCard = false">Закрыть</button>
      </template>
    </Modal>

    <!-- Форма -->
    <Modal v-model="showForm" :title="editing ? 'Редактировать автора' : 'Новый автор'">
      <form id="author-form" @submit.prevent="save">
        <div class="form-group">
          <label class="form-label">ФИО <span class="req">*</span></label>
          <input v-model="form.full_name" class="input" placeholder="Фамилия Имя Отчество" required maxlength="255" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label class="form-label">Краткое имя</label>
            <input v-model="form.short_name" class="input" :placeholder="abbreviateName(form.full_name) || 'Фамилия И.О.'" maxlength="100" />
            <div class="form-hint">Если не заполнено — сформируется автоматически</div>
          </div>
          <div class="form-group">
            <label class="form-label">Email</label>
            <input v-model="form.email" class="input" type="email" placeholder="email@example.com" maxlength="255" />
          </div>
        </div>
        <div class="form-group">
          <label class="form-label">Организация</label>
          <input v-model="form.organization" class="input" placeholder="Место службы / работы / учёбы" maxlength="500" />
        </div>
        <div class="form-group">
          <label class="form-label">Должность / звание</label>
          <input v-model="form.position" class="input" maxlength="255" />
        </div>
      </form>
      <template #footer>
        <button class="btn btn-secondary" type="button" @click="showForm = false">Отмена</button>
        <button class="btn btn-primary" type="submit" form="author-form" :disabled="saving">{{ saving ? 'Сохранение…' : 'Сохранить' }}</button>
      </template>
    </Modal>

    <!-- Объединение -->
    <Modal v-model="showMerge" title="Объединить авторов" size="sm">
      <p class="text-muted text-sm" style="margin-bottom:14px">
        Все работы и участие в конференциях автора <strong style="color:var(--c-text)">{{ mergeSource?.full_name }}</strong>
        будут перенесены к выбранному автору, а эта запись — удалена. Используйте для устранения дублей
        («Иванов И.И.» и «Иванов Иван Иванович»).
      </p>
      <div class="form-group">
        <label class="form-label">Основная запись</label>
        <select v-model="mergeTarget" class="select">
          <option value="">— выберите —</option>
          <option v-for="a in mergeCandidates" :key="a.id" :value="String(a.id)">{{ a.full_name }} ({{ a.total }})</option>
        </select>
      </div>
      <template #footer>
        <button class="btn btn-secondary" @click="showMerge = false">Отмена</button>
        <button class="btn btn-primary" :disabled="!mergeTarget || saving" @click="merge">Объединить</button>
      </template>
    </Modal>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useToast } from 'vue-toastification'
import { authorsApi, reportsApi } from '@/utils/api'
import { formatDate, abbreviateName } from '@/utils/format'
import { useSort } from '@/composables/useSort'
import { useOpenFromQuery } from '@/composables/useOpenFromQuery'
import { confirmDialog } from '@/composables/useConfirm'
import Modal from '@/components/common/Modal.vue'
import SortTh from '@/components/common/SortTh.vue'

const toast = useToast()
const tab = ref('list')
const stats = ref([])
const loadError = ref('')
const search = ref('')

const workGroups = [
  { key: 'articles', label: 'Научные статьи', icon: '📄', route: 'Articles' },
  { key: 'proposals', label: 'Рац. предложения', icon: '💡', route: 'Proposals' },
  { key: 'software', label: 'Программное обеспечение', icon: '💾', route: 'Software' },
  { key: 'conferences', label: 'Участие в конференциях', icon: '🗓', route: 'Conferences' },
]

const filtered = computed(() => {
  const q = search.value.trim().toLowerCase()
  if (!q) return stats.value
  return stats.value.filter(a => [a.full_name, a.short_name, a.organization, a.email, a.position]
    .some(v => (v || '').toLowerCase().includes(q)))
})
const { sortKey, sortDir, toggle, sorted } = useSort(filtered, {
  name: a => a.full_name, org: a => a.organization, position: a => a.position, total: a => a.total,
}, { key: 'name', dir: 'asc' })
const sortProps = computed(() => ({ sortKey: sortKey.value, sortDir: sortDir.value, toggle }))

async function load() {
  loadError.value = ''
  try { stats.value = (await authorsApi.stats()).data } catch (e) { loadError.value = e.message }
}
onMounted(load)

// ── Карточка ─────────────────────────────────────────────────────────────────
const showCard = ref(false)
const card = ref(null)
const cardLoading = ref(false)
async function openCard(a) {
  showCard.value = true
  cardLoading.value = true
  card.value = { author: a }
  try { card.value = (await authorsApi.works(a.id)).data } catch (e) { toast.error(e.message); showCard.value = false }
  finally { cardLoading.value = false }
}
useOpenFromQuery(stats, openCard)

// ── Форма ────────────────────────────────────────────────────────────────────
const showForm = ref(false)
const editing = ref(null)
const saving = ref(false)
const form = ref({})
function openCreate() {
  editing.value = null
  form.value = { full_name: '', short_name: '', email: '', organization: '', position: '' }
  showForm.value = true
}
function openEdit(a) {
  editing.value = a
  form.value = { full_name: a.full_name, short_name: a.short_name || '', email: a.email || '', organization: a.organization || '', position: a.position || '' }
  showForm.value = true
}
async function save() {
  if (!form.value.full_name.trim()) return toast.error('Введите ФИО')
  saving.value = true
  try {
    if (editing.value) { await authorsApi.update(editing.value.id, form.value); toast.success('Сохранено') }
    else {
      const exists = stats.value.find(a => a.full_name.toLowerCase() === form.value.full_name.trim().toLowerCase())
      if (exists) toast.info('Такой автор уже есть в справочнике')
      else { await authorsApi.create(form.value); toast.success('Автор добавлен') }
    }
    showForm.value = false
    await load()
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}
async function remove(a) {
  const works = a.total + a.conferences_count
  const ok = await confirmDialog({
    title: 'Удалить автора?',
    message: works
      ? `${a.full_name} указан(а) в ${works} записях. Работы не удалятся, но автор будет убран из них.\n\nЕсли это дубль — лучше используйте «Объединить» (⇄).`
      : a.full_name,
  })
  if (!ok) return
  try { await authorsApi.delete(a.id); toast.success('Удалено'); await load() } catch (e) { toast.error(e.message) }
}

// ── Объединение ──────────────────────────────────────────────────────────────
const showMerge = ref(false)
const mergeSource = ref(null)
const mergeTarget = ref('')
const mergeCandidates = computed(() => {
  const src = mergeSource.value
  if (!src) return []
  const surname = src.full_name.split(' ')[0].toLowerCase()
  // Однофамильцы — вверху списка
  return stats.value.filter(a => a.id !== src.id).sort((a, b) =>
    (b.full_name.toLowerCase().startsWith(surname) - a.full_name.toLowerCase().startsWith(surname)) || a.full_name.localeCompare(b.full_name, 'ru'))
})
function openMerge(a) { mergeSource.value = a; mergeTarget.value = ''; showMerge.value = true }
async function merge() {
  saving.value = true
  try {
    await authorsApi.merge(mergeSource.value.id, Number(mergeTarget.value))
    toast.success('Авторы объединены')
    showMerge.value = false
    await load()
  } catch (e) { toast.error(e.message) } finally { saving.value = false }
}

async function exportRating(fmt) {
  try { await reportsApi.exportRating(fmt) } catch (e) { toast.error(e.message) }
}
const print = () => window.print()
</script>

<style scoped>
.rank { display: inline-flex; align-items: center; justify-content: center; width: 26px; height: 26px; border-radius: 50%; font-size: 12px; font-weight: 700; background: var(--c-surface); color: var(--c-text2); }
.rank-0 { background: rgba(245,158,11,0.2); color: #f59e0b; }
.rank-1 { background: rgba(139,149,181,0.25); color: #a0aabf; }
.rank-2 { background: rgba(200,121,65,0.2); color: #c87941; }
.works { margin-top: 14px; }
.works__head { font-size: 13px; font-weight: 600; display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.works__item { display: flex; align-items: center; gap: 8px; padding: 7px 10px; border-radius: 7px; color: var(--c-text); font-size: 13px; }
.works__item:hover { background: var(--c-bg3); text-decoration: none; }
.works__title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
</style>
