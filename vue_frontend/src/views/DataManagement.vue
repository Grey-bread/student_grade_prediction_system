<template>
  <div class="data-management-container">
    <div class="page-header">
      <h2>数据管理中心</h2>
      <p>统一管理学生数据的上传和采集工作</p>
    </div>

    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" type="card" class="management-tabs">
      <!-- 数据上传标签页 -->
      <el-tab-pane label="数据上传" name="upload">
        <div class="tab-content">
          <div class="upload-section">
            <h3>学生数据文件上传</h3>
            <p class="section-description">上传CSV或Excel格式的学生数据文件进行系统分析</p>
            
            <div class="upload-area">
              <el-upload
                class="upload-demo"
                drag
                action="/api/analysis/uploads"
                multiple
                :auto-upload="false"
                :on-change="handleFileChange"
                :before-upload="beforeUpload"
                :file-list="uploadFiles"
                accept=".csv,.xlsx,.xls">
                <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
                <div class="el-upload__text">
                  将文件拖到此处，或 <em>点击上传</em>
                </div>
                <template #tip>
                  <div class="el-upload__tip">
                    支持扩展名：.csv, .xlsx, .xls
                  </div>
                </template>
              </el-upload>
              
              <el-button 
                type="primary" 
                :disabled="uploadFiles.length === 0" 
                @click="submitUpload"
                class="upload-btn">
                开始上传
              </el-button>
            </div>

            <!-- 上传历史 -->
            <div class="upload-history">
              <h3>最近上传历史</h3>
              <el-table :data="uploadHistory || []" style="width: 100%" v-if="(uploadHistory || []).length > 0">
                <el-table-column prop="filename" label="文件名" width="280"></el-table-column>
                <el-table-column prop="uploadTime" label="上传时间" width="180"></el-table-column>
                <el-table-column prop="fileSize" label="文件大小"></el-table-column>
                <el-table-column prop="status" label="状态">
                  <template #default="scope">
                    <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
                  </template>
                </el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button type="text" size="small" @click="viewFileDetails(scope.row)">查看详情</el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="empty-state">
                <el-empty description="暂无上传记录"></el-empty>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>

      <!-- 数据采集标签页 -->
      <el-tab-pane label="数据采集" name="collection">
        <div class="tab-content">
          <div class="collection-section">
            <h3>数据源配置</h3>
            <p class="section-description">配置和管理系统的数据采集来源</p>

            <div class="data-sources">
              <el-card v-for="source in dataSources" :key="source.id" class="source-card">
                <template #header>
                  <div class="card-header">
                    <span>{{ source.name }}</span>
                    <el-button type="text" size="small" @click="editDataSource(source)">编辑</el-button>
                  </div>
                </template>
                <div class="source-info">
                  <p><strong>类型：</strong>{{ source.type }}</p>
                  <p><strong>状态：</strong>
                    <el-tag :type="source.active ? 'success' : 'warning'">
                      {{ source.active ? '已激活' : '未激活' }}
                    </el-tag>
                  </p>
                  <p><strong>最后采集：</strong>{{ formatDate(source.lastCollection) }}</p>
                  <el-button 
                    type="primary" 
                    size="small" 
                    :disabled="!source.active"
                    @click="collectData(source.id)">
                    立即采集
                  </el-button>
                </div>
              </el-card>

              <el-card class="add-source-card">
                <div class="add-source-content" @click="showAddSourceDialog">
                  <el-icon class="add-icon"><Plus /></el-icon>
                  <p>添加新数据源</p>
                </div>
              </el-card>
            </div>

            <!-- 采集任务列表 -->
            <div class="collection-tasks">
              <h3>采集任务列表</h3>
              <el-table :data="collectionTasks || []" style="width: 100%" v-if="(collectionTasks || []).length > 0">
                <el-table-column prop="name" label="任务名称" width="200"></el-table-column>
                <el-table-column prop="source" label="数据源" width="150"></el-table-column>
                <el-table-column prop="status" label="状态">
                  <template #default="scope">
                    <el-tag 
                      :type="getStatusType(scope.row.status)">
                      {{ scope.row.status }}
                    </el-tag>
                  </template>
                </el-table-column>
                <el-table-column prop="progress" label="进度">
                  <template #default="scope">
                    <el-progress :percentage="scope.row.progress" :status="getStatusProgress(scope.row.status)"></el-progress>
                  </template>
                </el-table-column>
                <el-table-column prop="createdAt" label="创建时间" width="180"></el-table-column>
                <el-table-column label="操作" width="120">
                  <template #default="scope">
                    <el-button 
                      type="text" 
                      size="small" 
                      :disabled="scope.row.status !== 'running'"
                      @click="cancelTask(scope.row.id)">
                      取消
                    </el-button>
                  </template>
                </el-table-column>
              </el-table>
              <div v-else class="empty-state">
                <el-empty description="暂无采集任务"></el-empty>
              </div>
            </div>
          </div>
        </div>
      </el-tab-pane>
    </el-tabs>

    <!-- 添加数据源对话框 -->
    <el-dialog
      v-model="addSourceVisible"
      title="添加数据源"
      width="500px">
      <el-form :model="newSource" :rules="sourceRules" ref="sourceForm">
        <el-form-item label="数据源名称" prop="name">
          <el-input v-model="newSource.name" placeholder="请输入数据源名称"></el-input>
        </el-form-item>
        <el-form-item label="数据源类型" prop="type">
          <el-select v-model="newSource.type" placeholder="请选择数据源类型">
            <el-option label="API接口" value="api"></el-option>
            <el-option label="数据库" value="database"></el-option>
            <el-option label="文件系统" value="file_system"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="配置信息" prop="config">
          <el-input type="textarea" v-model="newSource.config" placeholder="请输入配置信息"></el-input>
        </el-form-item>
        <el-form-item>
          <el-switch v-model="newSource.active" active-text="启用" inactive-text="禁用"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="addSourceVisible = false">取消</el-button>
          <el-button type="primary" @click="submitNewSource">确认</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 编辑数据源对话框 -->
    <el-dialog
      v-model="editSourceVisible"
      title="编辑数据源"
      width="520px">
      <el-form :model="editSource">
        <el-form-item label="数据源名称">
          <el-input v-model="editSource.name" />
        </el-form-item>
        <el-form-item label="数据源类型">
          <el-select v-model="editSource.type" placeholder="请选择数据源类型">
            <el-option label="API接口" value="api"></el-option>
            <el-option label="数据库" value="database"></el-option>
            <el-option label="文件系统" value="file_system"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="配置信息">
          <el-input type="textarea" v-model="editSource.config" />
        </el-form-item>
        <el-form-item>
          <el-switch v-model="editSource.active" active-text="启用" inactive-text="禁用"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button type="danger" @click="deleteSource(editSource.id)" v-if="editSource.id">删除</el-button>
          <el-button @click="editSourceVisible = false">取消</el-button>
          <el-button type="primary" @click="saveEditSource">保存</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive } from 'vue'
import { UploadFilled, Plus } from '@element-plus/icons-vue'
import axios from 'axios'

export default {
  name: 'DataManagement',
  components: {
    UploadFilled,
    Plus
  },
  setup() {
    // 标签页状态
    const activeTab = ref('upload')
    
    // 上传文件相关
    const uploadFiles = ref([])
    
    // 数据，初始为空，将从后端获取
    const uploadHistory = ref([])
    const dataSources = ref([])
    const collectionTasks = ref([])
    
    // 加载真实数据（来自后端数据库）
    const loadData = async () => {
      try {
        const [uploadsRes, sourcesRes, tasksRes] = await Promise.all([
          axios.get('/api/analysis/uploads'),
          axios.get('/api/analysis/data-sources', { params: { onlySaved: 1 } }),
          axios.get('/api/analysis/collection-tasks')
        ])

        uploadHistory.value = (uploadsRes.data && uploadsRes.data.data) || []
        dataSources.value = (sourcesRes.data && sourcesRes.data.data) || []
        collectionTasks.value = (tasksRes.data && tasksRes.data.data) || []
      } catch (err) {
        console.error('加载数据失败: ', err)
      }
    }
    
    // 组件挂载时加载数据
    loadData()
    
    // 新增数据源对话框
    const addSourceVisible = ref(false)
    const newSource = reactive({
      name: '',
      type: '',
      config: '',
      active: true
    })
    
    // 数据源表单验证规则
    const sourceRules = {
      name: [
        { required: true, message: '请输入数据源名称', trigger: 'blur' },
        { min: 2, max: 50, message: '长度在 2 到 50 个字符', trigger: 'blur' }
      ],
      type: [
        { required: true, message: '请选择数据源类型', trigger: 'change' }
      ],
      config: [
        { required: true, message: '请输入配置信息', trigger: 'blur' }
      ]
    }
    
    // 文件变化处理
    const handleFileChange = (file) => {
      // 检查文件是否已存在
      const isExist = uploadFiles.value.some(item => item.name === file.name)
      if (!isExist) {
        uploadFiles.value.push(file)
      }
    }
    
    // 上传前检查
    const beforeUpload = (file) => {
      const isCSV = file.type === 'text/csv' || file.name.endsWith('.csv')
      const isExcel = file.type.includes('excel') || 
                     file.name.endsWith('.xlsx') || 
                     file.name.endsWith('.xls')
      
      if (!isCSV && !isExcel) {
        alert('请上传CSV或Excel格式的文件!')
        return false
      }
      
      const isLt2M = file.size / 1024 / 1024 < 10
      if (!isLt2M) {
        alert('文件大小不能超过10MB!')
        return false
      }
      
      return true
    }
    
    // 提交上传
    const submitUpload = async () => {
      const formData = new FormData()
      uploadFiles.value.forEach(file => {
        if (file && file.raw) {
          formData.append('files', file.raw, file.name)
        }
      })

      try {
        await axios.post('/api/analysis/uploads', formData, {
          headers: { 'Content-Type': 'multipart/form-data' }
        })
        // 成功后，刷新上传历史并清空待上传列表
        await loadData()
        uploadFiles.value = []
        alert('文件上传成功!')
      } catch (error) {
        console.error('上传失败:', error)
        alert('上传失败，请重试!')
      }
    }
    
    // 查看文件详情
    const viewFileDetails = (file) => {
      console.log('查看文件详情:', file)
      // 实际应用中这里会显示文件详情
    }
    
    // 显示添加数据源对话框
    const showAddSourceDialog = () => {
      addSourceVisible.value = true
    }
    
    // 编辑数据源
    const editSourceVisible = ref(false)
    const editSource = reactive({ id: null, name: '', type: '', config: '', active: true, lastCollection: null })
    const editDataSource = (source) => {
      editSource.id = source.id
      editSource.name = source.name
      editSource.type = source.type
      editSource.config = source.config || ''
      editSource.active = !!source.active
      editSource.lastCollection = source.lastCollection || null
      editSourceVisible.value = true
    }
    const saveEditSource = async () => {
      try {
        await axios.patch(`/api/analysis/data-sources/${editSource.id}` , {
          name: editSource.name,
          type: editSource.type,
          config: editSource.config,
          active: editSource.active
        })
        await loadData()
        editSourceVisible.value = false
      } catch (err) {
        console.error('更新数据源失败: ', err)
        alert('更新失败，请重试')
      }
    }
    const deleteSource = async (id) => {
      try {
        await axios.delete(`/api/analysis/data-sources/${id}`)
        await loadData()
        editSourceVisible.value = false
      } catch (err) {
        console.error('删除数据源失败: ', err)
        alert('删除失败，请重试')
      }
    }
    
    // 提交新数据源
    const submitNewSource = async () => {
      try {
        await axios.post('/api/analysis/data-sources', {
          name: newSource.name,
          type: newSource.type,
          config: newSource.config,
          active: newSource.active
        })
        await loadData()
        // 重置表单
        Object.assign(newSource, { name: '', type: '', config: '', active: true })
        addSourceVisible.value = false
      } catch (err) {
        console.error('新增数据源失败: ', err)
        alert('新增失败，请检查后端服务。')
      }
    }
    
    // 采集数据
    const collectData = async (sourceId) => {
      const source = dataSources.value.find(s => s.id === sourceId)
      if (!source) return

      let createdId = null
      try {
        const resp = await axios.post('/api/analysis/collection-tasks', {
          source_id: source.id > 0 ? source.id : null,
          source_name: source.name,
          name: `${source.name}数据采集`
        })
        createdId = resp?.data?.data?.id || null
      } catch (err) {
        console.error('创建采集任务失败: ', err)
      }

      // 本地创建一个运行中任务用于展示进度
      const taskId = createdId || Date.now()
      collectionTasks.value.unshift({
        id: taskId,
        name: `${source.name}数据采集`,
        source: source.name,
        status: 'running',
        progress: 0,
        createdAt: new Date().toLocaleString()
      })
      simulateCollectionProgress(taskId, createdId, source.id)
    }
    
    // 模拟采集进度
    const simulateCollectionProgress = (taskId, serverId, sourceId) => {
      const task = collectionTasks.value.find(t => t.id === taskId)
      if (!task) return
      
      let progress = 0
      const interval = setInterval(() => {
        progress += Math.random() * 20
        if (progress >= 100) {
          progress = 100
          task.status = 'completed'
          if (serverId) {
            axios.patch(`/api/analysis/collection-tasks/${serverId}`, { status: 'completed', progress: 100 }).catch(()=>{})
          }
          clearInterval(interval)
          
          // 更新数据源最后采集时间
          const source = dataSources.value.find(s => s.name === task.source)
          if (source) {
            source.lastCollection = new Date().toLocaleString()
          }
          
          console.log('数据采集完成:', task.name)
        }
        task.progress = Math.floor(progress)
        if (serverId) {
          axios.patch(`/api/analysis/collection-tasks/${serverId}`, { progress: task.progress }).catch(()=>{})
        }
      }, 500)
    }
    
    // 取消任务
    const cancelTask = async (taskId) => {
      try {
        await axios.post(`/api/analysis/collection-tasks/${taskId}/cancel`)
      } catch (err) {
        console.error('取消任务失败: ', err)
      }
      const task = collectionTasks.value.find(t => t.id === taskId)
      if (task) task.status = 'cancelled'
    }
    
    // 格式化日期
    const formatDate = (dateStr) => {
      if (!dateStr) return '从未采集'
      return dateStr
    }
    
    // 格式化文件大小
    const formatFileSize = (bytes) => {
      if (bytes === 0) return '0 B'
      const k = 1024
      const sizes = ['B', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    }
    
    // 获取状态类型
    const getStatusType = (status) => {
      const typeMap = {
        'completed': 'success',
        'running': 'primary',
        'failed': 'danger',
        'cancelled': 'warning'
      }
      return typeMap[status] || 'info'
    }
    
    // 获取进度条状态
    const getStatusProgress = (status) => {
      if (status === 'failed') return 'exception'
      if (status === 'cancelled') return 'warning'
      if (status === 'completed') return 'success'
      return ''
    }
    
    return {
      activeTab,
      uploadFiles,
      uploadHistory,
      dataSources,
      collectionTasks,
      addSourceVisible,
      newSource,
      editSourceVisible,
      editSource,
      sourceRules,
      handleFileChange,
      beforeUpload,
      submitUpload,
      viewFileDetails,
      showAddSourceDialog,
      editDataSource,
      saveEditSource,
      deleteSource,
      submitNewSource,
      collectData,
      cancelTask,
      formatDate,
      getStatusType,
      getStatusProgress
    }
  }
}
</script>

<style scoped>
.data-management-container {
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
}

.management-tabs {
  background-color: #fff;
  border-radius: 8px;
  box-shadow: 0 2px 12px 0 rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.tab-content {
  padding: 20px;
}

.section-description {
  color: #606266;
  margin-bottom: 20px;
  font-size: 14px;
}

/* 上传区域样式 */
.upload-section {
  margin-bottom: 30px;
}

.upload-area {
  background-color: #f5f7fa;
  padding: 20px;
  border-radius: 8px;
  margin-bottom: 20px;
}

.upload-btn {
  margin-top: 15px;
}

/* 上传历史样式 */
.upload-history {
  margin-top: 30px;
}

.upload-history h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
}

/* 数据采集样式 */
.collection-section h3,
.collection-tasks h3 {
  font-size: 18px;
  font-weight: 600;
  color: #303133;
  margin-bottom: 15px;
}

.data-sources {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 20px;
  margin-bottom: 30px;
}

.source-card {
  transition: all 0.3s ease;
}

.source-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.source-info p {
  margin-bottom: 10px;
}

.add-source-card {
  border: 2px dashed #dcdfe6;
  display: flex;
  align-items: center;
  justify-content: center;
  height: 120px;
  cursor: pointer;
  transition: all 0.3s ease;
}

.add-source-card:hover {
  border-color: #409eff;
  color: #409eff;
}

.add-source-content {
  text-align: center;
  padding: 20px;
}

.add-icon {
  font-size: 32px;
  margin-bottom: 10px;
}

/* 采集任务样式 */
.collection-tasks {
  margin-top: 30px;
}

/* 空状态样式 */
.empty-state {
  padding: 40px 0;
  text-align: center;
}

/* 响应式设计 */
@media (max-width: 768px) {
  .data-sources {
    grid-template-columns: 1fr;
  }
  
  .tab-content {
    padding: 15px;
  }
}
</style>