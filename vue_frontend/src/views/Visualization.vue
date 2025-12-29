<template>
  <div class="visualization">
    <!-- 标签页切换 -->
    <el-tabs
      v-model="activeTab"
      type="card"
      class="visualization-tabs"
      @tab-change="handleTabChange"
    >
      <!-- 图表可视化标签页 -->
      <el-tab-pane label="📊 图表可视化" name="charts">
        <!-- 控制面板（与数据表可视化样式统一） -->
        <el-card class="control-panel" shadow="hover">
          <div class="filter-container">
            <div class="control-item">
              <span class="control-label">成绩表</span>
              <el-select
                v-model="chartDataTable"
                placeholder="选择数据源"
                class="control-input"
                @change="loadChartData"
              >
                <el-option
                  v-for="t in chartTables"
                  :key="t"
                  :label="getTableLabel(t)"
                  :value="t"
                >
                  <span style="float: left">{{ getTableLabel(t) }}</span>
                </el-option>
              </el-select>
            </div>

            <div class="control-item">
              <span class="control-label">按学号/姓名选择</span>
              <el-select
                v-model="studentSelector"
                filterable
                remote
                clearable
                placeholder="输入学号或姓名搜索"
                :remote-method="loadStudentOptions"
                class="control-input"
                @change="onStudentSelectorChange"
                @visible-change="
                  (val) => {
                    if (val && !studentOptions.length) loadStudentOptions();
                  }
                "
              >
                <el-option
                  v-for="stu in studentOptions"
                  :key="stu.student_id"
                  :label="formatStudentOption(stu)"
                  :value="stu.student_id"
                >
                  <span style="float: left">{{
                    formatStudentOption(stu)
                  }}</span>
                </el-option>
              </el-select>
            </div>

            <div class="action-section">
              <div class="action-wrap">
                <el-button
                  type="primary"
                  plain
                  icon="Refresh"
                  @click="loadChartData"
                  >刷新图表</el-button
                >
                <el-button
                  type="success"
                  :loading="loading.exportReport"
                  icon="Download"
                  @click="exportAnalysisReport"
                  >导出报告</el-button
                >
              </div>
            </div>
          </div>
        </el-card>

        <el-row :gutter="20">
          <!-- 学生详情 -->
          <el-col :span="24">
            <el-card v-loading="loading.detail" class="chart-card">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">🧑‍🎓 学生详情</span>
                </div>
              </template>
              <div
                style="
                  display: flex;
                  gap: 20px;
                  flex-wrap: wrap;
                  align-items: flex-start;
                "
              >
                <div style="flex: 1; min-width: 280px">
                  <div v-if="studentDetail.profile" class="detail-profile">
                    <el-descriptions :column="3" size="small" border>
                      <el-descriptions-item label="ID">{{
                        studentDetail.profile.student_id
                      }}</el-descriptions-item>
                      <el-descriptions-item label="学号">{{
                        studentDetail.profile.student_no
                      }}</el-descriptions-item>
                      <el-descriptions-item label="姓名">{{
                        studentDetail.profile.name
                      }}</el-descriptions-item>
                      <el-descriptions-item label="性别">{{
                        studentDetail.profile.gender
                      }}</el-descriptions-item>
                      <el-descriptions-item label="年级">{{
                        studentDetail.profile.grade
                      }}</el-descriptions-item>
                      <el-descriptions-item label="班级">{{
                        studentDetail.profile.class
                      }}</el-descriptions-item>
                      <el-descriptions-item label="电话">{{
                        studentDetail.profile.contact_phone
                      }}</el-descriptions-item>
                      <el-descriptions-item label="邮箱">{{
                        studentDetail.profile.email
                      }}</el-descriptions-item>
                    </el-descriptions>
                  </div>
                  <div v-else class="empty-container">
                    <el-empty description="请选择一个有效的学生ID" />
                  </div>
                  <div
                    v-if="studentDetail.grades"
                    class="detail-grades"
                    style="
                      margin-top: 12px;
                      display: flex;
                      gap: 8px;
                      flex-wrap: wrap;
                    "
                  >
                    <el-tag type="info"
                      >高数平均:
                      {{
                        fmtNum(
                          studentDetail.grades.calculus_avg_score ??
                            studentDetail.grades.total_score ??
                            studentDetail.grades.calculus_score,
                        )
                      }}</el-tag
                    >
                    <el-tag type="success"
                      >第一次:
                      {{
                        fmtNum(
                          studentDetail.grades.first_calculus_score ??
                            studentDetail.grades.calculus_score,
                        )
                      }}</el-tag
                    >
                    <el-tag type="success"
                      >第二次:
                      {{
                        fmtNum(studentDetail.grades.second_calculus_score)
                      }}</el-tag
                    >
                    <el-tag type="success"
                      >第三次:
                      {{
                        fmtNum(studentDetail.grades.third_calculus_score)
                      }}</el-tag
                    >
                    <el-tag
                      >学习时长:
                      {{ fmtNum(studentDetail.grades.study_hours) }}</el-tag
                    >
                    <el-tag type="warning"
                      >出勤:
                      {{
                        fmtNum(studentDetail.grades.attendance_count)
                      }}</el-tag
                    >
                    <el-tag type="danger"
                      >作业:
                      {{ fmtNum(studentDetail.grades.homework_score) }}</el-tag
                    >
                    <el-tag type="info"
                      >刷题:
                      {{ fmtNum(studentDetail.grades.practice_count) }}</el-tag
                    >
                  </div>
                  <div v-if="studentDetail.percentiles" style="margin-top: 8px">
                    <el-alert
                      type="success"
                      :closable="false"
                      show-icon
                      :title="`分位：高数平均 ${fmtNum(studentDetail.percentiles.calculus_avg_score)}%`"
                    />
                  </div>
                </div>
                <div style="flex: 1; min-width: 280px">
                  <div ref="detailChart" class="chart-container small"></div>
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-row :gutter="20">
          <!-- 成绩分布图 -->
          <el-col :span="12">
            <el-card v-loading="loading.distribution" class="chart-card">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">📊 多因素对高数成绩的影响</span>
                </div>
              </template>
              <div ref="distributionChart" class="chart-container small"></div>
            </el-card>
          </el-col>

          <!-- 饼图 - 分数段占比 -->
          <el-col :span="12">
            <el-card v-loading="loading.pie" class="chart-card">
              <template #header>
                <div class="card-header">
                  <span class="chart-title">🥧 分数段占比</span>
                </div>
              </template>
              <div ref="pieChart" class="chart-container small"></div>
            </el-card>
          </el-col>
        </el-row>

        <!-- 底部行移除 -->
      </el-tab-pane>

      <!-- 数据表可视化标签页 -->
      <el-tab-pane label="📋 数据表可视化" name="tables">
        <el-card class="filter-card" shadow="hover">
          <div class="filter-container">
            <el-select
              v-model="tableConfig.selectedTable"
              placeholder="选择数据表"
              style="width: 220px; margin-right: 20px"
              @change="handleTableChange"
            >
              <el-option
                v-for="table in tableConfig.tables"
                :key="table"
                :label="getTableLabel(table)"
                :value="table"
              >
                <span style="float: left">{{ getTableLabel(table) }}</span>
              </el-option>
            </el-select>

            <div class="search-section">
              <el-input
                v-model="tableConfig.searchQuery"
                placeholder="按学号或姓名搜索..."
                prefix-icon="Search"
                clearable
                style="width: 240px; margin-right: 20px"
              >
              </el-input>
            </div>

            <div class="action-section">
              <el-button
                type="primary"
                icon="Refresh"
                plain
                @click="refreshTableData"
              >
                刷新数据
              </el-button>
              <el-button type="success" icon="Plus" @click="showCreateDialog">
                新增记录
              </el-button>
              <el-button
                type="info"
                icon="Download"
                plain
                @click="exportTableData"
              >
                导出数据
              </el-button>
            </div>
          </div>
        </el-card>

        <el-card v-loading="tableConfig.loading" class="table-card">
          <template #header>
            <div class="card-header">
              <div>
                <span class="table-title">{{
                  getTableLabel(tableConfig.selectedTable)
                }}</span>
              </div>
            </div>
          </template>

          <div v-if="tableConfig.error" class="error-container">
            <el-alert
              title="数据加载失败"
              :description="tableConfig.error"
              type="error"
              show-icon
              closable
            >
            </el-alert>
          </div>

          <div
            v-else-if="!tableConfig.tableData.length && !tableConfig.loading"
            class="empty-container"
          >
            <el-empty description="暂无数据" />
          </div>

          <div v-else class="table-wrapper">
            <el-table
              :data="safeTableData"
              style="width: 100%"
              :default-sort="{ prop: 'id', order: 'ascending' }"
              border
              stripe
              highlight-current-row
              height="500"
              size="small"
              :cell-style="{ padding: '8px' }"
              :header-cell-style="{
                padding: '8px',
                backgroundColor: '#f5f7fa',
              }"
            >
              <template v-for="column in tableColumns" :key="column.prop">
                <el-table-column
                  :prop="column.prop"
                  :label="column.label"
                  :width="getColumnWidth(column.prop)"
                  :sortable="isSortable(column.prop)"
                  :align="getColumnAlign(column.prop)"
                  :fixed="isFixedColumn(column.prop)"
                >
                  <template #default="{ row }">
                    <template v-if="isDateColumn(column.prop)">
                      <el-tag size="small" type="info">{{
                        formatDate(row[column.prop])
                      }}</el-tag>
                    </template>
                    <template v-else-if="isScoreColumn(column.prop)">
                      <el-tag
                        :type="getScoreTagType(row[column.prop])"
                        size="small"
                      >
                        {{ row[column.prop] }}
                      </el-tag>
                    </template>
                    <template v-else-if="isIdColumn(column.prop)">
                      <span style="color: #409eff; font-weight: 500">{{
                        row[column.prop]
                      }}</span>
                    </template>
                    <template v-else>
                      {{ row[column.prop] || "-" }}
                    </template>
                  </template>
                </el-table-column>
              </template>

              <!-- 操作列 -->
              <el-table-column
                label="操作"
                width="160"
                align="center"
                fixed="right"
              >
                <template #default="{ row }">
                  <div style="display: flex; gap: 8px; justify-content: center">
                    <el-button
                      type="primary"
                      size="small"
                      icon="Edit"
                      @click="showEditDialog(row)"
                      >编辑</el-button
                    >
                    <el-button
                      type="danger"
                      size="small"
                      icon="Delete"
                      @click="deleteRecord(row)"
                      >删除</el-button
                    >
                  </div>
                </template>
              </el-table-column>
            </el-table>

            <div class="pagination-container">
              <el-pagination
                v-model:current-page="tableConfig.currentPage"
                v-model:page-size="tableConfig.pageSize"
                background
                layout="total, prev, pager, next, jumper, sizes"
                :total="tableTotalFiltered"
                :page-sizes="[10, 20, 50, 100]"
                @size-change="handleSizeChange"
                @current-change="handleCurrentChange"
              >
              </el-pagination>
            </div>
          </div>
        </el-card>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增/编辑对话框 -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="600px"
      @close="resetForm"
    >
      <el-form :model="formData" label-width="120px" label-position="left">
        <!-- UG 新增：先选择学生（学号/姓名），用于确定 student_id -->
        <template v-if="tableConfig.selectedTable === 'university_grades'">
          <el-form-item v-if="dialogMode === 'create'" label="关联学生">
            <el-select
              v-model="selectedStudentForForm"
              filterable
              :loading="studentOptionsLoading"
              placeholder="按学号或姓名搜索选择学生"
              style="width: 100%"
              @visible-change="
                (val) => {
                  if (val && !studentOptions.length) loadStudentOptions();
                }
              "
              @change="onSelectStudent"
            >
              <el-option
                v-for="stu in studentOptions"
                :key="stu.student_id"
                :label="formatStudentOption(stu)"
                :value="stu.student_id"
              >
                <span style="float: left">{{ formatStudentOption(stu) }}</span>
              </el-option>
            </el-select>
          </el-form-item>
          <el-alert
            v-if="dialogMode === 'create'"
            type="info"
            :closable="false"
            show-icon
            style="margin-bottom: 10px"
            title="请选择学生以自动填充 student_id（后端已开启校验，未选择将无法创建）"
          />
        </template>

        <template v-for="column in tableColumns" :key="column.prop">
          <!-- 跳过主键字段 -->
          <el-form-item v-if="!isPrimaryKey(column.prop)" :label="column.label">
            <template v-if="isDateColumn(column.prop)">
              <el-date-picker
                v-model="formData[column.prop]"
                type="date"
                placeholder="选择日期"
                format="YYYY-MM-DD"
                value-format="YYYY-MM-DD"
                style="width: 100%"
              />
            </template>
            <!-- UG 平均分为自动计算，禁止手填 -->
            <template v-else-if="column.prop === 'calculus_avg_score'">
              <el-input-number
                v-model="formData.calculus_avg_score"
                :min="0"
                :max="100"
                :precision="2"
                style="width: 100%"
                :disabled="true"
                placeholder="由三次成绩自动计算"
              />
            </template>
            <!-- 先渲染下拉选择（如年级/班级等），避免被数值输入覆盖 -->
            <template v-else-if="isSelectColumn(column.prop)">
              <el-select
                v-model="formData[column.prop]"
                placeholder="请选择"
                style="width: 100%"
              >
                <el-option
                  v-for="option in getColumnOptions(column.prop)"
                  :key="option"
                  :label="option"
                  :value="option"
                />
              </el-select>
            </template>
            <template v-else-if="isScoreColumn(column.prop)">
              <el-input-number
                v-model="formData[column.prop]"
                :min="0"
                :max="100"
                :precision="1"
                style="width: 100%"
                @change="onScoreChanged(column.prop)"
              />
            </template>
            <template v-else>
              <el-input
                v-model="formData[column.prop]"
                :placeholder="`请输入${column.label}`"
              />
            </template>
          </el-form-item>
        </template>
      </el-form>

      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="loading.save" @click="saveRecord">
          {{ dialogMode === "create" ? "创建" : "更新" }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script>
import * as echarts from "echarts";
import axios from "axios";
import { ElMessage, ElMessageBox } from "element-plus";

export default {
  name: "Visualization",
  data() {
    return {
      activeTab: "charts",
      chartDataTable: "university_grades",
      chartTables: [], // 图表可选表
      selectedStudentId: 1,
      studentDetail: {
        profile: null,
        grades: null,
        percentiles: null,
        factors: [],
      },

      // CRUD对话框
      dialogVisible: false,
      dialogTitle: "",
      dialogMode: "create", // 'create' 或 'edit'
      currentRecord: {},
      formData: {},
      // UG 新增时的学生选择
      studentOptions: [],
      studentOptionsLoading: false,
      selectedStudentForForm: null,
      studentSelector: null,

      // Loading states
      loading: {
        detail: false,
        distribution: false,

        radar: false,
        pie: false,
        save: false,
        exportReport: false,
        exportTable: false,
      },

      // Chart instances
      charts: {
        detail: null,
        distribution: null,

        radar: null,
        pie: null,
        predScatter: null,
        fiBar: null,
      },
      // Resize 节流控制
      _resizeRaf: null,
      _resizeBusy: false,
      _chartSizes: {},

      // 数据表配置
      tableConfig: {
        tables: ["students", "university_grades"],
        selectedTable: "students", // 默认为学生信息表
        searchQuery: "",
        tableData: [],
        total: 0,
        loading: false,
        error: null,
        currentPage: 1,
        pageSize: 20,
        tableLabels: {
          students: "学生信息表",
          university_grades: "大学成绩表",
        },
        distinctOptions: {},
        // 表结构配置
        tableConfigs: {
          students: {
            columns: [
              { prop: "student_id", label: "学生ID", type: "id" },
              { prop: "student_no", label: "学号", type: "text" },
              { prop: "name", label: "姓名", type: "text" },
              { prop: "gender", label: "性别", type: "category" },
              { prop: "grade", label: "年级", type: "category" },
              { prop: "class", label: "班级", type: "category" },
              { prop: "birth_date", label: "出生日期", type: "date" },
              { prop: "contact_phone", label: "联系电话", type: "text" },
              { prop: "email", label: "邮箱", type: "text" },
            ],
          },
          exam_scores: {
            columns: [
              { prop: "score_id", label: "成绩ID", type: "id" },
              { prop: "student_id", label: "学生ID", type: "id" },
              { prop: "course_id", label: "课程ID", type: "id" },
              { prop: "exam_type_id", label: "考试类型ID", type: "id" },
              { prop: "exam_name", label: "考试名称", type: "text" },
              { prop: "exam_date", label: "考试日期", type: "date" },
              { prop: "score", label: "分数", type: "score" },
              { prop: "score_level", label: "成绩等级", type: "category" },
              { prop: "ranking", label: "排名", type: "number" },
              { prop: "teacher_id", label: "教师ID", type: "id" },
              { prop: "comments", label: "评语", type: "text" },
            ],
          },
          class_performance: {
            columns: [
              { prop: "performance_id", label: "表现ID", type: "id" },
              { prop: "student_id", label: "学生ID", type: "id" },
              { prop: "course_id", label: "课程ID", type: "id" },
              { prop: "semester", label: "学期", type: "category" },
              { prop: "attendance_score", label: "出勤分数", type: "score" },
              { prop: "participation_score", label: "参与分数", type: "score" },
              { prop: "homework_score", label: "作业分数", type: "score" },
              { prop: "behavior_score", label: "行为分数", type: "score" },
              {
                prop: "total_performance_score",
                label: "总表现分数",
                type: "score",
              },
              { prop: "teacher_comments", label: "教师评语", type: "text" },
            ],
          },
          historical_grades: {
            columns: [
              { prop: "grade_id", label: "成绩ID", type: "id" },
              { prop: "student_id", label: "学生ID", type: "id" },
              { prop: "course_id", label: "课程ID", type: "id" },
              { prop: "semester", label: "学期", type: "category" },
              { prop: "academic_year", label: "学年", type: "category" },
              { prop: "midterm_score", label: "期中成绩", type: "score" },
              { prop: "final_score", label: "期末成绩", type: "score" },
              { prop: "usual_score", label: "平时成绩", type: "score" },
              { prop: "total_score", label: "总成绩", type: "score" },
              { prop: "grade_level", label: "成绩等级", type: "category" },
              { prop: "ranking", label: "排名", type: "number" },
              { prop: "teacher_id", label: "教师ID", type: "id" },
            ],
          },
          university_grades: {
            columns: [
              { prop: "student_id", label: "学生ID", type: "id" },
              {
                prop: "first_calculus_score",
                label: "高数第一次",
                type: "score",
              },
              {
                prop: "second_calculus_score",
                label: "高数第二次",
                type: "score",
              },
              {
                prop: "third_calculus_score",
                label: "高数第三次",
                type: "score",
              },
              { prop: "calculus_avg_score", label: "高数平均", type: "score" },
              { prop: "study_hours", label: "学习时长", type: "number" },
              { prop: "attendance_count", label: "出勤次数", type: "number" },
              { prop: "homework_score", label: "作业分数", type: "score" },
              { prop: "practice_count", label: "刷题数", type: "number" },
            ],
          },
        },
      },
      // 预测相关
      predictTargetOptions: [],
      predictConfig: {
        targetColumn: "",
        testSize: 0.2,
      },
      predictResult: null,
    };
  },

  computed: {
    tableColumns() {
      return (
        this.tableConfig.tableConfigs[this.tableConfig.selectedTable]
          ?.columns || []
      );
    },

    tableFilteredData() {
      // 确保 tableData 是数组
      const tableData = Array.isArray(this.tableConfig.tableData)
        ? this.tableConfig.tableData
        : [];

      let result = [...tableData];
      // 普通搜索过滤 - 只搜索学号和姓名
      if (this.tableConfig.searchQuery) {
        const query = this.tableConfig.searchQuery.toLowerCase();
        result = result.filter((row) => {
          // 只在学号(student_no)和姓名(name)字段中搜索
          const searchFields = [row.student_no, row.name].filter(
            (field) => field !== null && field !== undefined,
          );
          return searchFields.some((value) =>
            String(value).toLowerCase().includes(query),
          );
        });
      }

      // 分页
      const start =
        (this.tableConfig.currentPage - 1) * this.tableConfig.pageSize;
      const end = start + this.tableConfig.pageSize;
      return result.slice(start, end);
    },

    // 保障 Table 始终获得可迭代数组
    safeTableData() {
      const data = this.tableFilteredData;
      return Array.isArray(data) ? data : [];
    },

    tableTotalFiltered() {
      const tableData = Array.isArray(this.tableConfig.tableData)
        ? this.tableConfig.tableData
        : [];

      let result = [...tableData];

      // 应用搜索过滤 - 只搜索学号和姓名
      if (this.tableConfig.searchQuery) {
        const query = this.tableConfig.searchQuery.toLowerCase();
        result = result.filter((row) => {
          // 只在学号(student_no)和姓名(name)字段中搜索
          const searchFields = [row.student_no, row.name].filter(
            (field) => field !== null && field !== undefined,
          );
          return searchFields.some((value) =>
            String(value).toLowerCase().includes(query),
          );
        });
      }

      return result.length;
    },
  },

  watch: {
    chartDataTable: {
      handler() {
        // 切换数据表时，自动刷新学生详情和所有图表
        this.loadChartData();
      },
    },
    "tableConfig.selectedTable": {
      handler() {
        this.tableConfig.currentPage = 1;
        this.fetchTableData();
      },
    },
    "tableConfig.searchQuery": {
      handler() {
        this.tableConfig.currentPage = 1;
      },
    },
  },

  mounted() {
    this.$nextTick(() => {
      this.initCharts();
      // 先加载数据表,获取有效的学生ID,然后再加载图表数据
      setTimeout(async () => {
        await this.fetchChartTables();
        await this.fetchCrudTables();
        await this.fetchTableData();
        // 然后加载图表数据
        this.loadChartData();
      }, 100);
    });
    window.addEventListener("resize", this.handleResize);
  },

  beforeUnmount() {
    Object.values(this.charts).forEach((chart) => {
      chart?.dispose();
    });
    window.removeEventListener("resize", this.handleResize);
  },

  methods: {
    // 加载“数据表可视化”页签的表清单：按列名识别的成绩表 + students
    async fetchCrudTables() {
      try {
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
        this.tableConfig.tables = Array.from(set);
        // 默认选择：优先 university_grades 其次其他成绩表 再 students
        if (
          !this.tableConfig.selectedTable ||
          !this.tableConfig.tables.includes(this.tableConfig.selectedTable)
        ) {
          if (this.tableConfig.tables.includes("university_grades"))
            this.tableConfig.selectedTable = "university_grades";
          else if (gradeTables.length > 0)
            this.tableConfig.selectedTable = gradeTables[0];
          else if (this.tableConfig.tables.includes("students"))
            this.tableConfig.selectedTable = "students";
          else if (this.tableConfig.tables.length > 0)
            this.tableConfig.selectedTable = this.tableConfig.tables[0];
        }
      } catch (e) {
        console.warn("加载 CRUD 表清单失败:", e);
      }
    },
    async preloadDistinctOptions(props = []) {
      try {
        const table = this.tableConfig.selectedTable;
        if (!table) return;
        const cache = this.tableConfig.distinctOptions || {};
        for (const p of props) {
          if (cache[p] && Array.isArray(cache[p]) && cache[p].length) continue;
          const res = await axios.get("/api/analysis/distinct", {
            params: { table, column: p },
          });
          if (res.data?.status === "success") {
            cache[p] = Array.isArray(res.data.values) ? res.data.values : [];
          }
        }
        this.tableConfig.distinctOptions = { ...cache };
      } catch (e) {
        // 忽略错误
      }
    },
    onScoreChanged(prop) {
      // 仅在 UG 表中处理平均分
      if (this.tableConfig.selectedTable !== "university_grades") return;
      const keys = [
        "first_calculus_score",
        "second_calculus_score",
        "third_calculus_score",
      ];
      if (!keys.includes(prop)) return;
      this.recalcUgAvg();
    },
    recalcUgAvg() {
      if (this.tableConfig.selectedTable !== "university_grades") return;
      const s1 = Number(this.formData.first_calculus_score);
      const s2 = Number(this.formData.second_calculus_score);
      const s3 = Number(this.formData.third_calculus_score);
      const vals = [s1, s2, s3].filter((v) => Number.isFinite(v));
      if (vals.length >= 1) {
        const avg = vals.reduce((a, b) => a + b, 0) / vals.length;
        this.formData.calculus_avg_score = Number(avg.toFixed(2));
      } else {
        this.formData.calculus_avg_score = undefined;
      }
    },
    async onStudentIdChange() {
      await this.loadStudentDetail();
      await this.updateDetailChart();
      // 学生切换时，同步刷新“多因素影响”图，传入 student_id 以限定同侪范围
      await this.updateDistributionChart();
    },
    initCharts() {
      this.$nextTick(() => {
        if (this.$refs.detailChart) {
          this.charts.detail = echarts.init(this.$refs.detailChart);
        }
        if (this.$refs.distributionChart) {
          this.charts.distribution = echarts.init(this.$refs.distributionChart);
          console.log("分布图初始化完成");
        }

        if (this.$refs.radarChart) {
          this.charts.radar = echarts.init(this.$refs.radarChart);
          console.log("雷达图初始化完成");
        }
        if (this.$refs.pieChart) {
          this.charts.pie = echarts.init(this.$refs.pieChart);
          console.log("饼图初始化完成");
        }
        if (this.$refs.predScatterChart) {
          this.charts.predScatter = echarts.init(this.$refs.predScatterChart);
        }
        if (this.$refs.fiBarChart) {
          this.charts.fiBar = echarts.init(this.$refs.fiBarChart);
        }
      });
    },
    async fetchPredictColumns() {
      try {
        if (!this.chartDataTable) {
          this.predictTargetOptions = [];
          return;
        }
        const res = await axios.get("/api/analysis/columns", {
          params: { table: this.chartDataTable },
        });
        if (res.data?.status === "success") {
          const rec = res.data.recommended_targets || [];
          const nums = res.data.numeric_columns || [];
          const all = [...rec, ...nums];
          const set = new Set();
          let opts = all.filter((c) =>
            set.has(c) ? false : (set.add(c), true),
          );
          // 若为大学成绩表，限定为四个高数目标列
          if (this.chartDataTable === "university_grades") {
            const allowed = [
              "first_calculus_score",
              "second_calculus_score",
              "third_calculus_score",
              "calculus_avg_score",
            ];
            const exists = allowed.filter((c) => opts.includes(c));
            if (exists.length) opts = exists;
          }
          this.predictTargetOptions = opts;
          if (
            this.predictConfig.targetColumn &&
            !this.predictTargetOptions.includes(this.predictConfig.targetColumn)
          ) {
            this.predictConfig.targetColumn = "";
          }
        }
      } catch (e) {
        console.warn("加载预测列失败:", e);
      }
    },

    handleResize() {
      // 使用 rAF 节流，避免触发 ResizeObserver 循环告警
      if (this._resizeRaf) {
        cancelAnimationFrame(this._resizeRaf);
        this._resizeRaf = null;
      }
      this._resizeRaf = requestAnimationFrame(() => {
        if (this._resizeBusy) return;
        this._resizeBusy = true;
        try {
          Object.entries(this.charts).forEach(([key, chart]) => {
            if (chart && chart.getDom) {
              const dom = chart.getDom();
              if (dom) {
                const w = dom.clientWidth || 0;
                const h = dom.clientHeight || 0;
                if (w > 0 && h > 0) {
                  const last = this._chartSizes[key] || { w: -1, h: -1 };
                  // 仅当尺寸发生变化时才触发 resize（容忍1px抖动）
                  if (Math.abs(w - last.w) > 1 || Math.abs(h - last.h) > 1) {
                    try {
                      chart.resize();
                    } catch (e) {}
                    this._chartSizes[key] = { w, h };
                  }
                }
              }
            }
          });
        } catch (e) {
          // 忽略 resize 过程中的非致命错误
        } finally {
          // 加大延时释放 busy，进一步避免连续尺寸抖动
          setTimeout(() => {
            this._resizeBusy = false;
          }, 120);
        }
      });
    },

    handleTabChange(tabName) {
      if (tabName === "charts") {
        // 重新初始化图表以避免隐藏/显示导致的实例失效或残留配置
        this.$nextTick(() => {
          try {
            // 安全地销毁旧实例
            Object.keys(this.charts).forEach((key) => {
              if (this.charts[key]) {
                this.charts[key].dispose();
                this.charts[key] = null;
              }
            });
            // 重新创建实例（仅当对应容器存在）
            if (this.$refs.detailChart)
              this.charts.detail = echarts.init(this.$refs.detailChart);
            if (this.$refs.distributionChart)
              this.charts.distribution = echarts.init(
                this.$refs.distributionChart,
              );

            if (this.$refs.radarChart)
              this.charts.radar = echarts.init(this.$refs.radarChart);
            if (this.$refs.pieChart)
              this.charts.pie = echarts.init(this.$refs.pieChart);
            if (this.$refs.predScatterChart)
              this.charts.predScatter = echarts.init(
                this.$refs.predScatterChart,
              );
            if (this.$refs.fiBarChart)
              this.charts.fiBar = echarts.init(this.$refs.fiBarChart);
          } catch (e) {
            console.warn("图表重新初始化失败:", e);
          }
          // 重新加载数据并渲染
          this.loadChartData();
          this.handleResize();
        });
      } else if (tabName === "tables") {
        // 离开图表页时主动销毁实例，防止后台渲染任务残留
        try {
          Object.keys(this.charts).forEach((key) => {
            if (this.charts[key]) {
              this.charts[key].dispose();
              this.charts[key] = null;
            }
          });
        } catch (e) {
          console.warn("离开图表页 dispose 异常:", e);
        }
        if (!this.tableConfig.tableData.length) {
          this.fetchTableData();
        }
      }
    },

    // 趋势类型已移除

    async loadChartData() {
      // 先拉取学生详情，再并行渲染其他图表
      await this.loadStudentDetail();
      await Promise.all([
        this.updateDetailChart(),
        this.updateDistributionChart(),
        this.updatePieChart(),
      ]);
    },

    async loadStudentDetail() {
      try {
        if (!this.selectedStudentId) return;
        const res = await axios.get("/api/analysis/student-detail", {
          params: {
            student_id: this.selectedStudentId,
            table: this.chartDataTable,
          },
        });
        if (res.data?.status === "success") {
          this.studentDetail = {
            profile: res.data.profile || null,
            grades: res.data.grades || null,
            percentiles: res.data.percentiles || null,
            factors: Array.isArray(res.data.factors) ? res.data.factors : [],
          };
          // 仅更新数据，渲染由 updateDetailChart 统一处理
        }
      } catch (e) {
        console.warn("加载学生详情失败:", e);
      }
    },

    async updateDetailChart() {
      if (!this.charts.detail) return;
      this.loading.detail = true;
      try {
        const factors = this.studentDetail?.factors || [];
        const option = {
          title: { text: "学习投入与行为（该生）", left: "center" },
          tooltip: { trigger: "axis" },
          grid: { left: "8%", right: "5%", bottom: "10%", top: "18%" },
          xAxis: { type: "category", data: factors.map((f) => f.name) },
          yAxis: { type: "value" },
          series: [
            {
              type: "bar",
              data: factors.map((f) => Number(f.value) || 0),
              barWidth: "50%",
            },
          ],
        };
        this.charts.detail.clear();
        this.charts.detail.setOption(option, true);
      } catch (e) {
        console.warn("渲染学生详情图失败:", e);
      } finally {
        this.loading.detail = false;
      }
    },

    async updateDistributionChart() {
      if (!this.charts.distribution) return;
      this.loading.distribution = true;
      try {
        // 动态根据当前表名请求
        if (this.chartDataTable && this.chartDataTable !== "students") {
          // 通用成绩表分布接口（如有）
          const params = { buckets: 5, table: this.chartDataTable };
          if (this.selectedStudentId)
            params.student_id = this.selectedStudentId;
          // 兼容原有 university_grades 特例
          const url =
            this.chartDataTable === "university_grades"
              ? "/api/analysis/ug/calculus-by-factors-bucket"
              : "/api/analysis/ug/calculus-by-factors-bucket";
          const res = await axios.get(url, { params });
          const series = (res.data?.series || []).map((s) => ({
            name: s.name,
            type: "line",
            data: s.data,
            smooth: true,
          }));
          const option = {
            title: {
              text: "多因素对高数成绩的影响（分档：低→高）",
              left: "center",
            },
            tooltip: { trigger: "axis" },
            legend: { top: 28 },
            xAxis: { type: "category", data: res.data?.labels || [] },
            yAxis: { type: "value", name: "平均高数成绩" },
            series,
          };
          this.charts.distribution.setOption(option, true);
        } else if (this.chartDataTable === "students") {
          const res = await axios.get(
            "/api/analysis/students/category-distribution",
          );
          const grade = res.data?.data?.grade || [];
          const option = {
            title: { text: "年级分布", left: "center" },
            tooltip: { trigger: "axis" },
            xAxis: { type: "category", data: grade.map((i) => i.name) },
            yAxis: { type: "value" },
            series: [{ type: "bar", data: grade.map((i) => i.value) }],
          };
          this.charts.distribution.setOption(option, true);
        }
      } catch (error) {
        console.error("加载可视化二失败:", error);
        ElMessage.error("加载可视化二失败");
      } finally {
        this.loading.distribution = false;
      }
    },

    async updateRadarChart() {
      if (!this.charts.radar) return;

      this.loading.radar = true;
      try {
        const params = {
          table: "class_performance", // 雷达图固定使用课堂表现表数据
        };

        // 如果选择了学生ID，添加到参数中
        if (this.selectedStudentId) {
          params.student_id = this.selectedStudentId;
        }

        const response = await axios.get("/api/analysis/radar-data", {
          params,
        });

        if (response.data.status === "success") {
          // 如果有提示信息，显示给用户
          if (response.data.message) {
            console.warn(response.data.message);
          }

          const option = {
            title: {
              text: "课堂表现多维度分析",
              left: "center",
              subtext: response.data.message || "",
            },
            tooltip: {},
            legend: {
              data: (response.data.series || []).map((s) => s?.name || "未知"),
              top: 30,
            },
            radar: {
              indicator: response.data.indicator || [],
              center: ["50%", "55%"],
              radius: "60%",
            },
            series: [
              {
                type: "radar",
                data: (response.data.series || []).map((s) => ({
                  value: s?.value || [],
                  name: s?.name || "未知",
                  areaStyle: {
                    color: (s?.name || "").includes("班级")
                      ? "rgba(64, 158, 255, 0.3)"
                      : "rgba(255, 99, 132, 0.3)",
                  },
                })),
              },
            ],
          };

          this.charts.radar.setOption(option);
        }
      } catch (error) {
        console.error("加载雷达图数据失败:", error);
        // 不显示错误提示，而是显示空状态
        if (this.charts.radar) {
          const emptyOption = {
            title: {
              text: "课堂表现多维度分析",
              left: "center",
              subtext: "数据加载失败",
            },
            radar: {
              indicator: [
                { name: "维度1", max: 100 },
                { name: "维度2", max: 100 },
                { name: "维度3", max: 100 },
              ],
              center: ["50%", "55%"],
              radius: "60%",
            },
            series: [
              {
                type: "radar",
                data: [
                  {
                    value: [0, 0, 0],
                    name: "暂无数据",
                    areaStyle: {
                      color: "rgba(200, 200, 200, 0.3)",
                    },
                  },
                ],
              },
            ],
          };
          this.charts.radar.setOption(emptyOption);
        }
      } finally {
        this.loading.radar = false;
      }
    },

    async updatePieChart() {
      if (!this.charts.pie) return;
      this.loading.pie = true;
      try {
        // 动态根据当前表名请求
        if (this.chartDataTable && this.chartDataTable !== "students") {
          const response = await axios.get(
            "/api/analysis/score-band-distribution",
            { params: { table: this.chartDataTable } },
          );
          if (response.data.status === "success") {
            const pieData = response.data.data || [];
            const total =
              response.data.total ||
              pieData.reduce((sum, item) => sum + (item.value || 0), 0);
            const option = {
              title: {
                text: "分数段占比",
                left: "center",
                subtext: `总计 ${total} 条记录`,
              },
              tooltip: {
                trigger: "item",
                formatter: (p) => `${p.name}: ${p.value} (${p.percent}%)`,
              },
              legend: {
                orient: "vertical",
                left: "left",
                top: "middle",
                data: pieData.map((i) => i.name),
              },
              series: [
                {
                  name: "分数段",
                  type: "pie",
                  radius: ["40%", "70%"],
                  data: pieData,
                },
              ],
            };
            this.charts.pie.setOption(option, true);
          }
        } else if (this.chartDataTable === "students") {
          const res = await axios.get(
            "/api/analysis/students/category-distribution",
          );
          const grade = res.data?.data?.grade || [];
          const option = {
            title: { text: "学生年级占比", left: "center" },
            tooltip: {
              trigger: "item",
              formatter: (p) => `${p.name}: ${p.value} (${p.percent}%)`,
            },
            series: [{ type: "pie", radius: "60%", data: grade }],
          };
          this.charts.pie.setOption(option, true);
        }
      } catch (error) {
        console.error("加载饼图数据失败:", error);
        ElMessage.error("加载饼图数据失败");
      } finally {
        this.loading.pie = false;
      }
    },

    async runPrediction() {
      // 需要用户手动选择目标列
      if (!this.predictConfig?.targetColumn) {
        ElMessage.warning("请先选择目标列（必选）");
        return;
      }
      this.loading.predict = true;
      try {
        const body = {
          table: this.chartDataTable,
          targetColumn: this.predictConfig.targetColumn,
          testSize: this.predictConfig.testSize,
          previewLimit: 50,
        };
        const res = await axios.post("/api/training/predict-table", body);
        if (res.data?.status === "success") {
          this.predictResult = res.data.data || res.data;
          this.renderPredictCharts();
          this.$nextTick(() => this.handleResize());
        } else {
          this.predictResult = null;
        }
      } catch (e) {
        console.error("预测失败:", e);
        this.predictResult = null;
      } finally {
        this.loading.predict = false;
      }
    },

    renderPredictCharts() {
      // 散点：实际 vs 预测
      try {
        if (this.charts.predScatter && this.predictResult?.predictions) {
          const actual = this.predictResult.predictions.actual || [];
          const predicted = this.predictResult.predictions.predicted || [];
          const points = actual.map((y, i) => [y, predicted[i]]);
          const option = {
            title: { text: "预测值 vs 实际值", left: "center" },
            xAxis: { name: "实际值" },
            yAxis: { name: "预测值" },
            tooltip: {
              trigger: "item",
              formatter: (p) => `实际: ${p.value[0]}<br/>预测: ${p.value[1]}`,
            },
            series: [{ type: "scatter", data: points, symbolSize: 6 }],
          };
          this.charts.predScatter.setOption(option, true);
        }
      } catch (e) {
        console.warn("散点渲染失败", e);
      }

      // 柱状：特征重要性
      try {
        if (
          this.charts.fiBar &&
          Array.isArray(this.predictResult?.feature_importance)
        ) {
          const fi = this.predictResult.feature_importance.slice(0, 10);
          const option = {
            title: { text: "Top10 特征重要性", left: "center" },
            grid: { left: "3%", right: "4%", bottom: "3%", containLabel: true },
            xAxis: { type: "value" },
            yAxis: { type: "category", data: fi.map((x) => x.feature) },
            series: [{ type: "bar", data: fi.map((x) => x.importance) }],
          };
          this.charts.fiBar.setOption(option, true);
        }
      } catch (e) {
        console.warn("特征重要性渲染失败", e);
      }
    },

    fmtNum(v) {
      if (v === null || v === undefined) return "-";
      const n = Number(v);
      return isNaN(n) ? "-" : n.toFixed(4);
    },
    // 加载可用于图表的数据表列表
    async fetchChartTables() {
      // 优先使用按列名识别的“成绩表”，并额外保留 students 用于学生详情
      try {
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

        // 允许的图表数据源：优先成绩类表，同时保留 students（用于详情联动）
        const set = new Set(gradeTables);
        if (allTables.includes("students")) set.add("students");
        this.chartTables = Array.from(set);

        // 默认选择：优先 university_grades 其次其它成绩表，再 students
        if (!this.chartTables.includes(this.chartDataTable)) {
          if (this.chartTables.includes("university_grades"))
            this.chartDataTable = "university_grades";
          else if (gradeTables.length > 0) this.chartDataTable = gradeTables[0];
          else if (this.chartTables.includes("students"))
            this.chartDataTable = "students";
          else if (this.chartTables.length > 0)
            this.chartDataTable = this.chartTables[0];
        }

        await this.fetchPredictColumns();
      } catch (e) {
        console.warn("加载表清单失败:", e);
      }
    },

    // 表格相关方法
    handleTableChange() {
      this.tableConfig.currentPage = 1;
      this.fetchTableData();
      this.fetchPredictColumns();
    },

    async fetchTableData() {
      this.tableConfig.loading = true;
      this.tableConfig.error = null;

      try {
        console.log(`正在加载${this.tableConfig.selectedTable}表数据...`);
        // 使用分页请求处理大数据量
        const response = await axios.get(
          `/api/analysis/table-data?table=${this.tableConfig.selectedTable}&page=1&page_size=1000`,
          {
            timeout: 15000, // 15秒超时
            headers: {
              Accept: "application/json",
              "Content-Type": "application/json",
            },
          },
        );
        console.log(
          `${this.tableConfig.selectedTable}表响应状态:`,
          response.status,
        );
        if (response.data && response.data.status === "success") {
          this.tableConfig.tableData = response.data.data || [];
          this.tableConfig.total =
            response.data.total || this.tableConfig.tableData.length;
          // 动态生成自定义表的列配置，优先用后端 columns 字段顺序
          if (!this.tableConfig.tableConfigs[this.tableConfig.selectedTable]) {
            const rows = this.tableConfig.tableData;
            // 优先用后端 columns 字段
            const colOrder =
              Array.isArray(response.data.columns) &&
              response.data.columns.length
                ? response.data.columns
                : Array.isArray(rows) && rows.length > 0
                  ? Object.keys(rows[0])
                  : [];
            const columns = colOrder.map((k) => ({
              prop: k,
              label: this.translateColumnName ? this.translateColumnName(k) : k,
              type: k.includes("score")
                ? "score"
                : k.includes("id")
                  ? "id"
                  : "text",
            }));
            this.tableConfig.tableConfigs[this.tableConfig.selectedTable] = {
              columns,
            };
          }
          console.log(
            `${this.tableConfig.selectedTable}表加载成功，显示${this.tableConfig.tableData.length}条记录，总共${this.tableConfig.total}条`,
          );
        } else {
          const errorMsg = response.data?.message || "加载数据失败";
          this.tableConfig.error = errorMsg;
          console.error(
            `${this.tableConfig.selectedTable}表加载失败:`,
            errorMsg,
          );
        }
      } catch (error) {
        console.error(
          `获取${this.tableConfig.selectedTable}表数据失败:`,
          error,
        );
        let errorMessage = "加载数据失败";
        if (error.code === "ECONNABORTED") {
          errorMessage = "请求超时，数据量较大，请稍后重试";
        } else if (error.response) {
          errorMessage = `服务器错误 (${error.response.status}): ${error.response.statusText}`;
        } else if (error.request) {
          errorMessage = "网络连接失败，请检查后端服务是否运行";
        } else {
          errorMessage = error.message || "未知错误";
        }
        this.tableConfig.error = errorMessage;
      } finally {
        this.tableConfig.loading = false;
      }
    },

    refreshTableData() {
      this.tableConfig.currentPage = 1;
      this.tableConfig.searchQuery = "";
      this.fetchTableData();
    },

    async exportTableData() {
      try {
        this.loading.exportTable = true;
        const table = this.tableConfig.selectedTable;
        const res = await axios.get(`/api/analysis/export-table`, {
          params: { table },
          responseType: "blob",
        });
        const blob = new Blob([res.data], { type: "text/csv;charset=utf-8;" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        const label = this.getTableLabel(table);
        link.href = url;
        link.download = `${label || table}_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.csv`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success("数据导出成功");
      } catch (err) {
        console.error("导出数据失败:", err);
        ElMessage.error("导出失败，请稍后重试");
      } finally {
        this.loading.exportTable = false;
      }
    },

    async exportAnalysisReport() {
      try {
        this.loading.exportReport = true;
        const params = {
          table: this.chartDataTable,
          student_id: this.selectedStudentId || undefined,
        };
        const res = await axios.get("/api/analysis/export-report", {
          params,
          responseType: "blob",
        });
        const blob = new Blob([res.data], { type: "application/zip" });
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement("a");
        link.href = url;
        link.download = `数据分析报告_${new Date().toISOString().slice(0, 19).replace(/[:T]/g, "-")}.zip`;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        ElMessage.success("报告导出成功");
      } catch (err) {
        console.error("导出报告失败:", err);
        ElMessage.error("导出失败，请稍后重试");
      } finally {
        this.loading.exportReport = false;
      }
    },

    handleSizeChange() {
      this.tableConfig.currentPage = 1;
    },

    handleCurrentChange() {
      window.scrollTo({ top: 0, behavior: "smooth" });
    },

    getTableLabel(table) {
      const map = this.tableConfig.tableLabels || {};
      if (map[table]) return map[table];
      if ([...String(table)].some((ch) => ch.charCodeAt(0) > 127)) return table;
      // 纯数字或很短的原始名（如“1”、“1_2024”），直接显示原名，避免误显示“自定义表”
      const s = String(table);
      if (/^[0-9._-]+$/.test(s) || s.length <= 3) return s;
      return this.translateTableName(table);
    },
    translateColumnName(col) {
      const map = {
        student_id: "学生ID",
        student_no: "学号",
        name: "姓名",
        gender: "性别",
        grade: "年级",
        class: "班级",
        birth_date: "出生日期",
        contact_phone: "联系电话",
        email: "邮箱",
        calculus_score: "高等数学成绩",
        calculus_avg_score: "高数平均",
        first_calculus_score: "高数第一次",
        second_calculus_score: "高数第二次",
        third_calculus_score: "高数第三次",
        homework_score: "作业分数",
        study_hours: "学习时长",
        attendance_count: "出勤次数",
        practice_count: "刷题数",
        teacher_id: "教师ID",
        comments: "评语",
        behavior_score: "行为分数",
        total_performance_score: "总表现分数",
        teacher_comments: "教师评语",
        grade_id: "成绩ID",
        academic_year: "学年",
        grade_level: "成绩等级",
        performance: "表现",
        // 兜底
      };
      return map[col] || col;
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

    getColumnWidth(prop) {
      if (prop.includes("id")) return 100;
      if (prop.includes("name") || prop.includes("no")) return 120;
      if (prop.includes("score") || prop.includes("grade")) return 90;
      if (prop.includes("date")) return 130;
      if (prop.includes("email")) return 180;
      if (prop.includes("phone")) return 130;
      return 150;
    },

    getColumnAlign(prop) {
      if (
        prop.includes("id") ||
        prop.includes("score") ||
        prop.includes("ranking")
      ) {
        return "center";
      }
      return "left";
    },

    isSortable(prop) {
      return (
        prop.includes("id") ||
        prop.includes("score") ||
        prop.includes("ranking") ||
        prop.includes("date")
      );
    },

    isFixedColumn(prop) {
      return prop.includes("student_id") || prop === "name";
    },

    isDateColumn(prop) {
      return prop.includes("date");
    },

    isScoreColumn(prop) {
      // 优先使用列配置类型判断
      const cols =
        this.tableConfig.tableConfigs[this.tableConfig.selectedTable]
          ?.columns || [];
      const cfg = cols.find((c) => c.prop === prop);
      if (cfg && cfg.type) {
        // 仅当标记为 score 或 number 时使用数字输入
        return cfg.type === "score" || cfg.type === "number";
      }
      // 回退：根据字段名的启发式，排除年级/班级/等级
      if (prop === "grade" || prop === "class" || prop === "grade_level")
        return false;
      return /score/i.test(prop);
    },

    isIdColumn(prop) {
      return prop.includes("_id");
    },

    formatDate(dateString) {
      if (!dateString) return "-";
      return dateString.toString().split("T")[0];
    },

    getScoreTagType(score) {
      if (typeof score !== "number") return "info";
      if (score >= 90) return "success";
      if (score >= 80) return "";
      if (score >= 60) return "warning";
      return "danger";
    },

    // CRUD 相关方法
    async showCreateDialog() {
      this.dialogMode = "create";
      this.dialogTitle = `新增${this.getTableLabel(this.tableConfig.selectedTable)}记录`;
      this.formData = {};
      this.dialogVisible = true;
      // 预取年级/班级选项，确保为下拉可选
      await this.preloadDistinctOptions(["grade", "class"]);
      // 若是 UG 表，预加载学生列表，并尝试用上方已选学生ID预选
      if (this.tableConfig.selectedTable === "university_grades") {
        this.loadStudentOptions().then(() => {
          if (this.selectedStudentId) {
            const exists = this.studentOptions.find(
              (s) => s.student_id === this.selectedStudentId,
            );
            if (exists) {
              this.selectedStudentForForm = this.selectedStudentId;
              this.onSelectStudent(this.selectedStudentId);
            }
          }
          this.recalcUgAvg();
        });
      }
    },

    async showEditDialog(row) {
      this.dialogMode = "edit";
      this.dialogTitle = `编辑${this.getTableLabel(this.tableConfig.selectedTable)}记录`;
      this.currentRecord = { ...row };
      this.formData = { ...row };
      this.dialogVisible = true;
      await this.preloadDistinctOptions(["grade", "class"]);
      // 打开时同步一次平均分
      this.recalcUgAvg();
    },

    async deleteRecord(row) {
      try {
        await ElMessageBox.confirm("确定要删除这条记录吗？", "提示", {
          confirmButtonText: "确定",
          cancelButtonText: "取消",
          type: "warning",
        });

        const primaryKey = this.getPrimaryKeyValue(row);
        const response = await axios.delete(
          `/api/analysis/table/${this.tableConfig.selectedTable}/delete/${primaryKey}`,
        );

        if (response.data.status === "success") {
          ElMessage.success("删除成功");
          this.fetchTableData();
        } else {
          ElMessage.error(response.data.message || "删除失败");
        }
      } catch (error) {
        if (error !== "cancel") {
          console.error("删除记录失败:", error);
          ElMessage.error("删除失败：" + error.message);
        }
      }
    },

    async saveRecord() {
      this.loading.save = true;
      try {
        // UG 创建前置校验：必须具备 student_id（或可映射字段）
        if (
          this.dialogMode === "create" &&
          this.tableConfig.selectedTable === "university_grades"
        ) {
          const hasStudentId = !!this.formData.student_id;
          const hasStudentNo = !!this.formData.student_no;
          if (!hasStudentId && !hasStudentNo) {
            this.loading.save = false;
            ElMessage.warning(
              "请先选择关联学生（学号/姓名），以提供 student_id 或学号",
            );
            return;
          }
          // 可选：若三次成绩齐全，前端先计算平均分，减少后端计算压力
          this.recalcUgAvg();
        }
        // 编辑UG时也同步一次平均分
        if (
          this.dialogMode === "edit" &&
          this.tableConfig.selectedTable === "university_grades"
        ) {
          this.recalcUgAvg();
        }
        let response;
        if (this.dialogMode === "create") {
          response = await axios.post(
            `/api/analysis/table/${this.tableConfig.selectedTable}/create`,
            this.formData,
          );
        } else {
          const primaryKey = this.getPrimaryKeyValue(this.currentRecord);
          response = await axios.put(
            `/api/analysis/table/${this.tableConfig.selectedTable}/update/${primaryKey}`,
            this.formData,
          );
        }

        if (response.data.status === "success") {
          ElMessage.success(
            this.dialogMode === "create" ? "创建成功" : "更新成功",
          );
          this.dialogVisible = false;
          this.fetchTableData();
        } else {
          ElMessage.error(response.data.message || "保存失败");
        }
      } catch (error) {
        console.error("保存记录失败:", error);
        ElMessage.error("保存失败：" + error.message);
      } finally {
        this.loading.save = false;
      }
    },

    // 载入学生选项（用于 UG 新增）
    async loadStudentOptions() {
      if (this.studentOptions.length) return;
      this.studentOptionsLoading = true;
      try {
        const resp = await axios.get("/api/analysis/table-data", {
          params: { table: "students", page: 1, page_size: 10000 },
        });
        if (resp.data?.status === "success") {
          const arr = Array.isArray(resp.data.data) ? resp.data.data : [];
          // 仅保留必要字段，避免大对象占用内存
          this.studentOptions = arr.map((s) => ({
            student_id: s.student_id,
            student_no: s.student_no,
            name: s.name,
            grade: s.grade,
            class: s.class,
          }));
        }
      } catch (e) {
        console.warn("加载学生列表失败:", e);
      } finally {
        this.studentOptionsLoading = false;
      }
    },

    onStudentSelectorChange(val) {
      if (!val) return;
      this.selectedStudentId = val;
      // 同步加载学生详情与图表
      this.onStudentIdChange();
    },

    formatStudentOption(stu) {
      if (!stu) return "";
      const no = stu.student_no ? `学号:${stu.student_no}` : "学号:未知";
      const nm = stu.name ? `姓名:${stu.name}` : "姓名:未知";
      const gc = [stu.grade, stu.class].filter(Boolean).join(" ");
      return `${no} ｜ ${nm}${gc ? " ｜ " + gc : ""}`;
    },

    onSelectStudent(val) {
      const stu = this.studentOptions.find((s) => s.student_id === val);
      if (!stu) return;
      // 写入表单字段，确保后端能解析 student_id 或 student_no
      this.formData.student_id = stu.student_id;
      if (stu.student_no) this.formData.student_no = stu.student_no;
    },

    resetForm() {
      this.formData = {};
      this.currentRecord = {};
    },

    getPrimaryKeyValue(row) {
      const primaryKeys = {
        students: "student_id",
        university_grades: "student_id",
        exam_scores: "score_id",
        class_performance: "performance_id",
        historical_grades: "grade_id",
      };
      const key = primaryKeys[this.tableConfig.selectedTable];
      return row[key];
    },

    isPrimaryKey(prop) {
      const primaryKeys = {
        students: "student_id",
        university_grades: "student_id",
        exam_scores: "score_id",
        class_performance: "performance_id",
        historical_grades: "grade_id",
      };
      return prop === primaryKeys[this.tableConfig.selectedTable];
    },

    isSelectColumn(prop) {
      const selectColumns = [
        "gender",
        "grade",
        "class",
        "status",
        "score_level",
        "semester",
        "academic_year",
        "grade_level",
      ];
      return selectColumns.includes(prop);
    },

    getColumnOptions(prop) {
      // 1) 优先使用后端去重接口缓存（与数据库一致）
      const cache = this.tableConfig.distinctOptions || {};
      if (Array.isArray(cache[prop]) && cache[prop].length) {
        return cache[prop];
      }
      // 2) 其次从当前加载的数据中动态提取选项
      try {
        const rows = Array.isArray(this.tableConfig.tableData)
          ? this.tableConfig.tableData
          : [];
        const vals = Array.from(
          new Set(
            rows
              .map((r) => r?.[prop])
              .filter((v) => v !== null && v !== undefined && v !== "")
              .map((v) => String(v)),
          ),
        );
        if (vals.length) {
          const collator = new Intl.Collator("zh-CN", {
            numeric: true,
            sensitivity: "base",
          });
          return vals.sort(collator.compare);
        }
      } catch (e) {
        /* ignore */
      }

      // 3) 回退仅提供通用项；年级/班级不再硬编码
      const defaults = {
        gender: ["男", "女"],
        status: ["在读", "休学", "毕业", "转学"],
        score_level: ["A", "B", "C", "D", "E"],
        semester: ["第一学期", "第二学期"],
        academic_year: ["2023-2024", "2024-2025"],
        grade_level: ["优秀", "良好", "中等", "及格", "不及格"],
      };
      if (prop === "grade" || prop === "class") return [];
      return defaults[prop] || [];
    },
  },
};
</script>

<style scoped>
.visualization {
  padding: 20px;
}

.visualization-tabs {
  margin-bottom: 20px;
}

.chart-card,
.filter-card,
.table-card,
.control-panel {
  margin-bottom: 20px;
  background: #fff;
  border-radius: 6px;
  padding: 12px 16px;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.04);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chart-title,
.table-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}

.filter-container {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: nowrap; /* 强制一行显示，必要时使用滚动或响应式断点 */
  gap: 8px;
}

.search-section,
.action-section {
  display: flex;
  align-items: center;
  gap: 10px;
}

.filter-container .action-section {
  margin-left: 8px;
}

.filter-container > .control-item,
.filter-container > .action-section {
  flex: 1 1 0%;
  min-width: 0; /* allow children to shrink */
}

.control-input >>> .el-input__inner,
.control-input >>> .el-select .el-input__inner {
  width: 100%;
}

.control-input {
  width: 70%;
}

.action-section {
  display: flex;
  justify-content: center;
}
.action-wrap {
  display: flex;
  gap: 12px;
}

/* 使 control-panel 内的控件高度、圆角与表格区域一致（将图像1 -> 图像2 风格） */
.control-panel .el-select .el-input__inner,
.control-panel .el-input__inner,
.control-panel .el-input-number__wrapper,
.control-panel .el-input,
.filter-card .el-select .el-input__inner {
  height: 38px;
  line-height: 38px;
  padding: 6px 12px;
  border-radius: 8px;
}

.control-panel .el-button,
.filter-card .el-button {
  border-radius: 8px;
  padding: 6px 14px;
  min-width: 96px;
}

.control-panel .el-button--primary,
.filter-card .el-button--primary {
  background-color: #409eff;
  border-color: #409eff;
  color: #fff;
}
.control-panel .el-button--success,
.filter-card .el-button--success {
  background-color: #67c23a;
  border-color: #67c23a;
  color: #fff;
}
.control-panel .el-button--info,
.filter-card .el-button--info {
  background-color: #909399;
  border-color: #909399;
  color: #fff;
}

/* 让控件在一行内垂直居中，保持与图像2示例一致 */
.filter-container .search-section,
.filter-container .action-section {
  align-items: center;
}

.chart-container {
  height: 400px;
  width: 100%;
  padding: 8px 0;
  contain: layout paint size;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
}

.chart-container.small {
  height: 300px;
}

.table-wrapper {
  overflow: hidden;
}

.pagination-container {
  margin-top: 20px;
  display: flex;
  justify-content: center;
}

.error-container,
.empty-container {
  padding: 40px;
  text-align: center;
}

@media (max-width: 768px) {
  .filter-container {
    flex-direction: column;
    align-items: stretch;
  }

  .search-section,
  .action-section {
    justify-content: center;
    flex-wrap: wrap;
  }
}

/* 当宽度不足时，允许横向滚动以保持一行布局 */
@media (min-width: 769px) {
  .control-panel {
    overflow-x: auto;
  }
}

/* control-panel 左侧标签样式 */
.control-item {
  display: flex;
  align-items: center;
  gap: 4px;
}
.control-label {
  display: inline-block;
  width: auto; /* 由内容决定宽度，避免强制换行 */
  color: #606266;
  font-size: 14px;
  text-align: left;
  white-space: nowrap; /* 保持文字在一行显示 */
  margin-right: 8px;
}

@media (max-width: 900px) {
  .control-label {
    width: auto;
  }
  .filter-container {
    gap: 10px;
  }
}
</style>
