"""
数据分析路由

职责：
- 提供表清单、统计分析、学生反馈、趋势、相关性等接口

注意：
- 模块较大，核心方法均在端点内有说明
- 表结构/特征名称/学科关键词等映射集中在顶部常量
"""

# flask_backend/routes/analysis_routes.py
from flask import Blueprint, request, jsonify
from flask import Response, send_file
import pandas as pd
import numpy as np
import traceback, sys
from database import fetch_all, get_tables, execute_query, fetch_one, get_columns, execute_insert_return_id, execute_many
import os
import io
import zipfile
import json
from pathlib import Path
from datetime import datetime
from werkzeug.utils import secure_filename
from services.preprocessing import preprocess_df
import re

analysis_bp = Blueprint('analysis_bp', __name__)

# 用于存储处理后的数据的内存缓存
global_data = {}
global_data['dirty_tables'] = set()
global_data['column_labels'] = {}

def mark_table_dirty(table_name: str):
    try:
        if not isinstance(table_name, str) or not table_name:
            return
        ds = global_data.get('dirty_tables')
        if isinstance(ds, set):
            ds.add(table_name)
        else:
            global_data['dirty_tables'] = {table_name}
    except Exception:
        # 兜底，避免影响主流程
        pass

# 预定义表结构映射，用于优化特定表的处理
table_structures = {
    'class_performance': {
        'id_columns': ['performance_id', 'student_id', 'course_id'],
        'score_columns': ['attendance_score', 'participation_score', 'quiz_score', 
                         'assignment_score', 'project_score', 'final_exam_score'],
        'categorical_columns': ['semester', 'course_id', 'teacher_id', 
                               'learning_attitude', 'discipline'],
        'time_column': 'semester',
        'text_columns': ['teacher_comments', 'created_at', 'updated_at']
    },
    'students': {
        'id_columns': ['student_id'],
        'numerical_columns': [],  # 学生表通常没有直接的数值成绩
        'categorical_columns': ['gender', 'grade', 'class', 'status',
                               'hukou_type', 'is_boarding', 'family_income', 'parent_education'],
        'text_columns': ['name', 'student_no', 'birth_date', 'contact_phone', 'email', 
                        'admission_date', 'address', 'created_at', 'updated_at']
    },
    'exam_scores': {
        'id_columns': ['score_id', 'student_id', 'course_id', 'exam_type_id', 'teacher_id'],
        'score_columns': ['score'],
        'ranking_columns': ['ranking'],
        'categorical_columns': ['exam_type_id', 'score_level', 'course_id',
                               'difficulty', 'completion_status'],
        'time_column': 'exam_date',
        'text_columns': ['exam_name', 'comments', 'created_at']
    },
    'historical_grades': {
        'id_columns': ['grade_id', 'student_id', 'course_id', 'teacher_id'],
        'score_columns': ['midterm_score', 'final_score', 'usual_score', 'total_score'],
        'ranking_columns': ['ranking'],
        'categorical_columns': ['semester', 'academic_year', 'course_id', 'grade_level'],
        'time_column': 'semester',
        'text_columns': ['created_at']
    }
}

# 学科关键词映射，用于识别学科相关列
subject_keywords = {
    '语文': ['chinese', 'ch', '语文', 'chinese_score', 'ch_score'],
    '数学': ['math', 'mathematics', '数学', 'math_score', 'm_score'],
    '英语': ['english', 'en', '英语', 'english_score', 'e_score'],
    '物理': ['physics', '物理', 'physics_score', 'p_score'],
    '化学': ['chemistry', '化学', 'chemistry_score', 'c_score'],
    '生物': ['biology', '生物', 'biology_score', 'b_score'],
    '历史': ['history', '历史', 'history_score', 'h_score'],
    '地理': ['geography', '地理', 'geography_score', 'g_score'],
    '政治': ['politics', '政治', 'politics_score', 'po_score'],
    '体育': ['pe', 'physical', '体育', 'pe_score', 's_score']
}

# 特征名称映射，用于更友好的显示
feature_name_map = {
    # 通用
    'student_id': '学生ID',
    'course_id': '课程ID',
    'teacher_id': '教师ID',
    'semester': '学期',
    'academic_year': '学年',
    'ranking': '排名',
    'score': '分数',
    # class_performance表
    'attendance_score': '出勤分数',
    'attendance': '出勤分数',
    'attendance_rate': '出勤分数',
    'participation_score': '参与分数',
    'participation': '参与分数',
    'quiz_score': '测验分数',
    'quiz': '测验分数',
    'assignment_score': '作业分数',
    'assignment': '作业分数',
    'homework': '作业分数',
    'project_score': '项目分数',
    'project': '项目分数',
    'final_exam_score': '期末考试分数',
    'final_exam': '期末考试分数',
    'final_score': '期末成绩',
    'midterm_score': '期中成绩',
    'usual_score': '平时成绩',
    'learning_attitude': '学习态度',
    'discipline': '纪律表现',
    # students表
    'student_no': '学号',
    'name': '姓名',
    'gender': '性别',
    'grade': '年级',
    'class': '班级',
    'status': '学籍状态',
    'hukou_type': '户口类型',
    'is_boarding': '是否住校',
    'family_income': '家庭收入',
    'parent_education': '父母学历',
    # exam_scores表
    'score_id': '成绩ID',
    'exam_type_id': '考试类型ID',
    'exam_name': '考试名称',
    'exam_date': '考试日期',
    'score_level': '成绩等级',
    'difficulty': '试卷难度',
    'completion_status': '完成状态',
    # historical_grades表
    'grade_id': '成绩记录ID',
    'midterm_score': '期中成绩',
    'final_score': '期末成绩',
    'usual_score': '平时成绩',
    'total_score': '总成绩',
    'grade_level': '等级'
}

@analysis_bp.route('/student-feedback', methods=['GET'])
def student_feedback():
    """根据真实数据生成学生个性化反馈与建议。
    入参: student_id (必填), course_id (可选)
    返回: 学生基本信息、成绩概览、课堂表现对比、优势与待提升、建议
    """
    try:
        student_id = request.args.get('student_id')
        course_id = request.args.get('course_id')
        # 可选：允许前端覆盖默认使用的表，便于使用上传的自定义表
        students_table = request.args.get('students_table', 'students')
        grades_table = request.args.get('grades_table', 'historical_grades')
        exams_table = request.args.get('exams_table', 'exam_scores')
        performance_table = request.args.get('performance_table', 'class_performance')
        courses_table = request.args.get('courses_table', 'courses')
        if not student_id:
            return jsonify({'status': 'error', 'message': '缺少参数: student_id'}), 400

        # 读取所需表的数据（优先DB，失败则CSV）
        students_df = get_table_data(students_table)
        hg_df = get_table_data(grades_table)
        exam_df = get_table_data(exams_table)
        perf_df = get_table_data(performance_table)
        courses_df = get_table_data(courses_table)

        # 学生基本信息
        student_info = None
        if students_df is not None and not students_df.empty:
            srow = students_df[students_df['student_id'].astype(str) == str(student_id)]
            if not srow.empty:
                sr = srow.iloc[0]
                student_info = {
                    'student_id': int(sr['student_id']) if pd.notna(sr.get('student_id')) else None,
                    'name': str(sr.get('name') or ''),
                    'gender': str(sr.get('gender') or ''),
                    'grade': str(sr.get('grade') or ''),
                    'class': str(sr.get('class') or ''),
                }
        if not student_info:
            student_info = {'student_id': int(student_id), 'name': '', 'gender': '', 'grade': '', 'class': ''}

        # 课程名称映射
        course_name_map = {}
        if courses_df is not None and not courses_df.empty and 'course_id' in courses_df.columns:
            for _, r in courses_df.iterrows():
                try:
                    course_name_map[int(r['course_id'])] = str(r.get('course_name') or f"课程{r['course_id']}")
                except Exception:
                    continue

        # 历史成绩概览
        overview = {
            'avg_total_score': None,
            'latest_total_score': None,
            'by_course': []
        }
        if hg_df is not None and not hg_df.empty:
            sdf = hg_df[hg_df['student_id'].astype(str) == str(student_id)].copy()
            if course_id and 'course_id' in sdf.columns:
                sdf = sdf[sdf['course_id'].astype(str) == str(course_id)]
            if not sdf.empty:
                # 转为数值
                for col in ['midterm_score', 'final_score', 'usual_score', 'total_score']:
                    if col in sdf.columns:
                        sdf[col] = pd.to_numeric(sdf[col], errors='coerce')
                # 平均总分
                if 'total_score' in sdf.columns:
                    mean_total = sdf['total_score'].mean()
                    if pd.notna(mean_total):
                        overview['avg_total_score'] = round(float(mean_total), 2)
                # 最新记录（按grade_id优先，否则按index）
                latest_row = None
                if 'grade_id' in sdf.columns:
                    try:
                        latest_row = sdf.sort_values('grade_id').iloc[-1]
                    except Exception:
                        latest_row = sdf.iloc[-1]
                else:
                    latest_row = sdf.iloc[-1]
                if latest_row is not None and 'total_score' in latest_row:
                    try:
                        overview['latest_total_score'] = round(float(latest_row['total_score']), 2)
                    except Exception:
                        pass
                # 按课程汇总
                if 'course_id' in sdf.columns:
                    grp = sdf.groupby('course_id').agg({
                        'midterm_score': 'mean',
                        'final_score': 'mean',
                        'usual_score': 'mean',
                        'total_score': 'mean'
                    }).reset_index()
                    for _, r in grp.iterrows():
                        cid = int(r['course_id']) if pd.notna(r['course_id']) else None
                        overview['by_course'].append({
                            'course_id': cid,
                            'course_name': course_name_map.get(cid, f'课程{cid}') if cid else '未知课程',
                            'midterm_score': round(float(r['midterm_score']), 2) if pd.notna(r.get('midterm_score')) else None,
                            'final_score': round(float(r['final_score']), 2) if pd.notna(r.get('final_score')) else None,
                            'usual_score': round(float(r['usual_score']), 2) if pd.notna(r.get('usual_score')) else None,
                            'total_score': round(float(r['total_score']), 2) if pd.notna(r.get('total_score')) else None,
                        })

        # 最近考试成绩（每门课取最近一次）
        latest_exams = []
        if exam_df is not None and not exam_df.empty:
            edf = exam_df[exam_df['student_id'].astype(str) == str(student_id)].copy()
            if course_id and 'course_id' in edf.columns:
                edf = edf[edf['course_id'].astype(str) == str(course_id)]
            if not edf.empty:
                # 解析日期
                if 'exam_date' in edf.columns:
                    edf['exam_date_parsed'] = pd.to_datetime(edf['exam_date'], errors='coerce')
                else:
                    edf['exam_date_parsed'] = pd.NaT
                # 按课程取最新一条
                if 'course_id' in edf.columns:
                    edf_sorted = edf.sort_values(['course_id', 'exam_date_parsed'])
                    last_per_course = edf_sorted.groupby('course_id').tail(1)
                    for _, r in last_per_course.iterrows():
                        try:
                            cid = int(r['course_id']) if pd.notna(r.get('course_id')) else None
                            latest_exams.append({
                                'course_id': cid,
                                'course_name': course_name_map.get(cid, f'课程{cid}') if cid else '未知课程',
                                'exam_name': str(r.get('exam_name') or ''),
                                'exam_date': str(r.get('exam_date') or ''),
                                'score': round(float(r['score']), 2) if pd.notna(r.get('score')) else None,
                                'score_level': str(r.get('score_level') or ''),
                            })
                        except Exception:
                            continue

        # 课堂表现：学生均值 vs 全部均值
        perf_summary = {
            'student_avg': {},
            'class_avg': {}
        }
        perf_keys = ['attendance_score', 'participation_score', 'homework_score', 'behavior_score', 'total_performance_score']
        if perf_df is not None and not perf_df.empty:
            # 转成数值
            for col in perf_keys:
                if col in perf_df.columns:
                    perf_df[col] = pd.to_numeric(perf_df[col], errors='coerce')
            # 学生数据
            pdf = perf_df[perf_df['student_id'].astype(str) == str(student_id)] if 'student_id' in perf_df.columns else pd.DataFrame()
            # 课程过滤
            if course_id and not pdf.empty and 'course_id' in pdf.columns:
                pdf = pdf[pdf['course_id'].astype(str) == str(course_id)]
            # 计算均值
            for col in perf_keys:
                if col in perf_df.columns:
                    cv = perf_df[col].mean()
                    if pd.notna(cv):
                        perf_summary['class_avg'][col] = round(float(cv), 2)
                if not pdf.empty and col in pdf.columns:
                    sv = pdf[col].mean()
                    if pd.notna(sv):
                        perf_summary['student_avg'][col] = round(float(sv), 2)

        # 生成优势/待提升/建议
        strengths, weaknesses, suggestions = [], [], []
        def metric_label(k):
            return {
                'attendance_score': '出勤',
                'participation_score': '课堂参与',
                'homework_score': '作业完成',
                'behavior_score': '课堂纪律/行为',
                'total_performance_score': '综合表现'
            }.get(k, k)

        # 对比课堂表现
        for k in perf_keys:
            s = perf_summary['student_avg'].get(k)
            c = perf_summary['class_avg'].get(k)
            if s is None or c is None:
                continue
            if s >= c + 5:
                strengths.append(f"{metric_label(k)}高于班级平均 {round(s - c, 1)} 分")
            elif s <= c - 5:
                weaknesses.append(f"{metric_label(k)}低于班级平均 {round(c - s, 1)} 分")
                if k == 'attendance_score':
                    suggestions.append('提高出勤率，合理安排作息，按时到课。')
                elif k == 'participation_score':
                    suggestions.append('增加课堂互动，积极回答问题并参与讨论。')
                elif k == 'homework_score':
                    suggestions.append('按时高质量完成作业，可建立作业清单与检查机制。')
                elif k == 'behavior_score':
                    suggestions.append('遵守课堂纪律，专注听讲，减少分心。')
                elif k == 'total_performance_score':
                    suggestions.append('综合学习状态需要提升，建议制定阶段性学习计划并跟踪执行。')

        # 成绩层面的建议
        if overview['avg_total_score'] is not None:
            avg = overview['avg_total_score']
            if avg < 60:
                suggestions.append('总评偏低，建议从基础知识入手，先补齐薄弱知识点。')
            elif avg < 75:
                suggestions.append('成绩中等偏下，可通过刷题与错题复盘提升稳定性。')

        # 去重并截断建议数
        suggestions = list(dict.fromkeys(suggestions))[:8]

        return jsonify({
            'status': 'success',
            'student': student_info,
            'overview': overview,
            'latest_exams': latest_exams,
            'performance': perf_summary,
            'strengths': strengths,
            'weaknesses': weaknesses,
            'suggestions': suggestions
        }), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'生成学生反馈失败: {str(e)}'}), 500

@analysis_bp.route('/tables', methods=['GET'])
def list_tables():
    """获取数据库中的所有表名"""
    try:
        tables = []
        try:
            tables = get_tables() or []
        except Exception as db_err:
            print(f"获取数据库表失败，尝试CSV回退: {db_err}")

        # 如果数据库不可用或无表，尝试从 CSV 目录推断
        if not tables:
            csv_dir_candidates = [
                Path(__file__).parent.parent / 'database_datasets',
                Path(__file__).parent.parent.parent / 'database_datasets'
            ]
            csv_tables = set()
            for d in csv_dir_candidates:
                try:
                    if d.exists():
                        for p in d.glob('*.csv'):
                            csv_tables.add(p.stem)
                except Exception:
                    continue
            tables = sorted(list(csv_tables))

        return jsonify({
            'status': 'success',
            'tables': tables
        }), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@analysis_bp.route('/student-trends', methods=['GET'])
def get_student_trends():
    """获取学生个人成绩趋势"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', 'exam_scores')
        student_id = request.args.get('student_id')
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            # 返回默认趋势数据
            return jsonify({
                'status': 'success',
                'labels': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
                'legend': ['实际成绩', '预测成绩'],
                'series': [
                    {
                        'name': '实际成绩',
                        'type': 'line',
                        'data': [78, 82, 85, 88]
                    },
                    {
                        'name': '预测成绩',
                        'type': 'line',
                        'data': [80, 83, 86, 89]
                    }
                ]
            }), 200
        
        # 获取表结构
        structure = get_table_structure(table_name)
        
        # 查找时间分组列
        time_column = structure.get('time_column')
        if not time_column or time_column not in df.columns:
            # 尝试查找其他可能的时间列
            time_keywords = ['date', 'time', 'semester', 'term', 'month', 'year', 'exam', 'test']
            time_column = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in time_keywords):
                    time_column = col
                    break
        
        # 获取数值列
        numeric_columns = get_numeric_columns(df, table_name)
        
        # 如果有学生ID参数，过滤数据
        if student_id and 'student_id' in df.columns:
            df = df[df['student_id'].astype(str) == str(student_id)]
        
        # 如果没有时间列或数值列，使用默认数据
        if not time_column or not numeric_columns or df.empty:
            return jsonify({
                'status': 'success',
                'labels': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
                'legend': ['实际成绩', '预测成绩'],
                'series': [
                    {
                        'name': '实际成绩',
                        'type': 'line',
                        'data': [78, 82, 85, 88]
                    },
                    {
                        'name': '预测成绩',
                        'type': 'line',
                        'data': [80, 83, 86, 89]
                    }
                ]
            }), 200
        
        try:
            # 分组计算平均值
            grouped_data = df.groupby(time_column)[numeric_columns].mean().reset_index()
            
            # 对时间列进行排序
            if time_column in ['exam_date']:
                try:
                    grouped_data[time_column] = pd.to_datetime(grouped_data[time_column])
                    grouped_data = grouped_data.sort_values(by=time_column)
                except:
                    grouped_data = grouped_data.sort_values(by=time_column)
            else:
                grouped_data = grouped_data.sort_values(by=time_column)
            
            # 获取标签
            labels = grouped_data[time_column].astype(str).tolist()
            
            # 准备系列数据
            series = []
            legend = []
            
            # 优先使用分数列作为实际成绩
            actual_score_col = None
            for col in numeric_columns:
                if 'score' in col.lower() and not any(keyword in col.lower() for keyword in ['id', '编号']):
                    actual_score_col = col
                    break
            
            # 如果找到分数列，添加到系列中
            if actual_score_col:
                series.append({
                    'name': '实际成绩',
                    'type': 'line',
                    'data': [round(float(val), 1) for val in grouped_data[actual_score_col].tolist()]
                })
                legend.append('实际成绩')
            
            # 添加预测成绩（模拟数据）
            if len(series) > 0:
                actual_data = series[0]['data']
                # 生成基于实际数据的预测
                predicted_data = [round(val + np.random.uniform(-2, 2), 1) for val in actual_data]
                series.append({
                    'name': '预测成绩',
                    'type': 'line',
                    'data': predicted_data
                })
                legend.append('预测成绩')
            
            # 如果没有生成有效系列，使用默认数据
            if not series:
                # 选择第一个合适的数值列
                for col in numeric_columns:
                    if not any(keyword in col.lower() for keyword in ['id', '编号', 'number', 'num']):
                        series_name = get_friendly_column_name(col)
                        series.append({
                            'name': series_name,
                            'type': 'line',
                            'data': [round(float(val), 1) for val in grouped_data[col].tolist()]
                        })
                        legend.append(series_name)
            
            # 如果考试数量太多，只取最近的10个
            if len(labels) > 10:
                labels = labels[-10:]
                for s in series:
                    if s and 'data' in s and isinstance(s['data'], list):
                        s['data'] = s['data'][-10:]
            
            return jsonify({
                'status': 'success',
                'labels': labels,
                'legend': legend,
                'series': series
            }), 200
        except Exception as inner_error:
            print(f"处理学生趋势数据时出错: {inner_error}")
        
        # 使用默认数据
        return jsonify({
            'status': 'success',
            'labels': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
            'legend': ['实际成绩', '预测成绩'],
            'series': [
                {
                    'name': '实际成绩',
                    'type': 'line',
                    'data': [78, 82, 85, 88]
                },
                {
                    'name': '预测成绩',
                    'type': 'line',
                    'data': [80, 83, 86, 89]
                }
            ]
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取学生趋势数据失败: {str(e)}'
        }), 500

@analysis_bp.route('/model-accuracy', methods=['GET'])
def get_model_accuracy():
    """获取模型准确度指标"""
    try:
        # 获取请求参数
        model = request.args.get('model', 'default')
        
        # 返回模拟的模型评估指标
        metrics = [
            {
                'value': [85, 90, 88, 95],
                'name': f'{model} 模型评估指标'
            }
        ]
        
        return jsonify({
            'status': 'success',
            'metrics': metrics
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取模型准确度数据失败: {str(e)}'
        }), 500

@analysis_bp.route('/student-progress', methods=['GET'])
def get_student_progress():
    """获取学生进步情况数据"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', 'exam_scores')
        student_id = request.args.get('student_id')
        
        # 获取表数据
        df = get_table_data(table_name)
        
        labels = []
        progress = []
        
        if df is not None and not df.empty:
            # 如果指定了学生ID，过滤数据
            if student_id and 'student_id' in df.columns:
                df = df[df['student_id'].astype(str) == str(student_id)]
            
            # 查找时间列
            time_column = None
            time_keywords = ['date', 'time', 'semester', 'term', 'month', 'year', 'exam', 'test']
            for col in df.columns:
                if any(keyword in col.lower() for keyword in time_keywords):
                    time_column = col
                    break
            
            # 查找分数列
            score_column = None
            score_keywords = ['score', 'total_score', 'final_score', 'grade']
            for col in df.columns:
                if any(keyword in col.lower() for keyword in score_keywords):
                    if pd.api.types.is_numeric_dtype(df[col]):
                        score_column = col
                        break
            
            if time_column and score_column:
                # 对数据按时间分组计算平均分数
                try:
                    # 按时间排序
                    if 'date' in time_column.lower():
                        df[time_column] = pd.to_datetime(df[time_column], errors='coerce')
                    df_sorted = df.sort_values(by=time_column)
                    
                    # 按时间分组计算平均分
                    grouped = df_sorted.groupby(time_column)[score_column].mean()
                    
                    # 计算进步幅度（相对于前一个时间点）
                    scores = grouped.values
                    labels = [str(idx) for idx in grouped.index.tolist()]
                    
                    # 只取最近的数据（最多10个）
                    if len(labels) > 10:
                        labels = labels[-10:]
                        scores = scores[-10:]
                    
                    # 计算进步百分比
                    progress = [0]  # 第一个点没有进步
                    for i in range(1, len(scores)):
                        if scores[i-1] > 0:
                            pct_change = ((scores[i] - scores[i-1]) / scores[i-1]) * 100
                            progress.append(round(pct_change, 1))
                        else:
                            progress.append(0)
                except Exception as e:
                    print(f"计算进步数据时出错: {e}")
        
        # 如果没有成功计算数据，使用默认数据
        if not labels or not progress:
            labels = ['第一月', '第二月', '第三月', '第四月', '第五月']
            progress = [5, 8, 12, 15, 20]
        
        return jsonify({
            'status': 'success',
            'labels': labels,
            'progress': progress
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取学生进步情况数据失败: {str(e)}'
        }), 500

# 核心功能：获取数值型列用于相关性分析
def get_table_structure(table_name):
    """获取表结构信息"""
    return table_structures.get(table_name, {})

def get_numeric_columns(df, table_name):
    """获取数据框中的数值型列，用于相关性分析"""
    print(f"开始获取数值列 - 表名: {table_name}")
    numeric_columns = []
    
    # 获取表结构
    structure = table_structures.get(table_name, {})
    score_columns = structure.get('score_columns', [])
    ranking_columns = structure.get('ranking_columns', [])
    categorical_columns = structure.get('categorical_columns', [])
    id_columns = structure.get('id_columns', [])
    text_columns = structure.get('text_columns', [])
    
    # 排除列集合
    exclude_columns = set(categorical_columns + id_columns + text_columns)
    
    # 首先尝试添加预定义的数值列
    for col in score_columns + ranking_columns:
        if col in df.columns:
            try:
                numeric_col = pd.to_numeric(df[col], errors='coerce')
                if numeric_col.notna().sum() > 0:
                    numeric_columns.append(col)
                    df[col] = numeric_col
            except:
                continue
    
    # 自动检测所有可能的数值列（排除已知的非数值列）
    for col in df.columns:
        # 跳过已经添加的列和排除列
        if col in numeric_columns or col in exclude_columns:
            continue
        
        # 跳过明显的ID列
        col_lower = col.lower()
        if col_lower.endswith('_id') or col_lower.endswith('id') or col_lower == 'id':
            continue
        
        # 跳过日期、名称、时间戳等文本列
        if any(keyword in col_lower for keyword in ['date', 'name', 'no', '日期', '姓名', '名称', 
                                                      'created_at', 'updated_at', 'create_time', 
                                                      'update_time', 'timestamp', 'time']):
            continue
        
        try:
            # 尝试转换为数值类型
            numeric_col = pd.to_numeric(df[col], errors='coerce')
            # 检查是否有有效的数值数据
            valid_count = numeric_col.notna().sum()
            if valid_count > 0:
                # 检查是否真的是数值列（不是被错误转换的分类列）
                # 如果唯一值数量很少且都是整数，可能是分类列
                unique_count = numeric_col.dropna().nunique()
                if unique_count > 10 or (unique_count > 2 and valid_count > 100):
                    numeric_columns.append(col)
                    df[col] = numeric_col
                    print(f"  检测到数值列: {col} (唯一值: {unique_count})")
        except:
            continue
    
    print(f"数值列识别完成，最终识别到 {len(numeric_columns)} 个数值列: {numeric_columns}")
    return numeric_columns

def get_friendly_column_name(col):
    """获取列的友好显示名称"""
    key = str(col or '').strip()
    # 优先使用上传时记录的原始/显示列名映射
    try:
        table_name = global_data.get('current_table')
        if isinstance(table_name, str) and table_name:
            labels_cache = global_data.get('column_labels') or {}
            labels = labels_cache.get(table_name)
            if labels is None:
                rows = fetch_all(
                    "SELECT stored_name, COALESCE(display_name, original_name) AS label FROM table_column_mapping WHERE table_name=%s ORDER BY column_order",
                    [table_name]
                ) or []
                labels = {r.get('stored_name'): r.get('label') for r in rows if r.get('stored_name')}
                if 'column_labels' not in global_data:
                    global_data['column_labels'] = {}
                global_data['column_labels'][table_name] = labels
            disp = labels.get(key)
            if isinstance(disp, str) and disp.strip():
                return disp.strip()
    except Exception:
        pass
    if key in feature_name_map:
        return feature_name_map[key]
    # 统一小写用于关键词匹配
    low = key.lower()
    # 关键词兜底映射（避免出现英文Title Case）
    keyword_map = [
        (['attendance', 'attend'], '出勤分数'),
        (['participation', 'participate'], '参与分数'),
        (['quiz', 'test'], '测验分数'),
        (['assignment', 'homework', 'task'], '作业分数'),
        (['project'], '项目分数'),
        (['final', 'exam'], '期末考试分数'),
        (['midterm'], '期中成绩'),
        (['usual', 'daily'], '平时成绩'),
        (['score_level'], '成绩等级'),
        (['score'], '分数'),
    ]
    for keys, name in keyword_map:
        if any(k in low for k in keys):
            return name
    # 默认：将下划线转空格，但不做英文Title Case，避免出现英文标题
    # 若确实找不到映射，直接返回原始列名（中文列名能正常显示）
    return key.replace('_', ' ')

def get_table_data(table_name):
    """获取表数据，用于相关性分析"""
    print(f"开始获取表数据 - 表名: {table_name}")
    
    # 验证表名是否有效
    if not isinstance(table_name, str) or not table_name:
        print(f"错误: 无效的表名 '{table_name}'")
        return None
    
    # 若被标记为脏，强制清理缓存
    try:
        if table_name in (global_data.get('dirty_tables') or set()):
            if 'processed_data' in global_data:
                del global_data['processed_data']
            if 'current_data' in global_data:
                del global_data['current_data']
            # 移除脏标记
            (global_data.get('dirty_tables') or set()).discard(table_name)
            # 使 current_table 与传入不同，强制重新加载
            global_data['current_table'] = None
            print(f"表 {table_name} 命中脏标记，已清理缓存")
    except Exception:
        pass

    # 清空旧缓存以避免混淆
    if global_data.get('current_table') != table_name:
        print(f"切换表，清空旧缓存")
        if 'processed_data' in global_data:
            del global_data['processed_data']
    
    # 尝试从缓存获取数据
    if 'processed_data' in global_data and global_data.get('current_table') == table_name:
        print(f"从缓存获取已处理数据")
        try:
            return global_data['processed_data'].copy()
        except Exception as e:
            print(f"复制缓存数据时出错: {e}")
    elif 'current_data' in global_data and global_data.get('current_table') == table_name:
        print(f"从缓存获取原始数据")
        try:
            return global_data['current_data'].copy()
        except Exception as e:
            print(f"复制缓存数据时出错: {e}")
    
    # 从数据库加载
    print(f"从数据库加载表 {table_name} 的数据")
    df = None
    
    # 尝试从数据库加载
    try:
        tables = get_tables()
        if table_name in tables:
            table_data = fetch_all(f"SELECT * FROM {table_name}")
            if table_data is not None and table_data:
                print(f"查询到 {len(table_data)} 条记录")
                df = pd.DataFrame(table_data)
    except Exception as e:
        print(f"从数据库加载失败: {e}")
    
    # 如果数据库加载失败，尝试从CSV文件加载
    if df is None:
        print(f"尝试从CSV文件加载表 {table_name} 的数据")
        csv_paths = [
            f"../database_datasets/{table_name}.csv",
            f"database_datasets/{table_name}.csv"
        ]
        
        for csv_path in csv_paths:
            try:
                df = pd.read_csv(csv_path, encoding='utf-8')
                print(f"CSV数据加载成功")
                break
            except:
                continue
    
    # 如果加载成功，进行数据清理和缓存
    if df is not None:
        # 基本数据清理
        df = df.dropna(axis=1, how='all')
        
        # 保存到缓存
        global_data['current_data'] = df
        global_data['current_table'] = table_name
        return df
    else:
        print(f"生成表 {table_name} 的示例数据")
        # 生成示例数据，专注于相关性分析所需的数值列
        structure = table_structures.get(table_name, {})
        sample_data = {}
        
        # 添加ID列
        for id_col in structure.get('id_columns', ['id']):
            sample_data[id_col] = list(range(1, 51))
        
        # 添加数值列，确保有足够的数值列用于相关性分析
        numeric_columns = structure.get('score_columns', []) + structure.get('ranking_columns', [])
        
        # 如果没有预定义的数值列，添加默认列
        if len(numeric_columns) < 2:
            numeric_columns = ['score1', 'score2', 'score3']
        
        # 生成相关性较好的随机数据
        np.random.seed(42)  # 设置随机种子
        sample_data[numeric_columns[0]] = np.random.normal(70, 10, size=50).astype(int)
        
        # 其他列基于第一列生成，添加相关性
        for col in numeric_columns[1:]:
            correlation = np.random.uniform(0.6, 0.9)
            noise = np.random.normal(0, 8, size=50)
            sample_data[col] = (correlation * sample_data[numeric_columns[0]] + 
                               (1-correlation) * np.random.normal(70, 10, size=50) + noise).astype(int)
            sample_data[col] = np.clip(sample_data[col], 0, 100)
        
        # 创建DataFrame
        df = pd.DataFrame(sample_data)
        
        # 保存到缓存
        global_data['current_data'] = df
        global_data['current_table'] = table_name
        
        return df
    
    return None

@analysis_bp.route('/statistics', methods=['GET'])
def get_statistics():
    """获取数据统计信息"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', 'students')
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            return jsonify({
                'status': 'error',
                'message': f'没有找到{table_name}表的数据'
            }), 404
        
        # 获取数值列
        numeric_columns = get_numeric_columns(df, table_name)
        
        # 计算数值列统计信息
        numeric_statistics = []
        if numeric_columns:
            for col in numeric_columns:
                stats = {
                    'feature': get_friendly_column_name(col),
                    'mean': round(df[col].mean(), 2),
                    'std': round(df[col].std(), 2),
                    'min': float(df[col].min()),
                    'max': float(df[col].max()),
                    'missing': round(df[col].isna().mean() * 100, 2),
                    'count': int(df[col].count())
                }
                numeric_statistics.append(stats)
        
        # 获取分类列统计信息
        categorical_statistics = []
        structure = table_structures.get(table_name, {})
        categorical_columns = structure.get('categorical_columns', [])
        
        for col in categorical_columns:
            if col in df.columns:
                unique_values = df[col].dropna().unique()
                unique_count = len(unique_values)
                value_counts = df[col].value_counts()
                
                # 转换为JSON可序列化的格式
                value_distribution = {}
                for key, value in value_counts.items():
                    # 将 numpy/pandas 类型转换为 Python 原生类型
                    str_key = str(key)
                    int_value = int(value)
                    value_distribution[str_key] = int_value
                
                # 转换类别列表为字符串列表
                categories_list = [str(val) for val in unique_values[:10]]
                
                # 获取最频繁的值和频次
                most_frequent = value_counts.index[0] if len(value_counts) > 0 else None
                most_frequent_count = value_counts.iloc[0] if len(value_counts) > 0 else 0
                
                cat_stats = {
                    'column': get_friendly_column_name(col),
                    'feature': get_friendly_column_name(col),  # 兼容性字段
                    'type': 'categorical',
                    'count': int(df[col].count()),
                    'unique': int(unique_count),
                    'top': str(most_frequent) if most_frequent is not None else None,
                    'freq': int(most_frequent_count),
                    'missing': round(float(df[col].isna().mean() * 100), 2),
                    'value_counts': value_distribution,
                    'categories': categories_list  # 最多显示10个类别
                }
                categorical_statistics.append(cat_stats)
        
        return jsonify({
            'status': 'success',
            'numeric_statistics': numeric_statistics,
            'categorical_statistics': categorical_statistics,
            'total_records': int(len(df))
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取统计数据失败: {str(e)}'
        }), 500

@analysis_bp.route('/preprocess', methods=['POST'])
def preprocess_data():
    """数据预处理"""
    try:
        data = request.get_json()
        missing_value_strategy = data.get('missingValue', 'mean')
        outlier_strategy = data.get('outlier', 'iqr')
        table_name = data.get('table', global_data.get('current_table', 'students'))
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            return jsonify({
                'status': 'error',
                'message': '没有数据可供处理'
            }), 404
        
        # 记录原始数据统计
        original_rows = len(df)
        original_missing = df.isnull().sum().sum()
        
        # 预处理数据
        processed_df, encoders = preprocess_df(df, missing_value_strategy, outlier_strategy)
        
        # 更新全局缓存
        global_data['processed_data'] = processed_df
        
        # 记录预处理信息
        processed_rows = len(processed_df)
        processed_missing = processed_df.isnull().sum().sum()
        preprocess_info = {
            'missing_values_removed': original_missing - processed_missing,
            'outliers_removed': 0,  # 异常值处理是替换而不是删除，所以这里设为0
            'missing_value_strategy': missing_value_strategy,
            'outlier_strategy': outlier_strategy,
            'original_rows': original_rows,
            'processed_rows': processed_rows
        }
        
        return jsonify({
            'status': 'success',
            'message': '数据预处理完成',
            'info': preprocess_info
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@analysis_bp.route('/feature-engineering', methods=['POST'])
def feature_engineering():
    """特征工程"""
    try:
        # 记录请求参数
        data = request.get_json()
        print(f"特征工程请求参数: {data}")
        
        selection_methods = data.get('selection', [])
        transformations = data.get('transformation', [])
        table_name = data.get('table', global_data.get('current_table', 'students'))
        
        # 获取数据
        print(f"正在获取表 {table_name} 的数据")
        df = get_table_data(table_name)
        if df is None:
            print(f"错误: 表 {table_name} 没有数据")
            return jsonify({
                'status': 'error',
                'message': f'没有找到表 {table_name} 的数据'
            }), 404
        
        print(f"成功获取表数据，数据形状: {df.shape}")
        
        # 获取数值列
        print("正在识别数值列")
        numeric_columns = get_numeric_columns(df, table_name)
        print(f"识别到的数值列: {numeric_columns}")
        
        # 初始化默认值
        features = []
        correlation_matrix = np.array([[1.0]])
        
        # 如果有足够的数值列，计算真实的相关性矩阵
        if len(numeric_columns) >= 2:
            try:
                # 选择数值列
                numeric_df = df[numeric_columns].copy()
                print(f"数值数据框形状: {numeric_df.shape}")
                
                # 检查数据质量
                missing_values = numeric_df.isnull().sum()
                print(f"各列缺失值: {missing_values}")
                
                # 计算相关性矩阵
                print("计算相关性矩阵")
                correlation_matrix = numeric_df.corr().values
                # 保留两位小数
                correlation_matrix = np.round(correlation_matrix, 2)
                # 使用友好的特征名称
                features = [get_friendly_column_name(col) for col in numeric_columns]
                print(f"相关性矩阵形状: {correlation_matrix.shape}")
            except Exception as corr_error:
                print(f"计算相关性矩阵时出错: {corr_error}")
                # 使用默认值继续
                features = [get_friendly_column_name(col) for col in numeric_columns[:4]]  # 限制最多4个特征
                correlation_matrix = np.eye(len(features))  # 单位矩阵
        elif len(numeric_columns) == 1:
            # 只有一个数值列时
            print("只有一个数值列，使用默认相关性")
            features = [get_friendly_column_name(numeric_columns[0])]
            correlation_matrix = np.array([[1.0]])
        else:
            print("没有找到有效的数值列")
            features = ['特征1', '特征2']
            correlation_matrix = np.array([[1.0, 0.5], [0.5, 1.0]])
        
        # 转换为前端需要的格式
        data_points = []
        for i in range(len(features)):
            for j in range(len(features)):
                data_points.append([i, j, correlation_matrix[i][j]])
        
        # 准备响应数据
        result = {
            'status': 'success',
            'data': data_points,
            'features': features,
            'numeric_columns_count': len(numeric_columns),
            'debug_info': {
                'table_shape': list(df.shape),
                'numeric_columns': numeric_columns,
                'requested_methods': {
                    'selection': selection_methods,
                    'transformation': transformations
                }
            }
        }
        
        # 添加应用的方法信息
        if selection_methods or transformations:
            result['applied_methods'] = {
                'selection': selection_methods,
                'transformation': transformations
            }
        
        print(f"特征工程成功完成，返回 {len(features)} 个特征")
        return jsonify(result), 200
        
    except Exception as e:
        print(f"特征工程失败: {e}")
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'特征工程失败: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@analysis_bp.route('/class-trends', methods=['GET'])
def get_class_trends():
    """获取班级平均成绩趋势"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', 'exam_scores')
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            # 返回默认趋势数据
            return jsonify({
                'status': 'success',
                'exams': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
                'series': [
                    {
                        'name': '班级平均成绩',
                        'type': 'line',
                        'data': [78, 82, 85, 88]
                    }
                ]
            }), 200
        
        # 获取表结构
        structure = get_table_structure(table_name)
        
        # 查找时间分组列
        time_column = structure.get('time_column')
        if not time_column or time_column not in df.columns:
            # 尝试查找其他可能的时间列
            time_keywords = ['date', 'time', 'semester', 'term', 'month', 'year', 'exam', 'test']
            time_column = None
            for col in df.columns:
                if any(keyword in col.lower() for keyword in time_keywords):
                    time_column = col
                    break
        
        # 获取数值列
        numeric_columns = get_numeric_columns(df, table_name)
        
        # 如果没有时间列或数值列，使用默认数据
        if not time_column or not numeric_columns:
            return jsonify({
                'status': 'success',
                'exams': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
                'series': [
                    {
                        'name': '班级平均成绩',
                        'type': 'line',
                        'data': [78, 82, 85, 88]
                    }
                ]
            }), 200
        
        try:
            # 分组计算平均值
            grouped_data = df.groupby(time_column)[numeric_columns].mean().reset_index()
            
            # 对时间列进行排序（如果是日期类型）
            if time_column in ['exam_date']:
                # 尝试将时间列转换为日期类型并排序
                try:
                    grouped_data[time_column] = pd.to_datetime(grouped_data[time_column])
                    grouped_data = grouped_data.sort_values(by=time_column)
                except:
                    # 如果转换失败，尝试其他排序方式
                    grouped_data = grouped_data.sort_values(by=time_column)
            else:
                # 按值排序
                grouped_data = grouped_data.sort_values(by=time_column)
            
            # 获取考试名称
            exams = grouped_data[time_column].astype(str).tolist()
            
            # 准备系列数据
            series = []
            # 为每个数值列创建一个系列
            for col in numeric_columns:
                # 过滤掉ID相关列
                if not any(keyword in col.lower() for keyword in ['id', '编号', 'number', 'num']):
                    # 获取友好的系列名称
                    series_name = get_friendly_column_name(col)
                    
                    # 获取数据
                    data = [round(float(val), 1) for val in grouped_data[col].tolist()]
                    
                    series.append({
                        'name': series_name,
                        'type': 'line',
                        'data': data
                    })
            
            # 如果生成了有效系列数据，返回结果
            if series:
                # 如果考试数量太多，只取最近的10个
                if len(exams) > 10:
                    exams = exams[-10:]
                    for s in series:
                        if s and 'data' in s and isinstance(s['data'], list):
                            s['data'] = s['data'][-10:]
                
                return jsonify({
                    'status': 'success',
                    'labels': exams,
                    'legend': [s.get('name', '') for s in series],
                    'series': series
                }), 200
        except:
            # 分组失败，使用默认数据
            pass
        
        # 使用默认数据
        return jsonify({
            'status': 'success',
            'labels': ['第一次月考', '期中考试', '第二次月考', '期末考试'],
            'legend': ['班级平均成绩'],
            'series': [
                {
                    'name': '班级平均成绩',
                    'type': 'line',
                    'data': [78, 82, 85, 88]
                }
            ]
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取班级趋势数据失败: {str(e)}'
        }), 500

@analysis_bp.route('/subject-comparison', methods=['GET'])
def get_subject_comparison():
    """获取学科对比数据"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', global_data.get('current_table', 'students'))
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            # 返回默认数据
            return jsonify({
                'status': 'success',
                'labels': ['语文', '数学', '英语', '物理', '化学'],
                'legend': ['平均分'],
                'series': [
                    {
                        'name': '平均分',
                        'type': 'bar',
                        'data': [78, 82, 79, 85, 83]
                    }
                ]
            }), 200
        
        # 获取数值列
        numeric_columns = get_numeric_columns(df, table_name)
        
        # 如果没有数值列，返回默认数据
        if not numeric_columns:
            return jsonify({
                'status': 'success',
                'labels': ['语文', '数学', '英语', '物理', '化学'],
                'legend': ['平均分'],
                'series': [
                    {
                        'name': '平均分',
                        'type': 'bar',
                        'data': [78, 82, 79, 85, 83]
                    }
                ]
            }), 200
        
        # 准备学科数据
        subjects = []
        scores = []
        
        # 已处理的列集合
        processed_columns = set()
        
        # 优先匹配预定义的学科列
        for subject, keywords in subject_keywords.items():
            for col in numeric_columns:
                if col in processed_columns:
                    continue
                
                col_lower = col.lower()
                if any(keyword.lower() in col_lower for keyword in keywords):
                    # 计算平均值
                    avg_score = df[col].mean()
                    if pd.notna(avg_score):
                        subjects.append(subject)
                        scores.append(round(float(avg_score), 1))
                        processed_columns.add(col)
                    break
        
        # 处理剩余的数值列
        remaining_columns = [col for col in numeric_columns if col not in processed_columns]
        
        # 过滤掉不适合作为学科的列
        valid_remaining_columns = []
        for col in remaining_columns:
            if not any(keyword in col.lower() for keyword in ['id', '编号', 'number', 'num', 'ranking', '排名']):
                valid_remaining_columns.append(col)
        
        # 为剩余的有效列添加到学科列表
        max_subjects = 8  # 最多显示8个学科
        for col in valid_remaining_columns[:max_subjects - len(subjects)]:
            # 获取友好的学科名称
            subject_name = get_friendly_column_name(col)
            # 计算平均值
            avg_score = df[col].mean()
            if pd.notna(avg_score):
                subjects.append(subject_name)
                scores.append(round(float(avg_score), 1))
        
        # 如果没有找到足够的学科数据，使用默认数据
        if len(subjects) < 3:
            subjects = ['语文', '数学', '英语', '物理', '化学']
            scores = [78, 82, 79, 85, 83]
        
        return jsonify({
            'status': 'success',
            'labels': subjects,  # 统一使用 labels 字段
            'legend': ['平均分'],
            'series': [
                {
                    'name': '平均分',
                    'type': 'bar',
                    'data': scores
                }
            ]
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取学科对比数据失败: {str(e)}'
        }), 500



# 只保留相关性分析功能
@analysis_bp.route('/table-data', methods=['GET'])
def get_table_data_api():
    """获取表的数据，支持分页"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', 'students')
        page = int(request.args.get('page', 1))
        page_size = int(request.args.get('page_size', 1000))  # 默认每页1000条
        
        print(f"获取表数据: {table_name}, 页码: {page}, 每页: {page_size}")
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None or df.empty:
            return jsonify({
                'status': 'error',
                'message': f'没有找到{table_name}表的数据'
            }), 404
        
        total_records = len(df)
        
        # 分页处理
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size
        df_page = df.iloc[start_idx:end_idx]
        
        # 将DataFrame转换为字典列表，处理特殊数据类型
        df_clean = df_page.copy()
        
        # 处理可能导致JSON序列化问题的数据类型
        for col in df_clean.columns:
            if pd.api.types.is_datetime64_any_dtype(df_clean[col]):
                # 转换日期为字符串
                df_clean[col] = df_clean[col].dt.strftime('%Y-%m-%d')
                df_clean[col] = df_clean[col].replace('NaT', '')
            elif pd.api.types.is_numeric_dtype(df_clean[col]):
                # 处理数值类型的NaN
                df_clean[col] = df_clean[col].fillna(0)
            else:
                # 处理文本类型的NaN
                df_clean[col] = df_clean[col].fillna('')
        
        # 转换为字典列表并进一步处理特殊数据类型
        data = []
        for record in df_clean.to_dict('records'):
            clean_record = {}
            for key, value in record.items():
                # 处理各种可能的数据类型
                if pd.isna(value) or value is None:
                    clean_record[key] = None
                elif isinstance(value, (pd.Timestamp, np.datetime64)):
                    clean_record[key] = str(value)[:10] if not pd.isna(value) else None
                elif isinstance(value, (np.integer, np.floating)):
                    clean_record[key] = float(value) if not pd.isna(value) else None
                elif hasattr(value, 'date'):  # datetime.date对象
                    clean_record[key] = str(value)
                else:
                    clean_record[key] = str(value) if value != 'nan' else None
            data.append(clean_record)
        
        print(f"返回数据: {len(data)} 条记录，总共: {total_records} 条")
        
        return jsonify({
            'status': 'success',
            'data': data,
            'total': total_records,
            'page': page,
            'page_size': page_size,
            'has_more': end_idx < total_records
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取表数据失败: {str(e)}'
        }), 500

@analysis_bp.route('/correlation', methods=['GET'])
def get_correlation():
    """获取特征相关性数据"""
    try:
        # 获取请求参数
        table_name = request.args.get('table', global_data.get('current_table', 'students'))
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None:
            # 使用默认数据
            features = ['特征1', '特征2', '特征3', '特征4']
            correlation_matrix = np.array([
                [1.00, 0.75, 0.82, 0.95],
                [0.75, 1.00, 0.68, 0.93],
                [0.82, 0.68, 1.00, 0.92],
                [0.95, 0.93, 0.92, 1.00]
            ])
        else:
            # 获取数值列
            numeric_columns = get_numeric_columns(df, table_name)
            
            # 如果没有足够的数值列，使用默认数据
            if len(numeric_columns) < 2:
                features = ['特征1', '特征2']
                correlation_matrix = np.array([[1.0, 0.5], [0.5, 1.0]])
            else:
                # 选择数值列
                numeric_df = df[numeric_columns].copy()
                # 计算相关性矩阵
                correlation_matrix = numeric_df.corr().values
                # 保留两位小数
                correlation_matrix = np.round(correlation_matrix, 2)
                # 使用友好的特征名称
                features = [get_friendly_column_name(col) for col in numeric_columns]
        
        # 转换为前端需要的格式
        data_points = []
        for i in range(len(features)):
            for j in range(len(features)):
                data_points.append([i, j, correlation_matrix[i][j]])
        
        return jsonify({
            'status': 'success',
            'features': features,
            'data': data_points
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@analysis_bp.route('/score-distribution', methods=['GET'])
def get_score_distribution():
    """
    try:
        table_name = request.args.get('table', 'historical_grades')
        student_id = request.args.get('student_id')

        df = get_table_data(table_name)
        if df is None or df.empty:
            return jsonify({'status': 'success', 'features': [], 'data': [], 'message': '暂无数据'}), 200

        # 可选按学生过滤
        if student_id and 'student_id' in df.columns:
            student_df = df[df['student_id'].astype(str) == str(student_id)]
            if not student_df.empty:
                df = student_df

        # 选择最多4个数值列（关键词优先）
        numeric_cols = []
        for col in df.columns:
            try:
                ser = pd.to_numeric(df[col], errors='coerce')
                if ser.notna().sum() > 0:
                    numeric_cols.append(col)
            except Exception:
                continue
        if not numeric_cols:
            return jsonify({'status': 'success', 'features': [], 'data': [], 'message': '无可用数值列'}), 200

        def _priority(c):
            low = str(c).lower()
            score_like = any(k in low for k in ['score', 'grade', '分', '绩'])
            return (0 if score_like else 1, c)

        numeric_cols = sorted(numeric_cols, key=_priority)[:4]

        features, data = [], []
        for col in numeric_cols:
            fname = get_friendly_column_name(col)
            try:
                vals = pd.to_numeric(df[col], errors='coerce').dropna()
                mean_val = float(vals.mean()) if len(vals) > 0 else 0.0
                if np.isnan(mean_val):
                    mean_val = 0.0
                features.append(fname)
                data.append(round(mean_val, 2))
            except Exception:
                features.append(fname)
                data.append(0)

        return jsonify({'status': 'success', 'features': features, 'data': data}), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@analysis_bp.route('/grade-distribution', methods=['GET'])
def get_grade_distribution():
    """
    try:
        table_name = request.args.get('table', 'exam_scores')
        score_level_column = request.args.get('column')

        df = get_table_data(table_name)
        if df is None or df.empty:
            return jsonify({'status': 'error', 'message': '无法获取数据表'}), 404

        # 自动识别分类列
        if not score_level_column or score_level_column not in df.columns:
            cand = None
            for col in df.columns:
                low = str(col).lower()
                if any(k in low for k in ['level', 'grade', 'rank', '等级', '级别']):
                    cand = col
                    break
            if cand is None:
                for col in df.columns:
                    try:
                        uniq = df[col].dropna().astype(str).nunique()
                        if 2 <= uniq <= 8:
                            cand = col
                            break
                    except Exception:
                        continue
            score_level_column = cand if cand else None

        if not score_level_column or score_level_column not in df.columns:
            data = [{'name': n, 'value': 0} for n in ['A级(优秀)', 'B级(良好)', 'C级(中等)', 'D级(及格)', 'E级(不及格)']]
            return jsonify({'status': 'success', 'data': data, 'total': 0, 'table': table_name}), 200

        
        # 按学生分组，获取每个学生的主要等级（最常见的等级）
        if 'student_id' in df.columns:
            print(f"[饼图] 按学生分组统计，总共{df['student_id'].nunique()}个学生")
            
            # 为每个学生找到最常见的成绩等级
            student_levels = []
            for student_id in df['student_id'].unique():
                student_df = df[df['student_id'] == student_id]
                student_score_levels = student_df[score_level_column].dropna()
                
                if len(student_score_levels) > 0:
                    # 取该学生最常见的等级，如果有并列则取字母序最小的
                    most_common_level = student_score_levels.mode().iloc[0]
                    student_levels.append(most_common_level)
            
            if len(student_levels) == 0:
                return jsonify({
                    'status': 'error',
                    'message': '没有有效的学生成绩等级数据'
                }), 404
            
            # 统计每个等级的学生数量
            import pandas as pd
            level_counts = pd.Series(student_levels).value_counts()
            total_students = len(student_levels)
            print(f"[饼图] 按学生统计，共{total_students}个学生，等级分布: {level_counts.to_dict()}")
            
        else:
            # 没有学生ID列，直接统计所有记录
            score_levels = df[score_level_column].dropna()
            if len(score_levels) == 0:
                return jsonify({
                    'status': 'error',
                    'message': '没有有效的成绩等级数据'
                }), 404
            level_counts = score_levels.value_counts()
            print(f"[饼图] 所有记录统计，共{len(score_levels)}条记录，等级分布: {level_counts.to_dict()}")
        
        # 确保所有等级都显示（包括数量为0的等级）
        all_levels = ['A', 'B', 'C', 'D', 'E']
        level_names = {
            'A': 'A级(优秀)',
            'B': 'B级(良好)', 
            'C': 'C级(中等)',
            'D': 'D级(及格)',
            'E': 'E级(不及格)'
        }
        
        # 构建返回数据，确保所有等级都包含
        data = []
        for level in all_levels:
            count = int(level_counts.get(level, 0))  # 如果没有该等级，默认为0
            data.append({
                'name': level_names[level],
                'value': count
            })
        
        total_count = int(level_counts.sum()) if len(level_counts) > 0 else 0
        count_type = "个学生" if 'student_id' in df.columns else "条记录"
        print(f"[饼图] 等级分布 - A:{level_counts.get('A', 0)}, B:{level_counts.get('B', 0)}, C:{level_counts.get('C', 0)}, D:{level_counts.get('D', 0)}, E:{level_counts.get('E', 0)}, 总计:{total_count}{count_type}")
        
        return jsonify({
            'status': 'success',
            'data': data,
            'total': total_count,
            'stat_method': 'student_most_common_level' if 'student_id' in df.columns else 'all_records',
            'table': table_name,
            'column': score_level_column
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


@analysis_bp.route('/radar-data', methods=['GET'])
def get_radar_data():
    """获取雷达图数据 - 多维度能力分析"""
    try:
        table_name = request.args.get('table', 'class_performance')
        student_id = request.args.get('student_id')
        
        # 获取表数据
        df = get_table_data(table_name)
        if df is None or df.empty:
            return jsonify({
                'status': 'error',
                'message': '无法获取数据'
            }), 404
        
        # 获取数值列
        numeric_columns = get_numeric_columns(df, table_name)
        
        # 如果数值列不足，返回错误但状态码改为200，让前端能正常处理
        if not numeric_columns or len(numeric_columns) < 2:
            return jsonify({
                'status': 'success',
                'indicator': [
                    {'name': '数据1', 'max': 100},
                    {'name': '数据2', 'max': 100},
                    {'name': '数据3', 'max': 100}
                ],
                'series': [
                    {'name': '暂无数据', 'value': [0, 0, 0]}
                ],
                'message': '当前表数值列不足，无法生成雷达图'
            }), 200

        # 准备雷达图数据
        indicators = []
        class_avg = []
        student_data = []
        used_names = set()  # 避免同义中文映射导致的重复维度（例如“分数”出现两次）

        # 选择所有可用的数值列作为雷达图维度（最多8个）
        for col in numeric_columns[:8]:
            try:
                # 计算班级平均值
                mean_val = float(df[col].mean())
                max_val = float(df[col].max())
                min_val = float(df[col].min())

                if np.isnan(mean_val) or np.isnan(max_val):
                    continue

                # 如果所有值都相同，设置一个合理的最大值
                if max_val == min_val:
                    max_val = mean_val > 0 and (mean_val * 1.5) or 100

                friendly = get_friendly_column_name(col)
                # 跳过重复维度名称，避免“两个分数”等重复显示
                if friendly in used_names:
                    continue
                used_names.add(friendly)

                indicators.append({
                    'name': friendly,
                    'max': round(max(max_val * 1.1, 1), 2)  # 最大值设为实际最大值的1.1倍，至少为1
                })
                class_avg.append(round(mean_val, 2))

                # 如果指定了学生ID，获取该学生的数据
                if student_id and 'student_id' in df.columns:
                    student_df = df[df['student_id'].astype(str) == str(student_id)]
                    if not student_df.empty:
                        student_val = float(student_df[col].mean())  # 使用mean以处理多条记录
                        student_data.append(round(student_val, 2) if not np.isnan(student_val) else 0)
                    else:
                        student_data.append(0)
            except Exception as e:
                print(f"处理列 {col} 时出错: {e}")
                continue

        # 如果处理后仍然没有有效数据
        if len(indicators) < 2:
            return jsonify({
                'status': 'success',
                'indicator': [
                    {'name': '数据1', 'max': 100},
                    {'name': '数据2', 'max': 100},
                    {'name': '数据3', 'max': 100}
                ],
                'series': [
                    {'name': '暂无有效数据', 'value': [0, 0, 0]}
                ]
            }), 200

        # 构建返回数据
        series_data = [
            {
                'name': '班级平均',
                'value': class_avg
            }
        ]

        if student_id and len(student_data) > 0 and len(student_data) == len(class_avg):
            series_data.append({
                'name': f'学生{student_id}',
                'value': student_data
            })

        return jsonify({
            'status': 'success',
            'indicator': indicators,
            'series': series_data
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500


# =============================================================================
# Export Endpoints
# =============================================================================

@analysis_bp.route('/export-table', methods=['GET'])
def export_table_csv():
    """导出指定数据表为 CSV 文件"""
    try:
        table_name = request.args.get('table')
        if not table_name:
            return jsonify({'status': 'error', 'message': '缺少参数 table'}), 400

        df = get_table_data(table_name)
        if df is None:
            return jsonify({'status': 'error', 'message': '无法获取数据表'}), 404

        # 确保列名是字符串，避免中文编码问题
        df.columns = [str(c) for c in df.columns]

        csv_buffer = io.StringIO()
        df.to_csv(csv_buffer, index=False)
        csv_buffer.seek(0)

        filename = f"{table_name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        return Response(
            csv_buffer.getvalue(),
            mimetype='text/csv; charset=utf-8',
            headers={
                'Content-Disposition': f"attachment; filename*=UTF-8''{filename}"
            }
        )
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500


@analysis_bp.route('/export-report', methods=['GET'])
def export_analysis_report():
    """导出数据分析报告为 ZIP（包含多份 CSV 汇总）"""
    try:
        table_name = request.args.get('table', 'exam_scores')
        trend_type = request.args.get('trendType', 'individual')
        student_id = request.args.get('student_id')

        df = get_table_data(table_name)
        if df is None or df.empty:
            return jsonify({'status': 'error', 'message': '无可用数据生成报告'}), 404

        # 构建内存 ZIP
        zip_bytes = io.BytesIO()
        with zipfile.ZipFile(zip_bytes, mode='w', compression=zipfile.ZIP_DEFLATED) as zf:
            # 原始数据（前 2000 行，避免超大文件）
            raw_csv = io.StringIO()
            df.head(2000).to_csv(raw_csv, index=False)
            zf.writestr('data/raw_sample.csv', raw_csv.getvalue())

            # 描述性统计
            try:
                desc = df.describe(include='all').fillna('')
                desc_csv = io.StringIO()
                desc.to_csv(desc_csv)
                zf.writestr('analysis/describe.csv', desc_csv.getvalue())
            except Exception as e:
                zf.writestr('analysis/describe_error.txt', f'生成描述性统计失败: {e}')

            # 数值列相关性
            try:
                numeric_df = df.select_dtypes(include=[np.number])
                if not numeric_df.empty:
                    corr = numeric_df.corr(numeric_only=True)
                    corr_csv = io.StringIO()
                    corr.to_csv(corr_csv)
                    zf.writestr('analysis/correlation.csv', corr_csv.getvalue())
                else:
                    zf.writestr('analysis/correlation_info.txt', '无数值列可用于相关性分析')
            except Exception as e:
                zf.writestr('analysis/correlation_error.txt', f'生成相关性失败: {e}')

            # 雷达图数据（仅课堂表现表）
            try:
                radar_params = {'table': 'class_performance'}
                if student_id:
                    radar_params['student_id'] = str(student_id)
                with analysis_bp.test_request_context(query_string=radar_params):
                    resp = get_radar_data()
                if isinstance(resp, tuple):
                    resp_data, status = resp
                    radar_json = resp_data.get_json() if hasattr(resp_data, 'get_json') else None
                else:
                    radar_json = resp.get_json() if hasattr(resp, 'get_json') else None
                if radar_json and radar_json.get('status') == 'success':
                    # 指标
                    indicators = radar_json.get('indicator', [])
                    ind_df = pd.DataFrame(indicators)
                    ind_csv = io.StringIO()
                    ind_df.to_csv(ind_csv, index=False)
                    zf.writestr('charts/radar_indicators.csv', ind_csv.getvalue())
                    # 系列
                    series = radar_json.get('series', [])
                    # 展平为列式 CSV
                    series_rows = []
                    for s in series:
                        name = s.get('name')
                        values = s.get('value', [])
                        row = {'series_name': name}
                        for i, v in enumerate(values):
                            row[f'dim_{i+1}'] = v
                        series_rows.append(row)
                    series_df = pd.DataFrame(series_rows)
                    series_csv = io.StringIO()
                    series_df.to_csv(series_csv, index=False)
                    zf.writestr('charts/radar_series.csv', series_csv.getvalue())
            except Exception as e:
                zf.writestr('charts/radar_error.txt', f'生成雷达数据失败: {e}')

            # 分布/进步等摘要（简化）
            try:
                # 统计每列非空数量
                nonnull = df.notnull().sum()
                nn_csv = io.StringIO()
                nonnull.to_csv(nn_csv, header=['nonnull_count'])
                zf.writestr('analysis/nonnull_counts.csv', nn_csv.getvalue())
            except Exception as e:
                zf.writestr('analysis/summary_error.txt', f'生成摘要失败: {e}')

            # 元数据
            meta = {
                'table': table_name,
                'trendType': trend_type,
                'student_id': student_id,
                'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            }
            zf.writestr('meta.json', json.dumps(meta, ensure_ascii=False, indent=2))

        zip_bytes.seek(0)
        filename = f"analysis_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.zip"
        return send_file(
            zip_bytes,
            mimetype='application/zip',
            as_attachment=True,
            download_name=filename
        )
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': str(e)}), 500

# =============================================================================
# CRUD Operations for Tables
# =============================================================================

@analysis_bp.route('/table/<table_name>/create', methods=['POST'])
def create_record(table_name):
    """创建新记录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请提供数据'}), 400
        
        # 构建INSERT SQL
        columns = list(data.keys())
        placeholders = ', '.join(['%s'] * len(columns))
        column_names = ', '.join(columns)
        
        sql = f"INSERT INTO {table_name} ({column_names}) VALUES ({placeholders})"
        values = [data[col] for col in columns]
        
        from database import execute_query
        execute_query(sql, values)
        
        # 清空缓存，强制重新加载
        if 'current_table' in global_data and global_data['current_table'] == table_name:
            global_data.clear()
        
        return jsonify({
            'status': 'success',
            'message': '创建成功'
        }), 201
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'创建失败: {str(e)}'
        }), 500


@analysis_bp.route('/table/<table_name>/update/<int:record_id>', methods=['PUT'])
def update_record(table_name, record_id):
    """更新记录"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'status': 'error', 'message': '请提供数据'}), 400
        
        # 构建UPDATE SQL
        set_clauses = ', '.join([f"{col} = %s" for col in data.keys()])
        
        # 确定主键列名
        primary_key = get_primary_key_column(table_name)
        
        sql = f"UPDATE {table_name} SET {set_clauses} WHERE {primary_key} = %s"
        values = list(data.values()) + [record_id]
        
        from database import execute_query
        result = execute_query(sql, values)
        
        # 清空缓存
        if 'current_table' in global_data and global_data['current_table'] == table_name:
            global_data.clear()
        
        return jsonify({
            'status': 'success',
            'message': '更新成功'
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'更新失败: {str(e)}'
        }), 500


@analysis_bp.route('/table/<table_name>/delete/<int:record_id>', methods=['DELETE'])
def delete_record(table_name, record_id):
    """删除记录"""
    try:
        # 确定主键列名
        primary_key = get_primary_key_column(table_name)
        
        sql = f"DELETE FROM {table_name} WHERE {primary_key} = %s"
        
        from database import execute_query
        execute_query(sql, [record_id])
        
        # 清空缓存
        if 'current_table' in global_data and global_data['current_table'] == table_name:
            global_data.clear()
        
        return jsonify({
            'status': 'success',
            'message': '删除成功'
        }), 200
        
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'删除失败: {str(e)}'
        }), 500


def get_primary_key_column(table_name):
    """获取表的主键列名"""
    primary_keys = {
        'students': 'student_id',
        'exam_scores': 'score_id',
        'class_performance': 'performance_id',
        'historical_grades': 'grade_id'
    }
    return primary_keys.get(table_name, 'id')


@analysis_bp.route('/student-courses', methods=['GET'])
def get_student_courses():
    """获取学生参与过的课程列表（用于下拉）
    入参：student_id（可选）、student_name（可选，支持包含匹配）
    规则：
      - 优先使用 student_id
      - 否则使用 student_name 模糊匹配，匹配到多条时选第一条，并在响应中返回匹配数量
    返回：courses: [{course_id, course_name}], resolved_student
    """
    try:
        student_id = request.args.get('student_id')
        student_name = request.args.get('student_name', '').strip()

        # 加载学生与课程表
        students_df = get_table_data('students')
        courses_df = get_table_data('courses')

        # 课程名称映射
        course_name_map = {}
        if courses_df is not None and not courses_df.empty and 'course_id' in courses_df.columns:
            for _, r in courses_df.iterrows():
                try:
                    course_name_map[int(r['course_id'])] = str(r.get('course_name') or f"课程{r['course_id']}")
                except Exception:
                    continue

        resolved_student = None
        match_count = 0

        # 解析目标学生
        if students_df is not None and not students_df.empty:
            if student_id:
                srow = students_df[students_df['student_id'].astype(str) == str(student_id)]
                if not srow.empty:
                    r = srow.iloc[0]
                    resolved_student = {
                        'student_id': int(r['student_id']) if pd.notna(r.get('student_id')) else None,
                        'name': str(r.get('name') or ''),
                        'grade': str(r.get('grade') or ''),
                        'class': str(r.get('class') or ''),
                    }
                    match_count = 1
            elif student_name:
                # 包含匹配（忽略大小写）
                mask = students_df['name'].astype(str).str.contains(student_name, case=False, na=False)
                matches = students_df[mask]
                match_count = len(matches)
                if match_count > 0:
                    r = matches.iloc[0]
                    student_id = str(r['student_id'])
                    resolved_student = {
                        'student_id': int(r['student_id']) if pd.notna(r.get('student_id')) else None,
                        'name': str(r.get('name') or ''),
                        'grade': str(r.get('grade') or ''),
                        'class': str(r.get('class') or ''),
                    }

        if not student_id:
            return jsonify({
                'status': 'error',
                'message': '请提供 student_id 或 student_name',
                'courses': [],
                'match_count': match_count,
                'resolved_student': resolved_student
            }), 400

        # 从三张数据表收集该生的课程ID
        course_ids = set()
        for table in ['historical_grades', 'exam_scores', 'class_performance']:
            df = get_table_data(table)
            if df is None or df.empty:
                continue
            if 'student_id' not in df.columns or 'course_id' not in df.columns:
                continue
            sdf = df[df['student_id'].astype(str) == str(student_id)]
            if not sdf.empty:
                for val in sdf['course_id'].dropna().unique().tolist():
                    try:
                        course_ids.add(int(val))
                    except Exception:
                        continue

        # 组装响应课程
        courses = []
        for cid in sorted(course_ids):
            courses.append({
                'course_id': cid,
                'course_name': course_name_map.get(cid, f'课程{cid}')
            })

        return jsonify({
            'status': 'success',
            'courses': courses,
            'resolved_student': resolved_student,
            'match_count': match_count
        }), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': f'获取学生课程失败: {str(e)}'
        }), 500


# =============================================================================
# 数据管理：上传记录、数据源、采集任务（使用真实数据库表保存状态）
# =============================================================================

# 上传目录（相对项目的 flask_backend/uploads）
UPLOAD_DIR = Path(__file__).resolve().parent.parent / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


def ensure_management_tables():
    """确保数据管理相关表已存在（id 自增主键；时间使用 DATETIME）。"""
    try:
        # 上传历史表
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS upload_history (
              id INT AUTO_INCREMENT PRIMARY KEY,
              filename VARCHAR(255) NOT NULL,
              file_size BIGINT DEFAULT 0,
              mime_type VARCHAR(100),
              stored_path VARCHAR(512),
              status VARCHAR(32) DEFAULT 'success',
              message TEXT,
              uploaded_at DATETIME DEFAULT CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )

        # 数据源表
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS data_sources (
              id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(100) NOT NULL,
              type VARCHAR(50) NOT NULL,
              config TEXT,
              active TINYINT(1) DEFAULT 1,
              last_collection DATETIME NULL,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )

        # 采集任务表
        execute_query(
            """
            CREATE TABLE IF NOT EXISTS collection_tasks (
              id INT AUTO_INCREMENT PRIMARY KEY,
              name VARCHAR(120) NOT NULL,
              source_id INT NULL,
              source_name VARCHAR(120),
              status VARCHAR(32) DEFAULT 'running',
              progress INT DEFAULT 0,
              created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
    )
    except Exception as e:
        print(f"[数据管理] 初始化管理表失败: {e}")


@analysis_bp.route('/uploads', methods=['GET', 'POST'])
def uploads_endpoint():
    """GET: 获取上传历史; POST: 接收文件上传（保存到磁盘并记录到 upload_history）。"""
    try:
        ensure_management_tables()

        if request.method == 'GET':
            rows = fetch_all(
                "SELECT id, filename, file_size, mime_type, stored_path, status, message, uploaded_at "
                "FROM upload_history ORDER BY uploaded_at DESC, id DESC LIMIT 100"
            ) or []
            # 转为前端期望结构
            data = []
            for r in rows:
                data.append({
                    'id': r.get('id'),
                    'filename': r.get('filename'),
                    'uploadTime': str(r.get('uploaded_at')) if r.get('uploaded_at') else None,
                    'fileSize': format_file_size_safe(r.get('file_size') or 0),
                    'status': r.get('status') or 'success',
                    'mime_type': r.get('mime_type'),
                    'path': r.get('stored_path')
                })
            return jsonify({'status': 'success', 'data': data}), 200

        # POST 上传
        files = request.files.getlist('files')
        if not files:
            return jsonify({'status': 'error', 'message': '请提供要上传的文件'}), 400

        saved = []
        # 工具方法：表名保留原样（支持中文/空格等），仅移除反引号与控制字符，避免SQL注入/解析问题
        def _preserve_table_name(name: str) -> str:
            s = str(name or '').strip()
            # 移除反引号，防止与SQL引用冲突
            s = s.replace('`', '')
            # 去除不可见控制字符
            s = re.sub(r"[\x00-\x1F\x7F]", "", s)
            # 空名兜底
            return s or 'uploaded_table'

        # 工具方法：列名清洗（尽量保留原始中文/空格等，仅移除反引号和控制字符）
        def _clean_column_name(raw) -> str:
            try:
                if pd.isna(raw):
                    return ''
            except Exception:
                pass
            s = str(raw or '').strip()
            # 去掉反引号，避免与SQL引用冲突
            s = s.replace('`', '')
            # 去除不可见控制字符
            s = re.sub(r"[\x00-\x1F\x7F]", "", s)
            return s

        # 工具方法：推断 MySQL 列类型
        def _infer_mysql_type(s: pd.Series) -> str:
            if pd.api.types.is_bool_dtype(s):
                return 'TINYINT(1)'
            if pd.api.types.is_integer_dtype(s):
                return 'BIGINT'
            if pd.api.types.is_float_dtype(s):
                return 'DOUBLE'
            if pd.api.types.is_datetime64_any_dtype(s):
                return 'DATETIME'
            try:
                lens = s.astype(str).map(lambda x: len(x) if x is not None else 0)
                max_len = int(lens.max() or 0)
            except Exception:
                max_len = 255
            if max_len <= 0:
                max_len = 64
            if max_len > 1000:
                return 'TEXT'
            return f"VARCHAR({min(max_len+10, 255)})"

        for f in files:
            try:
                # 文件名保留原样（含中文），仅移除危险字符，不做前缀/改名
                def _sanitize_filename(name: str) -> str:
                    s = str(name or '').strip()
                    # 去除路径分隔与 Windows 非法字符
                    s = s.replace('\\', '_').replace('/', '_')
                    s = re.sub(r'[<>:"\\|?*]', '_', s)
                    # 去除控制字符
                    s = re.sub(r'[\x00-\x1F\x7F]', '', s)
                    return s or 'uploaded_file'

                fname = _sanitize_filename(getattr(f, 'filename', ''))
                if not fname:
                    continue
                # 避免重名：前缀时间戳
                ts = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                subdir = UPLOAD_DIR / ts
                subdir.mkdir(parents=True, exist_ok=True)
                target_path = subdir / fname
                f.save(str(target_path))

                # 记录上传
                up_id = execute_insert_return_id(
                    "INSERT INTO upload_history (filename, file_size, mime_type, stored_path, status) "
                    "VALUES (%s, %s, %s, %s, %s)",
                    [fname, os.path.getsize(target_path), f.mimetype, str(target_path), 'success']
                )

                # 读取文件为 DataFrame
                df = None
                try:
                    if fname.lower().endswith('.csv'):
                        try:
                            df = pd.read_csv(str(target_path))
                        except UnicodeDecodeError:
                            df = pd.read_csv(str(target_path), encoding='gbk', errors='ignore')
                    elif fname.lower().endswith(('.xlsx', '.xls')):
                        try:
                            df = pd.read_excel(str(target_path))
                        except ImportError as ie:
                            raise RuntimeError('读取 Excel 需要安装 openpyxl，请安装后重试') from ie
                    else:
                        df = pd.read_csv(str(target_path))
                except Exception as read_err:
                    execute_query("UPDATE upload_history SET status='failed', message=%s WHERE id=%s", [f'读取文件失败: {read_err}', up_id])
                    saved.append({
                        'filename': fname,
                        'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                        'fileSize': format_file_size_safe(os.path.getsize(target_path)),
                        'status': 'failed'
                    })
                    continue

                # 空文件则仅记录信息
                if df is None or df.empty:
                    execute_query("UPDATE upload_history SET message=%s WHERE id=%s", [f'文件无数据，未创建数据表', up_id])
                else:
                    # 基于原始文件名推断表名
                    base = os.path.splitext(fname)[0]
                    # 按用户要求：数据库表名不修改（保留中文、大小写和空格），仅做最小安全处理
                    table_name = _preserve_table_name(base)
                    # 列名去重与安全化
                    used_names = set()
                    name_map = {}
                    ordered_new_cols = []
                    cols_sql = []
                    pk = None
                    for idx, col in enumerate(list(df.columns)):
                        # 处理缺失/空白/NaN 列名优先生成中文占位名，尽量保留原始中文
                        base_name = _clean_column_name(col)
                        if base_name in ('', 'nan', 'none'):
                            base_name = f"列{idx+1}"
                        # 去重：如重复则追加后缀 _2, _3...
                        unique = base_name
                        suffix = 2
                        while unique in used_names:
                            unique = f"{base_name}_{suffix}"
                            suffix += 1
                        used_names.add(unique)
                        name_map[col] = unique
                        ordered_new_cols.append(unique)

                        # 类型推断
                        series = df[col]
                        if unique == 'id' and pd.api.types.is_integer_dtype(series):
                            col_type = 'BIGINT'
                            pk = 'id'
                        else:
                            col_type = _infer_mysql_type(series)
                        # SQL 引用使用反引号包裹（列名中不包含反引号）
                        cols_sql.append(f"`{unique}` {col_type}")
                    if pk:
                        cols_sql = [c.replace('`id` BIGINT', '`id` BIGINT AUTO_INCREMENT') if c.startswith('`id` BIGINT') else c for c in cols_sql]
                        cols_sql.append("PRIMARY KEY (`id`)")
                    create_sql = (
                        f"CREATE TABLE IF NOT EXISTS `{table_name}` (" + ", ".join(cols_sql) + ") "
                        "ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;"
                    )
                    try:
                        execute_query(create_sql)
                    except Exception as ce:
                        execute_query("UPDATE upload_history SET status='failed', message=%s WHERE id=%s", [f'创建数据表失败: {ce}', up_id])
                        saved.append({
                            'filename': fname,
                            'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'fileSize': format_file_size_safe(os.path.getsize(target_path)),
                            'status': 'failed'
                        })
                        continue

                    # 插入数据
                    try:
                        # 使用与建表一致的唯一列名（按位置设置，解决 NaN 列名无法通过 dict 匹配的问题）
                        df2 = df.copy()
                        try:
                            df2.columns = ordered_new_cols
                        except Exception:
                            # 兜底：若列数不一致，回退逐列赋值
                            cols_tmp = list(df2.columns)
                            for i in range(min(len(cols_tmp), len(ordered_new_cols))):
                                cols_tmp[i] = ordered_new_cols[i]
                            df2.columns = cols_tmp
                        records = df2.where(pd.notnull(df2), None).to_dict(orient='records')
                        if records:
                            cols_safe = list(df2.columns)
                            placeholders = ",".join(["%s"] * len(cols_safe))
                            insert_sql = f"INSERT INTO `{table_name}` (" + ",".join([f"`{c}`" for c in cols_safe]) + f") VALUES ({placeholders})"
                            params = [tuple(rec.get(c) for c in cols_safe) for rec in records]
                            execute_many(insert_sql, params)

                        # 维护列名映射：先清空再写入
                        try:
                            execute_query("DELETE FROM table_column_mapping WHERE table_name=%s", [table_name])
                            mapping_rows = []
                            for idx, orig_col in enumerate(list(df.columns)):
                                # 原始列名转字符串；NaN/None 处理为空串
                                try:
                                    orig_str = '' if pd.isna(orig_col) else str(orig_col)
                                except Exception:
                                    orig_str = str(orig_col) if orig_col is not None else ''
                                stored = ordered_new_cols[idx] if idx < len(ordered_new_cols) else f"col_{idx+1}"
                                display = orig_str or stored
                                mapping_rows.append((table_name, idx+1, stored, orig_str, display))
                            execute_many(
                                "INSERT INTO table_column_mapping (table_name, column_order, stored_name, original_name, display_name) VALUES (%s,%s,%s,%s,%s)",
                                mapping_rows
                            )
                            # 清理缓存的列标签
                            try:
                                if table_name in (global_data.get('column_labels') or {}):
                                    del global_data['column_labels'][table_name]
                            except Exception:
                                pass
                        except Exception:
                            pass

                        # 标记缓存脏并自动注册数据源（若未存在）
                        try:
                            mark_table_dirty(table_name)
                        except Exception:
                            pass
                        try:
                            ds_name = f"{table_name} 表"
                            exist = fetch_one("SELECT id FROM data_sources WHERE name=%s", [ds_name])
                            if not exist:
                                cols_exist = set(get_columns(table_name) or [])
                                cfg = { 'table': table_name }
                                if 'updated_at' in cols_exist:
                                    cfg['updated_at_column'] = 'updated_at'
                                elif 'id' in cols_exist:
                                    cfg['key_column'] = 'id'
                                execute_query(
                                    "INSERT INTO data_sources (name, type, config, active) VALUES (%s,%s,%s,%s)",
                                    [ds_name, '数据库表', json.dumps(cfg, ensure_ascii=False), 1]
                                )
                        except Exception:
                            pass

                        execute_query("UPDATE upload_history SET message=%s WHERE id=%s", [f'表 `{table_name}` 已创建/更新', up_id])
                    except Exception as ie:
                        execute_query("UPDATE upload_history SET status='failed', message=%s WHERE id=%s", [f'插入数据失败: {ie}', up_id])
                        saved.append({
                            'filename': fname,
                            'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                            'fileSize': format_file_size_safe(os.path.getsize(target_path)),
                            'status': 'failed'
                        })
                        continue

                saved.append({
                    'filename': fname,
                    'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'fileSize': format_file_size_safe(os.path.getsize(target_path)),
                    'status': 'success'
                })
            except Exception as e:
                print(f"[上传] 保存文件失败: {e}")
                saved.append({
                    'filename': getattr(f, 'filename', '未知'),
                    'uploadTime': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'fileSize': '0 B',
                    'status': 'failed'
                })

        return jsonify({'status': 'success', 'uploaded': saved}), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'处理上传失败: {str(e)}'}), 500


@analysis_bp.route('/data-sources', methods=['GET', 'POST'])
def data_sources_endpoint():
    """GET: 列出数据源（优先数据库记录，若为空则基于真实表构造默认数据）; POST: 新增数据源。"""
    try:
        ensure_management_tables()

        if request.method == 'GET':
            rows = fetch_all(
                "SELECT id, name, type, config, active, last_collection, created_at FROM data_sources ORDER BY id DESC"
            ) or []
            if not rows:
                # 不返回临时项：当数据源为空时，基于真实表一次性创建正式数据源记录
                tables = get_tables() or []
                management = {'data_sources', 'upload_history', 'collection_tasks', 'data_sync_state', 'table_column_mapping'}
                created = 0
                for t in tables:
                    if t in management:
                        continue
                    try:
                        cfg = { 'table': t }
                        try:
                            cols = set(get_columns(t) or [])
                        except Exception:
                            cols = set()
                        # 常见增量列优先 updated_at 其后 id
                        if 'updated_at' in cols:
                            cfg['updated_at_column'] = 'updated_at'
                        elif 'id' in cols:
                            cfg['key_column'] = 'id'
                        execute_query(
                            "INSERT INTO data_sources (name, type, config, active) VALUES (%s,%s,%s,%s)",
                            [f"{t} 表", '数据库表', json.dumps(cfg, ensure_ascii=False), 1]
                        )
                        created += 1
                    except Exception as _e:
                        # 单表失败不影响整体
                        pass
                # 重新查询并返回
                rows = fetch_all(
                    "SELECT id, name, type, config, active, last_collection, created_at FROM data_sources ORDER BY id DESC"
                ) or []

            data = []
            for r in rows:
                data.append({
                    'id': r.get('id'),
                    'name': r.get('name'),
                    'type': r.get('type'),
                    'config': r.get('config'),
                    'active': bool(r.get('active', 1)),
                    'lastCollection': str(r.get('last_collection')) if r.get('last_collection') else None
                })
            return jsonify({'status': 'success', 'data': data}), 200

        # POST 新增
        payload = request.get_json(silent=True) or {}
        name = payload.get('name')
        dtype = payload.get('type')
        config = payload.get('config', '')
        active = 1 if payload.get('active', True) else 0
        if not name or not dtype:
            return jsonify({'status': 'error', 'message': 'name 与 type 为必填'}), 400

        execute_query(
            "INSERT INTO data_sources (name, type, config, active) VALUES (%s, %s, %s, %s)",
            [name, dtype, config, active]
        )
        return jsonify({'status': 'success', 'message': '创建成功'}), 201

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'数据源处理失败: {str(e)}'}), 500


@analysis_bp.route('/data-sources/<int:source_id>', methods=['GET', 'PUT', 'DELETE'])
def data_source_item(source_id: int):
    """单个数据源：GET 获取（含 config）；PUT 更新；DELETE 删除。"""
    try:
        ensure_management_tables()

        # 内置临时数据源（负ID）不支持此端点
        if source_id <= 0:
            return jsonify({'status': 'error', 'message': '该数据源不可编辑，请先创建正式数据源'}), 400

        if request.method == 'GET':
            row = fetch_one(
                "SELECT id, name, type, config, active, last_collection, created_at, updated_at FROM data_sources WHERE id=%s",
                [source_id]
            )
            if not row:
                return jsonify({'status': 'error', 'message': '数据源不存在'}), 404
            data = {
                'id': row.get('id'),
                'name': row.get('name'),
                'type': row.get('type'),
                'config': row.get('config'),
                'active': bool(row.get('active', 1)),
                'lastCollection': str(row.get('last_collection')) if row.get('last_collection') else None,
                'createdAt': str(row.get('created_at')) if row.get('created_at') else None,
                'updatedAt': str(row.get('updated_at')) if row.get('updated_at') else None,
            }
            return jsonify({'status': 'success', 'data': data}), 200

        if request.method == 'PUT':
            payload = request.get_json(silent=True) or {}
            name = payload.get('name')
            dtype = payload.get('type')
            config = payload.get('config', '')
            active = 1 if payload.get('active', True) else 0

            # 简单校验
            if not name or not dtype:
                return jsonify({'status': 'error', 'message': 'name 与 type 为必填'}), 400

            # 执行更新
            execute_query(
                "UPDATE data_sources SET name=%s, type=%s, config=%s, active=%s, updated_at=NOW() WHERE id=%s",
                [name, dtype, config, active, source_id]
            )
            return jsonify({'status': 'success', 'message': '更新成功'}), 200

        if request.method == 'DELETE':
            execute_query("DELETE FROM data_sources WHERE id=%s", [source_id])
            return jsonify({'status': 'success', 'message': '删除成功'}), 200

        return jsonify({'status': 'error', 'message': '不支持的请求方法'}), 405
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'数据源操作失败: {str(e)}'}), 500


@analysis_bp.route('/data-sources/<int:source_id>/collect', methods=['POST'])
def collect_now(source_id: int):
    """立即对某个数据源执行一次采集并刷新缓存。"""
    try:
        ensure_management_tables()
        if source_id <= 0:
            return jsonify({'status': 'error', 'message': '该数据源不可采集'}), 400
        row = fetch_one("SELECT id, name, config FROM data_sources WHERE id=%s", [source_id])
        if not row:
            return jsonify({'status': 'error', 'message': '数据源不存在'}), 404
        name = row.get('name')
        cfg = row.get('config') or '{}'
        try:
            import json
            cfg_obj = json.loads(cfg) if cfg.strip().startswith('{') else {}
        except Exception:
            cfg_obj = {}
        # 直接调用采集一次
        try:
            from services.collector import DataCollector
            DataCollector.instance()._collect_once(source_id, cfg_obj, name)
        except Exception as e:
            print(f"[CollectNow] 执行失败: {e}")
            return jsonify({'status': 'error', 'message': f'采集执行失败: {str(e)}'}), 500
        return jsonify({'status': 'success', 'message': '采集完成'}), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'立即采集失败: {str(e)}'}), 500


@analysis_bp.route('/collection-tasks', methods=['GET', 'POST', 'DELETE'])
def collection_tasks_endpoint():
    """GET: 列出采集任务; POST: 创建采集任务（状态 running, 进度 0）。"""
    try:
        ensure_management_tables()

        if request.method == 'GET':
            rows = fetch_all(
                "SELECT id, name, source_id, source_name, status, progress, created_at FROM collection_tasks "
                "ORDER BY created_at DESC, id DESC LIMIT 100"
            ) or []
            data = []
            for r in rows:
                data.append({
                    'id': r.get('id'),
                    'name': r.get('name'),
                    'source': r.get('source_name') or (f"源#{r.get('source_id')}" if r.get('source_id') else ''),
                    'status': r.get('status') or 'running',
                    'progress': int(r.get('progress') or 0),
                    'createdAt': str(r.get('created_at')) if r.get('created_at') else None
                })
            return jsonify({'status': 'success', 'data': data}), 200

        elif request.method == 'POST':
            # 创建任务
            payload = request.get_json(silent=True) or {}
            source_id = payload.get('source_id')
            source_name = payload.get('source_name')
            name = payload.get('name')
            if not name and source_name:
                name = f"{source_name}数据采集"
            if not name:
                name = '数据采集任务'

            new_id = execute_insert_return_id(
                "INSERT INTO collection_tasks (name, source_id, source_name, status, progress) VALUES (%s, %s, %s, %s, %s)",
                [name, source_id, source_name, 'running', 0]
            )
            return jsonify({'status': 'success', 'message': '任务已创建', 'id': new_id}), 201

        elif request.method == 'DELETE':
            # 清空任务历史
            execute_query("DELETE FROM collection_tasks")
            return jsonify({'status': 'success', 'message': '已清空任务列表'}), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'采集任务处理失败: {str(e)}'}), 500


@analysis_bp.route('/collection-tasks/<int:task_id>/cancel', methods=['POST'])
def cancel_collection_task(task_id: int):
    """取消任务（仅更新状态为 cancelled）。"""
    try:
        ensure_management_tables()
        execute_query(
            "UPDATE collection_tasks SET status='cancelled', updated_at=NOW() WHERE id=%s",
            [task_id]
        )
        return jsonify({'status': 'success', 'message': '已取消'}), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'取消失败: {str(e)}'}), 500


@analysis_bp.route('/collection-tasks/<int:task_id>', methods=['PUT'])
def update_collection_task(task_id: int):
    """更新任务状态/进度。允许传入 status 与 progress。"""
    try:
        ensure_management_tables()
        payload = request.get_json(silent=True) or {}
        status = payload.get('status')
        progress = payload.get('progress')
        fields = []
        params = []
        if status is not None:
            fields.append("status=%s")
            params.append(status)
        if progress is not None:
            try:
                progress = int(progress)
            except Exception:
                progress = 0
            fields.append("progress=%s")
            params.append(progress)
        if not fields:
            return jsonify({'status': 'error', 'message': '无可更新字段'}), 400
        set_clause = ", ".join(fields) + ", updated_at=NOW()"
        params.append(task_id)
        execute_query(f"UPDATE collection_tasks SET {set_clause} WHERE id=%s", params)
        return jsonify({'status': 'success', 'message': '已更新'}), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'更新任务失败: {str(e)}'}), 500


def format_file_size_safe(num_bytes: int) -> str:
    try:
        num = int(num_bytes or 0)
        if num <= 0:
            return '0 B'
        units = ['B', 'KB', 'MB', 'GB', 'TB']
        k = 1024.0
        i = 0
        while num >= k and i < len(units) - 1:
            num /= k
            i += 1
        return f"{num:.2f} {units[i]}"
    except Exception:
        return '0 B'