<template>
  <div class="model-training">
    <!-- 数据统计卡片 -->
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <h3>📊 训练数据统计</h3>
          <el-button size="small" @click="loadDataStats" :loading="loadingStats">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>
      
      <el-row :gutter="20" v-if="dataStats.overall">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ dataStats.overall.total_records || 0 }}</div>
            <div class="stat-label">总记录数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ dataStats.overall.total_students || 0 }}</div>
            <div class="stat-label">学生数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ dataStats.overall.total_courses || 0 }}</div>
            <div class="stat-label">课程数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">{{ (dataStats.overall.avg_score || 0).toFixed(2) }}</div>
            <div class="stat-label">平均分</div>
          </div>
        </el-col>
      </el-row>
    </el-card>

    <!-- 训练配置卡片 -->
    <el-card class="config-card">
      <template #header>
        <div class="card-header">
          <h3>⚙️ 训练配置</h3>
        </div>
      </template>

      <el-form :model="trainConfig" label-width="120px">
        <el-form-item label="目标列">
          <el-select v-model="trainConfig.targetColumn" placeholder="选择预测目标">
            <el-option label="总分 (total_score)" value="total_score" />
            <el-option label="期末成绩 (final_score)" value="final_score" />
            <el-option label="期中成绩 (midterm_score)" value="midterm_score" />
          </el-select>
        </el-form-item>

        <el-form-item label="测试集比例">
          <el-slider v-model="trainConfig.testSize" :min="10" :max="40" :step="5" show-stops />
          <span class="slider-label">{{ trainConfig.testSize }}%</span>
        </el-form-item>

        <el-form-item label="数据源">
          <el-radio-group v-model="trainConfig.dataSource">
            <el-radio label="database">数据库</el-radio>
            <el-radio label="upload" disabled>上传文件</el-radio>
          </el-radio-group>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" @click="startTraining" :loading="training" size="large">
            <el-icon><VideoPlay /></el-icon>
            开始训练
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="training" class="training-progress">
        <el-progress :percentage="progress" :status="progress === 100 ? 'success' : ''" />
        <p class="progress-text">{{ progressText }}</p>
      </div>
    </el-card>

    <!-- 训练结果卡片 -->
    <el-card v-if="trainResult && trainResult.metrics" class="result-card">
      <template #header>
        <div class="card-header">
          <h3>📈 训练结果</h3>
        </div>
      </template>

      <el-row :gutter="20">
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-name">R² 分数</div>
            <div class="metric-value" :class="getR2Class(trainResult.metrics.r2)">
              {{ (trainResult.metrics.r2 * 100).toFixed(2) }}%
            </div>
            <div class="metric-desc">模型拟合优度</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-name">平均绝对误差 (MAE)</div>
            <div class="metric-value">{{ trainResult.metrics.mae.toFixed(2) }}</div>
            <div class="metric-desc">预测误差</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-name">均方根误差 (RMSE)</div>
            <div class="metric-value">{{ trainResult.metrics.rmse.toFixed(2) }}</div>
            <div class="metric-desc">预测偏差</div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <h4>🏆 模型对比结果</h4>
      <el-table :data="processedModelResults" style="width: 100%; margin-top: 16px">
        <el-table-column prop="model_name" label="模型名称" width="200" />
        <el-table-column prop="r2_score" label="R² 分数" width="150">
          <template #default="scope">
            <el-tag :type="scope.row.r2_score > 0.8 ? 'success' : scope.row.r2_score > 0.6 ? '' : 'warning'">
              {{ (Number(scope.row.r2_score || 0) * 100).toFixed(2) }}%
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="mae" label="平均绝对误差">
          <template #default="scope">
            {{ formatNumber(scope.row.mae) }}
          </template>
        </el-table-column>
        <el-table-column prop="rmse" label="均方根误差">
          <template #default="scope">
            {{ formatNumber(scope.row.rmse) }}
          </template>
        </el-table-column>
        <el-table-column prop="is_best" label="最佳模型" width="100">
          <template #default="scope">
            <el-icon v-if="scope.row.is_best" color="#67C23A" :size="20"><CircleCheck /></el-icon>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

  <h4>🔍 特征重要性（前十）</h4>
      <div v-if="trainResult.feature_importance && trainResult.feature_importance.length > 0" class="feature-importance">
        <div v-for="(item, index) in trainResult.feature_importance" :key="index" class="feature-item">
          <div class="feature-name">{{ item.feature }}</div>
          <div class="feature-bar-container">
            <div class="feature-bar" :style="{ width: (item.importance * 100) + '%' }"></div>
          </div>
          <div class="feature-value">{{ (item.importance * 100).toFixed(1) }}%</div>
        </div>
      </div>

      <el-divider />

      <h4>📊 可视化结果</h4>
      <el-row :gutter="20">
        <el-col :span="12" v-if="trainResult.visualizations.prediction_scatter">
          <div class="viz-container">
            <h5>预测值对比实际值</h5>
            <img :src="'data:image/png;base64,' + trainResult.visualizations.prediction_scatter" alt="预测散点图" />
          </div>
        </el-col>
        <el-col :span="12" v-if="trainResult.visualizations.feature_importance">
          <div class="viz-container">
            <h5>特征重要性分布</h5>
            <img :src="'data:image/png;base64,' + trainResult.visualizations.feature_importance" alt="特征重要性" />
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <div class="training-info">
        <p><strong>训练样本数：</strong> {{ trainResult.training_samples }}</p>
        <p><strong>目标列：</strong> {{ trainResult.target_column }}</p>
        <p><strong>模型文件：</strong> {{ trainResult.model_file }}</p>
      </div>
    </el-card>
  </div>
</template>

<script>
import axios from 'axios'
import { Refresh, VideoPlay, CircleCheck } from '@element-plus/icons-vue'

export default {
  name: 'ModelTraining',
  components: { Refresh, VideoPlay, CircleCheck },
  data() {
    return {
      training: false,
      progress: 0,
      progressText: '准备训练...',
      loadingStats: false,
      dataStats: {
        overall: null,
        by_semester: []
      },
      trainConfig: {
        targetColumn: 'total_score',
        testSize: 20,
        dataSource: 'database'
      },
      trainResult: {
        metrics: null,
        model_results: [],
        feature_importance: [],
        visualizations: {},
        training_samples: 0,
        target_column: '',
        model_file: ''
      }
    }
  },
  mounted() {
    this.loadDataStats()
  },
  methods: {
    formatNumber(val) {
      const num = Number(val)
      return Number.isFinite(num) ? num.toFixed(2) : '-'
    },
    async loadDataStats() {
      try {
        this.loadingStats = true
        const response = await axios.get('/api/training/data-stats')
        if (response.data.status === 'success') {
          this.dataStats = response.data.data
        }
      } catch (error) {
        console.error('加载数据统计失败:', error)
        this.$message.error('加载数据统计失败')
      } finally {
        this.loadingStats = false
      }
    },

    async startTraining() {
      try {
        this.training = true
        this.progress = 0
        this.progressText = '正在从数据库加载训练数据...'
        // 重置训练结果
        this.trainResult = {
          metrics: null,
          model_results: [],
          feature_importance: [],
          visualizations: {},
          training_samples: 0,
          target_column: '',
          model_file: ''
        }

        // 模拟进度更新
        const progressInterval = setInterval(() => {
          if (this.progress < 90) {
            this.progress += 10
            if (this.progress === 30) {
              this.progressText = '数据预处理中...'
            } else if (this.progress === 50) {
              this.progressText = '模型训练中...'
            } else if (this.progress === 70) {
              this.progressText = '评估模型性能...'
            } else if (this.progress === 90) {
              this.progressText = '生成训练报告...'
            }
          }
        }, 500)

        const response = await axios.post('/api/training/train', {
          targetColumn: this.trainConfig.targetColumn,
          testSize: this.trainConfig.testSize / 100,
          dataSource: this.trainConfig.dataSource
        })

        clearInterval(progressInterval)

        if (response.data.status === 'success') {
          this.progress = 100
          this.progressText = '训练完成！'
          this.trainResult = response.data.data
          this.$message.success('模型训练完成！')
        } else {
          this.$message.error(response.data.message || '训练失败')
        }
      } catch (error) {
        console.error('训练失败:', error)
        this.$message.error(error.response?.data?.message || '训练失败，请检查后端服务')
      } finally {
        this.training = false
      }
    },

    getR2Class(r2) {
      if (r2 >= 0.8) return 'excellent'
      if (r2 >= 0.6) return 'good'
      return 'fair'
    }
  },
  computed: {
    processedModelResults() {
      const raw = this.trainResult && this.trainResult.model_results
      if (!raw) return []

      // 如果后端返回的是数组且结构已符合预期，直接返回
      if (Array.isArray(raw)) {
        // 补齐必要字段，避免模板渲染时报错
        const arr = raw.map(item => ({
          model_name: item.model_name || item.name || '-',
          r2_score: Number(item.r2_score ?? item.cv_mean ?? 0),
          mae: item.mae,
          rmse: item.rmse,
          is_best: Boolean(item.is_best)
        }))
        // 标记最佳模型（按 r2_score 最大）
        let bestIdx = -1
        let bestVal = -Infinity
        arr.forEach((r, idx) => {
          if (Number(r.r2_score) > bestVal) { bestVal = Number(r.r2_score); bestIdx = idx }
        })
        if (bestIdx >= 0) arr[bestIdx].is_best = true
        return arr
      }

      // 若返回的是对象字典，转换为数组
      const entries = Object.entries(raw).map(([name, res]) => ({
        model_name: name,
        r2_score: Number((res && (res.r2_score ?? res.cv_mean)) || 0),
        mae: res && res.mae,
        rmse: res && res.rmse,
        is_best: false
      }))
      // 标记最佳模型
      let bestIdx = -1
      let bestVal = -Infinity
      entries.forEach((r, idx) => {
        if (Number(r.r2_score) > bestVal) { bestVal = Number(r.r2_score); bestIdx = idx }
      })
      if (bestIdx >= 0) entries[bestIdx].is_best = true
      return entries
    }
  }
}
</script>

<style scoped>
.model-training {
  padding: 20px;
}

.stats-card,
.config-card,
.result-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-header h3 {
  margin: 0;
  font-size: 18px;
  font-weight: 600;
}

/* 统计项 */
.stat-item {
  text-align: center;
  padding: 20px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}

.stat-value {
  font-size: 32px;
  font-weight: bold;
  margin-bottom: 8px;
}

.stat-label {
  font-size: 14px;
  opacity: 0.9;
}

/* 训练进度 */
.training-progress {
  margin-top: 24px;
  padding: 20px;
  background: #f5f7fa;
  border-radius: 8px;
}

.progress-text {
  text-align: center;
  margin-top: 12px;
  color: #606266;
  font-size: 14px;
}

.slider-label {
  margin-left: 12px;
  color: #409eff;
  font-weight: bold;
}

/* 指标卡片 */
.metric-card {
  text-align: center;
  padding: 24px;
  background: #fff;
  border: 1px solid #ebeef5;
  border-radius: 12px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.05);
}

.metric-name {
  font-size: 14px;
  color: #909399;
  margin-bottom: 12px;
}

.metric-value {
  font-size: 36px;
  font-weight: bold;
  color: #409eff;
  margin-bottom: 8px;
}

.metric-value.excellent {
  color: #67c23a;
}

.metric-value.good {
  color: #409eff;
}

.metric-value.fair {
  color: #e6a23c;
}

.metric-desc {
  font-size: 12px;
  color: #c0c4cc;
}

/* 特征重要性 */
.feature-importance {
  margin-top: 16px;
}

.feature-item {
  display: flex;
  align-items: center;
  margin-bottom: 12px;
}

.feature-name {
  width: 200px;
  font-size: 14px;
  color: #606266;
}

.feature-bar-container {
  flex: 1;
  height: 24px;
  background: #f5f7fa;
  border-radius: 12px;
  overflow: hidden;
  margin: 0 12px;
}

.feature-bar {
  height: 100%;
  background: linear-gradient(90deg, #409eff 0%, #67c23a 100%);
  border-radius: 12px;
  transition: width 0.3s ease;
}

.feature-value {
  width: 60px;
  text-align: right;
  font-weight: bold;
  color: #409eff;
}

/* 可视化容器 */
.viz-container {
  margin-bottom: 20px;
}

.viz-container h5 {
  margin-bottom: 12px;
  color: #303133;
}

.viz-container img {
  width: 100%;
  border-radius: 8px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.1);
}

/* 训练信息 */
.training-info {
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
}

.training-info p {
  margin: 8px 0;
  color: #606266;
}
</style>
