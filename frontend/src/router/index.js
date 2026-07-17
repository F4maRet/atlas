import { createRouter, createWebHistory } from 'vue-router'

const routes = [
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

export default createRouter({
  history: createWebHistory(),
  routes,
})
