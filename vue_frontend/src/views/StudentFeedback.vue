<template>
  <div class="student-feedback">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>学生反馈</h2>
        </div>
      </template>

      <!-- 查询条件（基于新数据集：students / university_grades） -->
      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="成绩表">
          <el-select v-model="query.selectedGradeTable" placeholder="选择成绩表" style="width: 180px;"
            @focus="fetchGradeTables" @change="onGradeTableChange">
            <el-option v-for="t in gradeTables" :key="t" :label="getTableLabel(t)" :value="t" />
          </el-select>
        </el-form-item>
        <el-form-item label="按学号/姓名选择">
          <el-select v-model="query.selectedStudent" filterable clearable placeholder="输入学号或姓名搜索"
                     style="width: 220px;" @focus="ensureStudentsLoadedPreferBackend(query.selectedGradeTable)" @change="onSelectStudent">
            <el-option v-for="s in studentsList" :key="s.student_id" :label="`${s.student_no || '—'} - ${s.name || '—'}`" :value="s.student_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生ID">
          <el-input v-model="query.studentId" placeholder="或直接输入学生ID" style="width: 120px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadFeedback">生成反馈</el-button>
          <el-button type="success" :disabled="!hasDetail" @click="saveFeedback" plain>保存</el-button>
        </el-form-item>
      </el-form>

      <!-- 加载中占位 -->
      <el-skeleton v-if="loading" :rows="6" animated />
      
      <!-- 未加载数据 -->
      <el-empty v-else-if="!hasDetail" description="请先通过上方“学号/姓名选择”或输入学生ID，点击生成反馈" />

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
            <el-tag type="info">ID: {{ (detail.profile && detail.profile.student_id) || query.studentId }}</el-tag>
            <el-tag>{{ (detail.profile && detail.profile.name) || '—' }}</el-tag>
            <el-tag type="success">{{ (detail.profile && detail.profile.gender) || '—' }}</el-tag>
            <el-tag type="warning">{{ (detail.profile && detail.profile.grade) || '—' }}</el-tag>
            <el-tag type="primary">{{ (detail.profile && detail.profile.class) || '—' }}</el-tag>
          </div>
        </el-card>

        <!-- 成绩概览（来自 university_grades，新：一二三次 + 平均） -->
        <el-row :gutter="16" class="kpis">
          <el-col :span="6">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">高数平均分</div>
              <div class="kpi-value">{{ formatScore(detail.grades?.calculus_avg_score) }}</div>
              <div class="kpi-sub">分位：{{ formatScore(detail.percentiles?.calculus_avg_score) }}%</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">高数第一次</div>
              <div class="kpi-value">{{ formatScore(detail.grades?.first_calculus_score) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">高数第二次</div>
              <div class="kpi-value">{{ formatScore(detail.grades?.second_calculus_score) }}</div>
            </el-card>
          </el-col>
          <el-col :span="6">
            <el-card class="kpi-card" shadow="hover">
              <div class="kpi-title">高数第三次</div>
              <div class="kpi-value">{{ formatScore(detail.grades?.third_calculus_score) }}</div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 学习投入（简化为标签展示） -->
        <el-card class="section-card" v-if="(detail.factors || []).length">
          <template #header><div class="section-header">学习投入</div></template>
          <div class="info">
            <el-tag v-for="f in detail.factors" :key="f.name" type="info" class="pill">{{ f.name }}：{{ f.value ?? '—' }}</el-tag>
          </div>
        </el-card>

        <!-- 成绩趋势反馈 -->
        <el-card class="section-card">
          <template #header><div class="section-header">成绩趋势反馈</div></template>
          <div v-if="trendFeedback.length">
            <p v-for="(t, i) in trendFeedback" :key="i" style="margin:6px 0;">{{ t }}</p>
          </div>
          <el-empty v-else description="暂无趋势结论" />
        </el-card>

        <!-- 薄弱环节定位 -->
        <el-card class="section-card">
          <template #header><div class="section-header">薄弱环节定位</div></template>
          <div v-if="weaknessFeedback.length">
            <p v-for="(t, i) in weaknessFeedback" :key="i" style="margin:6px 0;">{{ t }}</p>
          </div>
          <el-empty v-else description="未发现明显薄弱环节" />
        </el-card>

        <!-- 个性化提升建议 -->
        <el-card class="section-card">
          <template #header><div class="section-header">个性化提升建议</div></template>
          <div v-if="suggestionFeedback.length">
            <el-timeline>
              <el-timeline-item v-for="(s, idx) in suggestionFeedback" :key="idx" :timestamp="`建议 ${idx+1}`" type="primary">{{ s }}</el-timeline-item>
            </el-timeline>
          </div>
          <el-empty v-else description="暂无建议" />
        </el-card>

        <!-- 历史记录（仅学生反馈） -->
        <el-card class="section-card">
          <template #header><div class="section-header">历史记录</div></template>
          <el-timeline v-if="historyList.length">
            <el-timeline-item v-for="h in historyList" :key="h.id" :timestamp="h.created_at" type="primary">
              <el-tag size="small" type="info" style="margin-right:6px;">学生反馈</el-tag>
              {{ h.summary || renderHistoryText(h) }}
            </el-timeline-item>
          </el-timeline>
          <el-empty v-else description="暂无历史记录" />
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
        courseId: null,
        selectedStudent: null
      },
      gradeTables: [],
      // 本地 CSV 容器（仅使用 UG，students 缺失也可渲染）
      csvUG: [],
      studentsList: [],
      detail: { profile: null, grades: null, percentiles: null, factors: [] },
      trendFeedback: [],
      weaknessFeedback: [],
      suggestionFeedback: [],
      historyList: [],
      classStats: { avgScore: null, avgHours: null, attemptAvg: { first: null, second: null, third: null } },
    }
  },
  computed: {
    hasDetail() {
      return !!(this.detail && (this.detail.grades || this.detail.profile))
    }
  },
  mounted() {
    this.fetchGradeTables()
    this.ensureStudentsLoadedPreferBackend().catch(()=>{})
  },
  methods: {
    async fetchGradeTables() {
      if (this.gradeTables.length) return
      try {
        const res = await axios.get('/api/analysis/grade-tables')
        if (res.data?.status === 'success') {
          this.gradeTables = res.data.tables || []
          if (!this.query.selectedGradeTable && this.gradeTables.length)
            this.query.selectedGradeTable = this.gradeTables[0]
        }
      } catch {}
    },
    getTableLabel(t) {
      if (!t) return ''
      if (/^[0-9._-]+$/.test(t) || t.length <= 3) return t
      const map = {university_grades:'大学成绩',historical_grades:'历史成绩',exam_scores:'考试成绩',class_performance:'课堂表现'}
      return map[t] || t
    },
    async ensureStudentsLoadedPreferBackend(tableName) {
      // tableName: 当前选中的成绩表名
      this.studentsList = []
      const table = tableName || this.query.selectedGradeTable || 'university_grades'
      try {
        const res = await axios.get('/api/analysis/table-data', { params: { table, page: 1, page_size: 10000 } })
        if (res.data?.status === 'success' && Array.isArray(res.data.data)) {
          // 尝试自动识别学生ID/学号/姓名字段
          const data = res.data.data
          // 兼容不同表字段
          this.studentsList = data.map(r => ({
            student_id: r.student_id || r.id || r.学号 || r.ID || '',
            student_no: r.student_no || r.学号 || r.id || r.ID || '',
            name: r.name || r.姓名 || '',
            gender: r.gender || r.性别 || '',
            grade: r.grade || r.年级 || '',
            class: r.class || r.班级 || ''
          }))
          return
        }
      } catch {}
      // fallback: 尝试本地csv
      try {
        const rows = await this.fetchCsv(`/data/${table}.csv`)
        this.studentsList = rows.map(r => ({
          student_id: r.student_id || r.id || r.学号 || r.ID || '',
          student_no: r.student_no || r.学号 || r.id || r.ID || '',
          name: r.name || r.姓名 || '',
          gender: r.gender || r.性别 || '',
          grade: r.grade || r.年级 || '',
          class: r.class || r.班级 || ''
        }))
      } catch (e) {}
    },

    onGradeTableChange(val) {
      // 切换成绩表时，刷新学生下拉并清空已选
      this.query.selectedStudent = null
      this.query.studentId = ''
      this.studentsList = []
      this.ensureStudentsLoadedPreferBackend(val)
    },
    onSelectStudent(val) {
      this.query.studentId = String(val || '')
    },
    async loadFeedback() {
      if (!this.query.studentId) {
        ElMessage.warning('请先通过“学号/姓名选择”或直接输入学生ID')
        return
      }
      this.loading = true
      this.detail = { profile: null, grades: null, percentiles: null, factors: [] }
      this.trendFeedback = []
      this.weaknessFeedback = []
      this.suggestionFeedback = []
      try {
        let usedBackend = false
        const gradesTable = this.query.selectedGradeTable || 'university_grades'
        try {
          const res = await axios.get('/api/analysis/student-detail', { params: { student_id: this.query.studentId, table: gradesTable } })
          if (res.data?.status === 'success') {
            usedBackend = true
            this.detail = {
              profile: res.data.profile || null,
              grades: res.data.grades || null,
              percentiles: res.data.percentiles || null,
              factors: Array.isArray(res.data.factors) ? res.data.factors : []
            }
          }
        } catch (e) {}
        await this.ensureUGLoadedPreferBackend(gradesTable)
        if (!usedBackend) {
          this.detail = this.buildDetailFromCsv(String(this.query.studentId).trim())
        }
        this.computeClassStats()
        this.buildThreeDimensionFeedback()
        await this.loadHistory()
        ElMessage.success('已生成反馈')
      } catch (e) {
        console.error(e)
        ElMessage.error(`生成反馈失败：${e.message}`)
      } finally {
        this.loading = false
      }
    },
    async saveFeedback() {
      if (!this.hasDetail) { this.$message?.warning?.('请先生成反馈'); return }
      try {
        const payload = {
          student_id: this.query.studentId,
          detail: this.detail,
          trendFeedback: this.trendFeedback,
          weaknessFeedback: this.weaknessFeedback,
          suggestionFeedback: this.suggestionFeedback,
          source: 'student-feedback-ui'
        }
        const res = await axios.post('/api/analysis/student-feedback/save', payload)
        if (res.data?.status === 'success') this.$message?.success?.('已保存到系统')
        else this.$message?.error?.(res.data?.message || '保存失败')
        await this.loadHistory()
      } catch (e) {
        console.error(e)
        this.$message?.error?.(e.response?.data?.message || e.message || '保存失败')
      }
    },
    async loadHistory() {
      try {
        if (!this.query.studentId) return
        const r = await axios.get('/api/analysis/student-feedback/history', { params: { student_id: this.query.studentId, limit: 100 } })
        if (r.data?.status === 'success') {
          const arr = Array.isArray(r.data.data) ? r.data.data : []
          this.historyList = arr.filter(it => String(it.entry_type || '').toLowerCase() !== 'progress')
        }
        else this.historyList = []
      } catch { this.historyList = [] }
    },
    renderHistoryText(h) {
      try {
        const p = h?.payload || {}
        const w = Array.isArray(p.weaknessFeedback) ? p.weaknessFeedback : (Array.isArray(p.weaknesses) ? p.weaknesses : [])
        const s = Array.isArray(p.suggestionFeedback) ? p.suggestionFeedback : (Array.isArray(p.suggestions) ? p.suggestions : [])
        const ww = w.filter(x=>x).slice(0,2)
        const ss = s.filter(x=>x).slice(0,2)
        return (ww.concat(ss).join('；')) || '生成反馈'
      } catch { return '记录' }
    },
    async ensureUGLoadedPreferBackend() {
      const gradesTable = this.query.selectedGradeTable || 'university_grades'
      try {
        const ug = await axios.get('/api/analysis/table-data', { params: { table: gradesTable, page: 1, page_size: 10000 } })
        if (ug.data?.status === 'success' && Array.isArray(ug.data.data) && ug.data.data.length) {
          this.csvUG = ug.data.data
          return
        }
      } catch {}
      const ugCsv = await this.fetchCsv(`/data/${gradesTable}.csv`)
      this.csvUG = ugCsv
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
        header.forEach((h, idx) => {
          obj[h] = parts[idx] !== undefined ? parts[idx] : ''
        })
        rows.push(obj)
      }
      return rows
    },
    buildDetailFromCsv(studentId) {
      const sid = String(studentId)
      const student = null
      const ug = this.csvUG.find(r => String(r.student_id) === sid) || null
      const grades = ug ? { ...ug } : null
      if (grades) {
        const toNum = (x) => {
          const v = Number(x)
          return isNaN(v) ? null : v
        }
        grades.first_calculus_score = grades.first_calculus_score != null ? toNum(grades.first_calculus_score) : toNum(grades.calculus_score)
        grades.second_calculus_score = grades.second_calculus_score != null ? toNum(grades.second_calculus_score) : null
        grades.third_calculus_score = grades.third_calculus_score != null ? toNum(grades.third_calculus_score) : null
        const parts = [grades.first_calculus_score, grades.second_calculus_score, grades.third_calculus_score].filter(v => v !== null && v !== undefined)
        if (parts.length > 0) {
          grades.calculus_avg_score = Number((parts.reduce((a,b)=>a+b,0) / parts.length).toFixed(2))
        } else {
          const fallbackAvg = toNum(grades.total_score) ?? toNum(grades.calculus_score)
          grades.calculus_avg_score = fallbackAvg
        }
      }
      const percentiles = {}
      if (grades && grades.calculus_avg_score != null) {
        const pool = this.csvUG.map(r => {
          const a = [Number(r.first_calculus_score), Number(r.second_calculus_score), Number(r.third_calculus_score)].filter(x=>!isNaN(x))
          if (a.length) return a.reduce((p,c)=>p+c,0)/a.length
          const t = Number(r.total_score)
          const c = Number(r.calculus_score)
          return !isNaN(t) ? t : (!isNaN(c) ? c : NaN)
        }).filter(x => !isNaN(x))
        const v = Number(grades.calculus_avg_score)
        const cnt = pool.length
        const le = pool.filter(x => x <= v).length
        percentiles.calculus_avg_score = cnt ? (le / cnt * 100) : null
      }
      const factors = []
      if (ug) {
        const fMap = [
          { key: 'study_hours', name: '学习时长' },
          { key: 'attendance_count', name: '出勤次数' },
          { key: 'homework_score', name: '作业分数' },
          { key: 'practice_count', name: '刷题数' },
        ]
        for (const f of fMap) {
          const val = Number(ug[f.key])
          factors.push({ name: f.name, value: isNaN(val) ? null : val })
        }
      }
      return {
        profile: student,
        grades,
        percentiles,
        factors
      }
    },
    computeClassStats() {
      if (!Array.isArray(this.csvUG) || !this.csvUG.length) return
      const toNum = (v) => { const n = Number(v); return isNaN(n) ? null : n }
      const nums = this.csvUG.map(r => {
        const parts = [toNum(r.first_calculus_score), toNum(r.second_calculus_score), toNum(r.third_calculus_score)].filter(v => v!=null)
        const avg = parts.length ? parts.reduce((a,b)=>a+b,0)/parts.length : (toNum(r.calculus_avg_score) ?? toNum(r.total_score) ?? toNum(r.calculus_score))
        return avg
      }).filter(v => v!=null)
      const hoursArr = this.csvUG.map(r => toNum(r.study_hours)).filter(v=>v!=null)
      const firstArr = this.csvUG.map(r => toNum(r.first_calculus_score)).filter(v=>v!=null)
      const secondArr = this.csvUG.map(r => toNum(r.second_calculus_score)).filter(v=>v!=null)
      const thirdArr = this.csvUG.map(r => toNum(r.third_calculus_score)).filter(v=>v!=null)
      const avg = (arr) => arr.length ? (arr.reduce((a,b)=>a+b,0)/arr.length) : null
      this.classStats = {
        avgScore: avg(nums),
        avgHours: avg(hoursArr),
        attemptAvg: {
          first: avg(firstArr),
          second: avg(secondArr),
          third: avg(thirdArr)
        }
      }
    },
    buildThreeDimensionFeedback() {
      const g = this.detail.grades || {}
      const toNum = (v) => { const n = Number(v); return isNaN(n) ? null : n }
      const first = toNum(g.first_calculus_score ?? g.calculus_score)
      const second = toNum(g.second_calculus_score)
      const third = toNum(g.third_calculus_score)
      const avgScore = toNum(g.calculus_avg_score ?? g.total_score ?? g.calculus_score)
      const attempts = [first, second, third].filter(v=>v!=null)
      const classAvg = this.classStats.avgScore
      const attemptAvg = this.classStats.attemptAvg
      const hours = toNum(g.study_hours)
      const avgHours = this.classStats.avgHours
      let trendTexts = []
      let predicted = avgScore
      if (attempts.length >= 2) {
        const last = attempts[attempts.length-1]
        const prev = attempts[attempts.length-2]
        const delta = last - prev
        predicted = Math.min(100, Math.max(20, last + 0.8 * delta))
      }
      const inc12 = (second!=null && first!=null) ? (second - first) : null
      const inc23 = (third!=null && second!=null) ? (third - second) : null
      const steadilyUp = (inc12!=null && inc23!=null && inc12>=2 && inc23>=2) ||
                         (attempts.length>=2 && (attempts[attempts.length-1] - attempts[0] >= 4) && (Math.max(...attempts)-Math.min(...attempts) <= 12))
      const volatile = attempts.length>=2 && (Math.max(...attempts)-Math.min(...attempts) >= 15)
      if (steadilyUp && classAvg!=null && predicted!=null && predicted >= classAvg) {
        trendTexts.push('你的成绩持续进步，学习状态良好，预测后续能保持优势，建议继续维持当前学习节奏。')
      } else if (volatile && classAvg!=null && predicted!=null && predicted < classAvg) {
        trendTexts.push('成绩稳定性不足，可能受知识点掌握不扎实或学习方法影响，需重点关注波动原因，针对性调整。')
      } else if (predicted!=null && classAvg!=null) {
        trendTexts.push(`当前预测分约为 ${predicted.toFixed(1)}，班级均分约为 ${classAvg.toFixed(1)}。`)
      }
      this.trendFeedback = trendTexts
      let weakTexts = []
      let belowCnt = 0
      if (first!=null && attemptAvg.first!=null && first < attemptAvg.first) belowCnt++
      if (second!=null && attemptAvg.second!=null && second < attemptAvg.second) belowCnt++
      if (third!=null && attemptAvg.third!=null && third < attemptAvg.third) belowCnt++
      if (belowCnt >= 3) {
        weakTexts.push('高数成绩连续3次低于班级平均，且预测分仍处于下游，是你的薄弱科目，需优先分配更多学习时间。')
      }
      if (avgScore!=null && classAvg!=null && avgScore < classAvg - 5) {
        weakTexts.push(`你的高数平均分 ${avgScore.toFixed(1)} 低于班级均分 ${classAvg.toFixed(1)}，建议优先补强基础知识点。`)
      }
      this.weaknessFeedback = weakTexts
      let sugg = []
      if (hours!=null && avgHours!=null && hours < avgHours) {
        const incPerDay = 1
        const diff = (avgHours - hours)
        const stuH = hours.toFixed(1)
        const avgH = avgHours.toFixed(1)
        sugg.push(`每周学习时长仅 ${stuH} 小时，低于班级平均 ${avgH} 小时，建议每天增加 ${incPerDay} 小时专项练习。`)
      }
      const f = Array.isArray(this.detail.factors) ? this.detail.factors : []
      const val = (name) => { const it = f.find(x=>x.name===name); return it ? Number(it.value) : null }
      const att = val('出勤次数'), hw = val('作业分数'), prac = val('刷题数')
      if (att!=null && att < 70) sugg.push('出勤次数偏低，建议保证按时到课并积极参与课堂，提升学习效率。')
      if (hw!=null && hw < 75) sugg.push('作业得分偏低，建议规范书写、按时完成，并针对错题及时复盘。')
      if (prac!=null && prac < 30) sugg.push('刷题数量不足，建议增加针对性训练，优先突破薄弱题型。')
      if (!sugg.length) sugg.push('维持当前学习节奏与方法，可尝试挑战更高难度题目以巩固优势。')
      this.suggestionFeedback = sugg
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
.kpi-sub { margin-top: 6px; font-size: 12px; color: #909399; }
.perf-grid { display: none; }
.pill { margin: 4px; }
@media (max-width: 768px) {
  .perf-grid { grid-template-columns: 1fr; }
}
</style>
