<template>
  <div class="student-feedback">
    <el-card class="main-card">
      <template #header>
        <div class="card-header">
          <h2>学生反馈</h2>
        </div>
      </template>

      <!-- 查询条件 -->
      <el-form :inline="true" :model="query" class="query-form">
        <el-form-item label="成绩表">
          <el-select v-model="query.selectedGradeTable" placeholder="选择成绩表" style="width: 180px;" @focus="fetchGradeTables">
            <el-option
              v-for="t in gradeTables"
              :key="t"
              :label="getTableLabel(t)"
              :value="t"
            />
          </el-select>
        </el-form-item>

        <el-form-item label="按学号/姓名选择">
          <el-select
            v-model="query.selectedStudent"
            filterable
            clearable
            placeholder="输入学号或姓名搜索"
            style="width: 220px;"
            @focus="ensureStudentsLoadedPreferBackend"
            @change="onSelectStudent"
          >
            <el-option
              v-for="s in studentsList"
              :key="s.student_id"
              :label="`${s.student_no || '—'} - ${s.name || '—'}`"
              :value="s.student_id"
            />
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

      <!-- 空数据提示 -->
      <el-empty
        v-else-if="!hasDetail"
        description="请先通过上方“学号/姓名选择”或输入学生ID，点击生成反馈"
      />

      <!-- 展示反馈详情 -->
      <div v-else>
        <!-- 基本信息 -->
        <el-card class="section-card">
          <template #header>
            <div class="section-header">基本信息</div>
          </template>
          <div class="info">
            <el-tag type="info">ID: {{ safeGet(detail, 'profile.student_id', query.studentId) }}</el-tag>
            <el-tag>{{ safeGet(detail, 'profile.name') }}</el-tag>
            <el-tag type="success">{{ safeGet(detail, 'profile.gender') }}</el-tag>
            <el-tag type="warning">{{ safeGet(detail, 'profile.grade') }}</el-tag>
            <el-tag type="primary">{{ safeGet(detail, 'profile.class') }}</el-tag>
          </div>
        </el-card>

        <!-- 成绩概览 -->
        <div class="kpis">
          <el-card class="kpi-card" shadow="hover" v-for="(item, idx) in kpiList" :key="idx">
            <div class="kpi-title">{{ item.title }}</div>
            <div class="kpi-value">{{ formatScore(item.value) }}</div>
            <div class="kpi-sub" v-if="item.sub">分位：{{ formatScore(item.sub) }}%</div>
          </el-card>
        </div>

        <!-- 学习投入 -->
        <el-card class="section-card" v-if="detail.factors?.length">
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

        <!-- 历史记录 -->
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
      query: { studentId: '', selectedStudent: null, selectedGradeTable: null },
      gradeTables: [],
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
    hasDetail() { return !!(this.detail && (this.detail.grades || this.detail.profile)) },
    kpiList() {
      const g = this.detail.grades || {}
      return [
        { title: '高数平均分', value: g.calculus_avg_score, sub: this.detail.percentiles?.calculus_avg_score },
        { title: '高数第一次', value: g.first_calculus_score },
        { title: '高数第二次', value: g.second_calculus_score },
        { title: '高数第三次', value: g.third_calculus_score },
      ]
    }
  },
  mounted() {
    this.fetchGradeTables()
    this.ensureStudentsLoadedPreferBackend().catch(()=>{})
  },
  watch: {
    'query.selectedGradeTable'(newVal, oldVal) {
      // 用户切换成绩表时，清理旧数据并尝试预加载新表数据
      this.onGradeTableChange(newVal)
    }
  },
  methods: {
    toNum(v) { const n = Number(v); return isNaN(n) ? null : n },
    // 当选择不同成绩表时调用：清理旧缓存并预加载新表数据
    async onGradeTableChange(table) {
      // 立刻清理界面上与旧表相关的展示，避免在异步加载失败时仍显示旧数据
      this.csvUG = []
      this.detail = { profile: null, grades: null, percentiles: null, factors: [] }
      this.trendFeedback = []
      this.weaknessFeedback = []
      this.suggestionFeedback = []
      // 预取新表数据（容错，不抛出）
      try { await this.ensureUGLoadedPreferBackend(table) } catch (e) { this.csvUG = [] }
    },
    formatScore(val) { return this.toNum(val) === null ? '—' : this.toNum(val).toFixed(1) },
    safeGet(obj, path, defaultVal='—') {
      try { return path.split('.').reduce((o,k)=>o?.[k], obj) ?? defaultVal } catch { return defaultVal }
    },

    // 数据接口
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
      const map = { university_grades:'大学成绩', historical_grades:'历史成绩', exam_scores:'考试成绩', class_performance:'课堂表现' }
      return map[t] || t
    },
    async ensureStudentsLoadedPreferBackend() {
      if (this.studentsList.length) return
      try {
        const res = await axios.get('/api/analysis/table-data', { params: { table:'students', page:1, page_size:10000 } })
        if (res.data?.status==='success' && Array.isArray(res.data.data)) { this.studentsList=res.data.data; return }
      } catch {}
      try {
        const rows = await this.fetchCsv('/data/students.csv')
        this.studentsList = rows.map(r=>({ student_id:r.student_id, student_no:r.student_no, name:r.name, gender:r.gender, grade:r.grade, class:r.class }))
      } catch {}
    },
    onSelectStudent(val) { this.query.studentId = String(val||'') },

    // CSV 处理
    async fetchCsv(url) {
      const res = await fetch(url, { cache:'no-store' })
      if (!res.ok) throw new Error(`无法读取 ${url}`)
      const text = await res.text()
      return this.parseCsv(text)
    },
    parseCsv(text) {
      const rows = []
      const [headerLine, ...lines] = text.split(/\r?\n/).filter(Boolean)
      const headers = headerLine.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(h=>h.trim())
      for (const line of lines) {
        const values = line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).map(v=>v.trim().replace(/^"|"$/g,''))
        if (values.length < headers.length) continue
        rows.push(Object.fromEntries(headers.map((h,i)=>[h, values[i]])))
      }
      return rows
    },

    // 生成反馈
    async loadFeedback() {
      if (!this.query.studentId) { ElMessage.warning('请先通过“学号/姓名选择”或直接输入学生ID'); return }
      this.loading = true
      this.detail={ profile:null, grades:null, percentiles:null, factors:[] }
      this.trendFeedback=[]; this.weaknessFeedback=[]; this.suggestionFeedback=[]
      try {
        let usedBackend = false
        const gradesTable = this.query.selectedGradeTable || 'university_grades'
        try {
          const res = await axios.get('/api/analysis/student-detail', { params:{ student_id:this.query.studentId, table:gradesTable }})
          if (res.data?.status==='success') {
            usedBackend=true
            this.detail={
              profile: res.data.profile||null,
              grades: res.data.grades||null,
              percentiles: res.data.percentiles||null,
              factors: Array.isArray(res.data.factors)?res.data.factors:[]
            }
          }
        } catch{}
        await this.ensureUGLoadedPreferBackend(gradesTable)
        if (!usedBackend) this.detail = this.buildDetailFromCsv(String(this.query.studentId).trim())
        this.computeClassStats()
        this.buildThreeDimensionFeedback()
        await this.loadHistory()
        ElMessage.success('已生成反馈')
      } catch(e) { console.error(e); ElMessage.error(`生成反馈失败：${e.message}`) }
      finally { this.loading=false }
    },

    async saveFeedback() {
      if (!this.hasDetail) { this.$message?.warning?.('请先生成反馈'); return }
      try {
        const payload={ student_id:this.query.studentId, detail:this.detail, trendFeedback:this.trendFeedback, weaknessFeedback:this.weaknessFeedback, suggestionFeedback:this.suggestionFeedback, source:'student-feedback-ui' }
        const res=await axios.post('/api/analysis/student-feedback/save', payload)
        if(res.data?.status==='success') this.$message?.success?.('已保存到系统')
        else this.$message?.error?.(res.data?.message||'保存失败')
        await this.loadHistory()
      } catch(e){ console.error(e); this.$message?.error?.(e.response?.data?.message || e.message || '保存失败') }
    },

    async loadHistory() {
      try {
        if(!this.query.studentId) return
        const r=await axios.get('/api/analysis/student-feedback/history', { params:{ student_id:this.query.studentId, limit:100 } })
        if(r.data?.status==='success') this.historyList = (r.data.data||[]).filter(it => String(it.entry_type||'').toLowerCase()!=='progress')
        else this.historyList=[]
      } catch { this.historyList=[] }
    },

    renderHistoryText(h) {
      try {
        const p = h?.payload || {}
        const w = (p.weaknessFeedback||p.weaknesses||[]).slice(0,2)
        const s = (p.suggestionFeedback||p.suggestions||[]).slice(0,2)
        return [...w,...s].join('；')||'生成反馈'
      } catch { return '记录' }
    },

    async ensureUGLoadedPreferBackend(table = this.query.selectedGradeTable || 'university_grades') {
      // 先清空本地缓存，避免在加载过程中显示旧数据
      this.csvUG = []
      try {
        const ug = await axios.get('/api/analysis/table-data', { params: { table, page: 1, page_size: 10000 } })
        if (ug.data?.status === 'success' && Array.isArray(ug.data.data) && ug.data.data.length) {
          this.csvUG = ug.data.data
          return true
        }
      } catch (e) {
        // 忽略后端错误，尝试从静态 CSV 读取
      }
      try {
        const ugCsv = await this.fetchCsv(`/data/${table}.csv`)
        this.csvUG = ugCsv
        return true
      } catch (e) {
        // 无法加载到任何数据时，确保 csvUG 为空并返回失败
        this.csvUG = []
        return false
      }
    },

    buildDetailFromCsv(studentId) {
      const sid=String(studentId)
      const ug=this.csvUG.find(r=>String(r.student_id)===sid) || null
      const grades=ug ? {...ug} : null
      if(grades){
        const toNum=this.toNum
        grades.first_calculus_score=grades.first_calculus_score!=null ? toNum(grades.first_calculus_score) : toNum(grades.calculus_score)
        grades.second_calculus_score=grades.second_calculus_score!=null ? toNum(grades.second_calculus_score) : null
        grades.third_calculus_score=grades.third_calculus_score!=null ? toNum(grades.third_calculus_score) : null
        const parts=[grades.first_calculus_score, grades.second_calculus_score, grades.third_calculus_score].filter(v=>v!=null)
        grades.calculus_avg_score = parts.length ? Number((parts.reduce((a,b)=>a+b,0)/parts.length).toFixed(2)) : toNum(grades.total_score) ?? toNum(grades.calculus_score)
      }
      const percentiles={}
      if(grades?.calculus_avg_score!=null){
        const pool=this.csvUG.map(r=>{
          const a=[this.toNum(r.first_calculus_score), this.toNum(r.second_calculus_score), this.toNum(r.third_calculus_score)].filter(x=>x!=null)
          return a.length?a.reduce((p,c)=>p+c,0)/a.length: this.toNum(r.total_score) ?? this.toNum(r.calculus_score)
        }).filter(x=>x!=null)
        const v=grades.calculus_avg_score
        percentiles.calculus_avg_score=pool.length?(pool.filter(x=>x<=v).length/pool.length*100):null
      }
      const factors=[]
      if(ug){
        const fMap=[{key:'study_hours',name:'学习时长'},{key:'attendance_count',name:'出勤次数'},{key:'homework_score',name:'作业分数'},{key:'practice_count',name:'刷题数'}]
        for(const f of fMap){
          const val=this.toNum(ug[f.key])
          factors.push({name:f.name, value:val})
        }
      }
      return { profile:null, grades, percentiles, factors }
    },

    computeClassStats() {
      if(!Array.isArray(this.csvUG)||!this.csvUG.length) return
      const toNum=this.toNum
      const nums=this.csvUG.map(r=>{
        const parts=[toNum(r.first_calculus_score), toNum(r.second_calculus_score), toNum(r.third_calculus_score)].filter(v=>v!=null)
        return parts.length ? parts.reduce((a,b)=>a+b,0)/parts.length : toNum(r.calculus_avg_score)??toNum(r.total_score)??toNum(r.calculus_score)
      }).filter(v=>v!=null)
      const hoursArr=this.csvUG.map(r=>toNum(r.study_hours)).filter(v=>v!=null)
      const firstArr=this.csvUG.map(r=>toNum(r.first_calculus_score)).filter(v=>v!=null)
      const secondArr=this.csvUG.map(r=>toNum(r.second_calculus_score)).filter(v=>v!=null)
      const thirdArr=this.csvUG.map(r=>toNum(r.third_calculus_score)).filter(v=>v!=null)
      const avg=arr=>arr.length?arr.reduce((a,b)=>a+b,0)/arr.length:null
      this.classStats={ avgScore:avg(nums), avgHours:avg(hoursArr), attemptAvg:{ first:avg(firstArr), second:avg(secondArr), third:avg(thirdArr) } }
    },

    buildThreeDimensionFeedback() {
      this.computeTrendFeedback()
      this.computeWeaknessFeedback()
      this.computeSuggestions()
    },

    computeTrendFeedback() {
      const g=this.detail.grades||{}
      const first=this.toNum(g.first_calculus_score ?? g.calculus_score)
      const second=this.toNum(g.second_calculus_score)
      const third=this.toNum(g.third_calculus_score)
      const avgScore=this.toNum(g.calculus_avg_score ?? g.total_score ?? g.calculus_score)
      const attempts=[first,second,third].filter(v=>v!=null)
      const classAvg=this.classStats.avgScore
      let trendTexts=[], predicted=avgScore
      if(attempts.length>=2){ const last=attempts[attempts.length-1], prev=attempts[attempts.length-2]; predicted=Math.min(100,Math.max(20,last+0.8*(last-prev))) }
      const inc12=(second!=null&&first!=null)?(second-first):null
      const inc23=(third!=null&&second!=null)?(third-second):null
      const steadilyUp=(inc12!=null&&inc23!=null&&inc12>=2&&inc23>=2) || (attempts.length>=2&&(attempts[attempts.length-1]-attempts[0]>=4)&&(Math.max(...attempts)-Math.min(...attempts)<=12))
      const volatile=attempts.length>=2&&(Math.max(...attempts)-Math.min(...attempts)>=15)
      if(steadilyUp&&classAvg!=null&&predicted!=null&&predicted>=classAvg) trendTexts.push('你的成绩持续进步，学习状态良好，预测后续能保持优势，建议继续维持当前学习节奏。')
      else if(volatile&&classAvg!=null&&predicted!=null&&predicted<classAvg) trendTexts.push('成绩稳定性不足，可能受知识点掌握不扎实或学习方法影响，需重点关注波动原因，针对性调整。')
      else if(predicted!=null&&classAvg!=null) trendTexts.push(`当前预测分约为 ${predicted.toFixed(1)}，班级均分约为 ${classAvg.toFixed(1)}。`)
      this.trendFeedback=trendTexts
    },

    computeWeaknessFeedback() {
      const g=this.detail.grades||{}
      const first=this.toNum(g.first_calculus_score)
      const second=this.toNum(g.second_calculus_score)
      const third=this.toNum(g.third_calculus_score)
      const avgScore=this.toNum(g.calculus_avg_score ?? g.total_score ?? g.calculus_score)
      const attemptAvg=this.classStats.attemptAvg
      const classAvg=this.classStats.avgScore
      let weakTexts=[], belowCnt=0
      if(first!=null&&attemptAvg.first!=null&&first<attemptAvg.first) belowCnt++
      if(second!=null&&attemptAvg.second!=null&&second<attemptAvg.second) belowCnt++
      if(third!=null&&attemptAvg.third!=null&&third<attemptAvg.third) belowCnt++
      if(belowCnt>=3) weakTexts.push('高数成绩连续3次低于班级平均，且预测分仍处于下游，是你的薄弱科目，需优先分配更多学习时间。')
      if(avgScore!=null&&classAvg!=null&&avgScore<classAvg-5) weakTexts.push(`你的高数平均分 ${avgScore.toFixed(1)} 低于班级均分 ${classAvg.toFixed(1)}，建议优先补强基础知识点。`)
      this.weaknessFeedback=weakTexts
    },

    computeSuggestions() {
      const g=this.detail.grades||{}
      const hours=this.toNum(g.study_hours)
      const avgHours=this.classStats.avgHours
      const f=Array.isArray(this.detail.factors)?this.detail.factors:[]
      const val=name=>{ const it=f.find(x=>x.name===name); return it?this.toNum(it.value):null }
      let sugg=[]
      if(hours!=null&&avgHours!=null&&hours<avgHours){ const incPerDay=1; const diff=avgHours-hours; sugg.push(`每周学习时长仅 ${hours.toFixed(1)} 小时，低于班级平均 ${avgHours.toFixed(1)} 小时，建议每天增加 ${incPerDay} 小时专项练习。`) }
      if(val('出勤次数')!=null && val('出勤次数')<70) sugg.push('出勤次数偏低，建议保证按时到课并积极参与课堂，提升学习效率。')
      if(val('作业分数')!=null && val('作业分数')<75) sugg.push('作业得分偏低，建议规范书写、按时完成，并针对错题及时复盘。')
      if(val('刷题数')!=null && val('刷题数')<30) sugg.push('刷题数量不足，建议增加针对性训练，优先突破薄弱题型。')
      if(!sugg.length) sugg.push('维持当前学习节奏与方法，可尝试挑战更高难度题目以巩固优势。')
      this.suggestionFeedback=sugg
    }
  }
}
</script>

<style scoped>
.main-card { margin: 20px; }
.card-header { display: flex; align-items: baseline; gap: 12px; }
.query-form { margin-bottom: 10px; }
.section-card { margin-top: 16px; }
.section-header { font-weight: 600; }
.info { display: flex; flex-wrap: wrap; gap: 8px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap:16px; margin:10px 0; }
.kpi-card { text-align: center; }
.kpi-title { color: #909399; font-size: 13px; }
.kpi-value { font-size: 28px; font-weight: 700; color: #303133; }
.kpi-sub { margin-top: 6px; font-size: 12px; color: #909399; }
.pill { margin: 4px; }
@media (max-width: 768px) { .kpis { grid-template-columns: 1fr; } }
</style>
