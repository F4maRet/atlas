<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar__logo">
        <span class="sidebar__logo-icon">⬡</span>
        <div>
          <div class="sidebar__logo-title">АТЛАС</div>
          <div class="sidebar__logo-sub">СНД v1.0</div>
        </div>
      </div>

      <nav class="sidebar__nav">
        <div class="sidebar__section-label">Основное</div>
        <RouterLink v-for="item in mainNav" :key="item.to" :to="item.to" class="sidebar__link">
          <span class="sidebar__link-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>

        <div class="sidebar__section-label">Справочники</div>
        <RouterLink v-for="item in refNav" :key="item.to" :to="item.to" class="sidebar__link">
          <span class="sidebar__link-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>

        <div class="sidebar__section-label">Система</div>
        <RouterLink v-for="item in sysNav" :key="item.to" :to="item.to" class="sidebar__link">
          <span class="sidebar__link-icon">{{ item.icon }}</span>
          <span>{{ item.label }}</span>
        </RouterLink>
      </nav>

      <div class="sidebar__footer">
        <div class="sidebar__footer-dot" :class="{ online: health }"></div>
        <span>{{ health ? 'Сервер онлайн' : 'Нет соединения' }}</span>
      </div>
    </aside>

    <div class="main-content">
      <header class="topbar">
        <div class="topbar__breadcrumb">{{ currentPageTitle }}</div>
        <div class="topbar__right">
          <span class="text-muted text-sm">{{ currentDate }}</span>
        </div>
      </header>
      <main class="content-area">
        <RouterView />
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { format } from 'date-fns'
import { ru } from 'date-fns/locale'
import api from '@/utils/api'

const health = ref(false)
const route = useRoute()

const mainNav = [
  { to: '/',            icon: '◈', label: 'Дашборд' },
  { to: '/articles',    icon: '📄', label: 'Научные статьи' },
  { to: '/proposals',   icon: '💡', label: 'Рац. предложения' },
  { to: '/software',    icon: '💾', label: 'Программное обеспечение' },
]
const refNav = [
  { to: '/authors',     icon: '👤', label: 'Авторы' },
  { to: '/collections', icon: '📚', label: 'Сборники' },
  { to: '/conferences', icon: '🗓', label: 'Конференции' },
]
const sysNav = [
  { to: '/reports',     icon: '📊', label: 'Отчётность' },
  { to: '/templates',   icon: '🗂', label: 'Шаблоны документов' },
]

const allNav = [...mainNav, ...refNav, ...sysNav]

const currentPageTitle = computed(() => {
  const found = allNav.find(n => n.to === route.path)
  return found ? found.label : 'АТЛАС'
})

const currentDate = computed(() =>
  format(new Date(), 'd MMMM yyyy', { locale: ru })
)

onMounted(async () => {
  try {
    await api.get('/../../health')
    health.value = true
  } catch {
    health.value = false
  }
})
</script>

<style scoped>
.app-layout {
  display: flex;
  height: 100vh;
  overflow: hidden;
}

/* Sidebar */
.sidebar {
  width: var(--sidebar-w);
  background: var(--c-bg2);
  border-right: 1px solid var(--c-border);
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  overflow-y: auto;
}
.sidebar__logo {
  display: flex; align-items: center; gap: 12px;
  padding: 20px 18px 16px;
  border-bottom: 1px solid var(--c-border);
}
.sidebar__logo-icon {
  font-size: 28px;
  color: var(--c-accent);
  line-height: 1;
}
.sidebar__logo-title {
  font-size: 17px; font-weight: 700;
  background: linear-gradient(135deg, var(--c-accent), var(--c-accent2));
  -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  letter-spacing: 2px;
}
.sidebar__logo-sub {
  font-size: 10px; color: var(--c-text3);
  letter-spacing: 1px; text-transform: uppercase;
}
.sidebar__nav { padding: 12px 10px; flex: 1; }
.sidebar__section-label {
  font-size: 10px; font-weight: 600; color: var(--c-text3);
  text-transform: uppercase; letter-spacing: 0.8px;
  padding: 12px 8px 6px;
}
.sidebar__link {
  display: flex; align-items: center; gap: 10px;
  padding: 8px 10px; border-radius: 8px;
  color: var(--c-text2); text-decoration: none;
  font-size: 13px; font-weight: 400;
  transition: var(--transition);
  margin-bottom: 2px;
}
.sidebar__link:hover { background: var(--c-surface); color: var(--c-text); text-decoration: none; }
.sidebar__link.router-link-active { background: rgba(79,124,255,0.15); color: var(--c-accent); font-weight: 500; }
.sidebar__link-icon { font-size: 15px; width: 20px; text-align: center; }

.sidebar__footer {
  display: flex; align-items: center; gap: 8px;
  padding: 14px 18px;
  border-top: 1px solid var(--c-border);
  font-size: 12px; color: var(--c-text3);
}
.sidebar__footer-dot {
  width: 7px; height: 7px; border-radius: 50%; background: var(--c-red);
  transition: background 0.3s;
}
.sidebar__footer-dot.online { background: var(--c-green); }

/* Main */
.main-content { flex: 1; display: flex; flex-direction: column; overflow: hidden; }
.topbar {
  height: var(--header-h);
  display: flex; align-items: center; justify-content: space-between;
  padding: 0 32px;
  border-bottom: 1px solid var(--c-border);
  background: var(--c-bg2);
  flex-shrink: 0;
}
.topbar__breadcrumb { font-size: 14px; font-weight: 500; color: var(--c-text); }
.content-area { flex: 1; overflow-y: auto; }
</style>
