<template>
  <div class="page">
    <div class="page-header">
      <h1><span class="page-title-icon">◈</span> Дашборд</h1>
      <div class="page-header__actions">
        <RouterLink :to="{ name: 'Articles', query: { new: 1 } }" class="btn btn-ghost btn-sm">+ Статья</RouterLink>
        <RouterLink :to="{ name: 'Proposals', query: { new: 1 } }" class="btn btn-ghost btn-sm">+ Рац. предложение</RouterLink>
        <RouterLink :to="{ name: 'Software', query: { new: 1 } }" class="btn btn-ghost btn-sm">+ ПО</RouterLink>
      </div>
    </div>

    <div v-if="error" class="alert alert-error">⚠️ {{ error }} <button class="btn btn-ghost btn-sm ml-auto" @click="load">↺ Повторить</button></div>

    <div class="stats-grid">
      <RouterLink v-for="s in statCards" :key="s.label" :to="s.link" class="stat-card stat-card--link">
        <div class="stat-card__label">{{ s.icon }} {{ s.label }}</div>
        <div class="stat-card__value" :style="{ color: s.color }">
          <span v-if="loading" class="skeleton" style="display:block;width:50px;height:30px"></span>
          <template v-else>{{ d[s.key] ?? 0 }}</template>
        </div>
      </RouterLink>
    </div>

    <!-- Требует внимания -->
    <div v-if="attentionItems.length" class="attention">
      <RouterLink v-for="a in attentionItems" :key="a.text" :to="a.link" class="attention__item">
        <span class="attention__num">{{ a.count }}</span>
        <span>{{ a.text }}</span>
        <span class="ml-auto">→</span>
      </RouterLink>
    </div>

    <div class="dash-row">
      <section class="card">
        <div class="card-title"><h3>🕓 Последние добавления</h3></div>
        <div v-if="!d.recent?.length" class="text-muted text-sm">{{ loading ? 'Загрузка…' : 'Пока ничего не добавлено' }}</div>
        <RouterLink v-for="item in d.recent" :key="item.type + item.id" :to="{ name: TYPES[item.type].route, query: { open: item.id } }" class="row-link">
          <span class="badge" :class="TYPES[item.type].badge">{{ TYPES[item.type].label }}</span>
          <div class="row-link__body">
            <div class="truncate" style="font-weight:500">{{ item.title }}</div>
            <div v-if="item.authors.length" class="text-dim text-sm truncate">{{ item.authors.join(', ') }}</div>
          </div>
          <span class="text-dim text-sm nowrap">{{ formatDate(item.created_at) }}</span>
        </RouterLink>
      </section>

      <section class="card">
        <div class="card-title"><h3>📊 Статьи по типам</h3><RouterLink to="/articles" class="btn btn-ghost btn-sm">Все →</RouterLink></div>
        <div v-if="!d.article_types?.length" class="text-muted text-sm">Нет статей</div>
        <div v-for="t in bars(d.article_types)" :key="t.label" class="bar-row">
          <div class="bar-row__label truncate" :title="t.label">{{ t.label }}</div>
          <div class="bar-row__track"><div class="bar-row__fill" :style="{ width: t.pct + '%', background: 'var(--c-accent)' }"></div></div>
          <div class="bar-row__count">{{ t.count }}</div>
        </div>
        <div class="card-title mt-4"><h3>📊 Рац. предложения по типам</h3><RouterLink to="/proposals" class="btn btn-ghost btn-sm">Все →</RouterLink></div>
        <div v-if="!d.proposal_types?.length" class="text-muted text-sm">Нет предложений</div>
        <div v-for="t in bars(d.proposal_types)" :key="t.label" class="bar-row">
          <div class="bar-row__label truncate" :title="t.label">{{ t.label }}</div>
          <div class="bar-row__track"><div class="bar-row__fill" :style="{ width: t.pct + '%', background: 'var(--c-amber)' }"></div></div>
          <div class="bar-row__count">{{ t.count }}</div>
        </div>
      </section>
    </div>

    <div class="dash-row">
      <section class="card">
        <div class="card-title"><h3>📅 Ближайшие конференции</h3><RouterLink to="/conferences" class="btn btn-ghost btn-sm">Все →</RouterLink></div>
        <div v-if="!d.upcoming_conferences?.length" class="text-muted text-sm">Нет предстоящих конференций</div>
        <RouterLink v-for="c in d.upcoming_conferences" :key="c.id" :to="{ name: 'Conferences', query: { open: c.id } }" class="row-link">
          <span class="badge" :class="c.ongoing ? 'badge-green' : 'badge-amber'">{{ c.ongoing ? 'идёт' : formatDateShort(c.date_start) }}</span>
          <div class="row-link__body">
            <div class="truncate" style="font-weight:500">{{ c.title }}</div>
            <div class="text-dim text-sm truncate">
              {{ formatRange(c.date_start, c.date_end) }}<span v-if="c.is_online"> · 🌐 онлайн</span><span v-else-if="c.location"> · 📍 {{ c.location }}</span>
            </div>
          </div>
        </RouterLink>
        <template v-if="d.past_conferences?.length">
          <div class="section-label">Недавно прошли</div>
          <RouterLink v-for="c in d.past_conferences" :key="c.id" :to="{ name: 'Conferences', query: { open: c.id } }" class="row-link row-link--dim">
            <span class="badge badge-gray">{{ formatDateShort(c.date_start) }}</span>
            <div class="row-link__body truncate">{{ c.title }}</div>
          </RouterLink>
        </template>
      </section>

      <section class="card">
        <div class="card-title"><h3>👤 Самые активные авторы</h3><RouterLink to="/authors" class="btn btn-ghost btn-sm">Все →</RouterLink></div>
        <div v-if="!d.top_authors?.length" class="text-muted text-sm">Нет данных</div>
        <RouterLink v-for="(a, i) in d.top_authors" :key="a.id" :to="{ name: 'Authors', query: { open: a.id } }" class="row-link">
          <span class="rank" :class="{ 'rank--top': i < 3 }">{{ i + 1 }}</span>
          <div class="row-link__body">
            <div class="truncate" style="font-weight:500">{{ a.full_name }}</div>
            <div class="text-dim text-sm truncate">{{ a.organization }}</div>
          </div>
          <div class="flex gap-2">
            <span v-if="a.articles_count" class="badge badge-blue">📄 {{ a.articles_count }}</span>
            <span v-if="a.proposals_count" class="badge badge-amber">💡 {{ a.proposals_count }}</span>
            <span v-if="a.software_count" class="badge badge-teal">💾 {{ a.software_count }}</span>
          </div>
        </RouterLink>

        <div class="card-title mt-4"><h3>📚 Сборники</h3><RouterLink to="/collections" class="btn btn-ghost btn-sm">Все →</RouterLink></div>
        <div v-if="!d.collections_list?.length" class="text-muted text-sm">Нет сборников</div>
        <RouterLink v-for="c in d.collections_list" :key="c.id" :to="{ name: 'Collections', query: { open: c.id } }" class="row-link">
          <div class="row-link__body">
            <div class="truncate" style="font-weight:500">{{ c.name }}</div>
            <div class="text-dim text-sm truncate">{{ c.university }}</div>
          </div>
          <span class="badge badge-blue">{{ pluralize(c.articles_count, 'статья', 'статьи', 'статей') }}</span>
        </RouterLink>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { reportsApi } from '@/utils/api'
import { formatDate, formatDateShort, formatRange, pluralize } from '@/utils/format'

const TYPES = {
  article: { label: 'Статья', badge: 'badge-blue', route: 'Articles' },
  proposal: { label: 'Рац. предл.', badge: 'badge-amber', route: 'Proposals' },
  software: { label: 'ПО', badge: 'badge-teal', route: 'Software' },
}
const statCards = [
  { key: 'articles', label: 'Статьи', icon: '📄', color: 'var(--c-accent)', link: '/articles' },
  { key: 'proposals', label: 'Рац. предл.', icon: '💡', color: 'var(--c-amber)', link: '/proposals' },
  { key: 'software', label: 'ПО', icon: '💾', color: 'var(--c-teal)', link: '/software' },
  { key: 'collections', label: 'Сборники', icon: '📚', color: 'var(--c-green)', link: '/collections' },
  { key: 'authors', label: 'Авторы', icon: '👤', color: 'var(--c-accent2)', link: '/authors' },
  { key: 'conferences', label: 'Конференции', icon: '🗓', color: 'var(--c-red)', link: '/conferences' },
]

const d = ref({})
const loading = ref(true)
const error = ref('')

const attentionItems = computed(() => {
  const a = d.value.attention
  if (!a) return []
  return [
    { count: a.articles_without_conclusion, text: 'статей без заключения об открытом опубликовании', link: '/articles' },
    { count: a.articles_without_file, text: 'статей без прикреплённого файла', link: '/articles' },
    { count: a.software_incomplete_docs, text: `ПО с неполным комплектом документов (из ${a.software_doc_types})`, link: '/software' },
  ].filter(x => x.count > 0)
})

function bars(list) {
  const max = Math.max(1, ...(list || []).map(t => t.count))
  return (list || []).map(t => ({ ...t, pct: Math.round(t.count / max * 100) }))
}

async function load() {
  loading.value = true
  error.value = ''
  try { d.value = (await reportsApi.dashboard()).data } catch (e) { error.value = e.message }
  finally { loading.value = false }
}
onMounted(load)
</script>

<style scoped>
.stat-card--link { text-decoration: none !important; color: inherit; transition: transform 0.15s, border-color 0.15s; }
.stat-card--link:hover { transform: translateY(-2px); border-color: var(--c-border2); }
.dash-row { display: grid; grid-template-columns: 1fr 1fr; gap: 18px; margin-top: 18px; }
@media (max-width: 1000px) { .dash-row { grid-template-columns: 1fr; } }
.section-label { font-size: 11px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em; color: var(--c-text3); margin: 14px 0 4px; }
.row-link { display: flex; align-items: center; gap: 10px; padding: 8px 6px; border-radius: 8px; color: var(--c-text); font-size: 13px; }
.row-link:hover { background: var(--c-bg3); text-decoration: none; }
.row-link--dim { opacity: 0.6; }
.row-link__body { flex: 1; min-width: 0; }
.bar-row { display: flex; align-items: center; gap: 8px; margin-bottom: 8px; }
.bar-row__label { font-size: 12px; width: 120px; flex-shrink: 0; }
.bar-row__track { flex: 1; height: 8px; background: var(--c-bg3); border-radius: 4px; overflow: hidden; }
.bar-row__fill { height: 100%; border-radius: 4px; transition: width 0.4s; }
.bar-row__count { font-size: 12px; font-weight: 600; width: 28px; text-align: right; }
.rank { width: 22px; height: 22px; border-radius: 50%; background: var(--c-bg3); display: flex; align-items: center; justify-content: center; font-size: 11px; font-weight: 700; flex-shrink: 0; color: var(--c-text2); }
.rank--top { background: var(--c-accent); color: #fff; }
.attention { display: flex; flex-direction: column; gap: 6px; }
.attention__item { display: flex; align-items: center; gap: 10px; padding: 10px 14px; border-radius: var(--radius); background: rgba(245,158,11,0.08); border: 1px solid rgba(245,158,11,0.25); color: var(--c-text); font-size: 13px; }
.attention__item:hover { background: rgba(245,158,11,0.14); text-decoration: none; }
.attention__num { font-weight: 700; color: var(--c-amber); min-width: 24px; }
</style>
