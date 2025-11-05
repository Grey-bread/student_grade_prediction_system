<template>
  <div class="teacher-dashboard">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>教师仪表盘</h2>
          <span class="sub">来自数据库的实时教学概览</span>
        </div>
      </template>

      <!-- 概览指标 -->
      <el-row :gutter="16" class="kpi-row" v-loading="loading">
        <el-col :span="6">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">授课课程数</div>
            <div class="kpi-value">{{ overview.total_courses ?? '—' }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">覆盖学生数</div>
            <div class="kpi-value">{{ overview.total_students ?? '—' }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">平均成绩</div>
            <div class="kpi-value">{{ formatScore(overview.avg_score) }}</div>
          </el-card>
        </el-col>
        <el-col :span="6">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">最近90天考试</div>
            <div class="kpi-value">{{ overview.recent_exams ?? 0 }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="14">
          <el-card class="section-card" v-loading="loading">
            <template #header><div class="section-header">我的课程</div></template>
            <el-table :data="courses" size="small" border stripe>
              <el-table-column prop="course_name" label="课程" min-width="120" />
              <el-table-column prop="students_count" label="学生数" width="100" />
              <el-table-column prop="avg_score" label="平均分" width="100">
                <template #default="scope">{{ formatScore(scope.row.avg_score) }}</template>
              </el-table-column>
              <el-table-column prop="last_exam_date" label="最近考试" width="120" />
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card class="section-card" v-loading="loading">
            <template #header><div class="section-header">最近考试</div></template>
            <el-table :data="recentExams" size="small" border stripe>
              <el-table-column prop="exam_name" label="考试" min-width="140" />
              <el-table-column prop="course_name" label="课程" width="100" />
              <el-table-column prop="exam_date" label="日期" width="110" />
              <el-table-column prop="score" label="分数" width="90">
                <template #default="scope">{{ formatScore(scope.row.score) }}</template>
              </el-table-column>
              <el-table-column prop="score_level" label="等级" width="80" />
            </el-table>
          </el-card>

          <el-card class="section-card" v-loading="loading">
            <template #header><div class="section-header">成绩等级分布</div></template>
            <div class="levels">
              <div class="level" v-for="lv in ['A','B','C','D','E']" :key="lv">
                <span class="lv">{{ lv }}</span>
                <el-tag type="info">{{ scoreLevel[lv] ?? 0 }}</el-tag>
              </div>
            </div>
          </el-card>
        </el-col>
      </el-row>
    </el-card>
  </div>
  
</template>

<script>
import axios from 'axios'

export default {
  name: 'TeacherDashboard',
  data() {
    return {
      loading: false,
      overview: { total_courses: 0, total_students: 0, avg_score: null, recent_exams: 0 },
      courses: [],
      recentExams: [],
      scoreLevel: { A: 0, B: 0, C: 0, D: 0, E: 0 }
    }
  },
  mounted() {
    this.loadAll()
  },
  methods: {
    getAuthHeaders() {
      const token = localStorage.getItem('token')
      return token ? { Authorization: `Bearer ${token}` } : {}
    },
    async loadAll() {
      this.loading = true
      try {
        const headers = this.getAuthHeaders()
        const [ov, cs, re, sl] = await Promise.all([
          axios.get('/api/teacher/dashboard/overview', { headers }),
          axios.get('/api/teacher/dashboard/courses', { headers }),
          axios.get('/api/teacher/dashboard/recent-exams', { headers }),
          axios.get('/api/teacher/dashboard/score-level', { headers }),
        ])
        if (ov.data?.status === 'success') this.overview = ov.data.data || this.overview
        if (cs.data?.status === 'success') this.courses = cs.data.data || []
        if (re.data?.status === 'success') this.recentExams = re.data.data || []
        if (sl.data?.status === 'success') this.scoreLevel = sl.data.data || this.scoreLevel
      } catch (e) {
        console.error('加载仪表盘失败', e)
        this.$message?.error?.(e.response?.data?.message || e.message || '加载仪表盘失败')
      } finally {
        this.loading = false
      }
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
.kpi-row { margin-bottom: 12px; }
.kpi-card { text-align: center; }
.kpi-title { color: #909399; font-size: 13px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #303133; }
.section-card { margin-top: 16px; }
.section-header { font-weight: 600; }
.levels { display: grid; grid-template-columns: repeat(5, 1fr); gap: 8px; }
.level { display: flex; align-items: center; justify-content: space-between; padding: 6px 8px; background: #f9fafb; border-radius: 6px; }
.lv { font-weight: 600; }
@media (max-width: 1024px) {
  .levels { grid-template-columns: repeat(3, 1fr); }
}
@media (max-width: 768px) {
  .levels { grid-template-columns: repeat(2, 1fr); }
}
</style>
