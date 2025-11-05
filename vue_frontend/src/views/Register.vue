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

    <div class="register-box glass-card">
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
import { User, Lock, Phone, Message, Picture, Refresh } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'

export default {
  name: 'Register',
  components: { User, Lock, Phone, Message, Picture, Refresh },
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
      bgImage: localStorage.getItem('authBgImage') || '',
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
      return { backgroundImage: 'linear-gradient(135deg, #ffffff 0%, #f8fafc 50%, #ffffff 100%)' }
    }
  },
  methods: {
    triggerBgUpload() { this.$refs.bgInput && this.$refs.bgInput.click() },
    onBgSelected(e) {
      const file = e?.target?.files?.[0]
      if (!file) return
      const reader = new FileReader()
      reader.onload = () => {
        try {
          const dataUrl = reader.result
          this.bgImage = dataUrl
          localStorage.setItem('authBgImage', dataUrl)
          ElMessage.success('背景已更新')
        } catch (err) {
          ElMessage.error('设置背景失败')
        }
      }
      reader.readAsDataURL(file)
      e.target.value = ''
    },
    resetBg() {
      this.bgImage = ''
      localStorage.removeItem('authBgImage')
      ElMessage.success('已恢复默认背景')
    },
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
/* 布局与背景 */
.auth-container { position: relative; min-height: 100vh; display: flex; justify-content: center; align-items: center; overflow: hidden; background-color: #ffffff; }
.auth-bg { position: fixed; inset: 0; background-size: cover; background-position: center; background-repeat: no-repeat; filter: brightness(0.95); transition: background-image 0.3s ease; }
.auth-bg-overlay { position: fixed; inset: 0; background: linear-gradient(to bottom right, rgba(0,0,0,0.2), rgba(0,0,0,0.35)); pointer-events: none; }
.auth-tools { position: absolute; top: 16px; right: 16px; display: flex; gap: 8px; z-index: 3; }
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
.register-form { width: 100%; }
.register-header { text-align: center; margin-bottom: 20px; }
.register-header h2 { font-size: 24px; font-weight: 700; color: #fff; letter-spacing: 1px; }
.hint { font-size: 14px; color: rgba(255,255,255,0.85); margin: 6px 0 0; }

/* 输入项优化 */
.input-item { margin-bottom: 18px; }
:deep(.el-input__wrapper) {
  border-radius: 12px;
  background: rgba(255,255,255,0.4) !important; /* 透明度调整为 0.4 */
  border: 1px solid rgba(255,255,255,0.35) !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
  box-shadow: none;
}
:deep(.el-input__wrapper.is-focus) { box-shadow: 0 0 0 3px rgba(64,158,255,0.25); }
:deep(.el-input__inner) { background-color: transparent !important; color: #0f172a; }
:deep(.el-input__inner::placeholder) { color: rgba(15,23,42,0.5); }
:deep(.el-input__prefix) { color: rgba(15,23,42,0.65); }

/* 注册按钮 */
.register-btn { width: 100%; height: 44px; border-radius: 12px; font-size: 16px; font-weight: 600; letter-spacing: 1px; }
/* 让主按钮呈现半透明玻璃效果 */
.register-btn {
  background: rgba(255,255,255,0.25) !important;
  border-color: rgba(255,255,255,0.4) !important;
  color: #ffffff !important;
  backdrop-filter: blur(4px);
  -webkit-backdrop-filter: blur(4px);
}
.register-btn:hover,
.register-btn:focus {
  background: rgba(255,255,255,0.32) !important;
  border-color: rgba(255,255,255,0.45) !important;
}
.register-btn.is-disabled,
.register-btn.is-loading {
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

/* 链接 */
.login-link { text-align: center; margin-top: 14px; }
.login-link a { color: #e0f2fe; }
.login-link a:hover { color: #bae6fd; }

/* 响应式 */
@media (max-width: 768px) {
  .glass-card { max-width: 92%; padding: 24px 18px; margin: 16px; }
  .register-header h2 { font-size: 20px; }
}
</style>
