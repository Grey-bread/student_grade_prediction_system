<template>
  <div class="auth-container">
    <!-- 背景层：支持渐变或自定义上传图片 -->
    <div class="auth-bg" :style="bgStyle"></div>
    <div class="auth-bg-overlay"></div>

    <!-- 背景设置控件 -->
    <div class="auth-tools">
      <input ref="bgInput" type="file" accept="image/*" class="bg-file-input" @change="onBgSelected" />
      <el-tooltip content="上传背景图片" placement="bottom">
        <el-button size="small" circle class="bg-tool-btn" @click="triggerBgUpload">
          <el-icon><Picture /></el-icon>
        </el-button>
      </el-tooltip>
      <el-tooltip content="恢复默认背景" placement="bottom">
        <el-button size="small" circle class="bg-tool-btn" @click="resetBg">
          <el-icon><Refresh /></el-icon>
        </el-button>
      </el-tooltip>
    </div>

    <div class="login-box glass-card">
      <el-form ref="loginForm" :model="loginForm" :rules="loginRules" class="login-form">
        <div class="login-header">
          <h2>教师登录</h2>
          <p class="hint">请输入教师账号和密码以登录系统</p>
        </div>

        <el-form-item prop="username" class="input-item">
          <el-input v-model="loginForm.username" placeholder="用户名/手机/邮箱" size="large" clearable>
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password" class="input-item">
          <el-input v-model="loginForm.password" type="password" show-password placeholder="密码" size="large" @keyup.enter="handleLogin">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <div class="login-options">
          <el-checkbox v-model="rememberMe">记住密码</el-checkbox>
          <a href="#" class="forget-pwd">忘记密码？</a>
        </div>

  <el-button type="primary" class="login-btn" :loading="loading" :disabled="loading" @click="handleLogin">登录</el-button>

        <div class="register-link">
          <router-link to="/register">还没有账号？立即注册</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { User, Lock, Picture, Refresh } from '@element-plus/icons-vue'

export default {
  name: 'Login',
  components: { User, Lock, Picture, Refresh },
  data() {
    return {
      bgImage: localStorage.getItem('authBgImage') || '',
      loginForm: { username: '', password: '' },
      loginRules: {
        username: [ { required: true, message: '请输入账号', trigger: 'blur' }, { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' } ],
        password: [ { required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' } ]
      },
      loading: false,
      rememberMe: false
    }
  },
  computed: {
    bgStyle() {
      if (this.bgImage) {
        return {
          backgroundImage: `url(${this.bgImage})`,
          backgroundSize: 'cover',
          backgroundPosition: 'center center'
        }
      }
      // 默认渐变背景（改为白色系，避免切换时出现蓝色闪烁，并呈现白色过渡）
      return {
        backgroundImage: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #ffffff 100%)'
      }
    }
  },
  created() {
    const rememberedUser = localStorage.getItem('remember_user')
    if (rememberedUser) { this.loginForm.username = rememberedUser; this.rememberMe = true }
  },
  methods: {
    triggerBgUpload() {
      this.$refs.bgInput && this.$refs.bgInput.click()
    },
    onBgSelected(e) {
      const file = e?.target?.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const dataUrl = reader.result
          this.bgImage = dataUrl
          localStorage.setItem('authBgImage', dataUrl)
          this.$message.success('背景已更新')
        } catch (err) {
          this.$message.error('设置背景失败')
        }
      }
      reader.readAsDataURL(file)
      // 清空 input 以便可重复选择同一文件
      e.target.value = ''
    },
    resetBg() {
      this.bgImage = ''
      localStorage.removeItem('authBgImage')
      this.$message.success('已恢复默认背景')
    },
    async handleLogin() {
      if (this.loading) return
      try {
        await this.$refs.loginForm.validate()
        this.loading = true
        const payload = { username: (this.loginForm.username || '').trim(), password: this.loginForm.password }
        const response = await axios.post('/api/teacher/login', payload)
        if (response.data.status === 'success') {
          // 后端返回结构: {status: 'success', data: {token: '...', teacher: {...}}}
          const token = response.data.data?.token || response.data.token
          if (!token) {
            this.$message.error('登录失败：未收到token')
            return
          }
          // 保存token和用户信息
          localStorage.setItem('token', token)
          localStorage.setItem('username', this.loginForm.username)
          if (this.rememberMe) {
            localStorage.setItem('remember_user', this.loginForm.username)
          } else {
            localStorage.removeItem('remember_user')
          }
          
          // 验证token已保存
          const savedToken = localStorage.getItem('token')
          if (!savedToken || savedToken !== token) {
            this.$message.error('登录失败：token保存失败')
            return
          }
          
          // 登录成功后，尝试获取头像以便顶部栏立即显示
          try {
            const headers = { Authorization: `Bearer ${token}` }
            const infoRes = await axios.get('/api/teacher/info', { headers })
            const avatar = infoRes?.data?.data?.avatar
            if (avatar && typeof avatar === 'string') {
              localStorage.setItem('userAvatar', avatar)
              // 通知根组件刷新头像
              window.dispatchEvent(new CustomEvent('avatarChanged', { detail: avatar }))
            }
          } catch (e) {
            // 获取头像失败不影响登录流程
          }

          this.$message.success('登录成功')
          // 使用nextTick确保token/头像已保存，然后跳转
          this.$nextTick(() => {
            const redirect = this.$route.query?.redirect || '/data-management'
            this.$router.push(redirect).catch(err => {
              // 忽略导航重复的错误
              if (err.name !== 'NavigationDuplicated') {
                console.error('路由跳转失败:', err)
              }
            })
          })
        } else {
          this.$message.error(response.data.message || '登录失败')
        }
      } catch (err) {
        this.$message.error(err.response?.data?.message || err.message || '登录失败')
      } finally { this.loading = false }
    }
  }
}
</script>

<style scoped>
/* 布局与背景 */
.auth-container {
  position: relative;
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  overflow: hidden;
  background-color: #ffffff; /* 防止背景未加载时出现蓝色，采用白色兜底 */
}
.auth-bg {
  position: fixed; /* 固定覆盖整个视口，避免容器尺寸变化露边 */
  inset: 0;
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat; /* 禁止平铺导致的边缘色块 */
  filter: brightness(0.95);
  transition: background-image 0.3s ease;
}
.auth-bg-overlay {
  position: fixed; /* 与背景层一致覆盖视口 */
  inset: 0;
  background: linear-gradient(to bottom right, rgba(0,0,0,0.2), rgba(0,0,0,0.35));
  pointer-events: none;
}
.auth-tools {
  position: absolute;
  top: 16px;
  right: 16px;
  display: flex;
  gap: 8px;
  z-index: 3;
}
.bg-file-input { display: none; }

/* 玻璃拟态卡片 */
.glass-card {
  width: 100%;
  max-width: 420px;
  border-radius: 16px;
  padding: 36px 28px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.25);
  position: relative;
  z-index: 2;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  background: rgba(255, 255, 255, 0.16);
  border: 1px solid rgba(255, 255, 255, 0.25);
}

/* 表单与标题 */
.login-form { width: 100%; }
.login-header { text-align: center; margin-bottom: 20px; }
.login-header h2 { font-size: 24px; font-weight: 700; color: #fff; letter-spacing: 1px; }
.hint { font-size: 14px; color: rgba(255,255,255,0.85); margin: 6px 0 0; }

/* 输入项优化（利用 element-plus 样式变量） */
.input-item { margin-bottom: 18px; }
:deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(255,255,255,0.4) !important; /* 透明度调整为 0.4 */
  border: 1px solid rgba(255,255,255,0.35) !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  box-shadow: none;
}
:deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 3px rgba(64,158,255,0.25);
}
:deep(.el-input__inner) {
  background-color: transparent !important;
  color: #0f172a; /* 深色文字，在浅白半透明背景上更清晰 */
}
:deep(.el-input__inner::placeholder) {
  color: rgba(15,23,42,0.5);
}
:deep(.el-input__prefix) {
  color: rgba(15,23,42,0.65);
}

/* 登录选项与链接 */
.login-options { display: flex; justify-content: space-between; align-items: center; margin: 8px 0 18px; font-size: 14px; color: #f1f5f9; }
.forget-pwd { color: #e0f2fe; text-decoration: none; }
.forget-pwd:hover { color: #bae6fd; }
.register-link { text-align: center; margin-top: 14px; }
.register-link a { color: #e0f2fe; }
.register-link a:hover { color: #bae6fd; }

/* 登录按钮 */
.login-btn { width: 100%; height: 44px; border-radius: 12px; font-size: 16px; font-weight: 600; letter-spacing: 1px; }

/* 让主按钮呈现半透明玻璃效果 */
.login-btn {
  background: rgba(255,255,255,0.25) !important;
  border-color: rgba(255,255,255,0.4) !important;
  color: #ffffff !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.login-btn:hover,
.login-btn:focus {
  background: rgba(255,255,255,0.32) !important;
  border-color: rgba(255,255,255,0.45) !important;
}
.login-btn.is-disabled,
.login-btn.is-loading {
  opacity: 0.8;
}

/* 顶部工具小圆按钮半透明 */
.bg-tool-btn {
  background: rgba(255,255,255,0.28) !important;
  border-color: rgba(255,255,255,0.45) !important;
  color: #ffffff !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.bg-tool-btn:hover,
.bg-tool-btn:focus {
  background: rgba(255,255,255,0.36) !important;
  border-color: rgba(255,255,255,0.5) !important;
}

/* 调整“记住密码”复选框配色，避免默认蓝色 */
:deep(.el-checkbox__label) { color: #e5e7eb !important; }
:deep(.el-checkbox__inner) {
  background: rgba(255,255,255,0.12);
  border-color: rgba(255,255,255,0.55);
}
:deep(.el-checkbox:hover .el-checkbox__inner) {
  border-color: rgba(255,255,255,0.8);
}
:deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: rgba(255,255,255,0.85);
  border-color: rgba(255,255,255,0.9);
}
:deep(.el-checkbox__input.is-checked .el-checkbox__inner::after) {
  border-color: #0f172a; /* 深色对勾提升可见度 */
}

/* 响应式 */
@media (max-width: 768px) {
  .glass-card { max-width: 92%; padding: 24px 18px; margin: 16px; }
  .login-header h2 { font-size: 20px; }
}
</style>
