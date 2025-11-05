<template>
  <div class="auth-container">
    <div class="register-box">
      <el-form
        ref="regForm"
        :model="form"
        :rules="rules"
        class="register-form"
      >
        <div class="register-header">
          <h2>教师注册</h2>
          <p class="hint">请填写以下信息完成注册</p>
        </div>

        <el-form-item prop="username" class="input-item">
          <el-input v-model="form.username" placeholder="用户名" size="large" clearable>
            <template #prefix>
              <el-icon><User /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="email" class="input-item">
          <el-input v-model="form.email" placeholder="邮箱" size="large" clearable>
            <template #prefix>
              <el-icon><Message /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="phone" class="input-item">
          <el-input v-model="form.phone" placeholder="手机号" size="large" clearable>
            <template #prefix>
              <el-icon><Phone /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="password" class="input-item">
          <el-input v-model="form.password" type="password" show-password placeholder="密码" size="large">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-form-item prop="confirmPassword" class="input-item">
          <el-input v-model="form.confirmPassword" type="password" show-password placeholder="确认密码" size="large" @keyup.enter="submit">
            <template #prefix>
              <el-icon><Lock /></el-icon>
            </template>
          </el-input>
        </el-form-item>

        <el-button type="primary" class="register-btn" :loading="loading" :disabled="loading" @click="submit">注册</el-button>

        <div class="login-link">
          <router-link to="/login">已有账号？立即登录</router-link>
        </div>
      </el-form>
    </div>
  </div>
</template>

<script>
import axios from 'axios'
import { User, Lock, Phone, Message } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'Register',
  components: { User, Lock, Phone, Message },
  data() {
    const validatePassword = (rule, value, callback) => {
      if (!value) return callback(new Error('请输入密码'))
      if (value.length < 6 || value.length > 20) return callback(new Error('密码长度在 6 到 20 个字符'))
      if (!/^(?=.*[a-z])(?=.*[A-Z])(?=.*\d).{6,20}$/.test(value)) return callback(new Error('密码必须包含大小写字母和数字'))
      if (this.form.confirmPassword) this.$refs.regForm.validateField('confirmPassword')
      callback()
    }

    const validateConfirmPassword = (rule, value, callback) => {
      if (!value) return callback(new Error('请输入确认密码'))
      if (value !== this.form.password) return callback(new Error('两次输入的密码不一致'))
      callback()
    }

    const validateEmail = (rule, value, callback) => {
      if (!value) return callback()
      if (!/^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$/.test(value)) {
        return callback(new Error('请输入有效的邮箱地址'))
      }
      callback()
    }

    const validatePhone = (rule, value, callback) => {
      if (!value) return callback()
      if (!/^1[3-9]\d{9}$/.test(value)) {
        return callback(new Error('请输入有效的手机号码'))
      }
      callback()
    }

    return {
      form: {
        username: this.$route.query.username || '',
        password: '',
        confirmPassword: '',
        name: '',
        email: '',
        phone: ''
      },
      loading: false,
      rules: {
        username: [
          { required: true, message: '请输入用户名', trigger: 'blur' },
          { min: 3, max: 20, message: '长度在 3 到 20 个字符', trigger: 'blur' },
          { pattern: /^[a-zA-Z0-9_-]+$/, message: '用户名只能包含字母、数字、下划线和连字符', trigger: ['blur', 'change'] }
        ],
        password: [ { required: true, validator: validatePassword, trigger: ['blur', 'change'] } ],
        confirmPassword: [ { required: true, validator: validateConfirmPassword, trigger: ['blur', 'change'] } ],
        name: [ { min: 2, max: 20, message: '姓名长度在 2 到 20 个字符', trigger: 'blur' } ],
        email: [ { validator: validateEmail, trigger: ['blur', 'change'] } ],
        phone: [ { validator: validatePhone, trigger: ['blur', 'change'] } ]
      }
    }
  },
  methods: {
    async submit(e) {
      e && e.preventDefault()
      if (this.loading) return
      try {
        await this.$refs.regForm.validate()
        this.loading = true

        const payload = {
          username: (this.form.username || '').trim(),
          password: this.form.password,
          name: this.form.name?.trim() || '',
          email: this.form.email?.trim() || '',
          phone: this.form.phone?.trim() || ''
        }

        const res = await axios.post('/api/teacher/register', payload)
        if (res.data && (res.data.code === 0 || res.data.status === 'success')) {
          ElMessage({ type: 'success', message: '注册成功，正在跳转登录页...', duration: 1500 })
          this.$refs.regForm.resetFields()
          setTimeout(() => this.$router.push({ path: '/login', query: { username: payload.username } }), 1200)
        } else {
          throw new Error(res.data?.message || '注册失败')
        }
      } catch (err) {
        ElMessage({ type: 'error', message: err.response?.data?.message || err.message || '注册失败' })
      } finally {
        this.loading = false
      }
    }
  }
}
</script>

<style scoped>
/* 注册容器样式，使用与主界面一致的风格 */
.register-box {
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

/* 注册表单样式 */
.register-form {
  width: 100%;
}

.register-header {
  text-align: center;
  margin-bottom: 28px;
}

.register-header h2 {
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

/* 注册按钮 */
.register-btn {
  width: 100%;
  height: 40px;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 500;
  background-color: #409eff;
  border-color: #409eff;
  transition: all 0.3s ease;
}

.register-btn:hover {
  background-color: #66b1ff;
  border-color: #66b1ff;
  box-shadow: 0 4px 12px rgba(64, 158, 255, 0.3);
}

.register-btn.is-loading {
  background-color: #409eff;
  border-color: #409eff;
}

/* 登录链接 */
.login-link {
  text-align: center;
  margin-top: 20px;
  font-size: 14px;
}

.login-link a {
  color: #409eff;
  text-decoration: none;
  transition: color 0.3s ease;
}

.login-link a:hover {
  color: #66b1ff;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .register-box {
    width: 90%;
    max-width: 400px;
    padding: 24px;
    margin: 20px;
  }
  
  .system-name {
    font-size: 18px;
  }
  
  .register-header h2 {
    font-size: 20px;
  }
}
</style>
