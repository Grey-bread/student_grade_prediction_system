<template>
  <div class="upload-page">
    <el-row type="flex" justify="center">
      <el-col :xs="22" :sm="18" :md="14" :lg="12">
        <el-card class="upload-card">
          <div class="card-header">
            <h2>上传学生数据</h2>
            <p class="sub">支持 Excel / CSV 文件，上传后会触发预测与可视化分析</p>
          </div>

          <div class="upload-area">
            <el-upload
              class="upload-drag"
              :http-request="customUpload"
              :show-file-list="false"
              accept=".csv,.xlsx,.xls"
              drag
            >
              <i class="el-icon-upload"></i>
              <p class="el-upload__text">将文件拖到此处，或点击上传</p>
              <div class="el-upload__tip">建议一次上传不超过 10MB；登录后可保存结果</div>
            </el-upload>

            <div v-if="!token" class="login-hint">
              <el-alert title="未登录：上传将作为匿名请求，登录可保存记录" type="warning" show-icon closable />
            </div>
          </div>

          <div v-if="loading" class="loading-row">
            <el-progress :percentage="progress" status="active"></el-progress>
            <div class="loading-text">正在分析数据...</div>
          </div>

          <div v-if="message" class="result-message">
            <el-alert :title="message" :type="isError? 'error':'success'" show-icon />
          </div>

        </el-card>
      </el-col>
    </el-row>

    <div v-if="predictionResult" class="results-wrap">
      <el-row :gutter="20">
        <el-col :span="24">
          <el-card>
            <h3>模型性能</h3>
            <el-row :gutter="20" class="metrics-row">
              <el-col :xs="24" :sm="8" v-for="(label, key) in metricKeys" :key="key">
                <div class="metric">
                  <div class="metric-label">{{ label }}</div>
                  <div class="metric-value">{{ formatNumber(predictionResult.metrics[key]) }}</div>
                </div>
              </el-col>
            </el-row>
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top:16px;">
        <el-col :xs="24" :md="12" v-if="predictionResult.visualizations.prediction_scatter">
          <el-card>
            <h3>预测 vs 实际（散点图）</h3>
            <img :src="'data:image/png;base64,' + predictionResult.visualizations.prediction_scatter" alt="scatter" style="width:100%;" />
          </el-card>
        </el-col>
        <el-col :xs="24" :md="12" v-if="predictionResult.visualizations.feature_importance">
          <el-card>
            <h3>特征重要性</h3>
            <img :src="'data:image/png;base64,' + predictionResult.visualizations.feature_importance" alt="feature" style="width:100%;" />
          </el-card>
        </el-col>
      </el-row>
    </div>
  </div>
</template>

<script>
import axios from 'axios'

export default {
  data() {
    return {
      token: localStorage.getItem('token') || null,
      predictionResult: null,
      message: null,
      isError: false,
      loading: false,
      progress: 0,
      metricKeys: { r2: 'R² 评分', mae: 'MAE', rmse: 'RMSE' }
    }
  },
  methods: {
    formatNumber(value) {
      if (value === undefined || value === null) return '--'
      return Number(value).toFixed(4)
    },
    async customUpload({ file, onSuccess, onError }) {
      if (!file) return
      const fd = new FormData()
      fd.append('file', file)

      this.loading = true
      this.message = null
      this.predictionResult = null
      this.progress = 10

      try {
        const headers = {}
        if (this.token) headers['Authorization'] = 'Bearer ' + this.token

        const res = await axios.post('/api/predict', fd, {
          headers,
          onUploadProgress: (e) => {
            if (e.total) this.progress = Math.min(90, Math.round((e.loaded / e.total) * 80) + 10)
          }
        })

        if (res.data.status === 'success') {
          this.predictionResult = res.data
          this.message = '分析完成'
          this.isError = false
          this.progress = 100
          onSuccess && onSuccess(res.data)
        } else {
          this.message = res.data.message || '预测失败'
          this.isError = true
          onError && onError(new Error(this.message))
        }
      } catch (err) {
        this.message = err.response?.data?.message || '请求失败'
        this.isError = true
        onError && onError(err)
      } finally {
        setTimeout(() => { this.loading = false; this.progress = 0 }, 500)
      }
    }
  }
}
</script>

<style scoped>
.upload-page { padding: 20px; }
.upload-card { padding: 20px; }
.card-header h2 { margin: 0; }
.card-header .sub { margin: 6px 0 0; color: #888 }
.upload-area { margin-top: 18px; }
.upload-drag { display:block; padding: 26px; border-radius: 6px; background: #fafafa }
.login-hint { margin-top: 12px }
.loading-row { margin-top: 12px }
.loading-text { margin-top: 8px; color:#666 }
.result-message { margin-top: 12px }
.results-wrap { max-width: 1200px; margin: 18px auto }
.metrics-row { margin-top: 12px }
.metric { text-align: center; padding: 12px }
.metric-label { color: #777 }
.metric-value { color: #2196F3; font-weight: 600; margin-top: 6px }
</style>
