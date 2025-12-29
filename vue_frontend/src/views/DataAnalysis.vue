<template>
  <div class="data-analysis">
    <!-- 数据选择区域 -->
    <el-row :gutter="20">
      <el-col :span="24">
        <el-card shadow="hover" class="selection-card">
          <template #header>
            <div class="card-header">
              <span class="header-icon">📊</span>
              <span class="header-title">数据源选择</span>
            </div>
          </template>
          <el-form :model="analysisForm" :inline="true" class="selection-form">
            <el-form-item label="数据表">
              <el-select
                v-model="analysisForm.selectedTable"
                placeholder="请选择数据表"
                style="width: 220px"
                :loading="loadingTables"
                @change="handleTableChange"
              >
                <el-option
                  v-for="table in availableTables"
                  :key="table"
                  :label="getTableDisplayName(table)"
                  :value="table"
                >
                  <span style="float: left">{{
                    getTableDisplayName(table)
                  }}</span>
                </el-option>
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button
                type="primary"
                :loading="loading"
                icon="Refresh"
                @click="refreshData"
              >
                刷新数据
              </el-button>
              <el-button
                icon="Download"
                :loading="loadingExport"
                @click="exportData"
                >导出报告</el-button
              >
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据概览卡片 -->
    <el-row v-if="dataOverview" :gutter="20">
      <el-col :span="6">
        <el-card shadow="hover" class="overview-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: #409eff">📈</div>
            <div class="stat-content">
              <div class="stat-label">数据总量</div>
              <div class="stat-value">{{ dataOverview.totalRecords || 0 }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="overview-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: #67c23a">🎯</div>
            <div class="stat-content">
              <div class="stat-label">数值特征</div>
              <div class="stat-value">
                {{ dataOverview.numericFeatures || 0 }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="overview-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: #e6a23c">📝</div>
            <div class="stat-content">
              <div class="stat-label">分类特征</div>
              <div class="stat-value">
                {{ dataOverview.categoricalFeatures || 0 }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card shadow="hover" class="overview-card">
          <div class="stat-item">
            <div class="stat-icon" style="background: #f56c6c">⚠️</div>
            <div class="stat-content">
              <div class="stat-label">缺失值</div>
              <div class="stat-value">
                {{ dataOverview.missingRate || "0%" }}
              </div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- 数据统计表格 -->
    <el-card v-loading="loading" class="analysis-card statistics-card">
      <template #header>
        <div class="card-header">
          <span class="header-icon">📋</span>
          <span class="header-title">特征统计分析</span>
          <el-tag v-if="statisticsData.length > 0" type="success" size="small">
            共 {{ statisticsData.length }} 个特征
          </el-tag>
        </div>
      </template>
      <el-empty
        v-if="statisticsData.length === 0 && !loading"
        description="暂无统计数据"
      />
      <el-table
        v-else
        :data="statisticsData || []"
        border
        stripe
        style="width: 100%"
        :default-sort="{ prop: 'mean', order: 'descending' }"
      >
        <el-table-column prop="feature" label="特征名称" width="200" fixed>
          <template #default="scope">
            <div>
              <el-tag
                :type="scope.row.type === 'categorical' ? 'warning' : 'primary'"
                size="small"
              >
                {{ scope.row.feature || scope.row.column }}
              </el-tag>
              <el-tag
                v-if="scope.row.type"
                :type="scope.row.type === 'categorical' ? 'success' : 'info'"
                size="mini"
                style="margin-left: 5px"
              >
                {{ scope.row.type === "categorical" ? "分类" : "数值" }}
              </el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="count" label="样本数" width="100" sortable>
          <template #default="scope">
            <span style="color: #409eff; font-weight: bold">{{
              scope.row.count
            }}</span>
          </template>
        </el-table-column>
        <el-table-column label="统计值" width="150" sortable>
          <template #default="scope">
            <div v-if="scope.row.type === 'categorical'">
              <div style="color: #e6a23c; font-size: 12px">
                唯一值: {{ scope.row.unique }}
              </div>
              <div style="color: #67c23a; font-size: 12px">
                最频繁: {{ scope.row.top }}
              </div>
            </div>
            <div v-else>
              <span style="color: #67c23a">平均值: {{ scope.row.mean }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="变异性" width="120" sortable>
          <template #default="scope">
            <div v-if="scope.row.type === 'categorical'">
              <span style="color: #e6a23c; font-size: 12px"
                >频次: {{ scope.row.freq }}</span
              >
            </div>
            <div v-else>
              <span style="color: #e6a23c">{{ scope.row.std }}</span>
            </div>
          </template>
        </el-table-column>
        <el-table-column label="值范围" width="200">
          <template #default="scope">
            <div v-if="scope.row.type === 'categorical'">
              <div
                v-if="scope.row.value_counts"
                style="max-height: 60px; overflow-y: auto"
              >
                <el-tag
                  v-for="(count, value) in Object.entries(
                    scope.row.value_counts,
                  ).slice(0, 3)"
                  :key="value[0]"
                  type="info"
                  size="mini"
                  style="margin: 1px"
                >
                  {{ value[0] }}:{{ value[1] }}
                </el-tag>
                <span
                  v-if="Object.keys(scope.row.value_counts).length > 3"
                  style="color: #999; font-size: 11px"
                  >...</span
                >
              </div>
            </div>
            <div v-else style="display: flex; align-items: center; gap: 5px">
              <el-tag type="info" size="small">{{ scope.row.min }}</el-tag>
              <span style="color: #999">~</span>
              <el-tag type="warning" size="small">{{ scope.row.max }}</el-tag>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="missing" label="缺失率" width="120" sortable>
          <template #default="scope">
            <el-progress
              :percentage="parseFloat(scope.row.missing || 0)"
              :color="getProgressColor(scope.row.missing)"
              :stroke-width="8"
            />
          </template>
        </el-table-column>
        <el-table-column label="数据质量" width="140">
          <template #default="scope">
            <el-tag :type="getQualityTagType(scope.row.missing)" size="small">
              {{ getQualityLabel(scope.row.missing) }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
    </el-card>

    <!-- 相关性分析热力图 -->
    <el-card v-loading="loading" class="analysis-card">
      <template #header>
        <div class="card-header">
          <span class="header-icon">🔥</span>
          <span class="header-title">特征相关性热力图</span>
          <el-tooltip
            content="显示各特征之间的皮尔逊相关系数，范围从-1到1"
            placement="top"
          >
            <el-icon><QuestionFilled /></el-icon>
          </el-tooltip>
        </div>
      </template>
      <el-empty
        v-if="!hasCorrelationData && !loading"
        description="暂无相关性数据，需要至少2个数值特征"
      />
      <div v-else ref="correlationChart" class="chart-container"></div>
    </el-card>
  </div>
</template>

<script>
import * as echarts from "echarts";
import axios from "axios";
import { ElMessage } from "element-plus";

export default {
  name: "DataAnalysis",
  data() {
    return {
      analysisForm: {
        // 默认展示“成绩表”：优先历史成绩表
        selectedTable: "historical_grades",
      },
      availableTables: [],
      statisticsData: [],
      categoricalStatistics: [],
      totalRecords: 0,
      dataOverview: null,
      correlationChart: null,
      loading: false,
      loadingTables: false,
      hasCorrelationData: false,
      tableNameMap: {
        students: "学生信息表",
        historical_grades: "历史成绩表",
        exam_scores: "考试成绩表",
        class_performance: "课堂表现表",
        courses: "课程信息表",
        exam_types: "考试类型表",
        university_grades: "大学成绩表",
      },
      loadingExport: false,
    };
  },
  mounted() {
    this.fetchTables()
      .then(() => {
        // 自动加载默认表的数据
        if (this.analysisForm.selectedTable) {
          this.refreshData();
        }
      })
      .catch((error) => {
        console.error("初始化数据失败:", error);
      });
    this.initCharts();
  },
  beforeUnmount() {
    this.disposeCharts();
  },
  methods: {
    // 获取表的显示名称
    getTableDisplayName(tableName) {
      // 先用内置映射
      if (this.tableNameMap[tableName]) return this.tableNameMap[tableName];
      // 若包含非ASCII（如中文），直接返回（避免在正则中使用控制字符）
      if ([...String(tableName)].some((ch) => ch.charCodeAt(0) > 127)) return tableName;
      // 若为纯数字或混合非字母的短名称（如 "1"、"1_2024"），直接显示原名，避免误显示为“自定义表”
      if (
        /^[0-9._-]+$/.test(String(tableName)) ||
        String(tableName).length <= 3
      )
        return String(tableName);
      // 英文名转中文
      return this.translateTableName(tableName);
    },
    // 英文表名转中文友好名（无英文展示）
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

    // 初始化所有图表
    initCharts() {
      this.$nextTick(() => {
        // 初始化相关性图表
        if (this.$refs.correlationChart && !this.correlationChart) {
          this.correlationChart = echarts.init(this.$refs.correlationChart);
          // 图表初始化
        }

        // 监听窗口大小变化
        window.addEventListener("resize", this.handleResize);
      });
    },

    // 处理窗口大小变化
    handleResize() {
      this.correlationChart?.resize();
    },

    // 销毁所有图表
    disposeCharts() {
      window.removeEventListener("resize", this.handleResize);
      this.correlationChart?.dispose();
    },

    // 获取数据库表列表（优先按列名识别“成绩表”，兼容上传的一次性表名如“1.csv”）
    async fetchTables() {
      this.loadingTables = true;
      const pickDefault = () => {
        if (!this.analysisForm.selectedTable) {
          if (this.availableTables.includes("historical_grades")) {
            this.analysisForm.selectedTable = "historical_grades";
          } else if (this.availableTables.includes("university_grades")) {
            this.analysisForm.selectedTable = "university_grades";
          } else if (this.availableTables.includes("exam_scores")) {
            this.analysisForm.selectedTable = "exam_scores";
          } else if (this.availableTables.includes("class_performance")) {
            this.analysisForm.selectedTable = "class_performance";
          } else if (this.availableTables.length > 0) {
            this.analysisForm.selectedTable = this.availableTables[0];
          }
        }
      };
      try {
        // 先直接询问后端“成绩表”识别结果（无需前端自行解析列）
        const gradeRes = await axios.get("/api/analysis/grade-tables");
        if (gradeRes.data?.status === "success") {
          const tables = gradeRes.data.tables || [];
          if (tables.length > 0) {
            this.availableTables = tables;
            if (!this.availableTables.includes(this.analysisForm.selectedTable))
              this.analysisForm.selectedTable = "";
            pickDefault();
            if (this.analysisForm.selectedTable) this.refreshData();
            this.loadingTables = false;
            return;
          }
          // 若识别为空，不返回，继续尝试 schema 回退
        }
      } catch (_) {
        /* 忽略，继续尝试 schema */
      }
      try {
        // 其次：获取 schema，自行按列名关键词过滤
        const schemaRes = await axios.get("/api/analysis/schema");
        if (schemaRes.data?.status === "success" && schemaRes.data.schema) {
          const schema = schemaRes.data.schema;
          const keywords = [
            "score",
            "grade",
            "gpa",
            "rank",
            "level",
            "分",
            "分数",
            "成绩",
            "等级",
            "排名",
          ];
          const matches = Object.entries(schema)
            .filter(
              ([t, cols]) =>
                Array.isArray(cols) &&
                cols.some((c) =>
                  keywords.some((k) => String(c).toLowerCase().includes(k)),
                ),
            )
            .map(([t]) => t);
          if (matches.length > 0) {
            this.availableTables = matches;
            if (!this.availableTables.includes(this.analysisForm.selectedTable))
              this.analysisForm.selectedTable = "";
            pickDefault();
            if (this.analysisForm.selectedTable) this.refreshData();
            this.loadingTables = false;
            return;
          }
        }
      } catch (_) {
        /* 忽略，继续 tables 回退 */
      }

      try {
        // 最后回退：仅表名启发式
        const response = await axios.get("/api/analysis/tables");
        if (response.data.status === "success") {
          const allTables = response.data.tables || [];
          const isGradeTable = (name) => {
            if (!name) return false;
            const n = String(name).toLowerCase();
            const allowList = new Set([
              "historical_grades",
              "university_grades",
              "exam_scores",
              "class_performance",
            ]);
            if (allowList.has(n)) return true;
            const kw = ["grade", "score", "成绩", "分数", "分", "performance"];
            return kw.some((k) => n.includes(k));
          };
          this.availableTables = (allTables || []).filter(isGradeTable);
          if (!this.availableTables.includes(this.analysisForm.selectedTable))
            this.analysisForm.selectedTable = "";
          pickDefault();
          if (this.analysisForm.selectedTable) this.refreshData();
        } else {
          ElMessage.error(response.data.message || "获取数据表列表失败");
        }
      } catch (error) {
        console.error("获取数据表列表失败:", error);
        ElMessage.error("获取数据表列表失败: " + error.message);
        throw error;
      } finally {
        this.loadingTables = false;
      }
    },

    // 表切换处理
    handleTableChange() {
      if (this.analysisForm.selectedTable) {
        this.refreshData();
      }
    },

    // 刷新所有数据
    refreshData() {
      if (!this.analysisForm.selectedTable) {
        ElMessage.warning("请先选择数据表");
        return;
      }

      this.loading = true;
      Promise.all([
        this.fetchStatistics(),
        this.updateCorrelationChart(),
      ]).finally(() => {
        this.loading = false;
      });
    },

    // 获取统计数据
    fetchStatistics() {
      return axios
        .get(
          `/api/analysis/statistics?table=${this.analysisForm.selectedTable}`,
        )
        .then((response) => {
          if (response.data.status === "success") {
            // 处理数值特征统计
            const numericStats = response.data.numeric_statistics || [];
            // 保存分类特征统计
            this.categoricalStatistics =
              response.data.categorical_statistics || [];
            // 合并数值统计和分类统计
            this.statisticsData = [
              ...numericStats,
              ...this.categoricalStatistics,
            ];
            // 保存总记录数
            this.totalRecords = response.data.total_records || 0;

            this.updateDataOverview();
          } else {
            ElMessage.error(response.data.message || "获取统计数据失败");
            this.statisticsData = [];
            this.categoricalStatistics = [];
          }
        })
        .catch((error) => {
          console.error("获取统计数据失败:", error);
          ElMessage.error("获取统计数据失败：" + error.message);
          this.statisticsData = [];
          this.categoricalStatistics = [];
        });
    },

    // 更新数据概览
    updateDataOverview() {
      const totalRecords =
        this.totalRecords || this.statisticsData[0]?.count || 0;
      const numericFeatures = this.statisticsData.length;
      const categoricalFeatures = this.categoricalStatistics?.length || 0;

      // 计算平均缺失率
      let avgMissingRate = 0;
      if (this.statisticsData.length > 0) {
        avgMissingRate =
          this.statisticsData.reduce((sum, stat) => {
            return sum + parseFloat(stat.missing || 0);
          }, 0) / this.statisticsData.length;
      }

      this.dataOverview = {
        totalRecords,
        numericFeatures,
        categoricalFeatures,
        missingRate: avgMissingRate.toFixed(2) + "%",
      };
    },

    // 更新相关性热力图
    updateCorrelationChart() {
      if (!this.analysisForm.selectedTable) {
        return Promise.resolve();
      }

      return axios
        .get(
          `/api/analysis/correlation?table=${this.analysisForm.selectedTable}`,
        )
        .then((response) => {
          if (response.data.status === "success") {
            const data = response.data.data || [];
            const features = response.data.features || [];

            // 收到相关性数据

            if (data.length === 0 || features.length < 2) {
              this.hasCorrelationData = false;
              if (this.correlationChart) {
                this.correlationChart.clear();
              }
              return;
            }

            this.hasCorrelationData = true;

            // 确保图表已初始化
            this.$nextTick(() => {
              if (!this.correlationChart && this.$refs.correlationChart) {
                this.correlationChart = echarts.init(
                  this.$refs.correlationChart,
                );
              }

              if (!this.correlationChart) {
                console.error("相关性图表初始化失败");
                return;
              }

              const option = {
                tooltip: {
                  position: "top",
                  formatter: function (params) {
                    return `${features[params.data[1]]} - ${features[params.data[0]]}<br/>相关系数: ${params.data[2]}`;
                  },
                },
                grid: {
                  height: "70%",
                  top: "15%",
                  containLabel: true,
                },
                xAxis: {
                  type: "category",
                  data: features,
                  splitArea: {
                    show: true,
                  },
                  axisLabel: {
                    rotate: 45,
                    interval: 0,
                  },
                },
                yAxis: {
                  type: "category",
                  data: features,
                  splitArea: {
                    show: true,
                  },
                },
                visualMap: {
                  min: -1,
                  max: 1,
                  calculable: true,
                  orient: "horizontal",
                  left: "center",
                  bottom: "5%",
                  inRange: {
                    color: [
                      "#313695",
                      "#4575b4",
                      "#74add1",
                      "#abd9e9",
                      "#e0f3f8",
                      "#ffffbf",
                      "#fee090",
                      "#fdae61",
                      "#f46d43",
                      "#d73027",
                      "#a50026",
                    ],
                  },
                  text: ["强正相关", "强负相关"],
                },
                series: [
                  {
                    name: "相关性",
                    type: "heatmap",
                    data: data,
                    label: {
                      show: true,
                      formatter: function (params) {
                        return params.data[2];
                      },
                      fontSize: 10,
                    },
                    emphasis: {
                      itemStyle: {
                        shadowBlur: 10,
                        shadowColor: "rgba(0, 0, 0, 0.5)",
                      },
                    },
                  },
                ],
              };

              // 使用 notMerge=true 强制完整替换，避免前一次配置残留导致缺少 visualMap 时触发
              // “Heatmap must use with visualMap” 错误
              try {
                this.correlationChart.clear();
              } catch (_) {
                // ignore
              }
              this.correlationChart.setOption(option, true);
              // 图表更新完成
            });
          } else {
            this.hasCorrelationData = false;
            ElMessage.error(response.data.message || "获取相关性数据失败");
          }
        })
        .catch((error) => {
          console.error("获取相关性数据失败:", error);
          this.hasCorrelationData = false;
          ElMessage.error("获取相关性数据失败：" + error.message);
        });
    },

    // 导出数据报告（ZIP）
    async exportData() {
      if (!this.analysisForm.selectedTable) {
        ElMessage.warning("请先选择数据表");
        return;
      }
      try {
        this.loadingExport = true;
        const params = { table: this.analysisForm.selectedTable };
        const res = await axios.get("/api/analysis/export-report", {
          params,
          responseType: "blob",
        });
        const blob = new Blob([res.data], { type: "application/zip" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        const label = this.getTableDisplayName(this.analysisForm.selectedTable);
        link.href = url;
        link.download = `${label || this.analysisForm.selectedTable}_分析报告_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success("报告导出成功");
      } catch (err) {
        console.error("导出报告失败:", err);
        ElMessage.error("导出失败，请稍后重试");
      } finally {
        this.loadingExport = false;
      }
    },

    // 获取进度条颜色
    getProgressColor(missing) {
      const value = parseFloat(missing || 0);
      if (value < 5) return "#67C23A";
      if (value < 20) return "#E6A23C";
      return "#F56C6C";
    },

    // 获取质量标签类型
    getQualityTagType(missing) {
      const value = parseFloat(missing || 0);
      if (value < 5) return "success";
      if (value < 20) return "warning";
      return "danger";
    },

    // 获取质量标签文本
    getQualityLabel(missing) {
      const value = parseFloat(missing || 0);
      if (value < 5) return "优秀";
      if (value < 20) return "良好";
      return "需改进";
    },

    // 获取类别标签颜色类型
    getCategoryTagType(index) {
      const types = ["", "success", "info", "warning", "danger"];
      return types[index % types.length];
    },
  },
};
</script>

<style scoped>
.data-analysis {
  padding: 20px;
  background: #f5f7fa;
  min-height: calc(100vh - 60px);
}

/* 选择卡片样式 */
.selection-card {
  margin-bottom: 20px;
  border-radius: 8px;
}

.selection-form {
  display: flex;
  align-items: center;
  gap: 15px;
}

/* 卡片头部样式 */
.card-header {
  display: flex;
  align-items: center;
  gap: 10px;
}

.header-icon {
  font-size: 20px;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

/* 概览卡片样式 */
.overview-card {
  margin-bottom: 20px;
  border-radius: 8px;
  transition: all 0.3s;
}

.overview-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.1);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 15px;
  padding: 10px;
}

.stat-icon {
  width: 60px;
  height: 60px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 28px;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: #909399;
  margin-bottom: 8px;
}

.stat-value {
  font-size: 28px;
  font-weight: bold;
  color: #303133;
}

/* 分析卡片样式 */
.analysis-card {
  margin-bottom: 20px;
  border-radius: 8px;
}

.statistics-card {
  margin-top: 0;
}

/* 图表容器样式 */
.chart-container {
  height: 500px;
  width: 100%;
  padding: 10px;
}

.chart-container.small {
  height: 350px;
}

/* 表格样式优化 */
:deep(.el-table) {
  border-radius: 4px;
}

:deep(.el-table th) {
  background: #f5f7fa;
  color: #606266;
  font-weight: 600;
}

:deep(.el-table td) {
  padding: 12px 0;
}

/* 进度条样式 */
:deep(.el-progress) {
  width: 100%;
}

:deep(.el-progress__text) {
  font-size: 12px !important;
}

/* 标签样式 */
:deep(.el-tag) {
  border-radius: 4px;
}

/* 响应式设计 */
@media (max-width: 1200px) {
  .stat-value {
    font-size: 24px;
  }

  .chart-container {
    height: 400px;
  }

  .chart-container.small {
    height: 300px;
  }
}

@media (max-width: 768px) {
  .data-analysis {
    padding: 10px;
  }

  .selection-form {
    flex-direction: column;
    align-items: stretch;
  }

  .stat-value {
    font-size: 20px;
  }

  .chart-container {
    height: 300px;
  }

  .chart-container.small {
    height: 250px;
  }
}

/* 空状态样式 */
:deep(.el-empty) {
  padding: 60px 0;
}

/* 加载状态 */
:deep(.el-loading-mask) {
  border-radius: 8px;
}

/* 动画效果 */
.analysis-card {
  animation: fadeInUp 0.5s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}
</style>
```
