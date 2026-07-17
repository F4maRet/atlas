import { createRouter, createWebHistory } from 'vue-router'
import { authApi } from '@/utils/api'

const routes = [
  { path: '/login',        name: 'Login',        component: () => import('@/views/LoginView.vue'), meta: { public: true } },
  { path: '/',             name: 'Dashboard',    component: () => import('@/views/DashboardView.vue') },
  { path: '/articles',     name: 'Articles',     component: () => import('@/views/ArticlesView.vue') },
  { path: '/proposals',    name: 'Proposals',    component: () => import('@/views/ProposalsView.vue') },
  { path: '/software',     name: 'Software',     component: () => import('@/views/SoftwareView.vue') },
  { path: '/collections',  name: 'Collections',  component: () => import('@/views/CollectionsView.vue') },
  { path: '/authors',      name: 'Authors',      component: () => import('@/views/AuthorsView.vue') },
  { path: '/conferences',  name: 'Conferences',  component: () => import('@/views/ConferencesView.vue') },
  { path: '/reports',      name: 'Reports',      component: () => import('@/views/ReportsView.vue') },
  { path: '/templates',    name: 'Templates',    component: () => import('@/views/TemplatesView.vue') },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// Проверяем сессию один раз и кэшируем результат — не дёргаем /auth/check
// на каждый переход между страницами.
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

  if (!isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  return true
})

// После логина/логаута форсируем повторную проверку при следующей навигации
export function invalidateAuthCache() {
  authChecked = false
}

export default router
