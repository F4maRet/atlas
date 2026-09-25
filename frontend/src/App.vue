<template>
  <RouterView v-if="route.meta.public" />
  <div v-else class="app-layout" :class="{ 'nav-open': navOpen }">
    <aside class="sidebar" aria-label="Главное меню">
      <div class="sidebar__logo">
        <img src="/favicon.svg" alt="" class="sidebar__logo-icon" />
        <div>
          <div class="sidebar__logo-title">АТЛАС</div>
          <div class="sidebar__logo-sub">Научная деятельность</div>
        </div>
      </div>

      <nav class="sidebar__nav">
        <template v-for="group in nav" :key="group.label">
          <div class="sidebar__section-label">{{ group.label }}</div>
          <RouterLink v-for="item in group.items" :key="item.to" :to="item.to" class="sidebar__link" @click="navOpen = false">
            <span class="sidebar__link-icon">{{ item.icon }}</span>
            <span>{{ item.label }}</span>
          </RouterLink>
        </template>
      </nav>

      <div class="sidebar__footer">
        <div class="sidebar__footer-dot" :class="{ online: health }"></div>
        <span>{{ health ? 'Сервер онлайн' : 'Нет соединения' }}</span>
        <button class="sidebar__btn" :title="theme === 'light' ? 'Тёмная тема' : 'Светлая тема'" @click="toggleTheme">
          {{ theme === 'light' ? '🌙' : '☀️' }}
        </button>
        <button class="sidebar__btn sidebar__btn--logout" title="Выйти" @click="logout">⏻</button>
      </div>
    </aside>
    <div class="nav-backdrop" @click="navOpen = false"></div>

    <div class="main-content">
      <header class="topbar">
        <button class="topbar__burger" aria-label="Меню" @click="navOpen = !navOpen">☰</button>
        <div class="topbar__title hide-sm">{{ route.meta.title }}</div>
        <GlobalSearch class="topbar__search" />
        <div class="topbar__date hide-sm">{{ currentDate }}</div>
      </header>
      <div v-if="!health" class="offline-banner">
        ⚠️ Нет связи с сервером. Изменения не будут сохранены, пока соединение не восстановится.
      </div>
      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
  <ConfirmDialog />
</template>

<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import { authApi, healthCheck } from '@/utils/api'
import { invalidateAuthCache } from '@/router'
import GlobalSearch from '@/components/common/GlobalSearch.vue'
import ConfirmDialog from '@/components/common/ConfirmDialog.vue'

const route = useRoute()
const router = useRouter()
const health = ref(true)
const navOpen = ref(false)
const theme = ref(document.documentElement.dataset.theme || 'dark')
const currentDate = format(new Date(), 'd MMMM yyyy, EEEEEE', { locale: ru })

const nav = [
  { label: 'Основное', items: [
    { to: '/', icon: '◈', label: 'Дашборд' },
    { to: '/articles', icon: '📄', label: 'Научные статьи' },
    { to: '/proposals', icon: '💡', label: 'Рац. предложения' },
    { to: '/software', icon: '💾', label: 'Программное обеспечение' },
  ] },
  { label: 'Справочники', items: [
    { to: '/authors', icon: '👤', label: 'Авторы' },
    { to: '/collections', icon: '📚', label: 'Сборники' },
    { to: '/conferences', icon: '🗓', label: 'Конференции' },
  ] },
  { label: 'Система', items: [
    { to: '/reports', icon: '📊', label: 'Отчётность' },
    { to: '/templates', icon: '🗂', label: 'Шаблоны документов' },
  ] },
]

function toggleTheme() {
  theme.value = theme.value === 'light' ? 'dark' : 'light'
  document.documentElement.dataset.theme = theme.value
  try { localStorage.setItem('atlas-theme', theme.value) } catch { /* ignore */ }
}

async function logout() {
  try { await authApi.logout() } catch { /* всё равно уходим на логин */ }
  invalidateAuthCache()
  router.push({ name: 'Login' })
}

// Раньше соединение проверялось один раз при загрузке — индикатор «онлайн» врал
let timer = null
async function ping() {
  try { health.value = await healthCheck() } catch { health.value = false }
}
onMounted(() => { ping(); timer = setInterval(ping, 30000) })
onBeforeUnmount(() => clearInterval(timer))
</script>

<style scoped>
.app-layout { display: flex; height: 100vh; overflow: hidden; }

.sidebar {
  width: var(--sidebar-w); background: var(--c-bg2); border-right: 1px solid var(--c-border);
  display: flex; flex-direction: column; flex-shrink: 0; overflow-y: auto; z-index: 200;
}
.sidebar__logo { display: flex; align-items: center; gap: 12px; padding: 18px 18px 14px; border-bottom: 1px solid var(--c-border); }
.sidebar__logo-icon { width: 32px; height: 32px; }
.sidebar__logo-title {
  font-size: 17px; font-weight: 700; letter-spacing: 2px;
  background: linear-gradient(135deg, var(--c-accent), var(--c-accent2));
  -webkit-background-clip: text; background-clip: text; -webkit-text-fill-color: transparent;
}
.sidebar__logo-sub { font-size: 10px; color: var(--c-text3); letter-spacing: 0.5px; text-transform: uppercase; }
.sidebar__nav { padding: 10px; flex: 1; }
.sidebar__section-label { font-size: 10px; font-weight: 600; color: var(--c-text3); text-transform: uppercase; letter-spacing: 0.8px; padding: 12px 8px 6px; }
.sidebar__link {
  display: flex; align-items: center; gap: 10px; padding: 8px 10px; border-radius: 8px;
  color: var(--c-text2); font-size: 13px; transition: var(--transition); margin-bottom: 2px;
}
.sidebar__link:hover { background: var(--c-surface); color: var(--c-text); text-decoration: none; }
.sidebar__link.router-link-exact-active { background: rgba(79,124,255,0.15); color: var(--c-accent); font-weight: 500; }
.sidebar__link-icon { font-size: 15px; width: 20px; text-align: center; }
.sidebar__footer { display: flex; align-items: center; gap: 8px; padding: 12px 14px 12px 18px; border-top: 1px solid var(--c-border); font-size: 12px; color: var(--c-text3); }
.sidebar__footer-dot { width: 7px; height: 7px; border-radius: 50%; background: var(--c-red); flex-shrink: 0; }
.sidebar__footer-dot.online { background: var(--c-green); }
.sidebar__btn { background: none; border: none; color: var(--c-text3); font-size: 14px; cursor: pointer; padding: 4px 6px; border-radius: 6px; line-height: 1; }
.sidebar__btn:first-of-type { margin-left: auto; }
.sidebar__btn:hover { background: var(--c-surface); color: var(--c-text); }
.sidebar__btn--logout:hover { color: var(--c-red); }

.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; min-width: 0; }
.topbar {
  height: var(--header-h); display: flex; align-items: center; gap: 16px; padding: 0 24px;
  border-bottom: 1px solid var(--c-border); background: var(--c-bg2); flex-shrink: 0;
}
.topbar__title { font-size: 14px; font-weight: 500; white-space: nowrap; }
.topbar__search { margin: 0 auto; }
.topbar__date { font-size: 12px; color: var(--c-text3); white-space: nowrap; }
.topbar__burger { display: none; background: none; border: none; color: var(--c-text); font-size: 20px; cursor: pointer; }
.offline-banner { background: rgba(240,64,96,0.12); color: var(--c-red); font-size: 13px; padding: 6px 24px; border-bottom: 1px solid rgba(240,64,96,0.3); }
.content-area { flex: 1; overflow-y: auto; }
.nav-backdrop { display: none; }

@media (max-width: 900px) {
  .sidebar { position: fixed; inset: 0 auto 0 0; transform: translateX(-100%); transition: transform 0.2s; box-shadow: var(--shadow); }
  .nav-open .sidebar { transform: none; }
  .nav-open .nav-backdrop { display: block; position: fixed; inset: 0; background: rgba(0,0,0,0.5); z-index: 150; }
  .topbar { padding: 0 12px; gap: 10px; }
  .topbar__burger { display: block; }
}
</style>
