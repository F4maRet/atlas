<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">◈</span> Дашборд</h1>
      <span class="text-muted text-sm">Сводная информация системы</span>
    </div>

    <!-- Stat cards -->
    <div class="stats-grid" style="grid-template-columns: repeat(auto-fill, minmax(160px,1fr))">
      <RouterLink v-for="s in stats" :key="s.label" :to="s.link" class="stat-card stat-card--link">
        <div class="stat-card__label">{{ s.label }}</div>
        <div class="stat-card__value" :style="{ color: s.color }">{{ s.value }}</div>
        <div class="stat-card__sub">{{ s.sub }}</div>
      </RouterLink>
    </div>

    <!-- Row 1: Recent additions + Charts -->
    <div class="dash-row">

      <!-- Recent additions -->
      <div class="card dash-card">
        <div class="card-head">
          <h3>🕓 Последние добавления</h3>
        </div>
        <div v-if="recentAll.length === 0" class="text-muted text-sm">Нет данных</div>
        <div v-for="item in recentAll" :key="item._key" class="recent-item">
          <div class="recent-item__left">
            <span class="badge" :class="item.badgeClass">{{ item.typeLabel }}</span>
          </div>
          <div class="recent-item__body">
            <div class="recent-item__title truncate">{{ item.title }}</div>
            <div class="recent-item__authors text-muted text-sm" v-if="item.authors?.length">
              {{ item.authors.map(a => a.short_name || a.full_name).join(', ') }}
            </div>
          </div>
          <div class="recent-item__date text-muted text-sm">{{ formatDate(item.created_at) }}</div>
        </div>
      </div>

      <!-- Bar charts -->
      <div class="card dash-card">
        <div class="card-head">
          <h3>📊 Статьи по типам</h3>
          <RouterLink to="/articles" class="btn btn-ghost btn-sm">Все →</RouterLink>
        </div>
        <div v-if="articleTypes.length === 0" class="text-muted text-sm">Нет статей</div>
        <div v-for="t in articleTypes" :key="t.label" class="bar-row">
          <div class="bar-row__label truncate">{{ t.label }}</div>
          <div class="bar-row__track">
            <div class="bar-row__fill" :style="{ width: t.pct + '%', background: 'var(--c-accent)' }"></div>
          </div>
          <div class="bar-row__count">{{ t.count }}</div>
        </div>

        <div class="card-head" style="margin-top: 20px">
          <h3>📊 Рац. предл. по типам</h3>
          <RouterLink to="/proposals" class="btn btn-ghost btn-sm">Все →</RouterLink>
        </div>
        <div v-if="proposalTypes.length === 0" class="text-muted text-sm">Нет предложений</div>
        <div v-for="t in proposalTypes" :key="t.label" class="bar-row">
          <div class="bar-row__label truncate">{{ t.label }}</div>
          <div class="bar-row__track">
            <div class="bar-row__fill" :style="{ width: t.pct + '%', background: 'var(--c-amber)' }"></div>
          </div>
          <div class="bar-row__count">{{ t.count }}</div>
        </div>
      </div>
    </div>

    <!-- Row 2: Conferences + Top authors -->
    <div class="dash-row">

      <!-- Upcoming conferences -->
      <div class="card dash-card">
        <div class="card-head">
          <h3>📅 Ближайшие конференции</h3>
          <RouterLink to="/conferences" class="btn btn-ghost btn-sm">Все →</RouterLink>
        </div>
        <div v-if="upcomingConfs.length === 0" class="text-muted text-sm">Нет предстоящих конференций</div>
        <div v-for="c in upcomingConfs" :key="c.id" class="conf-item">
          <div class="conf-item__dates">
            <span class="badge badge-amber">{{ formatConfDate(c.date_start) }}</span>
            <span v-if="c.date_end && c.date_end !== c.date_start" class="text-muted text-sm">→ {{ formatConfDate(c.date_end) }}</span>
          </div>
          <div class="conf-item__title truncate">{{ c.title }}</div>
          <div class="conf-item__meta text-muted text-sm">
            <span v-if="c.is_online">🌐 Онлайн</span>
            <span v-else-if="c.location">📍 {{ c.location }}</span>
          </div>
        </div>
        <div v-if="pastConfs.length" style="margin-top: 16px">
          <div class="section-label">Прошедшие</div>
          <div v-for="c in pastConfs" :key="c.id" class="conf-item conf-item--past">
            <div class="conf-item__dates">
              <span class="badge badge-gray">{{ formatConfDate(c.date_start) }}</span>
            </div>
            <div class="conf-item__title truncate text-muted">{{ c.title }}</div>
          </div>
        </div>
      </div>

      <!-- Top authors + Collections -->
      <div class="card dash-card">
        <div class="card-head">
          <h3>👤 Топ авторов</h3>
          <RouterLink to="/authors" class="btn btn-ghost btn-sm">Все →</RouterLink>
        </div>
        <div v-if="topAuthors.length === 0" class="text-muted text-sm">Нет данных</div>
        <div v-for="(a, i) in topAuthors" :key="a.id" class="author-row">
          <div class="author-row__rank" :class="i < 3 ? 'author-row__rank--top' : ''">{{ i + 1 }}</div>
          <div class="author-row__info">
            <div class="author-row__name">{{ a.short_name || a.full_name }}</div>
            <div class="author-row__org text-muted text-sm truncate">{{ a.organization }}</div>
          </div>
          <div class="author-row__counts">
            <span v-if="a.articles_count" class="mini-badge mini-badge--blue">📄 {{ a.articles_count }}</span>
            <span v-if="a.proposals_count" class="mini-badge mini-badge--amber">💡 {{ a.proposals_count }}</span>
            <span v-if="a.software_count" class="mini-badge mini-badge--teal">💾 {{ a.software_count }}</span>
          </div>
        </div>

        <div class="card-head" style="margin-top: 20px">
          <h3>📚 Сборники</h3>
          <RouterLink to="/collections" class="btn btn-ghost btn-sm">Все →</RouterLink>
        </div>
        <div v-if="recentCollections.length === 0" class="text-muted text-sm">Нет сборников</div>
        <div v-for="col in recentCollections" :key="col.id" class="recent-item">
          <div class="recent-item__body">
            <div class="recent-item__title truncate">{{ col.name }}</div>
            <div class="text-muted text-sm">{{ col.university }}</div>
          </div>
          <div class="recent-item__date">
            <span class="badge badge-blue">{{ col.articles_count }} ст.</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { format, parseISO } from 'date-fns'
import { ru } from 'date-fns/locale'
import { reportsApi, articlesApi, softwareApi, conferencesApi, proposalsApi, authorsApi } from '@/utils/api'

const dashboard = ref({})
const articles = ref([])
const proposals = ref([])
const software = ref([])
const conferences = ref([])
const authorStats = ref([])
const collections = ref([])

const stats = computed(() => [
  { label: 'Статьи',       value: dashboard.value.articles    ?? 0, color: 'var(--c-accent)',  sub: 'всего', link: '/articles' },
  { label: 'Рац. предл.',  value: dashboard.value.proposals   ?? 0, color: 'var(--c-amber)',   sub: 'всего', link: '/proposals' },
  { label: 'ПО',           value: dashboard.value.software    ?? 0, color: 'var(--c-teal)',    sub: 'всего', link: '/software' },
  { label: 'Сборники',     value: dashboard.value.collections ?? 0, color: 'var(--c-green)',   sub: 'всего', link: '/collections' },
  { label: 'Авторы',       value: dashboard.value.authors     ?? 0, color: 'var(--c-accent2)', sub: 'в справочнике', link: '/authors' },
  { label: 'Конференции',  value: dashboard.value.conferences ?? 0, color: 'var(--c-red)',     sub: 'в календаре', link: '/conferences' },
])

const recentAll = computed(() => {
  const items = [
    ...articles.value.map(a => ({ ...a, _key: `a${a.id}`, typeLabel: 'Статья', badgeClass: 'badge-blue' })),
    ...proposals.value.map(p => ({ ...p, _key: `p${p.id}`, typeLabel: 'Рац. пред.', badgeClass: 'badge-amber' })),
    ...software.value.map(s => ({ ...s, _key: `s${s.id}`, typeLabel: 'ПО', badgeClass: 'badge-teal' })),
  ]
  return items.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || '')).slice(0, 8)
})

const articleTypes = computed(() => {
  const map = {}
  for (const a of articles.value) {
    const key = a.article_type || 'Не указан'
    map[key] = (map[key] || 0) + 1
  }
  const total = articles.value.length || 1
  return Object.entries(map).sort((a, b) => b[1] - a[1]).map(([label, count]) => ({ label, count, pct: Math.round(count / total * 100) }))
})

const proposalTypes = computed(() => {
  const map = {}
  for (const p of proposals.value) {
    const key = p.proposal_type || 'Не указан'
    map[key] = (map[key] || 0) + 1
  }
  const total = proposals.value.length || 1
  return Object.entries(map).sort((a, b) => b[1] - a[1]).map(([label, count]) => ({ label, count, pct: Math.round(count / total * 100) }))
})

const todayStr = new Date().toISOString().slice(0, 10)
const upcomingConfs = computed(() => conferences.value.filter(c => (c.date_start || '') >= todayStr).slice(0, 4))
const pastConfs = computed(() => conferences.value.filter(c => (c.date_start || '') < todayStr).slice(0, 3))

const topAuthors = computed(() =>
  [...authorStats.value]
    .sort((a, b) => (b.articles_count + b.proposals_count + b.software_count) - (a.articles_count + a.proposals_count + a.software_count))
    .slice(0, 6)
)

const recentCollections = computed(() => collections.value.slice(0, 4))

const formatDate = d => d ? format(parseISO(d), 'd MMM yyyy', { locale: ru }) : ''
const formatConfDate = d => d ? format(parseISO(d), 'd MMM', { locale: ru }) : ''

onMounted(async () => {
  try {
    const [db, art, prop, sw, conf, auStats, col] = await Promise.all([
      reportsApi.dashboard(),
      articlesApi.list(),
      proposalsApi.list(),
      softwareApi.list(),
      conferencesApi.list(),
      authorsApi.stats(),
      reportsApi.collectionsList(),
    ])
    dashboard.value = db.data
    articles.value = art.data
    proposals.value = prop.data
    software.value = sw.data
    conferences.value = conf.data
    authorStats.value = auStats.data
    collections.value = col.data
  } catch (e) {
    console.error(e)
    // Partial load failed - try individual requests for better resilience
    try { const r = await reportsApi.dashboard(); dashboard.value = r.data } catch {}
    try { const r = await articlesApi.list(); articles.value = r.data } catch {}
    try { const r = await proposalsApi.list(); proposals.value = r.data } catch {}
    try { const r = await softwareApi.list(); software.value = r.data } catch {}
    try { const r = await conferencesApi.list(); conferences.value = r.data } catch {}
    try { const r = await authorsApi.stats(); authorStats.value = r.data } catch {}
    try { const r = await reportsApi.collectionsList(); collections.value = r.data } catch {}
  }
})
</script>

<style scoped>
.stat-card--link {
  text-decoration: none;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.15s;
}
.stat-card--link:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 16px rgba(0,0,0,0.12);
}
.dash-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 20px;
  margin-top: 20px;
}
@media (max-width: 900px) {
  .dash-row { grid-template-columns: 1fr; }
}
.dash-card { display: flex; flex-direction: column; }
.card-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
}
.card-head h3 { font-size: 14px; font-weight: 600; }
.section-label {
  font-size: 11px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  color: var(--c-text-muted);
  margin-bottom: 8px;
}
.recent-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--c-border);
}
.recent-item:last-child { border-bottom: none; }
.recent-item__left { flex-shrink: 0; }
.recent-item__body { flex: 1; min-width: 0; }
.recent-item__title { font-size: 13px; font-weight: 500; }
.recent-item__authors { font-size: 11px; margin-top: 2px; }
.recent-item__date { flex-shrink: 0; font-size: 11px; white-space: nowrap; }
.bar-row {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 8px;
}
.bar-row__label { font-size: 12px; width: 110px; flex-shrink: 0; }
.bar-row__track {
  flex: 1;
  height: 8px;
  background: var(--c-bg3);
  border-radius: 4px;
  overflow: hidden;
}
.bar-row__fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bar-row__count { font-size: 12px; font-weight: 600; width: 24px; text-align: right; flex-shrink: 0; }
.conf-item {
  display: flex;
  flex-direction: column;
  gap: 3px;
  padding: 10px 0;
  border-bottom: 1px solid var(--c-border);
}
.conf-item:last-child { border-bottom: none; }
.conf-item--past { opacity: 0.55; }
.conf-item__dates { display: flex; align-items: center; gap: 6px; }
.conf-item__title { font-size: 13px; font-weight: 500; }
.conf-item__meta { font-size: 11px; }
.author-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px solid var(--c-border);
}
.author-row:last-child { border-bottom: none; }
.author-row__rank {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--c-bg3);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 700;
  flex-shrink: 0;
  color: var(--c-text-muted);
}
.author-row__rank--top { background: var(--c-accent); color: #fff; }
.author-row__info { flex: 1; min-width: 0; }
.author-row__name { font-size: 13px; font-weight: 500; }
.author-row__org { font-size: 11px; }
.author-row__counts { display: flex; gap: 4px; flex-shrink: 0; }
.mini-badge {
  font-size: 10px;
  padding: 2px 5px;
  border-radius: 4px;
  font-weight: 600;
  white-space: nowrap;
}
.mini-badge--blue  { background: rgba(59,130,246,0.12); color: #3b82f6; }
.mini-badge--amber { background: rgba(245,158,11,0.12); color: #d97706; }
.mini-badge--teal  { background: rgba(20,184,166,0.12); color: #0d9488; }
</style>
