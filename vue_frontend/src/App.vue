<template>
  <div id="app">
    <div v-if="!isAuthRoute" class="main-container">
      <!-- 侧边栏 -->
      <aside class="sidebar">
        <div class="logo-container">
          <div class="logo-icon">
            <el-icon :size="32"><School /></el-icon>
          </div>
          <h1>学生成绩<br>预测系统</h1>
        </div>
        
        <!-- 侧边栏菜单 -->
        <el-menu
          :router="true"
          class="main-menu"
          :default-active="activeRoute"
          background-color="#1f2329"
          text-color="rgba(255, 255, 255, 0.9)"
          active-text-color="#409eff"
          router>
          <el-menu-item index="/data-management">
            <el-icon><DataLine /></el-icon>
            <span>数据管理</span>
          </el-menu-item>
          <el-menu-item index="/data-analysis">
            <el-icon><Histogram /></el-icon>
            <span>数据分析</span>
          </el-menu-item>
          <el-menu-item index="/model-training">
            <el-icon><Monitor /></el-icon>
            <span>模型训练</span>
          </el-menu-item>
          <el-menu-item index="/visualization">
            <el-icon><PieChart /></el-icon>
            <span>可视化表</span>
          </el-menu-item>
          <el-menu-item index="/student-feedback">
            <el-icon><ChatDotRound /></el-icon>
            <span>学生反馈</span>
          </el-menu-item>
          <el-menu-item index="/teacher-dashboard">
            <el-icon><Grid /></el-icon>
            <span>教师面板</span>
          </el-menu-item>
        </el-menu>
      </aside>
      
      <!-- 主内容区域 -->
      <div class="main-content-wrapper">
        <!-- 顶部导航栏 -->
        <header class="header">
          <div class="breadcrumb">
            <el-breadcrumb>
              <el-breadcrumb-item :to="{ path: '/' }">首页</el-breadcrumb-item>
              <el-breadcrumb-item>{{ currentPageTitle }}</el-breadcrumb-item>
            </el-breadcrumb>
          </div>
          <div class="user-info">
            <el-dropdown @command="handleUserCommand">
              <span class="user-dropdown">
                <el-avatar size="small" :src="userAvatar">{{ !userAvatar && username ? username.charAt(0) : '用' }}</el-avatar>
                <span>{{ username || '未登录' }}</span>
                <el-icon class="el-icon--right"><ArrowDown /></el-icon>
              </span>
              <template #dropdown>
                <el-dropdown-menu>
                  <el-dropdown-item command="profile">个人信息</el-dropdown-item>
                  <el-dropdown-item divided command="logout">退出登录</el-dropdown-item>
                </el-dropdown-menu>
              </template>
            </el-dropdown>
          </div>
        </header>
        
        <!-- 页面内容 -->
        <main class="page-content">
          <router-view v-slot="{ Component }">
            <transition name="fade-transform" mode="out-in">
              <keep-alive>
                <component :is="Component" />
              </keep-alive>
            </transition>
          </router-view>
        </main>
      </div>
    </div>
    
    <!-- 认证页面（登录/注册） -->
    <div v-else class="auth-container">
      <router-view v-slot="{ Component }">
        <transition name="fade" mode="out-in">
          <component :is="Component" />
        </transition>
      </router-view>
    </div>
  </div>
<!--
  根组件：
  - 左侧为主导航（数据管理/分析/训练/可视化/学生反馈/教师面板）
  - 顶部包含面包屑与用户信息
  - 非认证路由展示主框架；认证路由（登录/注册）展示独立容器
-->
</template>

<script>
// 根组件负责整体布局与用户状态展示，不包含具体业务数据请求
import { School, DataLine, Histogram, PieChart, Monitor, ChatDotRound, Grid, ArrowDown, DataBoard, Database } from '@element-plus/icons-vue'
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

export default {
  name: 'App',
  components: {
    Database,
    PieChart,
    Monitor,
    ChatDotRound,
    Grid,
    School,
    ArrowDown,
    DataLine,
    Histogram
  },
  setup() {
    const route = useRoute()
    const router = useRouter()
    const username = ref(localStorage.getItem('username') || '')
    const userAvatar = ref(localStorage.getItem('userAvatar') || '')
    
    // 头像变更事件处理函数
    const handleAvatarChange = (event) => {
      userAvatar.value = event.detail
    }
    
    // 监听头像变更事件
    onMounted(() => {
      window.addEventListener('avatarChanged', handleAvatarChange)
    })
    
    // 组件卸载时移除事件监听
    onBeforeUnmount(() => {
      window.removeEventListener('avatarChanged', handleAvatarChange)
    })
    
  // 认证路由列表（无需展示主侧栏与顶部栏）
    const authRoutes = ['/login', '/register']
    
    // 计算属性：是否为认证路由
    const isAuthRoute = computed(() => {
      return authRoutes.includes(route.path)
    })
    
    // 计算属性：当前活跃路由
    const activeRoute = computed(() => {
      return route.path || '/'  
    })
    
    // 计算属性：当前页面标题
    const currentPageTitle = computed(() => {
      const titleMap = {
        '/data-management': '数据管理',
        '/data-analysis': '数据分析',
        '/visualization': '可视化',
        '/model-training': '模型训练',
        '/student-feedback': '学生反馈',
        '/teacher-dashboard': '教师面板',
        '/profile': '个人信息'
      }
      return titleMap[route.path] || ''
    })
    
  // 用户菜单命令处理（跳转个人信息与退出登录）
    const handleUserCommand = (command) => {
      switch (command) {
        case 'profile':
          // 导航到个人信息页面
          router.push('/profile')
          break
        case 'settings':
          console.log('打开设置')
          break
        case 'logout':
          // 清除token
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          localStorage.removeItem('userAvatar')
          username.value = ''
          userAvatar.value = ''
          router.push('/login')
          break
      }
    }
    
  // 从 localStorage 同步登录状态（用户名与头像）
    const checkLoginStatus = () => {
      const storedUsername = localStorage.getItem('username') || ''
      const storedAvatar = localStorage.getItem('userAvatar') || ''
      username.value = storedUsername
      userAvatar.value = storedAvatar
    }
    
  // 监听路由变化：
  // - 同步一次登录状态
  // - 若目标为受保护路由且无 token，则回到登录
    watch(() => route.path, (newPath, oldPath) => {
      // 每次路由变化都尝试同步一次登录信息
      checkLoginStatus()

      // 跳过从登录页到其他页面的跳转，避免立即检查导致退出
      if (oldPath === '/login' && newPath !== '/login') {
        return
      }
      
      // 如果不是认证路由且没有token，重定向到登录页
      const token = localStorage.getItem('token')
      if (!authRoutes.includes(newPath) && !token) {
        router.push('/login').catch(err => {
          // 忽略导航重复的错误
          if (err.name !== 'NavigationDuplicated') {
            console.error('路由跳转失败:', err)
          }
        })
      }
    }, { immediate: false })
    
    // 组件挂载时检查登录状态
    onMounted(() => {
      checkLoginStatus()
    })
    
    return {
      isAuthRoute,
      activeRoute,
      currentPageTitle,
      username,
      userAvatar,
      handleUserCommand
    }
  }
}
</script>

<style>
/* 全局样式重置 */
* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

html, body {
  font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background-color: #f0f2f5;
  color: #333;
  font-size: 14px;
  margin: 0;
  padding: 0;
  width: 100%;
  height: 100%;
  overflow: hidden;
}

#app {
  width: 100%;
  height: 100%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* 主容器 */
.main-container {
  display: flex;
  width: 100%;
  height: 100vh;
}

/* 侧边栏样式 */
.sidebar {
  width: 220px;
  height: 100vh;
  background: linear-gradient(135deg, #1f2329 0%, #2c3e50 100%);
  color: white;
  position: relative;
  overflow-y: auto;
  box-shadow: 2px 0 8px rgba(0, 0, 0, 0.1);
  z-index: 10;
}

/* Logo样式 */
.logo-container {
  padding: 24px 16px;
  text-align: center;
  margin-bottom: 20px;
  position: relative;
}

.logo-icon {
  margin-bottom: 12px;
  display: flex;
  justify-content: center;
  align-items: center;
  width: 60px;
  height: 60px;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 16px;
  margin: 0 auto 12px;
  backdrop-filter: blur(10px);
}

.logo-container h1 {
  font-size: 18px;
  font-weight: 600;
  line-height: 1.4;
  color: rgba(255, 255, 255, 0.95);
  letter-spacing: 0.5px;
}

/* 侧边栏菜单样式 */
.main-menu {
  background: transparent;
  border-right: none;
}

.el-menu-item {
  display: flex;
  align-items: center;
  justify-content: flex-start;    /* 让图标+文字贴一起 */
  padding: 0 40px !important;     /* ← 减小左右空白 */
  height: 50px;
  border-radius: 14px;
}

.el-menu-item .el-icon {
  margin-right: 8px;              /* 适当距离 */
}

.el-menu-item span {
  display: inline-flex;
  align-items: center;
}

.el-menu-item:hover {
  background: rgba(255, 255, 255, 0.1) !important;
  border-color: rgba(64, 158, 255, 0.3);
  transform: translateX(4px);
}

.el-menu-item.is-active {
  background: rgba(64, 158, 255, 0.15) !important;
  color: #409eff !important;
  border-color: #409eff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

/* 菜单项内容样式 - 垂直居中布局 */
.el-menu-item__content {
  flex-direction: column !important;
  align-items: center !important;
  justify-content: center !important;
  height: 100%;
  padding: 0 !important;
}

/* 图标样式 */
.el-menu-item .el-icon {
  margin-right: 0 !important;
  margin-bottom: 6px;
  display: block;
  font-size: 18px;
  width: auto;
  text-align: center;
}

/* 文本样式 */
.el-menu-item > span {
  color: inherit !important;
  text-align: center !important;
  font-weight: inherit;
  letter-spacing: 0.5px;
  font-size: 13px;
  display: block;
  width: 100%;
}

/* 主内容区域 */
.main-content-wrapper {
  flex: 1;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

/* 顶部导航栏 */
.header {
  height: 60px;
  background-color: #fff;
  border-bottom: 1px solid #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  z-index: 5;
}

/* 面包屑 */
.breadcrumb {
  height: 100%;
  display: flex;
  align-items: center;
}

.breadcrumb .el-breadcrumb__item {
  font-size: 14px;
}

.breadcrumb .el-breadcrumb__item__inner {
  color: #606266;
  font-weight: 500;
}

.breadcrumb .el-breadcrumb__item:last-child .el-breadcrumb__item__inner {
  color: #303133;
  font-weight: 600;
}

/* 用户信息 */
.user-info {
  display: flex;
  align-items: center;
}

.user-dropdown {
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 8px;
  color: #606266;
  padding: 6px 12px;
  border-radius: 6px;
  transition: all 0.3s ease;
}

.user-dropdown:hover {
  background-color: #f5f7fa;
  color: #409eff;
}

.user-dropdown .el-avatar {
  background-color: #409eff;
}

/* 页面内容区域 */
.page-content {
  flex: 1;
  padding: 24px;
  overflow-y: auto;
  background-color: #f0f2f5;
}

/* 认证页面容器 */
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  width: 100%;
  min-height: 100vh;
  background: linear-gradient(135deg, #409eff 0%, #66b1ff 100%);
  padding: 20px;
  position: relative;
  overflow: hidden;
  margin: 0;
  box-sizing: border-box;
  flex-direction: column;
}

/* 背景装饰元素 */
.auth-container::before,
.auth-container::after {
  content: '';
  position: absolute;
  border-radius: 50%;
  z-index: 0;
}

.auth-container::before {
  width: 400px;
  height: 400px;
  background: rgba(255, 255, 255, 0.1);
  top: -100px;
  right: -100px;
  animation: float 15s ease-in-out infinite;
}

.auth-container::after {
  width: 300px;
  height: 300px;
  background: rgba(255, 255, 255, 0.05);
  bottom: -100px;
  left: -100px;
  animation: float 10s ease-in-out infinite reverse;
}

/* 浮动动画 */
@keyframes float {
  0%, 100% {
    transform: translate(0, 0) rotate(0deg);
  }
  50% {
    transform: translate(20px, 20px) rotate(5deg);
  }
}

/* 动画效果 */
.fade-enter-active, .fade-leave-active {
  transition: opacity 0.3s ease;
}

.fade-enter-from, .fade-leave-to {
  opacity: 0;
}

.fade-transform-enter-active, .fade-transform-leave-active {
  transition: all 0.4s ease;
}

.fade-transform-enter-from {
  opacity: 0;
  transform: translateX(20px);
}

.fade-transform-leave-to {
  opacity: 0;
  transform: translateX(-20px);
}



/* 响应式设计 */
@media (max-width: 768px) {
  .sidebar {
    width: 70px;
  }
  
  .logo-container h1, .el-menu-item > span {
    display: none;
  }
  
  .logo-icon {
    width: 40px;
    height: 40px;
    margin-bottom: 0;
  }
  
  .el-menu-item {
    height: 60px;
    margin: 6px 4px;
  }
  
  .el-menu-item .el-icon {
    margin-bottom: 0;
    font-size: 20px;
  }
  
  .page-content {
    padding: 16px;
  }
}
</style>