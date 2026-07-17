<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">📊</span> Отчётность</h1>
    </div>

    <!-- Tab switcher -->
    <div class="tab-bar">
      <button v-for="t in tabs" :key="t.key" class="tab-btn" :class="{ active: tab === t.key }" @click="tab = t.key">
        {{ t.icon }} {{ t.label }}
      </button>
    </div>

    <!-- Publication plan -->
    <div v-if="tab === 'plan'">
      <div style="display:flex;gap:12px;margin-bottom:16px;align-items:center;flex-wrap:wrap">
        <div class="search-bar" style="flex:1;margin-bottom:0;height:40px;box-sizing:border-box">
          <span>🔍</span>
          <input v-model="planSearch" placeholder="Поиск..." />
        </div>
        <div style="display:flex;align-items:center;gap:8px;flex-shrink:0;height:40px">
          <label style="font-size:13px;font-weight:500;color:var(--c-text2);white-space:nowrap;margin:0">Тип:</label>
          <select class="select" style="width:150px;height:40px;box-sizing:border-box" v-model="planType">
            <option value="">Все</option>
            <option value="article">Статьи</option>
            <option value="proposal">Рац. предл.</option>
            <option value="software">ПО</option>
          </select>
        </div>
        <button class="btn btn-secondary" style="height:40px;box-sizing:border-box;white-space:nowrap;flex-shrink:0" @click="printPlan">🖨 Печать</button>
      </div>
      <div class="card" style="padding:0;overflow:hidden" id="plan-table">
        <div class="table-wrap">
          <table>
            <thead>
              <tr>
                <th>#</th><th>Тип</th><th>Название</th><th>Авторы</th><th>Сборник</th><th>Дата</th>
              </tr>
            </thead>
            <tbody>
              <tr v-if="!filteredPlan.length">
                <td colspan="6" style="text-align:center;padding:32px" class="text-muted">Нет данных</td>
              </tr>
              <tr v-for="(item, i) in filteredPlan" :key="`${item.type}-${item.id}`">
                <td class="text-muted text-sm">{{ i + 1 }}</td>
                <td>
                  <span class="badge" :class="typeBadge(item.type)">{{ typeLabel(item.type) }}</span>
                </td>
                <td style="max-width:320px"><div class="truncate">{{ item.title }}</div></td>
                <td style="max-width:200px">
                  <div class="truncate text-sm">{{ item.authors.join(', ') }}</div>
                </td>
                <td class="text-muted text-sm">{{ item.collection_name || '—' }}</td>
                <td class="text-muted text-sm">{{ formatDate(item.created_at) }}</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
      <div class="text-muted text-sm" style="margin-top:8px">
        Всего: {{ filteredPlan.length }} записей
      </div>
    </div>

    <!-- Collections list report -->
    <div v-if="tab === 'collections'">
      <div class="flex-center gap-3" style="margin-bottom:16px">
        <button class="btn btn-secondary" @click="printCollections">🖨 Печать</button>
      </div>
      <div id="coll-report">
        <div v-for="c in collectionsList" :key="c.id" class="coll-report-item">
          <div class="coll-report-item__header">
            <div class="coll-report-item__title">{{ c.name }}</div>
            <div class="flex-center gap-3">
              <span class="badge badge-blue">{{ c.articles_count }} статей</span>
              <span v-if="c.is_past === true" class="badge badge-gray">Завершён</span>
              <span v-else-if="c.is_past === false" class="badge badge-green">Активен</span>
            </div>
          </div>
          <div class="coll-report-item__meta">
            <span v-if="c.university">🏛 {{ c.university }}</span>
            <span v-if="c.date_start">📅 {{ c.date_start }} — {{ c.date_end || '?' }}</span>
            <a v-if="c.url" :href="c.url" target="_blank" class="text-sm">🔗 Сайт</a>
          </div>
          <div v-if="c.articles.length" class="coll-report-item__articles">
            <div v-for="a in c.articles" :key="a.id" class="coll-report-item__article">
              • {{ a.title }}
            </div>
          </div>
          <div v-else class="text-muted text-sm">Статей не прикреплено</div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { reportsApi } from '@/utils/api'

const tab = ref('plan')
const tabs = [
  { key: 'plan',        icon: '📋', label: 'План публикаций' },
  { key: 'collections', icon: '📚', label: 'Список сборников' },
]
const plan = ref([])
const collectionsList = ref([])
const planSearch = ref('')
const planType = ref('')

const filteredPlan = computed(() => {
  let list = plan.value
  if (planType.value) list = list.filter(i => i.type === planType.value)
  if (planSearch.value) {
    const q = planSearch.value.toLowerCase()
    list = list.filter(i => i.title.toLowerCase().includes(q) || i.authors.some(a => a.toLowerCase().includes(q)))
  }
  return list
})

const typeLabel = t => ({ article: 'Статья', proposal: 'Рац. предл.', software: 'ПО' })[t] || t
const typeBadge = t => ({ article: 'badge-blue', proposal: 'badge-amber', software: 'badge-teal' })[t] || 'badge-gray'
const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''

function printPlan() { window.print() }
function printCollections() { window.print() }

const reportError = ref('')
onMounted(async () => {
  try {
    const [p, c] = await Promise.all([reportsApi.plan(), reportsApi.collectionsList()])
    plan.value = p.data
    collectionsList.value = c.data
  } catch (e) {
    reportError.value = e.message || 'Ошибка загрузки отчётов'
    console.error(e)
    // Try individually
    try { const r = await reportsApi.plan(); plan.value = r.data } catch {}
    try { const r = await reportsApi.collectionsList(); collectionsList.value = r.data } catch {}
  }
})
</script>

<style scoped>
.tab-bar { display: flex; gap: 4px; margin-bottom: 20px; border-bottom: 1px solid var(--c-border); padding-bottom: 0; }
.tab-btn {
  padding: 8px 18px; border: none; background: none; cursor: pointer;
  font-family: var(--font); font-size: 13px; font-weight: 500;
  color: var(--c-text2); border-bottom: 2px solid transparent;
  margin-bottom: -1px; transition: var(--transition);
}
.tab-btn:hover { color: var(--c-text); }
.tab-btn.active { color: var(--c-accent); border-bottom-color: var(--c-accent); }

.coll-report-item {
  background: var(--c-bg2); border: 1px solid var(--c-border);
  border-radius: var(--radius-lg); padding: 18px 20px; margin-bottom: 16px;
}
.coll-report-item__header { display: flex; align-items: center; justify-content: space-between; margin-bottom: 6px; }
.coll-report-item__title { font-size: 15px; font-weight: 600; }
.coll-report-item__meta { display: flex; gap: 16px; flex-wrap: wrap; font-size: 12px; color: var(--c-text2); margin-bottom: 10px; }
.coll-report-item__articles { display: flex; flex-direction: column; gap: 3px; }
.coll-report-item__article { font-size: 13px; color: var(--c-text2); padding-left: 8px; }
</style>
