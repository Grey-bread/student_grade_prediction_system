# 学生成绩分析与预测系统 · 使用指南（Windows）

本项目提供“学生成绩分析、可视化与预测”的端到端方案，含 Flask 后端与 Vue 3 前端。支持使用真实数据库（MySQL）或 CSV 数据回退，内置导出报告/导出数据、学生反馈、教师面板、数据管理、模型训练/预测等功能。

> 适用读者：教务/老师/数据分析同学；部署者/开发者。

---

## 1. 技术栈
- 后端：Flask + pandas + scikit-learn + PyJWT + mysql-connector-python
- 前端：Vue 3 + Element Plus + Axios + ECharts
- 数据：MySQL（优先）/ CSV 回退（`database_datasets/*.csv`）

---

## 2. 目录结构
```
flask_backend/              # Flask 后端
  app.py                    # 应用入口
  database.py               # MySQL 连接/CRUD 与 .env 加载
  requirements.txt          # 后端依赖
  .env                      # 环境变量
  routes/                   # 业务接口
    analysis_routes.py      # 分析/统计/导出等接口
    teacher_routes.py       # 登录/注册/头像/教师面板
    prediction_routes.py    # 预测接口
    training_routes.py      # 训练接口
  services/                 # 业务逻辑服务层
  uploads/                  # 文件上传目录

database_datasets/          # CSV 回退数据（无数据库时也可运行）

vue_frontend/               # Vue 前端
  src/                      # 页面与逻辑
  public/
  package.json
  vue.config.js             # 开发代理到后端 http://127.0.0.1:5000
```

---

## 3. 快速开始

### 3.1 后端（Flask）
1) 安装依赖（建议在项目根目录下使用自带虚拟环境或自行创建）
```powershell
# 如需自建虚拟环境（可选）
# python -m venv .venv
# .\.venv\Scripts\Activate.ps1

# 安装依赖
cd "E:\Code\student_grade_prediction_system\flask_backend"
python -m pip install -r requirements.txt
```

2) 配置环境变量
```properties
# flask_backend/.env 示例
DB_HOST=127.0.0.1
DB_USER=root
DB_PASSWORD=你的数据库密码
DB_NAME=student_grades
JWT_SECRET=请填写随机字符串
```
> 未配置/数据库不可用时，后端多数分析 API 会自动回退使用 `database_datasets` 下的 CSV 数据。

3) 启动后端
```powershell
python app.py
```
默认监听 `http://127.0.0.1:5000`，所有接口以 `/api` 开头（详见第 5 节）。

### 3.2 前端（Vue 3）
```powershell
cd "E:\Code\student_grade_prediction_system\vue_frontend"
npm install
npm run serve
```
开发地址默认 `http://localhost:8080`，已通过 `vue.config.js` 代理到后端 `http://127.0.0.1:5000/api`。

---

## 4. 使用流程速览
1) 浏览器打开前端地址，先注册/登录老师账号（头像上传支持，登录后会立即显示头像）。
2) 进入“数据表可视化”：
   - 选择表（学生信息/历史成绩/考试成绩/课堂表现），支持搜索/分页/增删改/导出 CSV。
3) 进入“图表可视化”：
   - 趋势图/分布图/进步图/雷达图/饼图可切换数据表和学生；支持导出分析报告（ZIP）。
4) “数据分析”：
   - 选择白名单内表（课堂表现/历史成绩/考试成绩/学生信息），查看统计与相关性热力图；支持导出报告（ZIP）。
5) “学生反馈”：
   - 使用真实数据生成个性化反馈（优势/待提升/建议/课堂表现对比/最近考试）。
6) “教师面板/训练/预测”：
   - 教师看板汇总指标；训练可选择模型与参数；预测支持单次/批量，返回可视化结果。

---

## 5. 关键后端接口（节选）
前缀均为 `/api`。

- 分析类（`/api/analysis`）
  - `GET /tables`：表清单；数据库不可用时会回退到 CSV 目录推断
  - `GET /statistics?table=...`：数值/分类特征统计
  - `GET /correlation?table=...`：相关性热力图数据
  - `GET /student-trends?table=...&student_id=...`：学生趋势
  - `GET /class-trends?table=...`：班级趋势
  - `GET /subject-comparison?table=...`：学科对比
  - `GET /student-progress?table=...&student_id=...`：进步曲线
  - `GET /radar-data?table=class_performance&student_id=...`：课堂表现雷达
  - `GET /grade-distribution?table=exam_scores`：等级分布饼图
  - `GET /table-data?table=...`：数据表数据（用于前端表格）
  - 导出：
    - `GET /export-table?table=students` → CSV 下载
    - `GET /export-report?table=exam_scores&student_id=1` → ZIP 下载（包含原始采样/描述性统计/相关性/非空统计/雷达图 JSON 展平为 CSV/元信息）

- 教师/用户类（`/api/teacher`）
  - `POST /register`、`POST /login`、`GET /info`、`POST /avatar`、`POST /change-password`、`GET /login-history`

- 模型/训练/预测（`/api/training`、`/api/prediction`）
  - 根据页面发起的选项调用，返回训练过程图像（base64）与评估指标或预测结果。

> 注：实际字段命名以代码为准，接口都已设置异常兜底和 CSV 回退，在数据库尚未准备好时也能体验核心功能。

---

## 6. 功能与页面指南

### 6.1 登录 / 注册 / 头像
- 登录成功后会立即获取用户信息与头像并显示；更换头像后本地缓存更新并广播刷新。
- 后端为 `teachers` 表自动做 avatar 列检查/迁移；记录登录历史。

### 6.2 数据表可视化
- 表白名单：`students`、`historical_grades`、`exam_scores`、`class_performance`
- 支持：搜索、分页、增删改、导出 CSV（按钮“导出数据”）

### 6.3 图表可视化
- 趋势图（个人/班级/学科对比）、成绩分布、进步曲线、课堂表现雷达、等级分布饼图
- 课堂表现雷达会将英文字段映射成中文并自动去重（不会再出现“两个分数”）
- 按钮“导出报告”：下载 ZIP 分析报告

### 6.4 数据分析
- 表白名单与上面一致；显示统计信息与相关性热力图
- 按钮“导出报告”：同样下载 ZIP 报告

### 6.5 学生反馈
- 基于真实数据输出：基本信息、历史成绩概览、最近考试、课堂表现（学生均值 vs 全班均值）、优势/待提升/建议

### 6.6 数据管理
- 上传历史、数据源与采集任务（后端与前端均已打通）。上传文件保存在 `flask_backend/uploads/`。

### 6.7 训练与预测
- 训练过程返回指标与图（base64），预测可按表或单条数据进行，并显示图表化结果。

---

## 7. 导出功能说明

### 7.1 导出数据（CSV）
- 页面：数据表可视化 → 右上角“导出数据”
- 接口：`GET /api/analysis/export-table?table=students`
- 编码：`UTF-8`

### 7.2 导出分析报告（ZIP）
- 页面：数据表可视化/图表可视化/数据分析 → “导出报告”
- 接口示例：`GET /api/analysis/export-report?table=exam_scores&student_id=1`
- 内容：
  - `data/raw_sample.csv`：原始数据采样（前 2000 行）
  - `analysis/describe.csv`：描述性统计
  - `analysis/correlation.csv`：数值列相关性
  - `analysis/nonnull_counts.csv`：各列非空统计
  - `charts/radar_indicators.csv` 与 `charts/radar_series.csv`
  - `meta.json`：生成时间、表名、学生ID、趋势类型

> 如果你更希望导出中文表头的 CSV，可在后端 `/export-table` 中将列名通过 `feature_name_map` 做一次映射（需求明确后可补）。

---

## 8. 常见问题与排查（Windows）

- 后端启动失败，终端 Exit Code: 1
  - 多数是依赖或数据库问题。请先安装依赖：
    ```powershell
    cd "E:\Code\student_grade_system_complete - 副本\flask_backend"
    python -m pip install -r requirements.txt
    python app.py
    ```
  - 若提示数据库连接失败：
    - 启动 MySQL；确认 `.env`（DB_HOST/DB_USER/DB_PASSWORD/DB_NAME）正确；数据库存在。
    - 未配置数据库也可以运行多数分析页面（自动回退 CSV），只是无法进行需要写入的操作。

- 前端 401 或 Token 过期
  - 重新登录；可在 axios 拦截器中统一处理 401 自动跳转（可选增强）。

- 端口占用
  - 后端默认 5000，前端默认 8080；如被占用，请调整 `app.py` 或前端启动参数。

- 中文乱码/不可见
  - 后端已设置 `JSON_AS_ASCII=False` 和响应头，导出的 CSV 使用 UTF-8；如 Excel 查看乱码，建议用“数据-从文本导入-UTF-8”。

---

## 9. 生产部署建议
- 后端：使用 WSGI（gunicorn/uwsgi）+ Nginx，设置环境变量与服务化启动（如 NSSM/Windows 服务）。
- 前端：打包 `npm run build`，将 `dist/` 上传到静态资源服务器或 Nginx。
- 安全：配置 JWT 秘钥、数据库账号最小权限、限制上传文件类型与大小。
- 监控：开启访问日志/错误日志；必要时加上 APM 与告警。

---


