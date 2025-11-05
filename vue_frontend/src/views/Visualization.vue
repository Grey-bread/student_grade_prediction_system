<template>
  <div class="visualization">
    <!-- 标签页切换 -->
    <el-tabs v-model="activeTab" type="card" class="visualization-tabs" @tab-change="handleTabChange">
      <!-- 图表可视化标签页 -->
      <el-tab-pane label="📊 图表可视化" name="charts">
        <!-- 控制面板 -->
        <el-card class="control-panel" shadow="hover">
          <el-form :inline="true" size="small">
            <el-form-item label="数据表">
              <el-select v-model="chartDataTable" placeholder="选择数据源" @change="loadChartData" style="width: 220px">
                <el-option
                  v-for="t in chartTables"
                  :key="t"
                  :label="getTableLabel(t)"
                  :value="t"
                >
                  <span style="float:left">{{ getTableLabel(t) }}</span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item label="学生ID" v-if="trendType === 'individual'">
              <el-input-number v-model="selectedStudentId" :min="1" :max="500" @change="loadChartData"></el-input-number>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadChartData" icon="Refresh">刷新图表</el-button>
              <el-button type="success" :loading="loading.exportReport" @click="exportAnalysisReport" icon="Download">导出报告</el-button>
            </el-form-item>
          </el-form>
        </el-card>

        <el-row :gutter="20">
          <!-- 成绩趋势图 -->
          <el-col :span="24">
            <el-card class="chart-card" v-loading="loading.trend">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">📈 成绩趋势分析</span>
                  <el-radio-group v-model="trendType" size="small" @change="handleTrendTypeChange">
                    <el-radio-button label="individual">个人成绩</el-radio-button>
                    <el-radio-button label="class">班级平均</el-radio-button>
                    <el-radio-button label="subject">学科对比</el-radio-button>
                  </el-radio-group>
                </div>
              </template>
              <div class="chart-container" ref="trendChart"></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 成绩分布图 -->
          <el-col :span="12">
            <el-card class="chart-card" v-loading="loading.distribution">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">📊 成绩分布分析</span>
                </div>
              </template>
              <div class="chart-container small" ref="distributionChart"></div>
            </el-card>
          </el-col>

          <!-- 学生进步情况 -->
          <el-col :span="12">
            <el-card class="chart-card" v-loading="loading.progress">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">🚀 学生进步情况</span>
                </div>
              </template>
              <div class="chart-container small" ref="progressChart"></div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 雷达图 - 学生综合能力 -->
          <el-col :span="12">
            <el-card class="chart-card" v-loading="loading.radar">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">🎯 课堂表现雷达图</span>
                </div>
              </template>
              <div class="chart-container small" ref="radarChart"></div>
            </el-card>
          </el-col>

          <!-- 饼图 - 成绩等级分布 -->
          <el-col :span="12">
            <el-card class="chart-card" v-loading="loading.pie">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">🥧 成绩等级分布</span>
                </div>
              </template>
              <div class="chart-container small" ref="pieChart"></div>
            </el-card>
          </el-col>
        </el-row>
      </el-tab-pane>

      <!-- 数据表可视化标签页 -->
      <el-tab-pane label="📋 数据表可视化" name="tables">
        <el-card class="filter-card" shadow="hover">
          <div class="filter-container">
            <el-select v-model="tableConfig.selectedTable" placeholder="选择数据表" style="width: 220px; margin-right: 20px;" @change="handleTableChange">
              <el-option
                v-for="table in tableConfig.tables"
                :key="table"
                :label="getTableLabel(table)"
                :value="table">
                <span style="float: left">{{ getTableLabel(table) }}</span>
              </el-option>
            </el-select>
            
            <div class="search-section">
              <el-input
                v-model="tableConfig.searchQuery"
                placeholder="按学号或姓名搜索..."
                prefix-icon="Search"
                clearable
                style="width: 240px; margin-right: 20px;">
              </el-input>
            </div>
            
            <div class="action-section">
              <el-button type="primary" @click="refreshTableData" icon="Refresh" plain>
                刷新数据
              </el-button>
              <el-button type="success" @click="showCreateDialog" icon="Plus">
                新增记录
              </el-button>
              <el-button type="info" @click="exportTableData" icon="Download" plain>
                导出数据
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card class="table-card" v-loading="tableConfig.loading">
          <template #header>
            <div class="card-header">
              <div>
                <span class="table-title">{{ getTableLabel(tableConfig.selectedTable) }}</span>
              </div>
            </div>
          </template>
          
          <div v-if="tableConfig.error" class="error-container">
            <el-alert
              title="数据加载失败"
              :description="tableConfig.error"
              type="error"
              show-icon
              closable>
            </el-alert>
          </div>
          
          <div v-else-if="!tableConfig.tableData.length && !tableConfig.loading" class="empty-container">
            <el-empty description="暂无数据" />
          </div>
          
          <div v-else class="table-wrapper">
            <el-table
              :data="safeTableData"
              style="width: 100%"
              :default-sort="{prop: 'id', order: 'ascending'}"
              border
              stripe
              highlight-current-row
              height="500"
              size="small"
              :cell-style="{padding: '8px'}"
              :header-cell-style="{padding: '8px', backgroundColor: '#f5f7fa'}">
              
              <template v-for="column in tableColumns" :key="column.prop">
                <el-table-column
                  :prop="column.prop"
                  :label="column.label"
                  :width="getColumnWidth(column.prop)"
                  :sortable="isSortable(column.prop)"
                  :align="getColumnAlign(column.prop)"
                  :fixed="isFixedColumn(column.prop)">
                  <template #default="{row}">
                    <template v-if="isDateColumn(column.prop)">
                      <el-tag size="small" type="info">{{ formatDate(row[column.prop]) }}</el-tag>
                    </template>
                    <template v-else-if="isScoreColumn(column.prop)">
                      <el-tag :type="getScoreTagType(row[column.prop])" size="small">
                        {{ row[column.prop] }}
                      </el-tag>
                    </template>
                    <template v-else-if="isIdColumn(column.prop)">
                      <span style="color: #409EFF; font-weight: 500">{{ row[column.prop] }}</span>
                    </template>
                    <template v-else>
                      {{ row[column.prop] || '-' }}
                    </template>
                  </template>
                </el-table-column>
              </template>
              
              <!-- 操作列 -->
              <el-table-column label="操作" width="160" align="center" fixed="right">
                <template #default="{row}">
                  <div style="display: flex; gap: 8px; justify-content: center;">
                    <el-button type="primary" size="small" @click="showEditDialog(row)" icon="Edit">编辑</el-button>
                    <el-button type="danger" size="small" @click="deleteRecord(row)" icon="Delete">删除</el-button>
                  </div>
                </template>
              </el-table-column>
            </el-table>
            
            <div class="pagination-container">
              <el-pagination
                background
                layout="total, prev, pager, next, jumper, sizes"
                :total="tableTotalFiltered"
                v-model:current-page="tableConfig.currentPage"
                v-model:page-size="tableConfig.pageSize"
                :page-sizes="[10, 20, 50, 100]"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange">
              </el-pagination>
            </div>
          </div>
        </el-card>

      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑对话框 -->
    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="600px" @close="resetForm">
      <el-form :model="formData" label-width="120px" label-position="left">
        <template v-for="column in tableColumns" :key="column.prop">
          <!-- 跳过主键字段 -->
          <el-form-item v-if="!isPrimaryKey(column.prop)" :label="column.label">
            <template v-if="isDateColumn(column.prop)">
              <el-date-picker
                v-model="formData[column.prop]"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </template>
            <template v-else-if="isScoreColumn(column.prop)">
              <el-input-number
                v-model="formData[column.prop]"
                :min="0"
                :max="100"
                :precision="1"
                style="width: 100%"
              />
            </template>
            <template v-else-if="isSelectColumn(column.prop)">
              <el-select v-model="formData[column.prop]" placeholder="请选择" style="width: 100%">
                <el-option
                  v-for="option in getColumnOptions(column.prop)"
                  :key="option"
                  :label="option"
                  :value="option"
                />
              </el-select>
            </template>
            <template v-else>
              <el-input
                v-model="formData[column.prop]"
                :placeholder="`请输入${column.label}`"
              />
            </template>
          </el-form-item>
        </template>
      </el-form>
      
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="saveRecord" :loading="loading.save">
          {{ dialogMode === 'create' ? '创建' : '更新' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import * as echarts from 'echarts'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus'

export default {
  name: 'Visualization',
  data() {
    return {
      activeTab: 'charts',
      trendType: 'individual',  // 默认为个人成绩
      chartDataTable: 'exam_scores',  // 默认为考试成绩表
      chartTables: [], // 图表可选表
      selectedStudentId: 1,  // 默认显示学生1的成绩
      
      // CRUD对话框
      dialogVisible: false,
      dialogTitle: '',
      dialogMode: 'create', // 'create' 或 'edit'
      currentRecord: {},
      formData: {},
      
      // Loading states
      loading: {
        trend: false,
        distribution: false,
        progress: false,
        radar: false,
        pie: false,
        save: false,
        exportReport: false,
        exportTable: false
      },
      
      // Chart instances
      charts: {
        trend: null,
        distribution: null,
        progress: null,
        radar: null,
        pie: null
      },
      
      // 数据表配置
      tableConfig: {
        tables: ['students', 'exam_scores', 'class_performance', 'historical_grades'],
        selectedTable: 'students',  // 默认为学生信息表
        searchQuery: '',
        tableData: [],
        total: 0,
        loading: false,
        error: null,
        currentPage: 1,
        pageSize: 20,
        tableLabels: {
          students: '学生信息表',
          exam_scores: '考试成绩表',
          class_performance: '课堂表现表',
          historical_grades: '历史成绩表'
        },
        // 表结构配置
        tableConfigs: {
          students: {
            columns: [
              { prop: 'student_id', label: '学生ID', type: 'id' },
              { prop: 'student_no', label: '学号', type: 'text' },
              { prop: 'name', label: '姓名', type: 'text' },
              { prop: 'gender', label: '性别', type: 'category' },
              { prop: 'grade', label: '年级', type: 'category' },
              { prop: 'class', label: '班级', type: 'category' },
              { prop: 'birth_date', label: '出生日期', type: 'date' },
              { prop: 'contact_phone', label: '联系电话', type: 'text' },
              { prop: 'email', label: '邮箱', type: 'text' },
              { prop: 'status', label: '状态', type: 'category' }
            ]
          },
          exam_scores: {
            columns: [
              { prop: 'score_id', label: '成绩ID', type: 'id' },
              { prop: 'student_id', label: '学生ID', type: 'id' },
              { prop: 'course_id', label: '课程ID', type: 'id' },
              { prop: 'exam_type_id', label: '考试类型ID', type: 'id' },
              { prop: 'exam_name', label: '考试名称', type: 'text' },
              { prop: 'exam_date', label: '考试日期', type: 'date' },
              { prop: 'score', label: '分数', type: 'score' },
              { prop: 'score_level', label: '成绩等级', type: 'category' },
              { prop: 'ranking', label: '排名', type: 'number' },
              { prop: 'teacher_id', label: '教师ID', type: 'id' },
              { prop: 'comments', label: '评语', type: 'text' }
            ]
          },
          class_performance: {
            columns: [
              { prop: 'performance_id', label: '表现ID', type: 'id' },
              { prop: 'student_id', label: '学生ID', type: 'id' },
              { prop: 'course_id', label: '课程ID', type: 'id' },
              { prop: 'semester', label: '学期', type: 'category' },
              { prop: 'attendance_score', label: '出勤分数', type: 'score' },
              { prop: 'participation_score', label: '参与分数', type: 'score' },
              { prop: 'homework_score', label: '作业分数', type: 'score' },
              { prop: 'behavior_score', label: '行为分数', type: 'score' },
              { prop: 'total_performance_score', label: '总表现分数', type: 'score' },
              { prop: 'teacher_comments', label: '教师评语', type: 'text' }
            ]
          },
          historical_grades: {
            columns: [
              { prop: 'grade_id', label: '成绩ID', type: 'id' },
              { prop: 'student_id', label: '学生ID', type: 'id' },
              { prop: 'course_id', label: '课程ID', type: 'id' },
              { prop: 'semester', label: '学期', type: 'category' },
              { prop: 'academic_year', label: '学年', type: 'category' },
              { prop: 'midterm_score', label: '期中成绩', type: 'score' },
              { prop: 'final_score', label: '期末成绩', type: 'score' },
              { prop: 'usual_score', label: '平时成绩', type: 'score' },
              { prop: 'total_score', label: '总成绩', type: 'score' },
              { prop: 'grade_level', label: '成绩等级', type: 'category' },
              { prop: 'ranking', label: '排名', type: 'number' },
              { prop: 'teacher_id', label: '教师ID', type: 'id' }
            ]
          }
        }
      }
    }
  },
  
  computed: {
    tableColumns() {
      return this.tableConfig.tableConfigs[this.tableConfig.selectedTable]?.columns || []
    },
    
    tableFilteredData() {
      // 确保 tableData 是数组
      const tableData = Array.isArray(this.tableConfig.tableData) 
        ? this.tableConfig.tableData 
        : []
      
      let result = [...tableData]
      
      // 普通搜索过滤 - 只搜索学号和姓名
      if (this.tableConfig.searchQuery) {
        const query = this.tableConfig.searchQuery.toLowerCase()
        result = result.filter(row => {
          // 只在学号(student_no)和姓名(name)字段中搜索
          const searchFields = [row.student_no, row.name].filter(field => field !== null && field !== undefined)
          return searchFields.some(value => 
            String(value).toLowerCase().includes(query)
          )
        })
      }
      
      // 分页
      const start = (this.tableConfig.currentPage - 1) * this.tableConfig.pageSize
      const end = start + this.tableConfig.pageSize
      return result.slice(start, end)
    },
    
    // 保障 Table 始终获得可迭代数组，避免 Element Plus 内部对数据迭代时报错
    safeTableData() {
      const data = this.tableFilteredData
      return Array.isArray(data) ? data : []
    },
    
    tableTotalFiltered() {
      const tableData = Array.isArray(this.tableConfig.tableData) 
        ? this.tableConfig.tableData 
        : []
      
      let result = [...tableData]
      
      // 应用搜索过滤 - 只搜索学号和姓名
      if (this.tableConfig.searchQuery) {
        const query = this.tableConfig.searchQuery.toLowerCase()
        result = result.filter(row => {
          // 只在学号(student_no)和姓名(name)字段中搜索
          const searchFields = [row.student_no, row.name].filter(field => field !== null && field !== undefined)
          return searchFields.some(value => 
            String(value).toLowerCase().includes(query)
          )
        })
      }
      
      return result.length
    }
  },
  
  mounted() {
    this.$nextTick(() => {
      this.initCharts()
      // 先加载数据表,获取有效的学生ID,然后再加载图表数据
      setTimeout(async () => {
        await this.fetchChartTables()
        await this.fetchTableData()
        // 然后加载图表数据
        this.loadChartData()
      }, 100)
    })
    window.addEventListener('resize', this.handleResize)
  },
  
  beforeUnmount() {
    Object.values(this.charts).forEach(chart => {
      chart?.dispose()
    })
    window.removeEventListener('resize', this.handleResize)
  },

  methods: {
    initCharts() {
      this.$nextTick(() => {
        if (this.$refs.trendChart) {
          this.charts.trend = echarts.init(this.$refs.trendChart)
          console.log('趋势图初始化完成')
        }
        if (this.$refs.distributionChart) {
          this.charts.distribution = echarts.init(this.$refs.distributionChart)
          console.log('分布图初始化完成')
        }
        if (this.$refs.progressChart) {
          this.charts.progress = echarts.init(this.$refs.progressChart)
          console.log('进步图初始化完成')
        }
        if (this.$refs.radarChart) {
          this.charts.radar = echarts.init(this.$refs.radarChart)
          console.log('雷达图初始化完成')
        }
        if (this.$refs.pieChart) {
          this.charts.pie = echarts.init(this.$refs.pieChart)
          console.log('饼图初始化完成')
        }
      })
    },

    handleResize() {
      Object.values(this.charts).forEach(chart => {
        chart?.resize()
      })
    },

    handleTabChange(tabName) {
      if (tabName === 'charts') {
        // 重新初始化图表以避免隐藏/显示导致的实例失效或残留配置
        this.$nextTick(() => {
          try {
            // 安全地销毁旧实例
            Object.keys(this.charts).forEach(key => {
              if (this.charts[key]) {
                this.charts[key].dispose()
                this.charts[key] = null
              }
            })
            // 重新创建实例（仅当对应容器存在）
            if (this.$refs.trendChart) this.charts.trend = echarts.init(this.$refs.trendChart)
            if (this.$refs.distributionChart) this.charts.distribution = echarts.init(this.$refs.distributionChart)
            if (this.$refs.progressChart) this.charts.progress = echarts.init(this.$refs.progressChart)
            if (this.$refs.radarChart) this.charts.radar = echarts.init(this.$refs.radarChart)
            if (this.$refs.pieChart) this.charts.pie = echarts.init(this.$refs.pieChart)
          } catch (e) {
            console.warn('图表重新初始化失败:', e)
          }
          // 重新加载数据并渲染
          this.loadChartData()
          this.handleResize()
        })
      } else if (tabName === 'tables') {
        // 离开图表页时主动销毁实例，防止后台渲染任务残留
        try {
          Object.keys(this.charts).forEach(key => {
            if (this.charts[key]) {
              this.charts[key].dispose()
              this.charts[key] = null
            }
          })
        } catch (e) {
          console.warn('离开图表页 dispose 异常:', e)
        }
        if (!this.tableConfig.tableData.length) {
          this.fetchTableData()
        }
      }
    },

    handleTrendTypeChange() {
      this.loadChartData()
    },

    async loadChartData() {
      await Promise.all([
        this.updateTrendChart(),
        this.updateDistributionChart(),
        this.updateProgressChart(),
        this.updateRadarChart(),
        this.updatePieChart()
      ])
    },

    async updateTrendChart() {
      if (!this.charts.trend) return
      
      this.loading.trend = true
      try {
        let response
        let apiUrl = ''
        let params = { table: this.chartDataTable }
        
        if (this.trendType === 'individual') {
          // 如果是个人趋势但没有选择学生ID,跳过加载
          if (!this.selectedStudentId) {
            console.warn('个人趋势需要选择学生ID')
            this.loading.trend = false
            return
          }
          apiUrl = '/api/analysis/student-trends'
          params.student_id = this.selectedStudentId
        } else if (this.trendType === 'class') {
          apiUrl = '/api/analysis/class-trends'
        } else if (this.trendType === 'subject') {
          apiUrl = '/api/analysis/subject-comparison'
        }
        
        response = await axios.get(apiUrl, { params })
        
        if (response.data.status === 'success') {
          const option = {
            title: {
              text: this.getTrendTitle(),
              left: 'center'
            },
            tooltip: {
              trigger: 'axis'
            },
            legend: {
              data: response.data.legend || [],
              top: 30
            },
            grid: {
              left: '3%',
              right: '4%',
              bottom: '3%',
              containLabel: true
            },
            xAxis: {
              type: 'category',
              data: response.data.labels || response.data.exams || [],
              boundaryGap: false
            },
            yAxis: {
              type: 'value',
              name: '分数'
            },
            series: (response.data.series || [])
              .filter(s => s && typeof s === 'object')
              .map(s => ({
                name: s?.name || '未知系列',
                type: typeof s?.type === 'string' ? s.type : 'line',
                data: Array.isArray(s?.data) ? s.data.map(v => (typeof v === 'number' ? v : (isNaN(Number(v)) ? 0 : Number(v)))) : [],
                smooth: true
              }))
          }
          // 最终兜底：若 series 为空或存在非对象项，使用占位系列避免 ECharts 内部读取 undefined.type
          if (!Array.isArray(option.series) || option.series.length === 0) {
            option.series = [{ name: '暂无数据', type: 'line', data: [] }]
          } else {
            option.series = option.series.filter(s => s && typeof s === 'object' && typeof s.type === 'string')
            if (option.series.length === 0) {
              option.series = [{ name: '暂无数据', type: 'line', data: [] }]
            }
          }
          console.debug('趋势图 option.series 最终送入:', option.series)
          
          // 避免保留历史无效系列导致渲染异常
          this.charts.trend.clear()
          try {
            this.charts.trend.setOption(option, true)
          } catch (e) {
            console.error('趋势图 setOption 异常，已回退为空系列:', e)
            this.charts.trend.setOption({
              xAxis: { type: 'category', data: [] },
              yAxis: { type: 'value' },
              series: [{ name: '暂无数据', type: 'line', data: [] }]
            }, true)
          }
        }
      } catch (error) {
        console.error('加载趋势数据失败:', error)
        ElMessage.error('加载趋势数据失败')
      } finally {
        this.loading.trend = false
      }
    },

    getTrendTitle() {
      if (this.trendType === 'individual') {
        return `学生${this.selectedStudentId}成绩趋势`
      } else if (this.trendType === 'class') {
        return '班级平均成绩趋势'
      } else {
        return '学科成绩对比'
      }
    },

    async updateDistributionChart() {
      if (!this.charts.distribution) return
      
      this.loading.distribution = true
      try {
        const params = { table: this.chartDataTable }
        
        // 如果选择了学生ID，添加到参数中
        if (this.trendType === 'individual' && this.selectedStudentId) {
          params.student_id = this.selectedStudentId
        }
        
        const response = await axios.get('/api/analysis/score-distribution', { params })
        
        if (response.data.status === 'success') {
          console.log('分布图数据:', response.data)
          
          const option = {
            title: {
              text: '历史成绩分布分析',
              left: 'center',
              subtext: this.trendType === 'individual' && this.selectedStudentId 
                ? `学生${this.selectedStudentId}的成绩分布` 
                : '全部学生平均成绩分布'
            },
            tooltip: {
              trigger: 'axis',
              axisPointer: {
                type: 'shadow'
              },
              formatter: '{b}: {c}分'
            },
            xAxis: {
              type: 'category',
              data: response.data.features || [],
              axisLabel: {
                interval: 0,
                fontSize: 12
              }
            },
            yAxis: {
              type: 'value',
              name: '平均分',
              min: 0,
              max: 100
            },
            grid: {
              bottom: '15%',
              left: '12%',
              right: '5%',
              top: '20%'
            },
            series: [{
              type: 'bar',
              data: response.data.data || [],
              barWidth: '50%',
              itemStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: '#83bff6' },
                  { offset: 0.5, color: '#188df0' },
                  { offset: 1, color: '#188df0' }
                ])
              },
              label: {
                show: true,
                position: 'top',
                formatter: '{c}分'
              }
            }]
          }
          
          this.charts.distribution.setOption(option)
        }
      } catch (error) {
        console.error('加载分布数据失败:', error)
        ElMessage.error('加载分布数据失败')
      } finally {
        this.loading.distribution = false
      }
    },

    async updateProgressChart() {
      if (!this.charts.progress) return
      
      this.loading.progress = true
      try {
        const params = { table: this.chartDataTable }
        
        // 如果选择了学生ID，添加到参数中
        if (this.trendType === 'individual' && this.selectedStudentId) {
          params.student_id = this.selectedStudentId
        }
        
        const response = await axios.get('/api/analysis/student-progress', { params })
        
        if (response.data.status === 'success') {
          const option = {
            title: {
              text: this.trendType === 'individual' 
                ? `学生${this.selectedStudentId}进步情况` 
                : '整体进步情况',
              left: 'center'
            },
            tooltip: {
              trigger: 'axis'
            },
            xAxis: {
              type: 'category',
              data: response.data.labels || []
            },
            yAxis: {
              type: 'value',
              name: '进步幅度 (%)'
            },
            series: [{
              type: 'line',
              data: response.data.progress || [],
              smooth: true,
              areaStyle: {
                color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
                  { offset: 0, color: 'rgba(103, 194, 58, 0.3)' },
                  { offset: 1, color: 'rgba(103, 194, 58, 0.1)' }
                ])
              },
              lineStyle: {
                width: 3,
                color: '#67C23A'
              },
              itemStyle: {
                color: '#67C23A'
              }
            }]
          }
          
          this.charts.progress.setOption(option)
        }
      } catch (error) {
        console.error('加载进步数据失败:', error)
        ElMessage.error('加载进步数据失败')
      } finally {
        this.loading.progress = false
      }
    },

    async updateRadarChart() {
      if (!this.charts.radar) return
      
      this.loading.radar = true
      try {
        const params = { 
          table: 'class_performance'  // 雷达图固定使用课堂表现表数据
        }
        
        // 如果选择了学生ID，添加到参数中
        if (this.trendType === 'individual' && this.selectedStudentId) {
          params.student_id = this.selectedStudentId
        }
        
        const response = await axios.get('/api/analysis/radar-data', { params })
        
        if (response.data.status === 'success') {
          // 如果有提示信息，显示给用户
          if (response.data.message) {
            console.warn(response.data.message)
          }
          
          const option = {
            title: {
              text: '课堂表现多维度分析',
              left: 'center',
              subtext: response.data.message || ''
            },
            tooltip: {},
            legend: {
              data: (response.data.series || []).map(s => s?.name || '未知'),
              top: 30
            },
            radar: {
              indicator: response.data.indicator || [],
              center: ['50%', '55%'],
              radius: '60%'
            },
            series: [{
              type: 'radar',
              data: (response.data.series || []).map(s => ({
                value: s?.value || [],
                name: s?.name || '未知',
                areaStyle: {
                  color: (s?.name || '').includes('班级') ? 'rgba(64, 158, 255, 0.3)' : 'rgba(255, 99, 132, 0.3)'
                }
              }))
            }]
          }
          
          this.charts.radar.setOption(option)
        }
      } catch (error) {
        console.error('加载雷达图数据失败:', error)
        // 不显示错误提示，而是显示空状态
        if (this.charts.radar) {
          const emptyOption = {
            title: {
              text: '课堂表现多维度分析',
              left: 'center',
              subtext: '数据加载失败'
            },
            radar: {
              indicator: [
                { name: '维度1', max: 100 },
                { name: '维度2', max: 100 },
                { name: '维度3', max: 100 }
              ],
              center: ['50%', '55%'],
              radius: '60%'
            },
            series: [{
              type: 'radar',
              data: [{
                value: [0, 0, 0],
                name: '暂无数据',
                areaStyle: {
                  color: 'rgba(200, 200, 200, 0.3)'
                }
              }]
            }]
          }
          this.charts.radar.setOption(emptyOption)
        }
      } finally {
        this.loading.radar = false
      }
    },

    async updatePieChart() {
      if (!this.charts.pie) return
      
      this.loading.pie = true
      try {
        const params = { 
          table: this.chartDataTable  // 使用所选数据表
        }
        
        // 饼图始终使用全部学生数据，不传student_id参数
        
        const response = await axios.get('/api/analysis/grade-distribution', { params })
        
        if (response.data.status === 'success') {
          // 打印数据用于调试
          console.log('饼图数据:', response.data)
          
          // 不过滤，显示所有等级（包括0人的）
          const pieData = response.data.data
          const total = response.data.total || pieData.reduce((sum, item) => sum + item.value, 0)
          const statMethod = response.data.stat_method === 'student_most_common_level' ? '按学生主要等级' : '按考试记录'
          
          const option = {
            title: {
              text: '考试成绩等级分布',
              left: 'center',
              subtext: `${statMethod} | 共${total}名学生`
            },
            tooltip: {
              trigger: 'item',
              formatter: function(params) {
                return `${params.seriesName}<br/>${params.name}: ${params.value}人 (${params.percent}%)`
              }
            },
            legend: {
              orient: 'vertical',
              left: 'left',
              top: 'middle',
              data: pieData.map(item => item.name)
            },
            series: [{
              name: '成绩等级',
              type: 'pie',
              radius: ['40%', '70%'],
              avoidLabelOverlap: false,
              itemStyle: {
                borderRadius: 10,
                borderColor: '#fff',
                borderWidth: 2
              },
              label: {
                show: true,
                formatter: function(params) {
                  // 只显示有数据的标签
                  if (params.value > 0) {
                    return `${params.name}: ${params.value}人\n${params.percent}%`
                  }
                  return ''
                }
              },
              emphasis: {
                label: {
                  show: true,
                  fontSize: '16',
                  fontWeight: 'bold'
                }
              },
              minAngle: 5, // 最小扇区角度，确保小值也能显示
              data: pieData
            }]
          }
          
          this.charts.pie.setOption(option)
        }
      } catch (error) {
        console.error('加载饼图数据失败:', error)
        ElMessage.error('加载饼图数据失败')
      } finally {
        this.loading.pie = false
      }
    },
    // 加载可用于图表的数据表列表
    async fetchChartTables() {
      try {
        const res = await axios.get('/api/analysis/tables')
        if (res.data?.status === 'success') {
          this.chartTables = res.data.tables || []
          // 初始化默认选择
          if (!this.chartTables.includes(this.chartDataTable)) {
            if (this.chartTables.includes('exam_scores')) this.chartDataTable = 'exam_scores'
            else if (this.chartTables.includes('historical_grades')) this.chartDataTable = 'historical_grades'
            else if (this.chartTables.length > 0) this.chartDataTable = this.chartTables[0]
          }
        }
      } catch (e) {
        console.warn('加载表清单失败:', e)
      }
    },

    // 表格相关方法
    handleTableChange() {
      this.tableConfig.currentPage = 1
      this.fetchTableData()
    },

    async fetchTableData() {
      this.tableConfig.loading = true
      this.tableConfig.error = null
      
      try {
        console.log(`正在加载${this.tableConfig.selectedTable}表数据...`)
        
        // 使用分页请求处理大数据量
        const response = await axios.get(`/api/analysis/table-data?table=${this.tableConfig.selectedTable}&page=1&page_size=1000`, {
          timeout: 15000, // 15秒超时
          headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json'
          }
        })
        
        console.log(`${this.tableConfig.selectedTable}表响应状态:`, response.status)
        
        if (response.data && response.data.status === 'success') {
          this.tableConfig.tableData = response.data.data || []
          this.tableConfig.total = response.data.total || this.tableConfig.tableData.length
          console.log(`${this.tableConfig.selectedTable}表加载成功，显示${this.tableConfig.tableData.length}条记录，总共${this.tableConfig.total}条`)
        } else {
          const errorMsg = response.data?.message || '加载数据失败'
          this.tableConfig.error = errorMsg
          console.error(`${this.tableConfig.selectedTable}表加载失败:`, errorMsg)
        }
      } catch (error) {
        console.error(`获取${this.tableConfig.selectedTable}表数据失败:`, error)
        
        let errorMessage = '加载数据失败'
        if (error.code === 'ECONNABORTED') {
          errorMessage = '请求超时，数据量较大，请稍后重试'
        } else if (error.response) {
          errorMessage = `服务器错误 (${error.response.status}): ${error.response.statusText}`
        } else if (error.request) {
          errorMessage = '网络连接失败，请检查后端服务是否运行'
        } else {
          errorMessage = error.message || '未知错误'
        }
        
        this.tableConfig.error = errorMessage
      } finally {
        this.tableConfig.loading = false
      }
    },

    

    refreshTableData() {
      this.tableConfig.currentPage = 1
      this.tableConfig.searchQuery = ''
      this.fetchTableData()
    },

    async exportTableData() {
      try {
        this.loading.exportTable = true
        const table = this.tableConfig.selectedTable
        const res = await axios.get(`/api/analysis/export-table`, {
          params: { table },
          responseType: 'blob'
        })
        const blob = new Blob([res.data], { type: 'text/csv;charset=utf-8;' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        const label = this.getTableLabel(table)
        link.href = url
        link.download = `${label || table}_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.csv`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        ElMessage.success('数据导出成功')
      } catch (err) {
        console.error('导出数据失败:', err)
        ElMessage.error('导出失败，请稍后重试')
      } finally {
        this.loading.exportTable = false
      }
    },

    async exportAnalysisReport() {
      try {
        this.loading.exportReport = true
        const params = {
          table: this.chartDataTable,
          trendType: this.trendType,
          student_id: this.trendType === 'individual' ? this.selectedStudentId : undefined
        }
        const res = await axios.get('/api/analysis/export-report', {
          params,
          responseType: 'blob'
        })
        const blob = new Blob([res.data], { type: 'application/zip' })
        const url = window.URL.createObjectURL(blob)
        const link = document.createElement('a')
        link.href = url
        link.download = `数据分析报告_${new Date().toISOString().slice(0,19).replace(/[:T]/g,'-')}.zip`
        document.body.appendChild(link)
        link.click()
        document.body.removeChild(link)
        window.URL.revokeObjectURL(url)
        ElMessage.success('报告导出成功')
      } catch (err) {
        console.error('导出报告失败:', err)
        ElMessage.error('导出失败，请稍后重试')
      } finally {
        this.loading.exportReport = false
      }
    },

    handleSizeChange() {
      this.tableConfig.currentPage = 1
    },

    handleCurrentChange() {
      window.scrollTo({ top: 0, behavior: 'smooth' })
    },

    getTableLabel(table) {
      const map = this.tableConfig.tableLabels || {}
      if (map[table]) return map[table]
      if (/[^\x00-\x7F]/.test(String(table))) return table
      return this.translateTableName(table)
    },
    translateTableName(name) {
      const dict = {
        'students': '学生', 'student': '学生',
        'exam': '考试', 'exams': '考试',
        'score': '成绩', 'scores': '成绩',
        'class': '课堂', 'classes': '课堂',
        'performance': '表现',
        'historical': '历史', 'history': '历史',
        'grade': '成绩', 'grades': '成绩',
        'course': '课程', 'courses': '课程',
        'teacher': '教师', 'teachers': '教师',
        'type': '类型', 'types': '类型',
        'record': '记录', 'records': '记录',
        'upload': '上传', 'data': '数据', 'source': '来源', 'mapping': '映射',
        'sync': '同步', 'state': '状态', 'status': '状态'
      }
      const parts = String(name).toLowerCase().split(/[^a-z0-9]+/).filter(Boolean)
      const cn = parts.map(p => dict[p]).filter(Boolean)
      if (cn.length) return cn.join('') + '表'
      return '自定义表'
    },

    getColumnWidth(prop) {
      if (prop.includes('id')) return 100
      if (prop.includes('name') || prop.includes('no')) return 120
      if (prop.includes('score') || prop.includes('grade')) return 90
      if (prop.includes('date')) return 130
      if (prop.includes('email')) return 180
      if (prop.includes('phone')) return 130
      return 150
    },

    getColumnAlign(prop) {
      if (prop.includes('id') || prop.includes('score') || prop.includes('ranking')) {
        return 'center'
      }
      return 'left'
    },

    isSortable(prop) {
      return prop.includes('id') || prop.includes('score') || prop.includes('ranking') || prop.includes('date')
    },

    isFixedColumn(prop) {
      return prop.includes('student_id') || prop === 'name'
    },

    isDateColumn(prop) {
      return prop.includes('date')
    },

    isScoreColumn(prop) {
      return prop.includes('score') || (prop.includes('grade') && !prop.includes('grade_id'))
    },

    isIdColumn(prop) {
      return prop.includes('_id')
    },

    formatDate(dateString) {
      if (!dateString) return '-'
      return dateString.toString().split('T')[0]
    },

    getScoreTagType(score) {
      if (typeof score !== 'number') return 'info'
      if (score >= 90) return 'success'
      if (score >= 80) return ''
      if (score >= 60) return 'warning'
      return 'danger'
    },

    

    // CRUD 相关方法
    showCreateDialog() {
      this.dialogMode = 'create'
      this.dialogTitle = `新增${this.getTableLabel(this.tableConfig.selectedTable)}记录`
      this.formData = {}
      this.dialogVisible = true
    },

    showEditDialog(row) {
      this.dialogMode = 'edit'
      this.dialogTitle = `编辑${this.getTableLabel(this.tableConfig.selectedTable)}记录`
      this.currentRecord = { ...row }
      this.formData = { ...row }
      this.dialogVisible = true
    },

    async deleteRecord(row) {
      try {
        await ElMessageBox.confirm('确定要删除这条记录吗？', '提示', {
          confirmButtonText: '确定',
          cancelButtonText: '取消',
          type: 'warning'
        })
        
        const primaryKey = this.getPrimaryKeyValue(row)
        const response = await axios.delete(`/api/analysis/table/${this.tableConfig.selectedTable}/delete/${primaryKey}`)
        
        if (response.data.status === 'success') {
          ElMessage.success('删除成功')
          this.fetchTableData()
        } else {
          ElMessage.error(response.data.message || '删除失败')
        }
      } catch (error) {
        if (error !== 'cancel') {
          console.error('删除记录失败:', error)
          ElMessage.error('删除失败：' + error.message)
        }
      }
    },

    async saveRecord() {
      this.loading.save = true
      try {
        let response
        if (this.dialogMode === 'create') {
          response = await axios.post(`/api/analysis/table/${this.tableConfig.selectedTable}/create`, this.formData)
        } else {
          const primaryKey = this.getPrimaryKeyValue(this.currentRecord)
          response = await axios.put(`/api/analysis/table/${this.tableConfig.selectedTable}/update/${primaryKey}`, this.formData)
        }
        
        if (response.data.status === 'success') {
          ElMessage.success(this.dialogMode === 'create' ? '创建成功' : '更新成功')
          this.dialogVisible = false
          this.fetchTableData()
        } else {
          ElMessage.error(response.data.message || '保存失败')
        }
      } catch (error) {
        console.error('保存记录失败:', error)
        ElMessage.error('保存失败：' + error.message)
      } finally {
        this.loading.save = false
      }
    },

    resetForm() {
      this.formData = {}
      this.currentRecord = {}
    },

    getPrimaryKeyValue(row) {
      const primaryKeys = {
        'students': 'student_id',
        'exam_scores': 'score_id',
        'class_performance': 'performance_id',
        'historical_grades': 'grade_id'
      }
      const key = primaryKeys[this.tableConfig.selectedTable]
      return row[key]
    },

    isPrimaryKey(prop) {
      const primaryKeys = {
        'students': 'student_id',
        'exam_scores': 'score_id',
        'class_performance': 'performance_id',
        'historical_grades': 'grade_id'
      }
      return prop === primaryKeys[this.tableConfig.selectedTable]
    },

    isSelectColumn(prop) {
      const selectColumns = ['gender', 'grade', 'class', 'status', 'score_level', 'semester', 'academic_year', 'grade_level']
      return selectColumns.includes(prop)
    },

    getColumnOptions(prop) {
      const options = {
        'gender': ['男', '女'],
        'grade': ['高一', '高二', '高三'],
        'class': ['高一1班', '高一2班', '高一3班', '高一4班', '高二1班', '高二2班', '高二3班', '高二4班', '高三1班', '高三2班', '高三3班', '高三4班'],
        'status': ['在读', '休学', '毕业', '转学'],
        'score_level': ['A', 'B', 'C', 'D', 'E'],
        'semester': ['第一学期', '第二学期'],
        'academic_year': ['2023-2024', '2024-2025'],
        'grade_level': ['优秀', '良好', '中等', '及格', '不及格']
      }
      return options[prop] || []
    }
  },

  watch: {
    trendType: {
      handler() {
        this.updateTrendChart()
      }
    },
    'tableConfig.selectedTable': {
      handler() {
        this.tableConfig.currentPage = 1
        this.fetchTableData()
      }
    },
    'tableConfig.searchQuery': {
      handler() {
        this.tableConfig.currentPage = 1
      }
    }
  }
}
</script>

<style scoped>
.visualization {
  padding: 20px;
}

.visualization-tabs {
  margin-bottom: 20px;
}

.chart-card, .filter-card, .table-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-title, .table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 15px;
}

.search-section, .action-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.chart-container {
  height: 400px;
  width: 100%;
}

.chart-container.small {
  height: 300px;
}

.table-wrapper {
  overflow: hidden;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.error-container, .empty-container {
  padding: 40px;
  text-align: center;
}

/* 已移除统计信息相关样式 */

/* 已移除表头统计标签 */

@media (max-width: 768px) {
  .filter-container {
    flex-direction: column;
    align-items: stretch;
  }
  
  .search-section, .action-section {
    justify-content: center;
    flex-wrap: wrap;
  }
}
</style>