<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">📊</span> Отчётность</h1>
    </div>

    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: tab === t.key }" @click="tab = t.key">{{ t.icon }} {{ t.label }}</button>
    </div>

    <div v-if="error" class="alert alert-error">⚠️ {{ error }} <button class="btn btn-ghost btn-sm ml-auto" @click="loadAll">↺ Повторить</button></div>

    <!-- План публикаций -->
    <template v-if="tab === 'plan'">
      <div class="toolbar">
        <div class="search-bar">
          <span>🔍</span>
          <input v-model="planSearch" placeholder="Название или автор…" />
        </div>
        <select v-model="planType" class="select" aria-label="Вид">
          <option value="">Все виды</option>
          <option value="article">Статьи</option>
          <option value="proposal">Рац. предложения</option>
          <option value="software">ПО</option>
        </select>
        <span class="toolbar__label">с</span>
        <input v-model="dateFrom" class="input" type="date" aria-label="С даты" />
        <span class="toolbar__label">по</span>
        <input v-model="dateTo" class="input" type="date" aria-label="По дату" />
        <div class="flex gap-2">
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportPlan('docx')">⬇ DOCX</button>
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportPlan('csv')">⬇ Excel (CSV)</button>
          <button class="btn btn-secondary btn-sm" @click="print">🖨 Печать</button>
        </div>
      </div>
      <div class="print-title">План публикаций{{ periodLabel }}</div>
      <div class="card card--flush">
        <div class="table-wrap">
          <table>
            <thead>
              <tr><th>#</th><th>Вид</th><th>Название</th><th class="hide-sm">Авторы</th><th class="hide-sm">Сборник</th><th>Дата</th></tr>
            </thead>
            <tbody>
              <tr v-if="!filteredPlan.length"><td colspan="6" class="text-muted" style="text-align:center;padding:32px">{{ loading ? 'Загрузка…' : 'Нет данных' }}</td></tr>
              <tr v-for="(item, i) in filteredPlan" :key="`${item.type}-${item.id}`" class="row-click"
                @click="$router.push({ name: ROUTES[item.type], query: { open: item.id } })">
                <td class="text-muted text-sm">{{ i + 1 }}</td>
                <td>
                  <span class="badge" :class="TYPE_BADGE[item.type]">{{ TYPE_LABEL[item.type] }}</span>
                  <div v-if="item.subtype" class="cell-sub">{{ item.subtype }}</div>
                </td>
                <td style="max-width:420px"><div class="cell-title">{{ item.title }}</div></td>
                <td class="hide-sm text-sm" style="max-width:240px">{{ item.authors.join(', ') || '—' }}</td>
                <td class="hide-sm text-muted text-sm">{{ item.collection_name || '—' }}</td>
                <td class="text-muted text-sm nowrap">{{ formatDateNum(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="results-count">
        Всего: {{ filteredPlan.length }} ·
        статей {{ counts.article }}, рац. предложений {{ counts.proposal }}, ПО {{ counts.software }}
      </div>
    </template>

    <!-- Сборники -->
    <template v-else>
      <div class="toolbar">
        <span class="text-muted text-sm">Сборники и опубликованные в них статьи</span>
        <div class="ml-auto flex gap-2">
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportCollections('docx')">⬇ DOCX</button>
          <button class="btn btn-secondary btn-sm" :disabled="exporting" @click="exportCollections('csv')">⬇ Excel (CSV)</button>
          <button class="btn btn-secondary btn-sm" @click="print">🖨 Печать</button>
        </div>
      </div>
      <div class="print-title">Список сборников</div>
      <div v-if="!collectionsList.length" class="card"><div class="empty-state"><div class="empty-state__text">Сборников нет</div></div></div>
      <div v-for="c in collectionsList" :key="c.id" class="coll card">
        <div class="coll__head">
          <div class="coll__title">{{ c.name }}</div>
          <span class="badge badge-blue">{{ pluralize(c.articles_count, 'статья', 'статьи', 'статей') }}</span>
          <span v-if="c.is_past === true" class="badge badge-gray">Завершён</span>
          <span v-else-if="c.is_past === false" class="badge badge-green">Активен</span>
        </div>
        <div class="coll__meta">
          <span v-if="c.university">🏛 {{ c.university }}</span>
          <span v-if="c.date_start || c.date_end">📅 {{ formatRange(c.date_start, c.date_end) }}</span>
          <a v-if="c.url" :href="c.url" target="_blank" rel="noopener noreferrer">🔗 Сайт</a>
        </div>
        <ol v-if="c.articles.length" class="coll__articles">
          <li v-for="a in c.articles" :key="a.id">
            <RouterLink :to="{ name: 'Articles', query: { open: a.id } }">{{ a.title }}</RouterLink>
          </li>
        </ol>
        <div v-else class="text-dim text-sm">Статей не прикреплено</div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useToast } from 'vue-toastification'
import { reportsApi } from '@/utils/api'
import { formatDateNum, formatRange, pluralize } from '@/utils/format'

const toast = useToast()
const tabs = [
  { key: 'plan', icon: '📋', label: 'План публикаций' },
  { key: 'collections', icon: '📚', label: 'Список сборников' },
]
const TYPE_LABEL = { article: 'Статья', proposal: 'Рац. предл.', software: 'ПО' }
const TYPE_BADGE = { article: 'badge-blue', proposal: 'badge-amber', software: 'badge-teal' }
const ROUTES = { article: 'Articles', proposal: 'Proposals', software: 'Software' }

const tab = ref('plan')
const plan = ref([])
const collectionsList = ref([])
const loading = ref(false)
const exporting = ref(false)
const error = ref('')
const planSearch = ref('')
const planType = ref('')
const dateFrom = ref('')
const dateTo = ref('')

const planParams = computed(() => ({
  type: planType.value || undefined, date_from: dateFrom.value || undefined, date_to: dateTo.value || undefined,
}))
const filteredPlan = computed(() => {
  const q = planSearch.value.trim().toLowerCase()
  if (!q) return plan.value
  return plan.value.filter(i => i.title.toLowerCase().includes(q) || i.authors.some(a => a.toLowerCase().includes(q)))
})
const counts = computed(() => {
  const c = { article: 0, proposal: 0, software: 0 }
  filteredPlan.value.forEach(i => c[i.type]++)
  return c
})
const periodLabel = computed(() => {
  if (!dateFrom.value && !dateTo.value) return ''
  return ` за период ${dateFrom.value ? formatDateNum(dateFrom.value) : '…'} — ${dateTo.value ? formatDateNum(dateTo.value) : 'н.в.'}`
})

async function loadPlan() {
  loading.value = true
  try { plan.value = (await reportsApi.plan(planParams.value)).data; error.value = '' }
  catch (e) { error.value = e.message }
  finally { loading.value = false }
}
async function loadAll() {
  await loadPlan()
  try { collectionsList.value = (await reportsApi.collectionsList()).data } catch (e) { error.value = e.message }
}
watch(planParams, loadPlan)
onMounted(loadAll)

async function run(fn) {
  exporting.value = true
  try { await fn() } catch (e) { toast.error(e.message) } finally { exporting.value = false }
}
const exportPlan = fmt => run(() => reportsApi.exportPlan({ format: fmt, ...planParams.value }))
const exportCollections = fmt => run(() => reportsApi.exportCollections(fmt))
const print = () => window.print()
</script>

<style scoped>
.coll { margin-bottom: 14px; }
.coll__head { display: flex; align-items: center; gap: 8px; flex-wrap: wrap; margin-bottom: 6px; }
.coll__title { font-size: 15px; font-weight: 600; margin-right: auto; }
.coll__meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--c-text2); margin-bottom: 10px; }
.coll__articles { padding-left: 22px; font-size: 13px; display: flex; flex-direction: column; gap: 3px; }
.coll__articles a { color: var(--c-text); }
@media print { .coll { break-inside: avoid; border-bottom: 1px solid #ccc; border-radius: 0; padding-bottom: 12px; } }
</style>
