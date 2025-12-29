<template>
  <div class="model-training">
    <!-- 数据统计卡片 -->
    <el-card class="stats-card">
      <template #header>
        <div class="card-header">
          <h3>📊 训练数据统计</h3>
          <el-button
            size="small"
            :loading="loadingStats"
            @click="loadDataStats"
          >
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-row v-if="dataStats.overall" :gutter="20">
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{ dataStats.overall.total_records || 0 }}
            </div>
            <div class="stat-label">总记录数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{
                dataStats.overall.total_students_all ||
                dataStats.overall.total_students ||
                0
              }}
            </div>
            <div class="stat-label">学生数</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <div class="stat-value">
              {{ (dataStats.overall.max_score || 0).toFixed(2) }}
            </div>
            <div class="stat-label">最高分</div>
          </div>
        </el-col>
        <el-col :span="6">
          <div class="stat-item">
            <!-- 优先显示高数平均分字段 calculus_avg_score，若后端仅提供 avg_score 则回退 -->
            <div class="stat-value">
              {{
                (
                  (dataStats.overall.calculus_avg_score ??
                    dataStats.overall.avg_score) ||
                  0
                ).toFixed(2)
              }}
            </div>
            <div class="stat-label">高数平均分</div>
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
        <el-form-item label="数据表">
          <el-select
            v-model="trainConfig.table"
            placeholder="选择数据源"
            style="width: 260px"
          >
            <el-option
              v-for="t in availableTables"
              :key="t"
              :label="getTableLabel(t)"
              :value="t"
            >
              <span style="float: left">{{ getTableLabel(t) }}</span>
            </el-option>
          </el-select>
        </el-form-item>
        <el-form-item label="目标列">
          <el-select
            v-model="trainConfig.targetColumn"
            placeholder="请选择（必选）"
            style="width: 300px"
            clearable
          >
            <el-option
              v-for="col in targetColumnOptions"
              :key="col"
              :label="translateColumnName(col)"
              :value="col"
            />
          </el-select>
          <template #error>
            <span v-if="!targetColumnOptions.length" style="color: #f56c6c"
              >当前表未检测到“高数第一次/第二次/第三次/平均”四列，请选择“大学成绩表”或检查表结构。</span
            >
          </template>
        </el-form-item>
        <div
          v-if="!targetColumnOptions.length"
          style="margin: -10px 0 10px 120px"
        >
          <el-alert
            type="warning"
            :closable="false"
            show-icon
            title="未找到可选目标列"
          >
            <template #description>
              请切换数据表为“university_grades”（大学成绩），或确保存在以下任一列：高数第一次/高数第二次/高数第三次/高数平均。
            </template>
          </el-alert>
        </div>

        <el-form-item label="测试集比例">
          <el-slider
            v-model="trainConfig.testSize"
            :min="10"
            :max="40"
            :step="5"
            show-stops
          />
          <span class="slider-label">{{ trainConfig.testSize }}%</span>
        </el-form-item>

        <el-form-item>
          <el-button
            type="primary"
            :disabled="!canStartTrain"
            :loading="training"
            size="large"
            @click="startTraining"
          >
            <el-icon><VideoPlay /></el-icon>
            开始训练与评估
          </el-button>
        </el-form-item>
      </el-form>

      <div v-if="training" class="training-progress">
        <el-progress
          :percentage="progress"
          :status="progress === 100 ? 'success' : ''"
        />
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
            <div
              class="metric-value"
              :class="getR2Class(trainResult.metrics.r2)"
            >
              {{ (trainResult.metrics.r2 * 100).toFixed(2) }}%
            </div>
            <div class="metric-desc">模型拟合优度</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-name">平均绝对误差 (MAE)</div>
            <div class="metric-value">
              {{ trainResult.metrics.mae.toFixed(2) }}
            </div>
            <div class="metric-desc">预测误差</div>
          </div>
        </el-col>
        <el-col :span="8">
          <div class="metric-card">
            <div class="metric-name">均方根误差 (RMSE)</div>
            <div class="metric-value">
              {{ trainResult.metrics.rmse.toFixed(2) }}
            </div>
            <div class="metric-desc">预测偏差</div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <h4>🏆 模型对比结果</h4>
      <el-table
        :data="processedModelResults"
        style="width: 100%; margin-top: 16px"
      >
        <el-table-column prop="model_name" label="模型名称" width="200" />
        <el-table-column prop="r2_score" label="R² 分数" width="150">
          <template #default="scope">
            <el-tag
              :type="
                scope.row.r2_score > 0.8
                  ? 'success'
                  : scope.row.r2_score > 0.6
                    ? ''
                    : 'warning'
              "
            >
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
            <el-icon v-if="scope.row.is_best" color="#67C23A" :size="20"
              ><CircleCheck
            /></el-icon>
          </template>
        </el-table-column>
      </el-table>

      <el-divider />

      <h4>🔍 特征重要性（前十）</h4>
      <div
        v-if="
          trainResult.feature_importance &&
          trainResult.feature_importance.length > 0
        "
        class="feature-importance"
      >
        <div
          v-for="(item, index) in trainResult.feature_importance"
          :key="index"
          class="feature-item"
        >
          <div class="feature-name">{{ item.feature }}</div>
          <div class="feature-bar-container">
            <div
              class="feature-bar"
              :style="{ width: item.importance * 100 + '%' }"
            ></div>
          </div>
          <div class="feature-value">
            {{ (item.importance * 100).toFixed(1) }}%
          </div>
        </div>
      </div>

      <el-divider />

      <h4>📊 可视化结果</h4>
      <el-row :gutter="20" style="margin-top: 12px">
        <el-col :span="12">
          <div class="viz-container">
            <h5>残差直方图（预测-实际）</h5>
            <div ref="trainResidual" class="chart-container small"></div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="viz-container">
            <h5>校准曲线（分位分箱）</h5>
            <div ref="trainCalibration" class="chart-container small"></div>
          </div>
        </el-col>
      </el-row>

      <el-row :gutter="20" style="margin-top: 12px">
        <el-col :span="12">
          <div class="viz-container">
            <h5>分数段热力图（预测×实际）</h5>
            <div ref="trainHeatmap" class="chart-container small"></div>
          </div>
        </el-col>
        <el-col :span="12">
          <div class="viz-container">
            <h5>按年级的MAE</h5>
            <div ref="trainErrorGrade" class="chart-container small"></div>
          </div>
        </el-col>
      </el-row>

      <el-divider />

      <div class="training-info">
        <p>
          <strong>训练样本数：</strong>
          {{ trainResult.training_samples || "-" }}
        </p>
        <p><strong>目标列：</strong> {{ trainResult.target_column }}</p>
        <p v-if="trainResult.model_file">
          <strong>模型文件：</strong> {{ trainResult.model_file }}
        </p>
        <p><strong>数据表：</strong> {{ getTableLabel(trainConfig.table) }}</p>
      </div>
    </el-card>
  </div>
</template>

<script>
import * as echarts from "echarts";
import axios from "axios";
import { Refresh, VideoPlay, CircleCheck } from "@element-plus/icons-vue";

export default {
  name: "ModelTraining",
  components: { Refresh, VideoPlay, CircleCheck },
  data() {
    return {
      training: false,
      progress: 0,
      progressText: "准备训练...",
      loadingStats: false,
      dataStats: {
        overall: null,
        by_semester: [],
      },
      availableTables: [],
      targetOptions: {
        columns: [],
        numeric_columns: [],
        recommended_targets: [],
      },
      trainConfig: {
        table: "",
        targetColumn: "",
        testSize: 20,
      },
      trainResult: {
        metrics: null,
        model_results: [],
        feature_importance: [],
        preview: [],
        training_samples: 0,
        target_column: "",
        model_file: "",
      },
      charts: {
        predScatter: null,
        fiBar: null,
        residual: null,
        calibration: null,
        heatmap: null,
        errorGrade: null,
      },
      // Resize 节流控制
      _resizeRaf: null,
      _resizeBusy: false,
      _chartSizes: {},
    };
  },
  computed: {
    canStartTrain() {
      return (
        Boolean(this.trainConfig.table) &&
        Boolean(this.trainConfig.targetColumn)
      );
    },
    targetColumnOptions() {
      // 仅允许四个高数相关目标列（若存在），否则回退为自动识别
      const allowed = [
        "first_calculus_score",
        "second_calculus_score",
        "third_calculus_score",
        "calculus_avg_score",
      ];
      const cols = Array.isArray(this.targetOptions.columns)
        ? this.targetOptions.columns
        : [];
      const exists = allowed.filter((c) => cols.includes(c));
      return exists;
    },
    processedModelResults() {
      const raw = this.trainResult && this.trainResult.model_results;
      if (!raw) return [];

      // 如果后端返回的是数组且结构已符合预期，直接返回
      if (Array.isArray(raw)) {
        // 补齐必要字段，避免模板渲染时报错
        const arr = raw.map((item) => ({
          model_name: item.model_name || item.name || "-",
          r2_score: Number(item.r2_score ?? item.cv_mean ?? 0),
          mae: item.mae,
          rmse: item.rmse,
          is_best: Boolean(item.is_best),
        }));
        // 标记最佳模型（按 r2_score 最大）
        let bestIdx = -1;
        let bestVal = -Infinity;
        arr.forEach((r, idx) => {
          if (Number(r.r2_score) > bestVal) {
            bestVal = Number(r.r2_score);
            bestIdx = idx;
          }
        });
        if (bestIdx >= 0) arr[bestIdx].is_best = true;
        return arr;
      }

      // 若返回的是对象字典，转换为数组
      const entries = Object.entries(raw).map(([name, res]) => ({
        model_name: name,
        r2_score: Number((res && (res.r2_score ?? res.cv_mean)) || 0),
        mae: res && res.mae,
        rmse: res && res.rmse,
        is_best: false,
      }));
      // 标记最佳模型
      let bestIdx = -1;
      let bestVal = -Infinity;
      entries.forEach((r, idx) => {
        if (Number(r.r2_score) > bestVal) {
          bestVal = Number(r.r2_score);
          bestIdx = idx;
        }
      });
      if (bestIdx >= 0) entries[bestIdx].is_best = true;
      return entries;
    },
  },
  watch: {
    "trainConfig.table"(val) {
      // 表切换时刷新可选目标列并清空已选
      this.trainConfig.targetColumn = "";
      this.fetchTargetColumns();
    },
  },
  mounted() {
    this.loadDataStats();
    this.loadTables();
    // 监听窗口尺寸变化，避免图表初始空白或拉伸异常
    window.addEventListener("resize", this.handleResize);
  },
  beforeUnmount() {
    window.removeEventListener("resize", this.handleResize);
    try {
      Object.values(this.charts).forEach(
        (ch) => ch && ch.dispose && ch.dispose(),
      );
    } catch (e) {}
  },
  methods: {
    handleResize() {
      if (this._resizeRaf) {
        cancelAnimationFrame(this._resizeRaf);
        this._resizeRaf = null;
      }
      this._resizeRaf = requestAnimationFrame(() => {
        if (this._resizeBusy) return;
        this._resizeBusy = true;
        try {
          Object.entries(this.charts).forEach(([key, ch]) => {
            if (ch && ch.getDom) {
              const dom = ch.getDom();
              if (dom) {
                const w = dom.clientWidth || 0;
                const h = dom.clientHeight || 0;
                if (w > 0 && h > 0) {
                  const last = this._chartSizes[key] || { w: -1, h: -1 };
                  if (Math.abs(w - last.w) > 1 || Math.abs(h - last.h) > 1) {
                    try {
                      ch.resize();
                    } catch (e) {}
                    this._chartSizes[key] = { w, h };
                  }
                }
              }
            }
          });
        } catch (e) {
          // 忽略非致命错误
        } finally {
          setTimeout(() => {
            this._resizeBusy = false;
          }, 120);
        }
      });
    },
    async fetchTargetColumns() {
      try {
        if (!this.trainConfig.table) {
          this.targetOptions = {
            columns: [],
            numeric_columns: [],
            recommended_targets: [],
          };
          return;
        }
        const res = await axios.get("/api/analysis/columns", {
          params: { table: this.trainConfig.table },
        });
        if (res.data?.status === "success") {
          this.targetOptions = {
            columns: res.data.columns || [],
            numeric_columns: res.data.numeric_columns || [],
            recommended_targets: res.data.recommended_targets || [],
          };
          // 将目标列限定为四个高数相关字段（若存在）
          const allowed = [
            "first_calculus_score",
            "second_calculus_score",
            "third_calculus_score",
            "calculus_avg_score",
          ];
          const exists = allowed.filter((c) =>
            this.targetOptions.columns.includes(c),
          );
          if (exists.length) {
            this.targetOptions.recommended_targets = exists;
          }
          // 若当前选择的目标列不在候选中，则置空以使用自动识别
          if (
            this.trainConfig.targetColumn &&
            !this.targetOptions.columns.includes(this.trainConfig.targetColumn)
          ) {
            this.trainConfig.targetColumn = "";
          }
        }
      } catch (e) {
        console.warn("加载列信息失败:", e);
      }
    },
    async loadTables() {
      try {
        // 优先使用按列名识别的成绩表，兼容上传的“1”等文件名；保留 students
        const [gradeRes, allRes] = await Promise.allSettled([
          axios.get("/api/analysis/grade-tables"),
          axios.get("/api/analysis/tables"),
        ]);
        let gradeTables = [];
        if (
          gradeRes.status === "fulfilled" &&
          gradeRes.value?.data?.status === "success"
        ) {
          gradeTables = gradeRes.value.data.tables || [];
        }
        let allTables = [];
        if (
          allRes.status === "fulfilled" &&
          allRes.value?.data?.status === "success"
        ) {
          allTables = allRes.value.data.tables || [];
        }
        const set = new Set(gradeTables);
        if (allTables.includes("students")) set.add("students");
        this.availableTables = Array.from(set);
        // 默认：优先 university_grades 其次其它成绩表，再 students
        if (
          !this.trainConfig.table ||
          !this.availableTables.includes(this.trainConfig.table)
        ) {
          if (this.availableTables.includes("university_grades"))
            this.trainConfig.table = "university_grades";
          else if (gradeTables.length > 0)
            this.trainConfig.table = gradeTables[0];
          else if (this.availableTables.includes("students"))
            this.trainConfig.table = "students";
          else if (this.availableTables.length > 0)
            this.trainConfig.table = this.availableTables[0];
        }
        await this.fetchTargetColumns();
      } catch (err) {
        console.error("加载表列表失败:", err);
      }
    },
    formatNumber(val) {
      const num = Number(val);
      return Number.isFinite(num) ? num.toFixed(2) : "-";
    },
    async loadDataStats() {
      try {
        this.loadingStats = true;
        const response = await axios.get("/api/training/data-stats");
        if (response.data.status === "success") {
          this.dataStats = response.data.data;
        }
      } catch (error) {
        console.error("加载数据统计失败:", error);
        this.$message.error("加载数据统计失败");
      } finally {
        this.loadingStats = false;
      }
    },

    async startTraining() {
      try {
        this.training = true;
        this.progress = 0;
        this.progressText = "正在加载数据并预处理...";
        // 重置训练结果
        this.trainResult = {
          metrics: null,
          model_results: [],
          feature_importance: [],
          preview: [],
          training_samples: 0,
          target_column: "",
          model_file: "",
        };

        // 模拟进度更新
        const progressInterval = setInterval(() => {
          if (this.progress < 90) {
            this.progress += 10;
            if (this.progress === 30) {
              this.progressText = "特征工程/编码中...";
            } else if (this.progress === 50) {
              this.progressText = "模型训练中...";
            } else if (this.progress === 70) {
              this.progressText = "评估模型性能...";
            } else if (this.progress === 90) {
              this.progressText = "生成训练报告...";
            }
          }
        }, 500);

        if (!this.trainConfig.table) {
          clearInterval(progressInterval);
          this.$message.error("请先选择数据表");
          this.training = false;
          return;
        }
        if (!this.trainConfig.targetColumn) {
          clearInterval(progressInterval);
          this.$message.error("请选择目标列（必选）");
          this.training = false;
          return;
        }

        const payload = {
          table: this.trainConfig.table,
          testSize: this.trainConfig.testSize / 100,
          targetColumn: this.trainConfig.targetColumn,
        };

        const response = await axios.post(
          "/api/training/predict-table",
          payload,
        );

        clearInterval(progressInterval);

        if (response.data.status === "success") {
          this.progress = 100;
          this.progressText = "训练完成！";
          this.trainResult = response.data.data || {};
          // 确保 DOM 已渲染后再初始化图表
          this.$nextTick(() => {
            this.renderTrainingCharts();
            // 渲染后再触发一次 resize，避免首屏尺寸计算不准
            setTimeout(() => {
              try {
                Object.values(this.charts).forEach(
                  (ch) => ch && ch.resize && ch.resize(),
                );
              } catch (e) {}
            }, 50);
          });
          this.$message.success("模型训练完成！");
        } else {
          this.$message.error(response.data.message || "训练失败");
        }
      } catch (error) {
        console.error("训练失败:", error);
        this.$message.error(
          error.response?.data?.message || "训练失败，请检查后端服务",
        );
      } finally {
        this.training = false;
      }
    },

    getR2Class(r2) {
      if (r2 >= 0.8) return "excellent";
      if (r2 >= 0.6) return "good";
      return "fair";
    },

    renderTrainingCharts() {
      // 预测散点图（仅绘制有实际值的样本）
      try {
        const container1 = this.$refs.trainPredScatter;
        if (container1) {
          if (!this.charts.predScatter)
            this.charts.predScatter = echarts.init(container1);
          const pts = (this.trainResult.preview || [])
            .filter((r) => r && r.actual !== null && r.actual !== undefined)
            .map((r) => [Number(r.actual), Number(r.predicted)]);
          const option1 = {
            tooltip: {
              trigger: "item",
              formatter: (p) =>
                `实际: ${p.value[0].toFixed(2)}<br/>预测: ${p.value[1].toFixed(2)}`,
            },
            xAxis: { name: "实际" },
            yAxis: { name: "预测" },
            series: [
              {
                type: "scatter",
                data: pts,
                symbolSize: 8,
                itemStyle: { color: "#409EFF" },
              },
            ],
          };
          this.charts.predScatter.setOption(option1, true);
        }
      } catch (e) {
        console.warn("渲染预测散点图失败", e);
      }

      // 特征重要性条形图
      try {
        const container2 = this.$refs.trainFiBar;
        if (container2) {
          if (!this.charts.fiBar) this.charts.fiBar = echarts.init(container2);
          const fi = this.trainResult.feature_importance || [];
          const labels = fi.map((x) => x.feature);
          const vals = fi.map((x) => Number(x.importance));
          const option2 = {
            tooltip: { trigger: "axis" },
            xAxis: { type: "value" },
            yAxis: { type: "category", data: labels, inverse: true },
            series: [
              { type: "bar", data: vals, itemStyle: { color: "#67C23A" } },
            ],
          };
          this.charts.fiBar.setOption(option2, true);
        }
      } catch (e) {
        console.warn("渲染特征重要性失败", e);
      }

      // 残差直方图
      try {
        const c = this.$refs.trainResidual;
        const vis = this.trainResult.visualizations || {};
        const residuals = Array.isArray(vis.residuals) ? vis.residuals : [];
        if (c) {
          if (!this.charts.residual) this.charts.residual = echarts.init(c);
          if (residuals.length) {
            const min = Math.min(...residuals),
              max = Math.max(...residuals);
            const bins = 20;
            const step = (max - min) / bins || 1;
            const edges = Array.from(
              { length: bins + 1 },
              (_, i) => min + i * step,
            );
            const counts = new Array(bins).fill(0);
            for (const v of residuals) {
              let idx = Math.floor((v - min) / step);
              if (idx < 0) idx = 0;
              if (idx >= bins) idx = bins - 1;
              counts[idx]++;
            }
            const labels = counts.map(
              (_, i) => `${edges[i].toFixed(1)}~${edges[i + 1].toFixed(1)}`,
            );
            const option = {
              tooltip: { trigger: "axis" },
              xAxis: {
                type: "category",
                data: labels,
                axisLabel: { rotate: 40 },
              },
              yAxis: { type: "value", name: "频数" },
              series: [
                { type: "bar", data: counts, itemStyle: { color: "#909399" } },
              ],
            };
            this.charts.residual.setOption(option, true);
          } else {
            this.charts.residual.setOption(
              {
                title: {
                  text: "暂无数据",
                  left: "center",
                  top: "middle",
                  textStyle: { color: "#909399" },
                },
                xAxis: { show: false },
                yAxis: { show: false },
                series: [],
              },
              true,
            );
          }
        }
      } catch (e) {
        console.warn("渲染残差直方图失败", e);
      }

      // 校准曲线
      try {
        const c = this.$refs.trainCalibration;
        const calib =
          (this.trainResult.visualizations &&
            this.trainResult.visualizations.calibration) ||
          null;
        if (c) {
          if (!this.charts.calibration)
            this.charts.calibration = echarts.init(c);
          if (calib && Array.isArray(calib.centers) && calib.centers.length) {
            const option = {
              tooltip: { trigger: "axis" },
              legend: { top: 10, data: ["平均预测", "平均实际"] },
              xAxis: { type: "value", name: "预测分箱中心" },
              yAxis: { type: "value", name: "分数" },
              series: [
                {
                  name: "平均预测",
                  type: "line",
                  data: (calib.centers || []).map((x, i) => [
                    x,
                    calib.avg_pred[i],
                  ]),
                },
                {
                  name: "平均实际",
                  type: "line",
                  data: (calib.centers || []).map((x, i) => [
                    x,
                    calib.avg_actual[i],
                  ]),
                },
              ],
            };
            this.charts.calibration.setOption(option, true);
          } else {
            this.charts.calibration.setOption(
              {
                title: {
                  text: "暂无数据",
                  left: "center",
                  top: "middle",
                  textStyle: { color: "#909399" },
                },
                xAxis: {},
                yAxis: {},
                series: [],
              },
              true,
            );
          }
        }
      } catch (e) {
        console.warn("渲染校准曲线失败", e);
      }

      // 分数段热力图
      try {
        const c = this.$refs.trainHeatmap;
        const bh =
          (this.trainResult.visualizations &&
            this.trainResult.visualizations.band_heatmap) ||
          null;
        if (c) {
          if (!this.charts.heatmap) this.charts.heatmap = echarts.init(c);
          if (
            bh &&
            Array.isArray(bh.labels) &&
            Array.isArray(bh.values) &&
            bh.values.length
          ) {
            const option = {
              tooltip: {
                position: "top",
                formatter: (p) =>
                  `${bh.labels[p.data[0]]} × ${bh.labels[p.data[1]]}: ${p.data[2]}`,
              },
              grid: { left: "10%", right: "8%", top: "10%", bottom: "12%" },
              xAxis: { type: "category", data: bh.labels, name: "预测段" },
              yAxis: { type: "category", data: bh.labels, name: "实际段" },
              visualMap: {
                min: 0,
                max: Math.max(1, ...bh.values.map((v) => v[2])),
                orient: "horizontal",
                left: "center",
                bottom: 0,
              },
              series: [
                { type: "heatmap", data: bh.values, label: { show: true } },
              ],
            };
            this.charts.heatmap.setOption(option, true);
          } else {
            this.charts.heatmap.setOption(
              {
                title: {
                  text: "暂无数据",
                  left: "center",
                  top: "middle",
                  textStyle: { color: "#909399" },
                },
                xAxis: {},
                yAxis: {},
                series: [],
              },
              true,
            );
          }
        }
      } catch (e) {
        console.warn("渲染热力图失败", e);
      }

      // 按年级MAE
      try {
        const c = this.$refs.trainErrorGrade;
        const eg =
          (this.trainResult.visualizations &&
            this.trainResult.visualizations.error_by_grade) ||
          [];
        if (c) {
          if (!this.charts.errorGrade) this.charts.errorGrade = echarts.init(c);
          if (eg.length) {
            const labels = eg.map((x) => x.name);
            const values = eg.map((x) => Number(x.mae || 0));
            const option = {
              tooltip: { trigger: "axis" },
              xAxis: { type: "category", data: labels },
              yAxis: { type: "value", name: "MAE" },
              series: [
                { type: "bar", data: values, itemStyle: { color: "#E6A23C" } },
              ],
            };
            this.charts.errorGrade.setOption(option, true);
          } else {
            this.charts.errorGrade.setOption(
              {
                title: {
                  text: "暂无数据",
                  left: "center",
                  top: "middle",
                  textStyle: { color: "#909399" },
                },
                xAxis: {},
                yAxis: {},
                series: [],
              },
              true,
            );
          }
        }
      } catch (e) {
        console.warn("渲染按年级MAE失败", e);
      }
    },

    getTableLabel(table) {
      if (!table) return "";
      const s = String(table);
      if ([...s].some((ch) => ch.charCodeAt(0) > 127)) return s;
      // 纯数字或很短的原始名（如“1”、“1_2024”），直接显示原名
      if (/^[0-9._-]+$/.test(s) || s.length <= 3) return s;
      return this.translateTableName(s);
    },
    translateTableName(name) {
      const dict = {
        students: "学生",
        student: "学生",
        exam: "考试",
        exams: "考试",
        score: "成绩",
        scores: "成绩",
        class: "课堂",
        classes: "课堂",
        performance: "表现",
        historical: "历史",
        history: "历史",
        grade: "成绩",
        grades: "成绩",
        course: "课程",
        courses: "课程",
        teacher: "教师",
        teachers: "教师",
        type: "类型",
        types: "类型",
        record: "记录",
        records: "记录",
        upload: "上传",
        data: "数据",
        source: "来源",
        mapping: "映射",
        sync: "同步",
        state: "状态",
        status: "状态",
      };
      const parts = String(name)
        .toLowerCase()
        .split(/[^a-z0-9]+/)
        .filter(Boolean);
      const cn = parts.map((p) => dict[p]).filter(Boolean);
      if (cn.length) return cn.join("") + "表";
      // 默认直接返回原始名称，避免误导
      return String(name);
    },
    translateColumnName(col) {
      const map = {
        total_score: "总成绩",
        final_score: "期末成绩",
        midterm_score: "期中成绩",
        usual_score: "平时成绩",
        score: "分数",
        ranking: "排名",
        calculus_score: "高等数学成绩",
        homework_score: "作业分数",
        first_calculus_score: "高数第一次",
        second_calculus_score: "高数第二次",
        third_calculus_score: "高数第三次",
        calculus_avg_score: "高数平均",
        study_hours: "学习时长",
        attendance_count: "出勤次数",
        practice_count: "刷题数",
      };
      return map[col] || col;
    },
  },
};
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

/* ECharts 容器尺寸（必需） */
.chart-container {
  width: 100%;
  height: 360px;
  contain: layout paint size;
  overflow: hidden;
}
.chart-container.small {
  height: 300px;
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
