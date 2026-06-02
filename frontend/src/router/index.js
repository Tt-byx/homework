import { createRouter, createWebHistory } from 'vue-router'

const routes = [
  // ========== 游客端 ==========
  {
    path: '/',
    component: () => import('@/components/layout/VisitorLayout.vue'),
    children: [
      {
        path: '',
        name: 'Home',
        component: () => import('@/views/visitor/HomeView.vue'),
      },
      {
        path: 'chat',
        name: 'Chat',
        component: () => import('@/views/visitor/ChatView.vue'),
      },
    ],
  },
  // ========== 管理后台 ==========
  {
    path: '/admin',
    component: () => import('@/components/layout/AdminLayout.vue'),
    redirect: '/admin/dashboard',
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: () => import('@/views/admin/DashboardView.vue'),
      },
      {
        path: 'knowledge',
        name: 'AdminKnowledge',
        component: () => import('@/views/admin/KnowledgeView.vue'),
      },
    ],
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

export default router
