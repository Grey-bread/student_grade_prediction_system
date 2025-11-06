<template>
  <div class="teacher-dashboard">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>教师仪表盘</h2>
          <span class="sub">后端可用优先；不可用时直接读取 CSV</span>
        </div>
      </template>

      <!-- 概览指标（基于 students / university_grades） -->
      <el-row :gutter="16" class="kpi-row" v-loading="loading">
        <el-col :span="8">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">学生总人数</div>
            <div class="kpi-value">{{ overview.total_students || '—' }}</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">UG 记录数</div>
            <div class="kpi-value">{{ overview.ug_records || 0 }}</div>
          </el-card>
        </el-col>
        <el-col :span="8">
          <el-card shadow="hover" class="kpi-card">
            <div class="kpi-title">平均高数分（平均）</div>
            <div class="kpi-value">{{ formatScore(overview.avg_calculus_avg) }}</div>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="16">
        <el-col :span="14">
          <el-card class="section-card" v-loading="loading">
            <template #header><div class="section-header">年级高数平均分</div></template>
            <el-table :data="avgByGrade" size="small" border stripe>
              <el-table-column prop="grade" label="年级" min-width="120" />
              <el-table-column prop="avg" label="平均分" width="120">
                <template #default="scope">{{ formatScore(scope.row.avg) }}</template>
              </el-table-column>
            </el-table>
          </el-card>
        </el-col>
        <el-col :span="10">
          <el-card class="section-card" v-loading="loading">
            <template #header><div class="section-header">成绩等级分布（A≥90, B≥80, C≥70, D≥60, E<60）</div></template>
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
      overview: { total_students: 0, ug_records: 0, avg_calculus_avg: null },
      avgByGrade: [],
      scoreLevel: { A: 0, B: 0, C: 0, D: 0, E: 0 }
    }
  },
  mounted() {
    this.loadAll()
  },
  methods: {
    async loadAll() {
      this.loading = true
      try {
        let backendOk = false
        try {
          // 学生总数（来自分类分布接口中的 total）
          const st = await axios.get('/api/analysis/students/category-distribution')
          if (st.data?.status === 'success') {
            this.overview.total_students = st.data.total || 0
            backendOk = true
          }
        } catch {}

        if (backendOk) {
          try {
            const ug = await axios.get('/api/analysis/table-data', { params: { table: 'university_grades', page: 1, page_size: 10000 } })
            if (ug.data?.status === 'success') {
              const rows = ug.data.data || []
              this.overview.ug_records = ug.data.total || rows.length
              let avgSum = 0, avgCnt = 0
              const lvl = { A:0, B:0, C:0, D:0, E:0 }
              for (const r of rows) {
                // 优先使用后端归一化后的 calculus_avg_score
                const a = Number(r.calculus_avg_score)
                if (!isNaN(a)) { avgSum += a; avgCnt += 1; if (a>=90) lvl.A++; else if (a>=80) lvl.B++; else if (a>=70) lvl.C++; else if (a>=60) lvl.D++; else lvl.E++; }
              }
              this.overview.avg_calculus_avg = avgCnt? (avgSum/avgCnt) : null
              this.scoreLevel = lvl
            }
          } catch {}

          try {
            const byGrade = await axios.get('/api/analysis/ug/avg-score-by-student-grade')
            if (byGrade.data?.status === 'success') {
              const labels = byGrade.data.labels || []
              const avg = byGrade.data.avg || []
              this.avgByGrade = labels.map((g, i) => ({ grade: g, avg: avg[i] }))
            }
          } catch {}
        }

        // 若后端不可用或数据不完整，改走 CSV
        if (!backendOk || !this.overview.ug_records) {
          const [students, ug] = await Promise.all([
            this.fetchCsv('/data/students.csv'),
            this.fetchCsv('/data/university_grades.csv')
          ])
          // 概览
          this.overview.total_students = students.length
          this.overview.ug_records = ug.length
          let avgSum = 0, avgCnt = 0
          const lvl = { A:0, B:0, C:0, D:0, E:0 }
          for (const r of ug) {
            // 兼容新旧列：以三次均值为准，否则回退 total/calculus
            const nums = [Number(r.first_calculus_score), Number(r.second_calculus_score), Number(r.third_calculus_score)].filter(x=>!isNaN(x))
            let a
            if (nums.length) a = nums.reduce((p,c)=>p+c,0)/nums.length
            else {
              const t = Number(r.total_score)
              const c = Number(r.calculus_score)
              a = !isNaN(t) ? t : (!isNaN(c) ? c : NaN)
            }
            if (!isNaN(a)) { avgSum += a; avgCnt += 1; if (a>=90) lvl.A++; else if (a>=80) lvl.B++; else if (a>=70) lvl.C++; else if (a>=60) lvl.D++; else lvl.E++; }
          }
          this.overview.avg_calculus_avg = avgCnt? (avgSum/avgCnt) : null
          this.scoreLevel = lvl

          // 年级均分：通过 student_id -> grade 关联
          const id2grade = {}
          for (const s of students) id2grade[String(s.student_id)] = s.grade
          const group = {}
          for (const r of ug) {
            const gid = id2grade[String(r.student_id)]
            const nums = [Number(r.first_calculus_score), Number(r.second_calculus_score), Number(r.third_calculus_score)].filter(x=>!isNaN(x))
            let a
            if (nums.length) a = nums.reduce((p,c)=>p+c,0)/nums.length
            else {
              const t = Number(r.total_score)
              const c = Number(r.calculus_score)
              a = !isNaN(t) ? t : (!isNaN(c) ? c : NaN)
            }
            if (!gid || isNaN(a)) continue
            if (!group[gid]) group[gid] = { sum:0, cnt:0 }
            group[gid].sum += a; group[gid].cnt += 1
          }
          this.avgByGrade = Object.keys(group).sort().map(g => ({ grade: g, avg: group[g].sum / group[g].cnt }))
        }
      } catch (e) {
        console.error('加载仪表盘失败', e)
        this.$message?.error?.(e.response?.data?.message || e.message || '加载仪表盘失败')
      } finally {
        this.loading = false
      }
    },
    async fetchCsv(url) {
      const res = await fetch(url, { cache: 'no-store' })
      if (!res.ok) throw new Error(`无法读取 ${url}`)
      const text = await res.text()
      return this.parseCsv(text)
    },
    parseCsv(text) {
      const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(l => l.trim().length)
      if (!lines.length) return []
      const header = lines[0].split(',').map(h => h.trim())
      const rows = []
      for (let i = 1; i < lines.length; i++) {
        const parts = lines[i].split(',')
        if (!parts.length || parts.length < header.length) continue
        const obj = {}
        header.forEach((h, idx) => { obj[h] = parts[idx] !== undefined ? parts[idx] : '' })
        rows.push(obj)
      }
      return rows
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
