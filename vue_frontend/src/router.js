// 路由配置：按需加载各页面组件，并在导航守卫中做登录校验
import { createRouter, createWebHistory } from 'vue-router'
const Login = () => import('./views/Login.vue')
const Register = () => import('./views/Register.vue')
const Profile = () => import('./views/Profile.vue')

// 简单登录状态检查（从 localStorage 读取 token）
const isAuthenticated = () => {
  return localStorage.getItem('token') !== null
}
const DataManagement = () => import('./views/DataManagement.vue')
const DataAnalysis = () => import('./views/DataAnalysis.vue')
const ModelTraining = () => import('./views/ModelTraining.vue')
const StudentFeedback = () => import('./views/StudentFeedback.vue')
const TeacherDashboard = () => import('./views/TeacherDashboard.vue')
const Visualization = () => import('./views/Visualization.vue')

// 路由表：需要登录的页面通过 meta.requiresAuth 标记
const routes = [
  { 
    path: '/', 
    redirect: '/login'
  },
  { 
    path: '/login', 
    component: Login 
  },
  { 
    path: '/register', 
    component: Register 
  },
  {
    path: '/data-management',
    component: DataManagement,
    meta: { requiresAuth: true }
  },
  {
    path: '/data-analysis',
    component: DataAnalysis,
    meta: { requiresAuth: true }
  },
  {
    path: '/model-training',
    component: ModelTraining,
    meta: { requiresAuth: true }
  },
  {
    path: '/student-feedback',
    component: StudentFeedback,
    meta: { requiresAuth: true }
  },
  {
    path: '/teacher-dashboard',
    component: TeacherDashboard,
    meta: { requiresAuth: true }
  },
  {
    path: '/visualization',
    component: Visualization,
    meta: { requiresAuth: true }
  },

  {
    path: '/profile',
    component: Profile,
    meta: { requiresAuth: true }
  }
]

const router = createRouter({ 
  history: createWebHistory(), 
  routes 
})

// 导航守卫：
// - 若目标路由标记 requiresAuth 且未登录，则跳转登录页
// - 若已登录访问登录/注册页，则重定向到数据管理页
router.beforeEach((to, from, next) => {
  // 获取当前登录状态
  const token = localStorage.getItem('token')
  const isLoggedIn = token !== null && token.trim() !== ''
  
  // 如果需要登录但未登录，重定向到登录页
  if (to.meta.requiresAuth && !isLoggedIn) {
    // 如果是从登录页跳转过来的，说明可能是刚登录但token还没保存，给一点延迟
    if (from.path === '/login') {
      // 再次检查token（可能异步保存了）
      setTimeout(() => {
        const checkToken = localStorage.getItem('token')
        if (checkToken && checkToken.trim() !== '') {
          next()
        } else {
          next({
            path: '/login',
            query: { redirect: to.fullPath }
          })
        }
      }, 100)
    } else {
      next({
        path: '/login',
        query: { redirect: to.fullPath }
      })
    }
    return
  }
  
  // 如果已登录且访问登录/注册页，重定向到数据管理页
  if (isLoggedIn && (to.path === '/login' || to.path === '/register')) {
    next('/data-management')
    return
  }
  
  next()
})

export default router
