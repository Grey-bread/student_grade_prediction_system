"""
模型训练路由

职责：
- 提供基于数据库数据的训练接口（POST /train）
- 提供已保存模型列表（GET /models）
- 提供训练数据统计（GET /data-stats）

注意：
- 当前示例仅返回评估结果与可视化，不实际持久化模型（可按需开启）
"""

# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from database import fetch_all, execute_query, fetch_one
from services.prediction import PredictionService
from services.preprocessing import preprocess_df
from services.model_selection import ModelSelector
import pandas as pd
import numpy as np
import traceback
import sys
import pickle
import os
from datetime import datetime
from routes.analysis_routes import get_table_data, get_primary_key_column

training_bp = Blueprint('training_bp', __name__)

# 模型保存目录
MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'models')
os.makedirs(MODEL_DIR, exist_ok=True)

@training_bp.route('/train', methods=['POST'])
def train_model():
    """
    训练成绩预测模型（支持从数据库加载数据）。
    入参 JSON：
    - targetColumn: 目标列（默认 total_score）
    - testSize: 测试集比例（0-1，默认 0.2）
    - dataSource: 数据源（当前支持 database）
    """
    try:
        data = request.get_json(force=True)
        target_column = data.get('targetColumn', 'total_score')
        test_size = float(data.get('testSize', 0.2))
        data_source = data.get('dataSource', 'database')  # database 或 upload
        table_override = data.get('table')  # 可选：自定义表名

        print(f"[TRAIN] 开始训练模型 - 目标列: {target_column}, 测试集比例: {test_size}")
        
        # 从数据库加载训练数据
        if table_override:
            # 通用：直接从指定表加载数据
            df = get_table_data(table_override)
            if df is None or df.empty:
                return jsonify({'status': 'error', 'message': f'表 {table_override} 无数据可用于训练'}), 400
            # 仅保留数值/分类列，由预处理负责编码
            # 下方将检查目标列是否存在
        elif data_source == 'database':
            # 查询历史成绩数据，联合学生信息
            query = """
                SELECT 
                    s.student_id,
                    s.gender,
                    s.grade,
                    s.class,
                    hg.course_id,
                    hg.semester,
                    hg.academic_year,
                    hg.midterm_score,
                    hg.final_score,
                    hg.usual_score,
                    hg.total_score,
                    hg.grade_level,
                    hg.ranking
                FROM historical_grades hg
                JOIN students s ON hg.student_id = s.student_id
                WHERE hg.total_score IS NOT NULL
                LIMIT 5000
            """
            
            print("[TRAIN] 从数据库查询训练数据...")
            rows = fetch_all(query)
            
            if not rows or len(rows) == 0:
                return jsonify({
                    'status': 'error',
                    'message': '数据库中没有可用的训练数据'
                }), 400
            
            # 转换为DataFrame
            df = pd.DataFrame(rows)
            print(f"[OK] 成功加载 {len(df)} 条训练数据")
            print(f"[INFO] 数据列: {df.columns.tolist()}")
            
        else:
            return jsonify({
                'status': 'error',
                'message': '暂不支持上传文件训练'
            }), 400
        
        # 检查目标列是否存在
        if target_column not in df.columns:
            available_cols = df.select_dtypes(include=['int64', 'float64']).columns.tolist()
            return jsonify({
                'status': 'error',
                'message': f'目标列 {target_column} 不存在，可用的数值列: {available_cols}'
            }), 400
        
        # 使用预测服务进行训练
        prediction_service = PredictionService()

        print("[TRAIN] 开始模型训练...")
        result = prediction_service.train_predict(df, target_col=target_column, test_size=test_size)

        # 保存模型（示例关闭，如需保存请取消注释）
        model_filename = f"model_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"
        model_path = os.path.join(MODEL_DIR, model_filename)

        print(f"[OK] 模型训练完成")
        print(f"[METRIC] R²: {result['metrics']['r2']:.4f}")
        print(f"[METRIC] MAE: {result['metrics']['mae']:.4f}")
        print(f"[METRIC] RMSE: {result['metrics']['rmse']:.4f}")
        
        # 返回训练结果
        return jsonify({
            'status': 'success',
            'message': '模型训练完成',
            'data': {
                'metrics': result['metrics'],
                'model_results': result['model_results'],
                'best_params': result['best_params'],
                'feature_importance': result['feature_importance'][:10] if result['feature_importance'] else [],
                'visualizations': result['visualizations'],
                'model_file': model_filename,
                'training_samples': len(df),
                'target_column': target_column
            }
        }), 200
        
    except Exception as e:
        print(f"[ERR] 训练失败: {str(e)}")
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'训练失败: {str(e)}'
        }), 500


@training_bp.route('/predict-table', methods=['POST'])
def predict_table():
    """
    基于指定表进行训练与预测：
    - 先对表数据进行预处理
    - 自动或按 targetColumn 选择目标列
    - 评估模型（留出集）并返回指标
    - 在全量样本上拟合并给出预测值（含对目标缺失样本的重点返回）

    入参 JSON：
    - table: 表名（必填）
    - targetColumn: 目标列（可选，默认自动猜测包含 score/grade/final 的列）
    - testSize: 测试集比例（默认0.2）
    - previewLimit: 预测预览条数（默认50）
    """
    try:
        data = request.get_json(force=True)
        table_name = data.get('table')
        target_column = data.get('targetColumn')
        test_size = float(data.get('testSize', 0.2))
        preview_limit = int(data.get('previewLimit', 50))

        if not table_name:
            return jsonify({'status': 'error', 'message': '缺少参数: table'}), 400

        # 加载表数据
        df_raw = get_table_data(table_name)
        if df_raw is None or df_raw.empty:
            return jsonify({'status': 'error', 'message': f'表 {table_name} 无可用数据'}), 400

        # 记录目标列缺失的样本，用于后续重点返回（仅在提供目标列时）
        missing_mask = None
        if target_column and target_column in df_raw.columns:
            missing_mask = df_raw[target_column].isna()

        # 预处理（去重/缺失填充/异常值/编码）
        df_proc, encoders = preprocess_df(df_raw)

        # 限定与校验目标列：必须手动指定；若存在四个高数目标列，则必须从其中选择
        allowed_targets = ['first_calculus_score', 'second_calculus_score', 'third_calculus_score', 'calculus_avg_score']
        allowed_in_df = [c for c in allowed_targets if c in df_proc.columns]

        if not target_column:
            # 不再自动识别，强制前端手动选择
            if allowed_in_df:
                return jsonify({'status': 'error', 'message': f'请指定目标列（可选: {", ".join(allowed_in_df)}）'}), 400
            return jsonify({'status': 'error', 'message': '请指定目标列'}), 400
        
        # 指定的目标列必须存在
        if target_column not in df_proc.columns:
            return jsonify({'status': 'error', 'message': f'目标列 {target_column} 不存在于表 {table_name}'}), 400
        
        # 若存在允许集合，则强制限定
        if allowed_in_df and target_column not in allowed_in_df:
            return jsonify({'status': 'error', 'message': f'目标列必须从 {", ".join(allowed_in_df)} 中选择'}), 400

        # 前置校验已覆盖不存在情况

        # 组装训练数据
        X_all = df_proc.drop(columns=[target_column])
        y_all = df_proc[target_column]
        feature_names = X_all.columns.tolist()

        # 划分评估集
        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X_all.values, y_all.values, test_size=max(min(test_size, 0.9), 0.05), random_state=42)

        # 选择模型并评估
        selector = ModelSelector()
        best_model, model_results, best_params = selector.select_best_model(X_train, y_train)
        y_pred = best_model.predict(X_test)

        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        import numpy as np
        metrics = {
            'r2': float(r2_score(y_test, y_pred)),
            'mae': float(mean_absolute_error(y_test, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred)))
        }

        # 在全量数据上重新拟合获取全量预测（便于给前端展示）
        best_model.fit(X_all.values, y_all.values)
        y_pred_all = best_model.predict(X_all.values)

        # 主键列用于拼装预览（若无则不返回ID）
        pk = get_primary_key_column(table_name)
        preview_rows = []
        try:
            n = min(preview_limit, len(y_all))  # 使用处理后的样本长度，避免越界
            for i in range(n):
                row = {
                    'predicted': float(y_pred_all[i]),
                    'actual': float(y_all.iloc[i]) if not pd.isna(y_all.iloc[i]) else None
                }
                # 优先从预处理后的数据中取主键，保证长度一致
                if pk and pk in df_proc.columns:
                    row[pk] = df_proc.iloc[i][pk]
                preview_rows.append(row)
        except Exception:
            pass

        # 目标缺失样本的预测（如果存在）
        predicted_missing = []
        try:
            if missing_mask is None and target_column in df_raw.columns:
                missing_mask = df_raw[target_column].isna()
            if missing_mask is not None and missing_mask.any():
                idxs = np.where(missing_mask.values)[0].tolist()
                for i in idxs[:preview_limit]:
                    row = {'predicted': float(y_pred_all[i])}
                    if pk in df_raw.columns:
                        row[pk] = df_raw.iloc[i][pk]
                    predicted_missing.append(row)
        except Exception:
            pass

        # 特征重要性
        fi = selector.get_feature_importance(best_model, feature_names)
        fi_records = None
        if fi is not None:
            # 确保可序列化
            fi_records = []
            try:
                for r in fi.to_dict('records'):
                    fi_records.append({
                        'feature': str(r.get('feature')),
                        'importance': float(r.get('importance')) if r.get('importance') is not None else 0.0
                    })
            except Exception:
                pass

        # 统一将 numpy 类型转换为原生 Python，避免 jsonify 报错
        def to_py(v):
            try:
                if isinstance(v, (np.integer,)):
                    return int(v)
                if isinstance(v, (np.floating,)):
                    return float(v)
                if isinstance(v, (np.ndarray,)):
                    return v.tolist()
                return v
            except Exception:
                return v

        # 规范化预览中的主键与数值类型
        if isinstance(preview_rows, list):
            for row in preview_rows:
                for k in list(row.keys()):
                    row[k] = to_py(row[k])
        if isinstance(predicted_missing, list):
            for row in predicted_missing:
                for k in list(row.keys()):
                    row[k] = to_py(row[k])

        # ===== 可视化派生数据 =====
        try:
            actual_list = [float(v) for v in y_all.tolist()]
            predicted_list = [float(v) for v in y_pred_all.tolist()]
            # 残差（预测-实际）
            residuals = [float(p - a) for p, a in zip(predicted_list, actual_list)]

            # 校准曲线：按预测分位数分箱
            import numpy as np
            try:
                q = np.quantile(predicted_list, np.linspace(0, 1, 11))
                # 去重以防所有预测值相同
                q = np.unique(q)
                if len(q) < 2:
                    q = np.array([min(predicted_list)-1, max(predicted_list)+1])
                bin_idx = np.digitize(predicted_list, q[1:-1], right=False)
                bins = max(bin_idx)+1 if len(predicted_list)>0 else 0
                avg_pred, avg_actual, centers = [], [], []
                for b in range(bins):
                    idxs = [i for i, bi in enumerate(bin_idx) if bi == b]
                    if not idxs:
                        avg_pred.append(None); avg_actual.append(None); centers.append(None)
                    else:
                        ap = float(np.mean([predicted_list[i] for i in idxs]))
                        aa = float(np.mean([actual_list[i] for i in idxs]))
                        avg_pred.append(ap); avg_actual.append(aa)
                        lo = q[b]; hi = q[b+1] if b+1 < len(q) else q[-1]
                        centers.append(float((lo+hi)/2))
                calibration = { 'centers': centers, 'avg_pred': avg_pred, 'avg_actual': avg_actual }
            except Exception:
                calibration = { 'centers': [], 'avg_pred': [], 'avg_actual': [] }

            # 分数段热力（预测段×实际段）
            bands = [(0,60),(60,70),(70,80),(80,90),(90,100.0000001)]
            band_labels = ['<60','60-70','70-80','80-90','90-100']
            def band_of(v: float):
                for i,(lo,hi) in enumerate(bands):
                    if v >= lo and v < hi: return i
                return None
            heat_values = []  # [pred_band_idx, actual_band_idx, count]
            from collections import Counter
            cnt = Counter()
            for p, a in zip(predicted_list, actual_list):
                pb, ab = band_of(p), band_of(a)
                if pb is not None and ab is not None:
                    cnt[(pb,ab)] += 1
            for i in range(len(band_labels)):
                for j in range(len(band_labels)):
                    heat_values.append([i, j, int(cnt.get((i,j), 0))])

            # 分年级误差（若联接得到）
            error_by_grade = []
            try:
                # 使用预处理后的 student_id，保证长度与 actual/predicted 一致
                if 'student_id' in df_proc.columns:
                    st = get_table_data('students')
                    if st is not None and not st.empty and 'student_id' in st.columns:
                        df_join = pd.DataFrame({
                            'student_id': df_proc['student_id'].values,
                            'actual': actual_list,
                            'predicted': predicted_list
                        })
                        dfj = df_join.merge(st[['student_id','grade']], on='student_id', how='left')
                        if 'grade' in dfj.columns:
                            # 使用聚合避免 groupby.apply 的行为变化警告
                            dfj2 = dfj.copy()
                            dfj2['abs_err'] = (dfj2['predicted'] - dfj2['actual']).abs()
                            grp = dfj2.groupby('grade', dropna=False).agg(
                                mae=('abs_err', 'mean'),
                                count=('abs_err', 'size')
                            ).reset_index()
                            error_by_grade = [
                                {'name': str(r['grade']), 'mae': float(r['mae']), 'count': int(r['count'])}
                                for _, r in grp.iterrows()
                            ]
            except Exception:
                error_by_grade = []

            # 最大误差样本（Top10）
            top_abs_errors = []
            try:
                diffs = [abs(p-a) for p,a in zip(predicted_list, actual_list)]
                idx_sorted = np.argsort(diffs)[::-1][:10].tolist()
                for i in idx_sorted:
                    rec = {'predicted': predicted_list[i], 'actual': actual_list[i], 'abs_error': float(diffs[i])}
                    if pk and pk in df_proc.columns:
                        rec[pk] = to_py(df_proc.iloc[i][pk])
                    top_abs_errors.append(rec)
            except Exception:
                pass

            visualizations = {
                'residuals': residuals,
                'calibration': calibration,
                'band_heatmap': { 'labels': band_labels, 'values': heat_values },
                'error_by_grade': error_by_grade,
                'top_abs_errors': top_abs_errors
            }
        except Exception:
            visualizations = None

        return jsonify({
            'status': 'success',
            'message': '训练与预测完成',
            'data': {
                'table': table_name,
                'target_column': target_column,
                'training_samples': int(len(y_all)),
                'metrics': {k: to_py(v) for k, v in metrics.items()},
                'model_results': {k: {kk: to_py(vv) for kk, vv in vv.items()} for k, vv in model_results.items()},
                'best_params': {k: to_py(v) for k, v in best_params.items()} if isinstance(best_params, dict) else best_params,
                'feature_importance': fi_records,
                'preview': preview_rows,
                'predicted_missing': predicted_missing,
                'visualizations': visualizations
            }
        }), 200

    except Exception as e:
        print(f"[ERR] predict-table 失败: {str(e)}")
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@training_bp.route('/predict-student', methods=['GET'])
def predict_student():
    """
    基于指定表为某个学生进行预测（使用该表训练一个模型）。
    入参（query）：
    - table: 表名（必填）
    - student_id: 学生ID（必填）
    - targetColumn: 目标列（可选）
    - course_id: 课程ID（可选，用于选择该生的某门课记录）
    返回：predicted（预测值）、target_column、metrics、feature_importance（可选）
    """
    try:
        table_name = request.args.get('table')
        student_id = request.args.get('student_id')
        target_column = request.args.get('targetColumn')
        course_id = request.args.get('course_id')

        if not table_name or not student_id:
            return jsonify({'status': 'error', 'message': '缺少参数: table 或 student_id'}), 400

        df_raw = get_table_data(table_name)
        if df_raw is None or df_raw.empty:
            return jsonify({'status': 'error', 'message': f'表 {table_name} 无可用数据'}), 400

        # 筛选该学生数据
        if 'student_id' not in df_raw.columns:
            return jsonify({'status': 'error', 'message': f'表 {table_name} 缺少 student_id 列，无法为学生预测'}), 400
        sdf = df_raw[df_raw['student_id'].astype(str) == str(student_id)].copy()
        if course_id and 'course_id' in sdf.columns:
            sdf = sdf[sdf['course_id'].astype(str) == str(course_id)]
        if sdf.empty:
            return jsonify({'status': 'error', 'message': '该学生在此表中无记录'}), 404

        # 预处理全表并训练模型
        df_proc, _ = preprocess_df(df_raw)
        # 自动/指定目标列（支持中文）
        if not target_column:
            en_keys = ('gpa','grade','score','final','total')
            zh_keys = ('总成绩','总分','分数','成绩','期末','期中','平时','总评')
            cand = []
            for c in df_proc.columns:
                if any(k in str(c) for k in zh_keys):
                    cand.append(c)
            for c in df_proc.columns:
                cl = str(c).lower()
                if any(k in cl for k in en_keys) and c not in cand:
                    cand.append(c)
            if cand:
                target_column = cand[0]
            else:
                nums = df_proc.select_dtypes(include=['int64','float64']).columns.tolist()
                if not nums:
                    return jsonify({'status': 'error', 'message': '无法识别目标列，请提供 targetColumn 或在表中包含成绩列（如“总成绩/总分/分数”等）'}), 400
                target_column = nums[-1]
        if target_column not in df_proc.columns:
            return jsonify({'status': 'error', 'message': f'目标列 {target_column} 不存在'}), 400

        X_all = df_proc.drop(columns=[target_column])
        y_all = df_proc[target_column]
        feature_names = X_all.columns.tolist()

        from sklearn.model_selection import train_test_split
        X_train, X_test, y_train, y_test = train_test_split(X_all.values, y_all.values, test_size=0.2, random_state=42)
        selector = ModelSelector()
        best_model, model_results, best_params = selector.select_best_model(X_train, y_train)
        from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score
        import numpy as np
        y_pred = best_model.predict(X_test)
        metrics = {
            'r2': float(r2_score(y_test, y_pred)),
            'mae': float(mean_absolute_error(y_test, y_pred)),
            'rmse': float(np.sqrt(mean_squared_error(y_test, y_pred)))
        }

        # 在全量数据上重新拟合
        best_model.fit(X_all.values, y_all.values)

        # 用该学生的“最新一条”记录做预测（优先按 grade_id 或 exam_date 排序）
        row = sdf.copy()
        sort_done = False
        for key in ['grade_id', 'score_id']:
            if key in row.columns:
                row = row.sort_values(by=key)
                sort_done = True
                break
        if not sort_done:
            if 'exam_date' in row.columns:
                row['exam_date_parsed'] = pd.to_datetime(row['exam_date'], errors='coerce')
                row = row.sort_values(by='exam_date_parsed')
                sort_done = True
        row_latest = row.iloc[-1:]

        # 将最新记录通过相同预处理对齐（简单做法：在全表预处理后对齐列名，取该行原始映射列）
        # 这里采用再次整体预处理并从 df_proc 中定位行索引的方式（可能不存在一一对应，做列交集对齐）
        # 构造与 X_all 同列的特征行
        feature_cols = list(feature_names)
        row_feat = row_latest.reindex(columns=feature_cols, fill_value=np.nan)
        # 缺失填充（用列均值）
        for c in feature_cols:
            if row_feat[c].isna().any():
                try:
                    mean_val = pd.to_numeric(X_all[c], errors='coerce').mean()
                    row_feat[c] = row_feat[c].fillna(mean_val)
                except Exception:
                    row_feat[c] = row_feat[c].fillna(0)

        pred_val = float(best_model.predict(row_feat.values)[0])

        fi = selector.get_feature_importance(best_model, feature_names)
        fi_records = None
        if fi is not None:
            fi_records = []
            try:
                for r in fi.to_dict('records'):
                    fi_records.append({
                        'feature': str(r.get('feature')),
                        'importance': float(r.get('importance')) if r.get('importance') is not None else 0.0
                    })
            except Exception:
                pass

        return jsonify({
            'status': 'success',
            'data': {
                'table': table_name,
                'student_id': student_id,
                'course_id': course_id,
                'target_column': target_column,
                'predicted': float(pred_val),
                'metrics': {k: float(v) for k, v in metrics.items()},
                'feature_importance': fi_records
            }
        }), 200

    except Exception as e:
        print(f"[ERR] predict-student 失败: {str(e)}")
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@training_bp.route('/models', methods=['GET'])
def get_models():
    """
    获取已训练的模型列表
    """
    try:
        models = []
        if os.path.exists(MODEL_DIR):
            for filename in os.listdir(MODEL_DIR):
                if filename.endswith('.pkl'):
                    filepath = os.path.join(MODEL_DIR, filename)
                    stat = os.stat(filepath)
                    models.append({
                        'filename': filename,
                        'size': stat.st_size,
                        'created_at': datetime.fromtimestamp(stat.st_ctime).strftime('%Y-%m-%d %H:%M:%S')
                    })
        
        return jsonify({
            'status': 'success',
            'data': models
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@training_bp.route('/data-stats', methods=['GET'])
def get_training_data_stats():
    """
    获取训练数据统计信息
    """
    try:
        # 方案优先级：university_grades（新表，真实数据）> historical_grades（旧表）

        # 学生总人数（来自学生表，DB 优先，失败则 CSV）
        total_students_all = 0
        try:
            row = fetch_one("SELECT COUNT(*) AS total_students_all FROM students")
            if row and 'total_students_all' in row:
                total_students_all = int(row['total_students_all'] or 0)
        except Exception:
            st = get_table_data('students')
            if st is not None and not st.empty:
                try:
                    total_students_all = int(len(st))
                except Exception:
                    total_students_all = 0

        # 优先用 university_grades 统计
        ug = get_table_data('university_grades')
        if ug is not None and not ug.empty:
            try:
                df = ug.copy()
                # 已在 get_table_data 中规范化过 calculus_avg_score，稳妥起见再转数值
                df['calculus_avg_score'] = pd.to_numeric(df.get('calculus_avg_score'), errors='coerce')
                overall = {
                    'total_records': int(len(df)),
                    'total_students': int(df['student_id'].nunique()) if 'student_id' in df.columns else None,
                    # UG 为单科数据，无课程列；置为 None（前端会显示 0）或可置为 1 表示单课程
                    'total_courses': None,
                    'avg_score': float(df['calculus_avg_score'].dropna().mean()) if df['calculus_avg_score'].notna().any() else None,
                    'min_score': float(df['calculus_avg_score'].dropna().min()) if df['calculus_avg_score'].notna().any() else None,
                    'max_score': float(df['calculus_avg_score'].dropna().max()) if df['calculus_avg_score'].notna().any() else None,
                }
                overall['total_students_all'] = total_students_all
                # UG 无学期字段，返回空列表
                return jsonify({'status': 'success', 'data': {'overall': overall, 'by_semester': []}}), 200
            except Exception:
                pass

        # 回退到 historical_grades（旧表）
        # 先尝试数据库统计
        try:
            stats_query = """
                SELECT 
                    COUNT(*) as total_records,
                    COUNT(DISTINCT student_id) as total_students,
                    COUNT(DISTINCT course_id) as total_courses,
                    AVG(total_score) as avg_score,
                    MIN(total_score) as min_score,
                    MAX(total_score) as max_score
                FROM historical_grades
                WHERE total_score IS NOT NULL
            """
            stats = fetch_all(stats_query)
        except Exception:
            stats = None

        # 按学期统计（DB 优先，失败则 CSV 回退）
        try:
            semester_stats_query = """
                SELECT 
                    semester,
                    academic_year,
                    COUNT(*) as record_count,
                    AVG(total_score) as avg_score
                FROM historical_grades
                WHERE total_score IS NOT NULL
                GROUP BY semester, academic_year
                ORDER BY academic_year DESC, semester
                LIMIT 10
            """
            semester_stats = fetch_all(semester_stats_query)
        except Exception:
            semester_stats = []
            hg = get_table_data('historical_grades')
            if hg is not None and not hg.empty:
                try:
                    df = hg.copy()
                    df['total_score'] = pd.to_numeric(df.get('total_score'), errors='coerce')
                    grp = df.dropna(subset=['total_score']).groupby(['academic_year','semester']).agg(
                        record_count=('total_score','count'),
                        avg_score=('total_score','mean')
                    ).reset_index()
                    grp = grp.sort_values(['academic_year','semester'], ascending=[False, True]).head(10)
                    semester_stats = [
                        {
                            'academic_year': str(r['academic_year']),
                            'semester': str(r['semester']),
                            'record_count': int(r['record_count']),
                            'avg_score': float(r['avg_score']) if pd.notna(r['avg_score']) else None
                        }
                        for _, r in grp.iterrows()
                    ]
                except Exception:
                    semester_stats = []

        # overall（DB 优先，失败则 CSV 回退）
        if stats and len(stats) > 0 and isinstance(stats[0], dict):
            overall = dict(stats[0])
        else:
            overall = {}
            hg = get_table_data('historical_grades')
            if hg is not None and not hg.empty:
                try:
                    df = hg.copy()
                    df['total_score'] = pd.to_numeric(df.get('total_score'), errors='coerce')
                    overall = {
                        'total_records': int(df['total_score'].notna().sum()),
                        'total_students': int(df['student_id'].nunique()) if 'student_id' in df.columns else None,
                        'total_courses': int(df['course_id'].nunique()) if 'course_id' in df.columns else None,
                        'avg_score': float(df['total_score'].dropna().mean()) if df['total_score'].notna().any() else None,
                        'min_score': float(df['total_score'].dropna().min()) if df['total_score'].notna().any() else None,
                        'max_score': float(df['total_score'].dropna().max()) if df['total_score'].notna().any() else None,
                    }
                except Exception:
                    overall = {}

        if isinstance(overall, dict):
            overall['total_students_all'] = total_students_all

        return jsonify({'status': 'success', 'data': {'overall': overall, 'by_semester': semester_stats}}), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500
