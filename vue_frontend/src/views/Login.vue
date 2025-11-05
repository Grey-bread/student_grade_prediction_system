<template>
  <div class="auth-container">
    <div class="login-box">
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
import { User, Lock } from '@element-plus/icons-vue'

export default {
  name: 'Login',
  components: { User, Lock },
  data() {
    return {
      loginForm: { username: '', password: '' },
      loginRules: {
        username: [ { required: true, message: '请输入账号', trigger: 'blur' }, { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' } ],
        password: [ { required: true, message: '请输入密码', trigger: 'blur' }, { min: 6, max: 20, message: '长度在 6 到 20 个字符', trigger: 'blur' } ]
      },
      loading: false,
      rememberMe: false
    }
  },
  created() {
    const rememberedUser = localStorage.getItem('remember_user')
    if (rememberedUser) { this.loginForm.username = rememberedUser; this.rememberMe = true }
  },
  methods: {
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
/* 登录容器样式，使用与主界面一致的风格 */
.login-box {
  width: 100%;
  max-width: 400px;
  background-color: #fff;
  border-radius: 12px;
  padding: 40px 32px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.15);
  position: relative;
  overflow: hidden;
  z-index: 1;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.95);
  margin: 0 auto;
}

/* 登录表单样式 */
.login-form {
  width: 100%;
}

.login-header {
  text-align: center;
  margin-bottom: 28px;
}

.login-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.hint {
  font-size: 14px;
  color: #606266;
  margin: 0;
}

/* 输入项样式 */
.input-item {
  margin-bottom: 20px;
}

.input-item .el-input {
  width: 100%;
}

.input-item .el-input__wrapper {
  border-radius: 8px;
  transition: all 0.3s ease;
}

.input-item .el-input__wrapper:hover {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.1);
}

.input-item .el-input__wrapper.is-focus {
  box-shadow: 0 0 0 2px rgba(64, 158, 255, 0.2);
}

/* 登录选项 */
.login-options {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
  font-size: 14px;
}

.forget-pwd {
  color: #409eff;
  text-decoration: none;
  transition: color 0.3s ease;
}

.forget-pwd:hover {
  color: #66b1ff;
}

/* 登录按钮 */
.login-btn {
  width: 100%;
  height: 40px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  background-color: #409eff;
  border-color: #409eff;
  transition: all 0.3s ease;
}

.login-btn:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.login-btn.is-loading {
  background-color: #409eff;
  border-color: #409eff;
}

/* 注册链接 */
.register-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
}

.register-link a {
  color: #409eff;
  text-decoration: none;
  transition: color 0.3s ease;
}

.register-link a:hover {
  color: #66b1ff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .login-box {
    width: 90%;
    max-width: 400px;
    padding: 24px;
    margin: 20px;
  }
  
  .system-name {
    font-size: 18px;
  }
  
  .login-header h2 {
    font-size: 20px;
  }
}
</style>
