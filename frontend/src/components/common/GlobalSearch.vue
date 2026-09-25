<template>
  <div class="gsearch" :class="{ open: open && query.length >= 2 }">
    <div class="gsearch__box">
      <span class="gsearch__icon">🔍</span>
      <input
        ref="input"
        v-model="query"
        class="gsearch__input"
        placeholder="Поиск по системе…"
        aria-label="Глобальный поиск"
        @focus="open = true"
        @blur="close"
        @keydown.down.prevent="move(1)"
        @keydown.up.prevent="move(-1)"
        @keydown.enter.prevent="go(hits[cursor])"
        @keydown.esc="open = false; input.blur()"
      />
      <kbd class="gsearch__kbd hide-sm">Ctrl K</kbd>
    </div>
    <div v-if="open && query.length >= 2" class="gsearch__results">
      <div v-if="loading && !hits.length" class="gsearch__empty">Поиск…</div>
      <div v-else-if="!hits.length" class="gsearch__empty">Ничего не найдено</div>
      <div
        v-for="(h, i) in hits" :key="h.type + h.id + i"
        class="gsearch__item" :class="{ active: i === cursor }"
        @mousedown.prevent="go(h)" @mouseenter="cursor = i"
      >
        <span class="badge" :class="TYPES[h.type].badge">{{ TYPES[h.type].label }}</span>
        <span class="gsearch__title">{{ h.title }}</span>
        <span v-if="h.subtitle" class="gsearch__sub">{{ h.subtitle }}</span>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { reportsApi } from '@/utils/api'

const TYPES = {
  article:    { label: 'Статья',      badge: 'badge-blue',   route: 'Articles' },
  proposal:   { label: 'Рац. предл.', badge: 'badge-amber',  route: 'Proposals' },
  software:   { label: 'ПО',          badge: 'badge-teal',   route: 'Software' },
  author:     { label: 'Автор',       badge: 'badge-purple', route: 'Authors' },
  collection: { label: 'Сборник',     badge: 'badge-green',  route: 'Collections' },
  conference: { label: 'Конференция', badge: 'badge-red',    route: 'Conferences' },
}

const router = useRouter()
const input = ref(null)
const query = ref('')
const hits = ref([])
const open = ref(false)
const loading = ref(false)
const cursor = ref(0)
let timer = null
let seq = 0

watch(query, q => {
  clearTimeout(timer)
  cursor.value = 0
  if (q.trim().length < 2) { hits.value = []; return }
  timer = setTimeout(async () => {
    const my = ++seq
    loading.value = true
    try {
      const { data } = await reportsApi.search(q.trim())
      if (my === seq) hits.value = data
    } catch { if (my === seq) hits.value = [] }
    finally { if (my === seq) loading.value = false }
  }, 250)
})

function move(d) {
  if (!hits.value.length) return
  cursor.value = (cursor.value + d + hits.value.length) % hits.value.length
}
function close() { setTimeout(() => { open.value = false }, 150) }
function go(h) {
  if (!h) return
  open.value = false
  query.value = ''
  input.value?.blur()
  router.push({ name: TYPES[h.type].route, query: { open: h.id } })
}

function onKey(e) {
  if ((e.ctrlKey || e.metaKey) && e.key.toLowerCase() === 'k') {
    e.preventDefault()
    input.value?.focus()
    input.value?.select()
  }
}
onMounted(() => document.addEventListener('keydown', onKey))
onBeforeUnmount(() => document.removeEventListener('keydown', onKey))
</script>

<style scoped>
.gsearch { position: relative; width: min(440px, 100%); }
.gsearch__box { display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 10px; background: var(--c-bg3); border: 1px solid var(--c-border); border-radius: var(--radius); }
.gsearch__box:focus-within { border-color: var(--c-accent); }
.gsearch__icon { font-size: 13px; opacity: 0.7; }
.gsearch__input { flex: 1; min-width: 0; border: none; background: transparent; outline: none; color: var(--c-text); font-family: var(--font); font-size: 13px; }
.gsearch__kbd { font-family: var(--font-mono); font-size: 10px; color: var(--c-text3); border: 1px solid var(--c-border2); border-radius: 4px; padding: 1px 5px; }
.gsearch__results { position: absolute; top: calc(100% + 6px); left: 0; right: 0; z-index: 500; background: var(--c-bg2); border: 1px solid var(--c-border2); border-radius: var(--radius); box-shadow: var(--shadow); max-height: 60vh; overflow-y: auto; padding: 4px; min-width: 320px; }
.gsearch__item { display: flex; align-items: center; gap: 8px; padding: 8px 10px; border-radius: 6px; cursor: pointer; font-size: 13px; }
.gsearch__item.active { background: var(--c-surface); }
.gsearch__title { flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.gsearch__sub { font-size: 11px; color: var(--c-text3); white-space: nowrap; max-width: 30%; overflow: hidden; text-overflow: ellipsis; }
.gsearch__empty { padding: 12px; color: var(--c-text3); font-size: 13px; text-align: center; }
</style>
