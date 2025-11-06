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
            <h3>数据源</h3>
            <div class="sources-toolbar">
              <el-button type="primary" @click="showAddSourceDialog"><el-icon><Plus /></el-icon>&nbsp;添加数据源</el-button>
              <el-button @click="loadData">刷新</el-button>
            </div>

            <el-table :data="dataSources" style="width: 100%" border stripe empty-text="暂无数据源">
              <el-table-column prop="name" label="名称" min-width="160" />
              <el-table-column prop="type" label="类型" width="120" />
              
              <el-table-column label="启用" width="120">
                <template #default="scope">
                  <el-switch 
                    v-model="scope.row.active" 
                    :active-value="true" 
                    :inactive-value="false" 
                    :disabled="!(scope.row.id > 0)"
                    @change="toggleSourceActive(scope.row)" />
                </template>
              </el-table-column>
              <el-table-column prop="lastCollection" label="最后采集" width="180">
                <template #default="scope">{{ formatDate(scope.row.lastCollection) }}</template>
              </el-table-column>
              <el-table-column label="配置" min-width="220">
                <template #default="scope">
                  <el-tooltip placement="top" effect="dark" :content="String(scope.row.config || '')">
                    <span class="config-ellipsis">{{ String(scope.row.config || '').slice(0, 50) }}<span v-if="String(scope.row.config || '').length > 50">...</span></span>
                  </el-tooltip>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="300" fixed="right">
                <template #default="scope">
                  <el-button size="small" :disabled="!(scope.row.id > 0)" @click="editDataSource(scope.row)">编辑</el-button>
                  <el-button size="small" type="primary" :disabled="!scope.row.active || !(scope.row.id > 0)" @click="collectData(scope.row.id)">立即采集</el-button>
                  <el-button type="text" size="small" @click="viewRuns(scope.row)">采集记录</el-button>
                  <template v-if="scope.row.id > 0">
                    <el-popconfirm title="确认删除该数据源？" confirm-button-text="删除" cancel-button-text="取消" @confirm="deleteDataSource(scope.row)">
                      <template #reference>
                        <el-button size="small" type="danger">删除</el-button>
                      </template>
                    </el-popconfirm>
                  </template>
                  <template v-else>
                    <el-tooltip content="内置临时项，不能删除" placement="top">
                      <el-button size="small" type="danger" disabled>删除</el-button>
                    </el-tooltip>
                  </template>
                </template>
              </el-table-column>
            </el-table>

            <!-- 采集任务列表 -->
            <div class="collection-tasks">
              <div class="tasks-header">
                <h3>采集任务列表</h3>
                <el-button size="small" type="danger" plain :disabled="(collectionTasks || []).length === 0" @click="clearTasks">清空</el-button>
              </div>
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
          <el-input type="textarea" v-model="newSource.config" placeholder='请输入JSON，如 {"table":"exam_scores","key_column":"id","interval_seconds":30}' rows="5"></el-input>
          <div class="json-tools">
            <el-button type="text" @click="formatJson('new')">格式化JSON</el-button>
            <el-button type="text" @click="applyTemplate('new','id')">模板：主键增量</el-button>
            <el-button type="text" @click="applyTemplate('new','updated')">模板：时间戳增量</el-button>
          </div>
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
      width="500px">
      <el-form :model="editSource" :rules="sourceRules" ref="editSourceForm">
        <el-form-item label="数据源名称" prop="name">
          <el-input v-model="editSource.name" placeholder="请输入数据源名称"></el-input>
        </el-form-item>
        <el-form-item label="数据源类型" prop="type">
          <el-select v-model="editSource.type" placeholder="请选择数据源类型">
            <el-option label="API接口" value="api"></el-option>
            <el-option label="数据库" value="database"></el-option>
            <el-option label="文件系统" value="file_system"></el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="配置信息" prop="config">
          <el-input type="textarea" v-model="editSource.config" placeholder='请输入JSON，如 {"table":"exam_scores","key_column":"id","interval_seconds":30}' rows="5"></el-input>
          <div class="json-tools">
            <el-button type="text" @click="formatJson('edit')">格式化JSON</el-button>
            <el-button type="text" @click="applyTemplate('edit','id')">模板：主键增量</el-button>
            <el-button type="text" @click="applyTemplate('edit','updated')">模板：时间戳增量</el-button>
          </div>
        </el-form-item>
        <el-form-item>
          <el-switch v-model="editSource.active" active-text="启用" inactive-text="禁用"></el-switch>
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editSourceVisible = false">取消</el-button>
          <el-button type="primary" @click="submitEditSource">保存</el-button>
        </span>
      </template>
    </el-dialog>

    <!-- 采集记录对话框（小尺寸，无内部滚动） -->
    <el-dialog v-model="runsVisible" :title="runsTitle" width="600px" class="fixed-runs-dialog">
      <el-table :data="runs" style="width:100%" border stripe empty-text="暂无记录" size="small">
        <el-table-column prop="runAt" label="时间" width="160" />
        <el-table-column prop="status" label="状态" width="90">
          <template #default="scope">
            <el-tag :type="scope.row.status === 'success' ? 'success' : 'danger'">{{ scope.row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="deltaRows" label="变化行数" width="100" />
        <el-table-column prop="error" label="错误信息" />
      </el-table>
    </el-dialog>
  </div>
</template>

<script>
import { ref, reactive, onBeforeUnmount } from 'vue'
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
  const runsVisible = ref(false)
  const runsTitle = ref('采集记录')
  const runs = ref([])
    
    // 加载真实数据（来自后端数据库）
    const loadData = async () => {
      try {
        const [uploadsRes, sourcesRes, tasksRes] = await Promise.all([
          axios.get('/api/analysis/uploads'),
          axios.get('/api/analysis/data-sources'),
          axios.get('/api/analysis/collection-tasks')
        ])

        uploadHistory.value = (uploadsRes.data && uploadsRes.data.data) || []
        dataSources.value = (sourcesRes.data && sourcesRes.data.data) || []
        // 安全兜底：若全为临时项(id<=0)且数量>4，仅保留前4个
        if (Array.isArray(dataSources.value) && dataSources.value.length > 4) {
          const allTemp = dataSources.value.every(s => !s || !s.id || s.id <= 0)
          if (allTemp) dataSources.value = dataSources.value.slice(0, 4)
        }
        collectionTasks.value = (tasksRes.data && tasksRes.data.data) || []
      } catch (err) {
        console.error('加载数据失败: ', err)
      }
    }

    // 后端已自动同步数据源，无需手动同步
    
  // 组件挂载时加载数据 + 定时刷新
  loadData()
  const _refreshTimer = setInterval(loadData, 30000)
  onBeforeUnmount(() => clearInterval(_refreshTimer))
    
    // 新增数据源对话框
    const addSourceVisible = ref(false)
    const editSourceVisible = ref(false)
    const newSource = reactive({
      name: '',
      type: '',
      config: '',
      active: true
    })
    const editSource = reactive({ id: null, name: '', type: '', config: '', active: true })
    
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
    const editDataSource = async (source) => {
      if (!source || !source.id || source.id <= 0) {
        alert('此数据源为临时/内置项，无法直接编辑，请先添加为正式数据源')
        return
      }
      try {
        // 获取完整数据（包含 config）
        const res = await axios.get(`/api/analysis/data-sources/${source.id}`)
        const data = (res && res.data && res.data.data) || source
        Object.assign(editSource, {
          id: data.id,
          name: data.name,
          type: data.type,
          config: data.config || '',
          active: Boolean(data.active)
        })
        editSourceVisible.value = true
      } catch (err) {
        console.error('加载数据源失败: ', err)
        alert('加载数据源失败')
      }
    }
    
    // 提交新数据源
    const validateJson = (val) => { try { if (!val || typeof val !== 'string') return false; JSON.parse(val); return true } catch { return false } }

    const submitNewSource = async () => {
      try {
        if (!validateJson(newSource.config)) { alert('配置信息必须是有效的JSON'); return }
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
    
    const submitEditSource = async () => {
      if (!editSource.id) return
      try {
        if (!validateJson(editSource.config)) { alert('配置信息必须是有效的JSON'); return }
        await axios.put(`/api/analysis/data-sources/${editSource.id}`, {
          name: editSource.name,
          type: editSource.type,
          config: editSource.config,
          active: editSource.active
        })
        await loadData()
        editSourceVisible.value = false
      } catch (err) {
        console.error('更新数据源失败: ', err)
        alert('更新失败，请检查后端服务。')
      }
    }

    const deleteDataSource = async (source) => {
      if (!source || !source.id || source.id <= 0) return
      try {
        await axios.delete(`/api/analysis/data-sources/${source.id}`)
        await loadData()
      } catch (err) {
        console.error('删除数据源失败: ', err)
        alert('删除失败，请检查后端服务。')
      }
    }

    const toggleSourceActive = async (source) => {
      try {
        if (!source || !source.id || source.id <= 0) { alert('临时数据源不可切换，请先创建'); return }
        await axios.put(`/api/analysis/data-sources/${source.id}`, {
          name: source.name,
          type: source.type,
          config: source.config || '',
          active: !!source.active
        })
        await loadData()
      } catch (err) {
        console.error('切换启用失败: ', err)
        alert('切换失败，请检查后端服务。')
      }
    }

    const formatJson = (mode) => {
      try {
        if (mode === 'new') {
          const obj = JSON.parse(newSource.config || '{}')
          newSource.config = JSON.stringify(obj, null, 2)
        } else {
          const obj = JSON.parse(editSource.config || '{}')
          editSource.config = JSON.stringify(obj, null, 2)
        }
      } catch (_) { alert('JSON 无法格式化，请检查语法') }
    }

    const applyTemplate = (mode, type) => {
      const tplId = '{\n  "table": "exam_scores",\n  "key_column": "id",\n  "interval_seconds": 30\n}'
      const tplUpdated = '{\n  "table": "historical_grades",\n  "updated_at_column": "updated_at",\n  "interval_seconds": 30\n}'
      const tpl = type === 'updated' ? tplUpdated : tplId
      if (mode === 'new') newSource.config = tpl; else editSource.config = tpl
    }
    
    // 采集数据
    const collectData = async (sourceId) => {
      const source = dataSources.value.find(s => s.id === sourceId)
      if (!source) return

      // 先在后端创建任务，获取真实任务ID
      let taskId = null
      try {
        const res = await axios.post('/api/analysis/collection-tasks', {
          source_id: source.id,
          source_name: source.name,
          name: `${source.name}数据采集`
        })
        taskId = (res && res.data && res.data.id) || null
      } catch (err) {
        console.error('创建任务失败: ', err)
      }

      // 调用后端立即采集一次（刷新缓存）
      if (source.id > 0) {
        try {
          await axios.post(`/api/analysis/data-sources/${source.id}/collect`)
        } catch (err) {
          console.error('立即采集失败: ', err)
        }
      }

      // 本地创建一个运行中任务用于展示进度（视觉反馈）
      const localId = taskId || Date.now()
      collectionTasks.value.unshift({
        id: localId,
        name: `${source.name}数据采集`,
        source: source.name,
        status: 'running',
        progress: 0,
        createdAt: new Date().toLocaleString()
      })
      simulateCollectionProgress(localId, !!taskId)
    }

    // 查看采集记录
    const viewRuns = async (source) => {
      try {
        runsTitle.value = `${source?.name || '采集'} - 最近记录`
        const res = await axios.get('/api/analysis/collection-runs', { params: { source_id: source?.id, limit: 20 } })
        runs.value = (res && res.data && res.data.data) || []
        runsVisible.value = true
      } catch (err) {
        console.error('获取采集记录失败: ', err)
        alert('无法获取采集记录')
      }
    }

    // 已移除策略展示
    
    // 模拟采集进度
    // 存放本地任务的 interval，便于清空和取消
    const taskIntervals = {}

    const simulateCollectionProgress = (taskId, hasServer = false) => {
      const task = collectionTasks.value.find(t => t.id === taskId)
      if (!task) return
      
      let progress = 0
      const interval = setInterval(() => {
        progress += Math.random() * 20
        if (progress >= 100) {
          progress = 100
          task.status = 'completed'
          clearInterval(interval)
          delete taskIntervals[taskId]
          
          // 更新数据源最后采集时间
          const source = dataSources.value.find(s => s.name === task.source)
          if (source) {
            source.lastCollection = new Date().toLocaleString()
          }

          // 将完成状态同步到后端任务（若有真实任务ID）
          if (hasServer) {
            axios.put(`/api/analysis/collection-tasks/${taskId}`, { status: 'completed', progress: 100 }).catch(()=>{})
          }
          
          console.log('数据采集完成:', task.name)
        }
        task.progress = Math.floor(progress)
      }, 500)
      taskIntervals[taskId] = interval
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
      if (taskIntervals[taskId]) {
        try { clearInterval(taskIntervals[taskId]) } catch (_) {}
        delete taskIntervals[taskId]
      }
    }

    const clearTasks = async () => {
      // 停止所有本地 interval
      Object.keys(taskIntervals).forEach(k => {
        try { clearInterval(taskIntervals[k]) } catch (_) {}
        delete taskIntervals[k]
      })
      try {
        await axios.delete('/api/analysis/collection-tasks')
      } catch (err) {
        console.error('清空任务失败: ', err)
      }
      collectionTasks.value = []
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
  editSourceVisible,
      newSource,
  editSource,
      sourceRules,
      handleFileChange,
      beforeUpload,
      submitUpload,
      viewFileDetails,
      showAddSourceDialog,
      editDataSource,
      submitNewSource,
  deleteDataSource,
  toggleSourceActive,
  formatJson,
  applyTemplate,
  submitEditSource,
      collectData,
      cancelTask,
      clearTasks,
      formatDate,
      getStatusType,
      getStatusProgress,
      runsVisible,
      runsTitle,
      runs,
      viewRuns,
      
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
  display: none; /* 已改为表格展示 */
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
.card-header .actions { display: flex; align-items: center; gap: 6px; }

.source-info p {
  margin-bottom: 10px;
}

.json-tools { margin-top: 6px; }

.add-source-card {
  display: none; /* 已改为表格工具栏添加按钮 */
}

.add-source-card:hover { display: none; }

.add-source-content {
  display: none;
}

.add-icon {
  display: none;
}

/* 采集任务样式 */
.collection-tasks {
  margin-top: 30px;
}

.tasks-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.sources-toolbar {
  display: flex;
  gap: 10px;
  margin: 8px 0 14px;
}

/* 移除诊断行样式 */

.config-ellipsis {
  display: inline-block;
  max-width: 100%;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
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

/* 固定“采集记录”对话框尺寸（通过 deep 选择器作用到 Teleport 到 body 的 DOM） */
:deep(.fixed-runs-dialog) {
  width: 600px !important;
  max-width: 600px;
}
:deep(.fixed-runs-dialog .el-dialog__body) {
  height: auto;
  max-height: none;
  overflow: visible;
  padding-top: 10px;
}
:deep(.fixed-runs-dialog .el-dialog__header) {
  border-bottom: 1px solid #ebeef5;
}
:deep(.fixed-runs-dialog .el-dialog__footer) {
  border-top: 1px solid #ebeef5;
}
</style>