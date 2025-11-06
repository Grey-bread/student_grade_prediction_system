<template>
  <div class="teacher-dashboard">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>教师面板 · 学生个体画像</h2>
        </div>
      </template>

      <!-- 查询条件：按学号/姓名选择或输入ID -->
      <el-form :inline="true" class="query-form">
        <el-form-item label="按学号/姓名选择">
          <el-select v-model="query.selectedStudent" filterable clearable placeholder="输入学号或姓名搜索"
                     style="width: 300px;" @focus="ensureStudentsLoaded" @change="onSelectStudent">
            <el-option v-for="s in studentsList" :key="s.student_id" :label="formatStudentLabel(s)" :value="s.student_id" />
          </el-select>
        </el-form-item>
        <el-form-item label="学生ID">
          <el-input v-model="query.studentId" placeholder="或直接输入学生ID" style="width: 200px;" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="loadPortrait">生成画像</el-button>
        </el-form-item>
      </el-form>

      <el-skeleton v-if="loading" :rows="6" animated />
      <el-empty v-else-if="!portrait" description="请选择学生并点击生成画像" />

      <div v-else>
        <!-- 基础信息 + 预测总览 -->
        <el-row :gutter="16" class="kpi-row">
          <el-col :span="10">
            <el-card class="section-card" shadow="hover">
              <template #header><div class="section-header">基础信息</div></template>
              <el-descriptions :column="2" border size="small">
                <el-descriptions-item label="ID">{{ portrait.profile?.student_id || '—' }}</el-descriptions-item>
                <el-descriptions-item label="学号">{{ portrait.profile?.student_no || '—' }}</el-descriptions-item>
                <el-descriptions-item label="姓名">{{ portrait.profile?.name || '—' }}</el-descriptions-item>
                <el-descriptions-item label="班级">{{ portrait.profile?.grade || '—' }} {{ portrait.profile?.class || '' }}</el-descriptions-item>
              </el-descriptions>
            </el-card>
          </el-col>
          
          <el-col :span="14">
              <el-card class="section-card" shadow="hover">
                <template #header><div class="section-header">成绩预测</div></template>
                <div class="pred-card" :class="{ center: !hasTrendSide }">
                  <div class="kpi-main">
                    <div class="tagline"><el-tag size="small" type="success">趋势外推</el-tag></div>
                    <div class="pred-value">{{ formatScore(portrait.predictions?.total?.value) }}</div>
                  </div>
                  <div class="kpi-side" v-if="hasTrendSide">
                    <div class="kpi-title">近三次成绩</div>
                    <div class="chips">
                      <span class="chip" v-for="(t,i) in (portrait.trend || [])" :key="i">
                        {{ t.label }}：{{ formatScore(t.score) }}
                      </span>
                    </div>
                    <div class="mini-desc" v-if="trendText">{{ trendText }}</div>
                  </div>
                </div>
              </el-card>
          </el-col>
        </el-row>

        <!-- 薄弱知识点 -->
        <el-row :gutter="16">
          <el-col :span="24">
            <el-card class="section-card" shadow="hover">
              <template #header><div class="section-header">薄弱知识点</div></template>
              <div v-if="(analysisFb?.weaknesses && analysisFb.weaknesses.length) || (portrait.weak_points?.length)">
                <ul class="list">
                  <li v-for="(w,i) in (analysisFb?.weaknesses?.length ? analysisFb.weaknesses : portrait.weak_points)" :key="i">{{ w }}</li>
                </ul>
              </div>
              <el-empty v-else description="未发现明显薄弱项" />
            </el-card>
          </el-col>
        </el-row>

        <!-- 反馈与建议 -->
        <el-row :gutter="16">
          <el-col :span="24">
            <el-card class="section-card" shadow="hover">
              <template #header><div class="section-header">反馈记录</div></template>
              <el-timeline v-if="feedbackRecordsDisplay.length">
                <el-timeline-item
                  v-for="(r,idx) in feedbackRecordsDisplay"
                  :key="idx"
                  :timestamp="r.time || '—'"
                  :type="r.source === '考试评语' ? 'primary' : 'success'"
                >
                  <el-tag size="small" type="info" style="margin-right:6px;">{{ r.source }}</el-tag>
                  {{ r.text }}
                </el-timeline-item>
              </el-timeline>
              <el-empty v-else description="暂无反馈记录" />
            </el-card>
          </el-col>
        </el-row>

        <el-card class="section-card" shadow="hover">
          <template #header><div class="section-header">关联建议</div></template>
          <div v-if="recommendedDisplay.length">
            <el-timeline>
              <el-timeline-item v-for="(s, i) in recommendedDisplay" :key="i" :timestamp="`建议 ${i+1}`" type="primary">
                {{ s }}
              </el-timeline-item>
            </el-timeline>
          </div>
          <el-empty v-else description="暂无建议" />
        </el-card>
      </div>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  name: 'TeacherDashboard',
  computed: {
    hasTrendSide() {
      const arr = Array.isArray(this.portrait?.trend) ? this.portrait.trend : []
      const hasScores = arr.some(x => x && x.score != null)
      const hasText = !!(this.trendText && String(this.trendText).trim())
      return hasScores || hasText
    },
    trendText() {
      // 优先使用后端提供的描述
      const d = this.portrait?.trend_description
      if (d && String(d).trim()) return d
      // 回退：由三次分数计算
      const arr = Array.isArray(this.portrait?.trend) ? this.portrait.trend : []
      if (!arr.length) return ''
      const vals = arr.map(x => Number(x?.score ?? 0))
      if (vals.length < 3) return ''
      const [a,b,c] = vals
      const d1 = b - a, d2 = c - b
      const eps = 1e-6
      const sg = (x) => Math.abs(x) < eps ? 0 : (x > 0 ? 1 : -1)
      const s1 = sg(d1), s2 = sg(d2)
      const seq = `（${a.toFixed(1)}→${b.toFixed(1)}→${c.toFixed(1)}）`
      if (s1 === 0 && s2 === 0) return `总体趋于平稳，波动不大${seq}`
      if (s1 > 0 && s2 > 0) return `成绩稳步上扬，进步清晰可见${seq}`
      if (s1 < 0 && s2 < 0) return `成绩阶段性回落，可关注学习节奏与巩固${seq}`
      if (s1 > 0 && s2 < 0) return `先扬后抑，建议查找波动原因并及时调整${seq}`
      if (s1 < 0 && s2 > 0) return `先行蓄力后上扬，回升势头良好${seq}`
      if (s1 === 0 && s2 > 0) return `前期平稳，后程发力上行${seq}`
      if (s1 === 0 && s2 < 0) return `前期平稳，后段有所回落${seq}`
      if (s1 > 0 && s2 === 0) return `上行后趋于稳定，走势平顺${seq}`
      if (s1 < 0 && s2 === 0) return `回落后趋于稳定，波动收敛${seq}`
      return `成绩走势发生变化${seq}`
    },
    feedbackRecordsDisplay() {
      // 历史记录优先
      if (this.historyList && this.historyList.length) {
        return this.historyList
          .filter(it => (it.entry_type || '').toLowerCase() !== 'progress')
          .map(it => ({
          time: it.created_at || '',
          source: '学生反馈',
          text: it.summary || this.renderHistoryText(it)
        }))
      }
      const p = this.portrait?.feedback?.records || []
      if (p.length) return p
      const exams = this.analysisFb?.latest_exams || []
      if (exams.length) {
        return exams.map(e => ({
          source: '最近考试',
          time: e.exam_date || '',
          text: `${e.course_name || '课程'}｜${e.exam_name || ''}：${(e.score==null||e.score==='')?'—':e.score}`
        }))
      }
      return []
    },
    
    recommendedDisplay() {
      const a = Array.isArray(this.portrait?.recommendations) ? this.portrait.recommendations : []
      const b = Array.isArray(this.analysisFb?.suggestions) ? this.analysisFb.suggestions : []
      // 优先展示画像，再补充分析建议；去重保序，并最终最多显示5条
      const set = new Set()
      const merged = []
      for (const s of [...a, ...b]) {
        if (s && !set.has(s)) { set.add(s); merged.push(s) }
        if (merged.length >= 5) break
      }
      return merged.slice(0, 5)
    }
  },
  data() {
    return {
      loading: false,
      query: { selectedStudent: null, studentId: '' },
      studentsList: [],
      portrait: null,
      analysisFb: null,
      historyList: []
    }
  },
  mounted() {
    this.ensureStudentsLoaded().catch(()=>{})
  },
  beforeUnmount() {
  },
  methods: {
    formatStudentLabel(s) {
      return `${s.student_no || '—'} - ${s.name || '—'}${s.grade ? ' ｜ '+s.grade : ''}${s.class ? ' '+s.class : ''}`
    },
    renderHistoryText(it) {
      // 当后端未提供 summary 时，前端生成简要摘要
      try {
        const p = it?.payload || {}
        if (it.entry_type === 'progress') {
          return (p.text || p.note || p.summary || '').trim() || '学习进展更新'
        }
        const w = Array.isArray(p.weaknessFeedback) ? p.weaknessFeedback : (Array.isArray(p.weaknesses) ? p.weaknesses : [])
        const s = Array.isArray(p.suggestionFeedback) ? p.suggestionFeedback : (Array.isArray(p.suggestions) ? p.suggestions : [])
        const ww = w.filter(x=>x).slice(0,2)
        const ss = s.filter(x=>x).slice(0,2)
        return (ww.concat(ss).join('；')) || '生成反馈'
      } catch { return '记录' }
    },
    async ensureStudentsLoaded() {
      if (this.studentsList.length) return
      try {
        const res = await axios.get('/api/analysis/table-data', { params: { table: 'students', page: 1, page_size: 10000 } })
        if (res.data?.status === 'success') {
          this.studentsList = res.data.data || []
        }
      } catch (e) {
        // CSV 回退
        try {
          const resp = await fetch('/data/students.csv', { cache: 'no-store' })
          const text = await resp.text()
          const lines = text.replace(/\r\n/g, '\n').replace(/\r/g, '\n').split('\n').filter(l => l.trim().length)
          const header = lines[0].split(',').map(h => h.trim())
          const arr = []
          for (let i=1;i<lines.length;i++){
            const parts = lines[i].split(','); if(parts.length < header.length) continue
            const o = {}; header.forEach((h,idx)=>o[h]=parts[idx]??''); arr.push(o)
          }
          this.studentsList = arr
        } catch {}
      }
    },
    onSelectStudent(val) { this.query.studentId = String(val || '') },
    async loadPortrait() {
      if (!this.query.studentId) { this.$message?.warning?.('请选择学生或输入ID'); return }
      this.loading = true
      this.portrait = null
      this.analysisFb = null
      try {
        const res = await axios.get('/api/teacher/student-portrait', { params: { student_id: this.query.studentId } })
        if (res.data?.status === 'success') {
          this.portrait = res.data.data
          // 读取学生反馈历史
          try {
            const h = await axios.get('/api/analysis/student-feedback/history', { params: { student_id: this.query.studentId, limit: 50 } })
            this.historyList = (h.data?.status === 'success' && Array.isArray(h.data.data)) ? h.data.data : []
          } catch (_) { this.historyList = [] }
          // 追加获取“学生反馈”分析结果，纳入薄弱点与建议
          try {
            const fb = await axios.get('/api/analysis/student-feedback', { params: { student_id: this.query.studentId } })
            if (fb.data?.status === 'success') this.analysisFb = fb.data
          } catch (_) {}
        } else {
          this.$message?.error?.(res.data?.message || '生成画像失败')
        }
      } catch (e) {
        console.error(e)
        this.$message?.error?.(e.response?.data?.message || e.message || '生成画像失败')
      } finally {
        this.loading = false
      }
    },
    
    formatScore(v) { return (v===null||v===undefined||isNaN(Number(v))) ? '—' : Number(v).toFixed(1) }
  }
}
</script>

<style scoped>
.main-card { margin: 20px; }
.card-header { display: flex; align-items: baseline; gap: 12px; }
.card-header .sub { color: #909399; font-size: 13px; }
.query-form { margin-bottom: 12px; }
.kpi-row { margin-bottom: 12px; }
.section-card { margin-top: 12px; }
.section-header { font-weight: 600; }
.pred-flex { display: flex; gap: 16px; align-items: flex-start; }
.pred-total { min-width: 220px; padding-right: 12px; border-right: 1px dashed #e5e7eb; }
.pred-value { font-size: 32px; font-weight: 700; color: #303133; line-height: 1.1; }
.kpi-title { color: #909399; font-size: 13px; margin-bottom: 6px; }
.kpi-sub { color: #a0aec0; font-size: 12px; margin-top: 4px; }
.pred-card { display: flex; gap: 20px; align-items: center; justify-content: flex-start; }
.pred-card.center { justify-content: center; }
.kpi-main { min-width: 220px; padding-right: 16px; border-right: 1px dashed #e5e7eb; }
.pred-card.center .kpi-main { border-right: none; text-align: center; }
.kpi-side { flex: 1; }
.chips { display: flex; flex-wrap: wrap; gap: 8px; }
.chip { background: #f5f7fa; padding: 6px 10px; border-radius: 999px; font-size: 13px; }
.tagline { margin-bottom: 6px; }
.mini-desc { color: #606266; font-size: 13px; margin-top: 6px; }
.muted { color: #a0aec0; font-size: 13px; }
.trend-text { min-height: 80px; display: flex; align-items: center; }
.trend-desc { font-size: 16px; color: #303133; }
.tags { display: flex; flex-wrap: wrap; gap: 8px; }
.tag { margin-bottom: 6px; }
.list { margin: 0; padding-left: 12px; }
@media (max-width: 768px) {
  .pred-card { flex-direction: column; }
  .kpi-main { border-right: none; }
}
</style>
