"""
模型训练路由

职责：
- 提供基于数据库真实数据的训练接口（POST /train）
- 提供已保存模型列表（GET /models）
- 提供训练数据统计（GET /data-stats）

注意：
- 当前示例仅返回评估结果与可视化，不实际持久化模型（可按需开启）
"""

# -*- coding: utf-8 -*-
from flask import Blueprint, request, jsonify
from database import fetch_all, execute_query, fetch_one
from services.prediction import PredictionService
import pandas as pd
import traceback
import sys
import pickle
import os
from datetime import datetime

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

        print(f"[TRAIN] 开始训练模型 - 目标列: {target_column}, 测试集比例: {test_size}")
        
        # 从数据库加载训练数据
        if data_source == 'database':
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
        # 统计可用的训练数据量
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

        # 学生总人数（来自学生表，新增学生应立即反映）
        total_students_all = 0
        try:
            row = fetch_one("SELECT COUNT(*) AS total_students_all FROM students")
            if row and 'total_students_all' in row:
                total_students_all = int(row['total_students_all'] or 0)
        except Exception:
            # 如果 students 表不存在或查询失败，兜底为 0，避免接口报错
            total_students_all = 0
        
        # 按学期统计
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
        
        overall = stats[0] if stats else {}
        # 增补 overall 字段：学生总人数（来自 students 表）
        if isinstance(overall, dict):
            overall['total_students_all'] = total_students_all

        return jsonify({
            'status': 'success',
            'data': {
                'overall': overall,
                'by_semester': semester_stats
            }
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
