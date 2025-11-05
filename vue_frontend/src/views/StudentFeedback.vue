<template>
  <div class="student-feedback">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>学生反馈</h2>
          <span class="sub">基于数据库数据生成个性化建议</span>
        </div>
      </template>

      <!-- 查询条件 -->
      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="学生ID">
          <el-input v-model="query.studentId" placeholder="请输入学生ID" style="width: 200px;" @change="onQueryChange" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="query.studentName" placeholder="可输入姓名查询" style="width: 180px;" @change="onQueryChange" />
        </el-form-item>
        <el-form-item label="课程">
          <el-select v-model="query.courseId" placeholder="该生参与过的课程" clearable style="width: 240px;">
            <el-option v-for="c in courseOptions" :key="c.course_id" :label="`${c.course_name} (${c.course_id})`" :value="c.course_id" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadFeedback">生成反馈</el-button>
        </el-form-item>
      </el-form>

  <!-- 加载中占位 -->
  <el-skeleton v-if="loading" :rows="6" animated />
      
  <!-- 未加载数据 -->
  <el-empty v-else-if="!feedback" description="请先输入学生ID并生成反馈" />

  <!-- 展示反馈详情 -->
  <div v-else>
        <!-- 学生基本信息 -->
        <el-card class="section-card" v-loading="loading">
          <template #header>
            <div class="section-header">
              <span>基本信息</span>
            </div>
          </template>
          <div class="info">
            <el-tag type="info">ID: {{ feedback.student?.student_id || query.studentId }}</el-tag>
            <el-tag>{{ feedback.student?.name || '—' }}</el-tag>
            <el-tag type="success">{{ feedback.student?.gender || '—' }}</el-tag>
            <el-tag type="warning">{{ feedback.student?.grade || '—' }}</el-tag>
            <el-tag type="primary">{{ feedback.student?.class || '—' }}</el-tag>
          </div>
        </el-card>

        <!-- 成绩概览 -->
        <el-row :gutter="16" class="kpis">
          <el-col :span="12">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">平均总评</div>
              <div class="kpi-value">{{ formatScore(feedback.overview?.avg_total_score) }}</div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">最近总评</div>
              <div class="kpi-value">{{ formatScore(feedback.overview?.latest_total_score) }}</div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-card class="section-card">
              <template #header><div class="section-header">按课程的平均成绩</div></template>
              <el-table :data="feedback.overview?.by_course || []" size="small" border stripe>
                <el-table-column prop="course_name" label="课程" width="120" />
                <el-table-column prop="midterm_score" label="期中" width="90" />
                <el-table-column prop="final_score" label="期末" width="90" />
                <el-table-column prop="usual_score" label="平时" width="90" />
                <el-table-column prop="total_score" label="总评" width="90" />
              </el-table>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="section-card">
              <template #header><div class="section-header">最近一次考试（每门课）</div></template>
              <el-table :data="feedback.latest_exams || []" size="small" border stripe>
                <el-table-column prop="course_name" label="课程" width="120" />
                <el-table-column prop="exam_name" label="考试" />
                <el-table-column prop="exam_date" label="日期" width="120" />
                <el-table-column prop="score" label="分数" width="90" />
                <el-table-column prop="score_level" label="等级" width="90" />
              </el-table>
            </el-card>
          </el-col>
        </el-row>

        <!-- 课堂表现对比 -->
        <el-card class="section-card">
          <template #header><div class="section-header">课堂表现：学生 vs 班级平均</div></template>
          <div class="perf-grid">
            <div v-for="item in perfItems" :key="item.key" class="perf-item">
              <div class="perf-title">{{ item.label }}</div>
              <div class="bars">
                <div class="bar">
                  <span class="bar-label">学生</span>
                  <el-progress :percentage="toPct(feedback.performance?.student_avg?.[item.key])" :stroke-width="10" status="success" />
                </div>
                <div class="bar">
                  <span class="bar-label">班级</span>
                  <el-progress :percentage="toPct(feedback.performance?.class_avg?.[item.key])" :stroke-width="10" />
                </div>
              </div>
            </div>
          </div>
        </el-card>

        <el-row :gutter="16">
          <el-col :span="12">
            <el-card class="section-card">
              <template #header><div class="section-header">优势</div></template>
              <div>
                <el-empty v-if="!feedback.strengths || feedback.strengths.length === 0" description="暂无" />
                <el-tag v-for="(s, idx) in feedback.strengths" :key="idx" type="success" effect="plain" class="pill">{{ s }}</el-tag>
              </div>
            </el-card>
          </el-col>
          <el-col :span="12">
            <el-card class="section-card">
              <template #header><div class="section-header">待提升</div></template>
              <div>
                <el-empty v-if="!feedback.weaknesses || feedback.weaknesses.length === 0" description="暂无" />
                <el-tag v-for="(w, idx) in feedback.weaknesses" :key="idx" type="warning" effect="plain" class="pill">{{ w }}</el-tag>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card class="section-card">
          <template #header><div class="section-header">个性化建议</div></template>
          <el-empty v-if="!feedback.suggestions || feedback.suggestions.length === 0" description="暂无建议" />
          <el-timeline v-else>
            <el-timeline-item v-for="(s, idx) in feedback.suggestions" :key="idx" :timestamp="`建议 ${idx+1}`" type="primary">{{ s }}</el-timeline-item>
          </el-timeline>
        </el-card>
      </div>
    </el-card>
  </div>
  
</template>

<script>
import axios from 'axios'
import { ElMessage } from 'element-plus'

export default {
  name: 'StudentFeedback',
  data() {
    return {
      loading: false,
      query: {
        studentId: '',
        studentName: '',
        courseId: null
      },
      feedback: null,
      courseOptions: [],
      perfItems: [
        { key: 'attendance_score', label: '出勤' },
        { key: 'participation_score', label: '课堂参与' },
        { key: 'homework_score', label: '作业完成' },
        { key: 'behavior_score', label: '课堂纪律/行为' },
        { key: 'total_performance_score', label: '综合表现' },
      ]
    }
  },
  mounted() {
    // 初始不加载课程，待输入学号或姓名后联动加载
  },
  methods: {
    async loadCourses() {
      try {
        const res = await axios.get('/api/analysis/student-courses', {
          params: {
            student_id: this.query.studentId || undefined,
            student_name: this.query.studentName || undefined
          }
        })
        if (res.data?.status === 'success') {
          this.courseOptions = res.data.courses || []
          // 若未填写学号但通过姓名解析出学生，则回填学号，便于后续生成反馈
          const resolved = res.data.resolved_student
          if (resolved && !this.query.studentId && resolved.student_id) {
            this.query.studentId = String(resolved.student_id)
          }
        } else {
          this.courseOptions = []
        }
      } catch (e) {
        this.courseOptions = []
        console.warn('加载该生参与课程失败', e)
      }
    },
    onQueryChange() {
      // 当学号或姓名变化时联动刷新课程下拉
      this.loadCourses()
    },
    async loadFeedback() {
      // 若仅输入了姓名，尝试解析学号
      if (!this.query.studentId && this.query.studentName) {
        await this.loadCourses()
      }
      if (!this.query.studentId) {
        ElMessage.warning('请先输入学生ID或姓名以定位学生')
        return
      }
      this.loading = true
      this.feedback = null
      try {
        const res = await axios.get('/api/analysis/student-feedback', {
          params: {
            student_id: this.query.studentId,
            course_id: this.query.courseId || undefined
          }
        })
        if (res.data?.status === 'success') {
          this.feedback = res.data
          ElMessage.success('已生成反馈')
        } else {
          throw new Error(res.data?.message || '生成反馈失败')
        }
      } catch (e) {
        console.error(e)
        ElMessage.error(`生成反馈失败：${e.message}`)
      } finally {
        this.loading = false
      }
    },
    toPct(val) {
      const num = parseFloat(val)
      if (isNaN(num)) return 0
      // 分数假定满分100
      return Math.max(0, Math.min(100, Math.round(num)))
    },
    formatScore(val) {
      return (val === null || val === undefined || isNaN(Number(val))) ? '—' : Number(val).toFixed(1)
    }
  }
}
</script>

<style scoped>
.main-card { margin: 20px; }
.card-header { display: flex; align-items: baseline; gap: 12px; }
.card-header .sub { color: #909399; font-size: 13px; }
.query-form { margin-bottom: 10px; }
.section-card { margin-top: 16px; }
.section-header { font-weight: 600; }
.info { display: flex; flex-wrap: wrap; gap: 8px; }
.kpis { margin: 10px 0; }
.kpi-card { text-align: center; }
.kpi-title { color: #909399; font-size: 13px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #303133; }
.perf-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 16px; }
.perf-item { padding: 8px 0; }
.perf-title { margin-bottom: 6px; font-weight: 600; }
.bars { display: flex; flex-direction: column; gap: 8px; }
.bar { display: grid; grid-template-columns: 60px 1fr; align-items: center; gap: 8px; }
.bar-label { color: #909399; font-size: 12px; }
.pill { margin: 4px; }
@media (max-width: 768px) {
  .perf-grid { grid-template-columns: 1fr; }
}
</style>
