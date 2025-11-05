<template>
  <div class="profile-container">
    <div class="page-header">
      <h2>个人信息</h2>
      <p>查看和管理您的个人资料信息</p>
    </div>

    <div class="profile-card">
      <!-- 个人信息展示 -->
      <div class="profile-header">
        <div class="avatar-container">
          <el-avatar size="120" :src="avatarUrl">{{ userInfo.name.charAt(0) }}</el-avatar>
          <el-button type="primary" size="small" class="change-avatar-btn" @click="changeAvatarVisible = true">更换头像</el-button>
        </div>
        <div class="user-basic-info">
          <h3>{{ userInfo.name || userInfo.username }}</h3>
          <p class="user-title">{{ userInfo.title || '暂无职称' }}</p>
          <p class="user-username">用户名：{{ userInfo.username }}</p>
        </div>
      </div>

      <div class="profile-content">
        <el-tabs v-model="activeTab">
          <!-- 基本信息 -->
          <el-tab-pane label="基本信息" name="basic">
            <el-form :model="userInfo" label-width="120px" class="profile-form">
              <el-form-item label="用户名">
                <el-input :model-value="userInfo.username" disabled />
              </el-form-item>
              <el-form-item v-if="userInfo.teacher_id" label="教师编号">
                <el-input :model-value="userInfo.teacher_id" disabled />
              </el-form-item>
              <el-form-item label="姓名">
                <el-input v-model="userInfo.name" placeholder="请输入姓名" :disabled="!isEditing" />
              </el-form-item>
              <el-form-item label="职称">
                <el-input v-model="userInfo.title" placeholder="请输入职称" :disabled="!isEditing" />
              </el-form-item>
              <el-form-item label="邮箱">
                <el-input v-model="userInfo.email" placeholder="请输入邮箱" :disabled="!isEditing" />
              </el-form-item>
              <el-form-item label="手机号">
                <el-input v-model="userInfo.phone" placeholder="请输入手机号" :disabled="!isEditing" />
              </el-form-item>
              <el-form-item label="注册时间">
                <el-input v-model="formattedCreatedAt" disabled />
              </el-form-item>
              <el-form-item>
                <template v-if="!isEditing">
                  <el-button type="primary" @click="startEdit">编辑信息</el-button>
                </template>
                <template v-else>
                  <el-button type="primary" @click="saveChanges">保存修改</el-button>
                  <el-button @click="cancelEdit">取消</el-button>
                </template>
              </el-form-item>
            </el-form>
          </el-tab-pane>

          <!-- 安全设置 -->
          <el-tab-pane label="安全设置" name="security">
            <div class="security-section">
              <el-form label-width="120px" class="security-form">
                <el-form-item label="修改密码" class="security-item">
                  <el-button type="primary" @click="changePasswordVisible = true">修改密码</el-button>
                </el-form-item>
                <el-form-item label="账号状态" class="security-item">
                  <el-tag type="success" size="large">正常</el-tag>
                </el-form-item>
                <el-form-item label="登录记录" class="security-item">
                  <el-button type="primary" @click="viewLoginHistory">查看登录记录</el-button>
                </el-form-item>
              </el-form>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <!-- 更换头像对话框 -->
    <el-dialog title="更换头像" v-model="changeAvatarVisible" width="400px">
      <div class="avatar-uploader">
        <el-upload
          class="avatar-uploader"
          action=""
          :auto-upload="false"
          :on-change="handleAvatarChange"
          :show-file-list="false"
          accept="image/*"
        >
          <img v-if="previewAvatar" :src="previewAvatar" class="avatar-preview" />
          <div v-else class="avatar-placeholder">
            <el-icon><Plus /></el-icon>
            <div class="avatar-text">点击上传</div>
          </div>
        </el-upload>
        <p class="avatar-hint">支持 JPG、PNG 格式，文件大小不超过 2MB</p>
      </div>
      <template #footer>
        <el-button @click="changeAvatarVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmAvatarChange">确定</el-button>
      </template>
    </el-dialog>

    <!-- 修改密码对话框 -->
    <el-dialog title="修改密码" v-model="changePasswordVisible" width="400px">
      <el-form :model="passwordForm" :rules="passwordRules" ref="passwordFormRef" label-width="120px">
        <el-form-item label="当前密码" prop="currentPassword">
          <el-input v-model="passwordForm.currentPassword" type="password" placeholder="请输入当前密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="passwordForm.newPassword" type="password" placeholder="请输入新密码" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="passwordForm.confirmPassword" type="password" placeholder="请确认新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="changePasswordVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmPasswordChange">确定</el-button>
      </template>
    </el-dialog>

    <!-- 登录记录对话框 -->
    <el-dialog title="登录记录" v-model="loginHistoryVisible" width="800px">
      <el-table :data="loginHistoryData || []" style="width: 100%">
        <el-table-column prop="login_time" label="登录时间" width="200" />
        <el-table-column prop="ip_address" label="IP地址" width="150" />
        <el-table-column prop="device" label="设备信息" />
        <el-table-column prop="location" label="登录地点" width="150" />
        <el-table-column prop="status" label="登录状态" width="100">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">
              {{ scope.row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <template #footer>
        <el-button @click="loginHistoryVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import axios from 'axios'
import { Plus } from '@element-plus/icons-vue'

export default {
  name: 'Profile',
  components: { Plus },
  data() {
    return {
      activeTab: 'basic',
      isEditing: false,
      originalUserInfo: {},
      userInfo: {
        username: '',
        name: '',
        email: '',
        phone: '',
        title: '',
        created_at: null
      },
      avatarUrl: '',
      changeAvatarVisible: false,
      previewAvatar: '',
      changePasswordVisible: false,
      passwordForm: {
        currentPassword: '',
        newPassword: '',
        confirmPassword: ''
      },
      passwordRules: {
        currentPassword: [
          { required: true, message: '请输入当前密码', trigger: 'blur' },
          { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
        ],
        newPassword: [
          { required: true, message: '请输入新密码', trigger: 'blur' },
          { min: 6, max: 20, message: '密码长度在 6 到 20 个字符', trigger: 'blur' }
        ],
        confirmPassword: [
          { required: true, message: '请确认新密码', trigger: 'blur' },
          { 
            validator: (rule, value, callback) => {
              if (value !== this.passwordForm.newPassword) {
                callback(new Error('两次输入的密码不一致'))
              } else {
                callback()
              }
            },
            trigger: 'blur'
          }
        ]
      },
      loginHistoryVisible: false,
      loginHistoryData: [
        // 模拟数据
        {
          login_time: '2024-01-15 09:23:45',
          ip_address: '192.168.1.1',
          device: 'Chrome / Windows 10',
          location: '北京市',
          status: 'success'
        },
        {
          login_time: '2024-01-14 16:45:30',
          ip_address: '192.168.1.1',
          device: 'Firefox / MacOS',
          location: '北京市',
          status: 'success'
        }
      ]
    }
  },
  computed: {
    // 格式化创建时间
    formattedCreatedAt() {
      return this.formatDate(this.userInfo.created_at)
    }
  },
  created() {
    this.fetchUserInfo()
    // 从localStorage加载头像
    const savedAvatar = localStorage.getItem('userAvatar')
    if (savedAvatar) {
      this.avatarUrl = savedAvatar
    }
  },
  methods: {
    // 获取用户信息
    async fetchUserInfo() {
      try {
        const token = localStorage.getItem('token')
        
        // 检查token是否存在或有效
        if (!token || !token.trim()) {
          this.$message.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          this.$router.push('/login')
          return
        }
        
        // 调用后端 API 获取完整用户信息
        const response = await axios.get('/api/teacher/info', {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
          }
        })
        
        if (response.data.status === 'success') {
          // 使用后端返回的真实用户数据
          const userData = response.data.data
          this.userInfo = {
            username: userData.username || '',
            teacher_id: userData.teacher_id || '',
            name: userData.name || '',
            email: userData.email || '',
            phone: userData.phone || '',
            title: userData.title || '',
            created_at: userData.created_at
          }
          
          // 优先使用后端返回的头像
          if (userData.avatar && typeof userData.avatar === 'string' && userData.avatar.startsWith('data:image')) {
            this.avatarUrl = userData.avatar
            localStorage.setItem('userAvatar', userData.avatar)
          }

          this.originalUserInfo = JSON.parse(JSON.stringify(this.userInfo))
        } else {
          this.$message.error(response.data.message || '获取用户信息失败')
          // 如果是认证错误，清除token并跳转到登录页
          if (response.data.message && 
              (response.data.message.includes('未授权') || 
               response.data.message.includes('令牌') || 
               response.data.message.includes('Token'))) {
            localStorage.removeItem('token')
            localStorage.removeItem('username')
            this.$router.push('/login')
          }
        }
      } catch (error) {
        console.error('Failed to fetch user info:', error)
        
        // 检查错误类型
        const errorStatus = error.response?.status
        const errorMessage = error.response?.data?.message || ''
        
        // 如果是401错误或token相关错误
        if (errorStatus === 401 || 
            errorMessage.includes('未授权') || 
            errorMessage.includes('令牌') || 
            errorMessage.includes('Token') ||
            errorMessage.includes('过期') ||
            errorMessage.includes('过期')) {
          this.$message.error('登录已过期，请重新登录')
          localStorage.removeItem('token')
          localStorage.removeItem('username')
          setTimeout(() => {
            this.$router.push('/login')
          }, 1000)
        } else {
          // 其他错误
          const errorMsg = errorMessage || '获取用户信息失败'
          this.$message.error(errorMsg)
        }
      }
    },

    // 开始编辑
    startEdit() {
      this.isEditing = true
      this.originalUserInfo = JSON.parse(JSON.stringify(this.userInfo))
    },

    // 取消编辑
    cancelEdit() {
      this.isEditing = false
      this.userInfo = JSON.parse(JSON.stringify(this.originalUserInfo))
    },

  // 保存修改
    async saveChanges() {
      const token = localStorage.getItem('token')
      
      // 检查token是否存在且格式正确
      if (!token || !token.trim() || token.split('.').length !== 3) {
        this.$message.warning('会话已过期，请重新登录')
        localStorage.removeItem('token')
        localStorage.removeItem('username')
        setTimeout(() => {
          this.$router.push('/login')
        }, 1500)
        return
      }
      
      try {
        // 调用后端 API 保存用户信息
        const response = await axios.put('/api/teacher/info', 
          {
            name: this.userInfo.name,
            email: this.userInfo.email,
            phone: this.userInfo.phone,
            title: this.userInfo.title
          },
          {
            headers: {
              'Authorization': `Bearer ${token}`,
              'Content-Type': 'application/json'
            }
          }
        )
        
        if (response.data && response.data.status === 'success') {
          this.isEditing = false
          this.$message.success('个人信息更新成功')
          // 重新获取更新后的用户信息
          await this.fetchUserInfo()
        } else {
          // 处理认证错误，例如token过期或无效
          if (response.data && response.data.message && 
              (response.data.message.includes('未授权') || 
               response.data.message.includes('令牌') || 
               response.data.message.includes('Token') ||
               response.data.message.includes('认证'))) {
            localStorage.removeItem('token')
            localStorage.removeItem('username')
            this.$message.error('登录已过期或无效，请重新登录')
            setTimeout(() => {
              this.$router.push('/login')
            }, 1500)
          } else {
            this.$message.error(response.data?.message || '保存失败，请稍后再试')
          }
        }
      } catch (error) {
        // 处理网络错误或服务器错误
        if (error.response) {
          // 处理HTTP响应错误
          if (error.response.status === 401) {
            localStorage.removeItem('token')
            localStorage.removeItem('username')
            this.$message.error('认证失败，请重新登录')
            setTimeout(() => {
              this.$router.push('/login')
            }, 1500)
          } else if (error.response.status >= 500) {
            this.$message.error('服务器错误，请稍后再试')
          } else {
            this.$message.error(`请求失败: ${error.response.statusText || '未知错误'}`)
          }
        } else if (error.request) {
          // 处理请求发送失败（网络问题）
          this.$message.error('网络连接失败，请检查您的网络')
        } else {
          // 处理其他错误
          this.$message.error('请求错误，请稍后再试')
        }
        console.error('Failed to save user info:', error)
      }
    },

    // 处理头像变更
    handleAvatarChange(file) {
      // 文件大小限制：2MB
      const maxSize = 2 * 1024 * 1024
      if (file.size > maxSize) {
        this.$message.warning('图片大小不能超过 2MB')
        return
      }
      const reader = new FileReader()
      reader.onload = (e) => {
        this.previewAvatar = e.target.result
      }
      reader.readAsDataURL(file.raw)
    },

    // 确认更换头像
    async confirmAvatarChange() {
      try {
        const token = localStorage.getItem('token')
        if (!token) {
          this.$message.error('登录已过期，请重新登录')
          return
        }
        if (!this.previewAvatar) {
          this.$message.warning('请先选择图片')
          return
        }
        
        // 创建FormData对象上传头像
        const formData = new FormData()
        // 获取上传的文件对象（从this.previewAvatar生成一个Blob对象）
        const response = await fetch(this.previewAvatar)
        const blob = await response.blob()
        formData.append('avatar', blob, 'avatar.png')
        
        // 调用后端 API 上传头像
        const uploadResponse = await axios.post('/api/teacher/upload-avatar', formData, {
          headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'multipart/form-data'
          }
        })
        
        if (uploadResponse.data.status === 'success') {
          this.avatarUrl = uploadResponse.data.data.avatarUrl || this.previewAvatar
          // 保存头像URL到localStorage，使主界面能同步更新
          localStorage.setItem('userAvatar', this.avatarUrl)
          this.changeAvatarVisible = false
          this.$message.success('头像更换成功')
          // 触发全局事件通知其他组件更新头像
          window.dispatchEvent(new CustomEvent('avatarChanged', { detail: this.avatarUrl }))
          // 刷新用户信息（带回服务端头像，确保持久化）
          this.fetchUserInfo()
        } else {
          this.$message.error(uploadResponse.data.message || '头像上传失败')
        }
      } catch (error) {
        this.$message.error('头像上传失败，请重试')
        console.error('Failed to upload avatar:', error)
      }
    },

    // 确认修改密码
    async confirmPasswordChange() {
      try {
        await this.$refs.passwordFormRef.validate()
        
        const token = localStorage.getItem('token')
        
        // 调用后端 API 修改密码
        const response = await axios.post('/api/teacher/change-password',
          {
            currentPassword: this.passwordForm.currentPassword,
            newPassword: this.passwordForm.newPassword
          },
          {
            headers: {
              'Authorization': `Bearer ${token}`
            }
          }
        )
        
        if (response.data.status === 'success') {
          this.changePasswordVisible = false
          this.passwordForm = {
            currentPassword: '',
            newPassword: '',
            confirmPassword: ''
          }
          this.$message.success('密码修改成功，请重新登录')
          
          // 登出并跳转到登录页
          setTimeout(() => {
            localStorage.removeItem('token')
            localStorage.removeItem('username')
            this.$router.push('/login')
          }, 1000)
        } else {
          this.$message.error(response.data.message || '密码修改失败')
        }
      } catch (error) {
        this.$message.error('密码修改失败，请重试')
        console.error('Failed to change password:', error)
      }
    },

    // 查看登录记录
    async viewLoginHistory() {
      try {
        const token = localStorage.getItem('token')
        
        // 调用后端 API 获取登录记录
        const response = await axios.get('/api/teacher/login-history', {
          headers: {
            'Authorization': `Bearer ${token}`
          }
        })
        
        if (response.data.status === 'success') {
          this.loginHistoryData = response.data.data || []
        } else {
          this.loginHistoryData = []
          this.$message.error(response.data.message || '获取登录记录失败')
        }
        
        this.loginHistoryVisible = true
      } catch (error) {
        this.loginHistoryData = []
        this.$message.error('获取登录记录失败')
        console.error('Failed to fetch login history:', error)
        this.loginHistoryVisible = true
      }
    },

    // 格式化日期
    formatDate(dateStr) {
      if (!dateStr) return ''
      const date = new Date(dateStr)
      return date.toLocaleString('zh-CN', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
      })
    }
  }
}
</script>

<style scoped>
.profile-container {
  padding: 20px;
  background-color: #fafafa;
  min-height: calc(100vh - 100px);
}

.page-header {
  margin-bottom: 30px;
}

.page-header h2 {
  font-size: 24px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 8px;
}

.page-header p {
  font-size: 14px;
  color: #606266;
  margin: 0;
}

.profile-card {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.profile-header {
  padding: 30px;
  border-bottom: 1px solid #ebeef5;
  display: flex;
  align-items: center;
}

.avatar-container {
  margin-right: 30px;
  display: flex;
  flex-direction: column;
  align-items: center;
}

.avatar-container .el-avatar {
  margin-bottom: 15px;
  font-size: 48px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.change-avatar-btn {
  width: 100%;
}

.user-basic-info h3 {
  margin: 0 0 8px 0;
  font-size: 20px;
  font-weight: 600;
  color: #303133;
}

.user-title {
  margin: 0 0 12px 0;
  font-size: 14px;
  color: #606266;
}

.user-username {
  margin: 0;
  font-size: 14px;
  color: #909399;
}

.profile-content {
  padding: 10px;
}

.profile-form,
.security-form {
  padding: 30px;
}

.profile-form .el-form-item {
  margin-bottom: 34px;
}

.profile-form .el-input {
  width: 300px;
}

.profile-form .el-input.is-disabled .el-input__inner {
  background-color: #f5f7fa;
  color: #606266;
}

.security-item {
  display: flex;
  align-items: center;
  padding: 15px 0;
  border-bottom: 1px solid #ebeef5;
}

.security-item:last-child {
  border-bottom: none;
}

.avatar-uploader {
  text-align: center;
}

.avatar-preview {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  object-fit: cover;
}

.avatar-placeholder {
  width: 150px;
  height: 150px;
  border-radius: 50%;
  border: 1px dashed #dcdfe6;
  display: flex;
  flex-direction: column;
  justify-content: center;
  align-items: center;
  margin: 0 auto;
  cursor: pointer;
  transition: all 0.3s;
  background-color: #f5f7fa;
}

.avatar-placeholder:hover {
  border-color: #409eff;
  color: #409eff;
}

.avatar-placeholder .el-icon {
  font-size: 32px;
  margin-bottom: 8px;
}

.avatar-text {
  font-size: 14px;
  color: #909399;
}

.avatar-hint {
  margin-top: 15px;
  font-size: 12px;
  color: #909399;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .profile-header {
    flex-direction: column;
    text-align: center;
  }
  
  .avatar-container {
    margin-right: 0;
    margin-bottom: 20px;
  }
  
  .profile-form,
  .security-form {
    padding: 20px;
  }
}
</style>