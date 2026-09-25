import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '@/utils/api'

const routes = [
  { path: '/login',       name: 'Login',       component: () => import('@/views/LoginView.vue'),       meta: { public: true, title: 'Вход' } },
  { path: '/',            name: 'Dashboard',   component: () => import('@/views/DashboardView.vue'),   meta: { title: 'Дашборд' } },
  { path: '/articles',    name: 'Articles',    component: () => import('@/views/ArticlesView.vue'),    meta: { title: 'Научные статьи' } },
  { path: '/proposals',   name: 'Proposals',   component: () => import('@/views/ProposalsView.vue'),   meta: { title: 'Рац. предложения' } },
  { path: '/software',    name: 'Software',    component: () => import('@/views/SoftwareView.vue'),    meta: { title: 'Программное обеспечение' } },
  { path: '/collections', name: 'Collections', component: () => import('@/views/CollectionsView.vue'), meta: { title: 'Сборники' } },
  { path: '/authors',     name: 'Authors',     component: () => import('@/views/AuthorsView.vue'),     meta: { title: 'Авторы' } },
  { path: '/conferences', name: 'Conferences', component: () => import('@/views/ConferencesView.vue'), meta: { title: 'Конференции' } },
  { path: '/reports',     name: 'Reports',     component: () => import('@/views/ReportsView.vue'),     meta: { title: 'Отчётность' } },
  { path: '/templates',   name: 'Templates',   component: () => import('@/views/TemplatesView.vue'),   meta: { title: 'Шаблоны документов' } },
  { path: '/:pathMatch(.*)*', redirect: '/' },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Сессию проверяем один раз и кэшируем — не дёргаем /auth/check на каждый переход.
let authChecked = false
let isAuthenticated = false

router.beforeEach(async (to) => {
  if (to.meta.public) return true
  if (!authChecked) {
    try {
      const { data } = await authApi.check()
      isAuthenticated = !!data.authenticated
    } catch {
      isAuthenticated = false
    }
    authChecked = true
  }
  if (!isAuthenticated) return { name: 'Login', query: { redirect: to.fullPath } }
  return true
})

router.afterEach(to => {
  document.title = to.meta.title ? `${to.meta.title} — АТЛАС` : 'СНД «АТЛАС»'
})

// После логина/логаута — повторная проверка при следующей навигации
export function invalidateAuthCache() {
  authChecked = false
}

export default router
