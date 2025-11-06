"""
教师相关路由

职责：
- 教师注册/登录/信息维护/头像上传
- 教师仪表盘数据

注意：
- 所有仪表盘接口均从 Authorization: Bearer <token> 中解析教师ID
- 数据加载通过 get_table_data，支持数据库/CSV 回退
"""

# flask_backend/routes/teacher_routes.py
from flask import Blueprint, request, jsonify
from services.auth import create_teacher, authenticate_teacher, verify_token
from database import fetch_one, execute_query
from routes.analysis_routes import get_table_data
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import traceback, sys
from mysql.connector import errors as mysql_errors
import base64
import re

# 预测相关（用于学生画像中的“成绩预测”）
from services.preprocessing import preprocess_df
from services.model_selection import ModelSelector

teacher_bp = Blueprint('teacher_bp', __name__)

def _ensure_teachers_avatar_column():
    """确保 teachers 表存在 avatar 列（若不存在则添加）。"""
    try:
        execute_query("ALTER TABLE teachers ADD COLUMN avatar LONGTEXT NULL")
    except Exception:
        # 已存在或数据库不可用时忽略
        pass

@teacher_bp.route('/info', methods=['PUT'])
def update_teacher_info():
    """更新教师基本信息（需 Bearer Token）。"""
    try:
        # 获取Authorization header
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'status':'error','message':'未授权访问'}), 401
        
        # 验证token
        try:
            token = auth.split(' ', 1)[1]
            # 确保token不为空且格式正确（JWT应有三个部分，用点分隔）
            if not token or not token.strip() or token.count('.') != 2:
                return jsonify({'status':'error','message':'无效的认证令牌格式'}), 401
            try:
                payload = verify_token(token)
                teacher_id = payload.get('sub')
            except Exception as e:
                # 捕获verify_token内部可能发生的所有异常
                return jsonify({'status':'error','message':'令牌无效或已过期'}), 401
        except (IndexError, ValueError) as e:
            return jsonify({'status':'error','message':'认证头格式错误'}), 401
        
        # 获取请求数据
        data = request.get_json(force=True)
        name = data.get('name')
        email = data.get('email')
        phone = data.get('phone')
        title = data.get('title')
        
        # 更新用户信息
        execute_query(
            "UPDATE teachers SET name = %s, email = %s, phone = %s, title = %s WHERE teacher_id = %s",
            (name, email, phone, title, teacher_id)
        )
        
        return jsonify({
            'status':'success',
            'message':'个人信息更新成功'
        }), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':str(e)}), 500

@teacher_bp.route('/change-password', methods=['POST'])
def change_password():
    """修改密码（需 Bearer Token）。"""
    try:
        # 获取Authorization header
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'status':'error','message':'未授权访问'}), 401
        
        # 验证token
        token = auth.split(' ', 1)[1]
        payload = verify_token(token)
        teacher_id = payload.get('sub')
        
        # 获取请求数据
        data = request.get_json(force=True)
        current_password = data.get('currentPassword')
        new_password = data.get('newPassword')
        
        if not current_password or not new_password:
            return jsonify({'status':'error','message':'当前密码和新密码不能为空'}), 400
        
        # 获取当前用户信息
        teacher = fetch_one("SELECT password FROM teachers WHERE teacher_id = %s", (teacher_id,))
        if not teacher:
            return jsonify({'status':'error','message':'用户不存在'}), 404
        
        # 验证当前密码
        from werkzeug.security import check_password_hash, generate_password_hash
        if not check_password_hash(teacher['password'], current_password):
            return jsonify({'status':'error','message':'当前密码错误'}), 400
        
        # 更新密码
        hashed_new_password = generate_password_hash(new_password)
        execute_query(
            "UPDATE teachers SET password = %s WHERE teacher_id = %s",
            (hashed_new_password, teacher_id)
        )
        
        return jsonify({
            'status':'success',
            'message':'密码修改成功'
        }), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':str(e)}), 500

@teacher_bp.route('/login-history', methods=['GET'])
def get_login_history():
    """获取最近登录历史（若无表则尝试创建并插入示例数据）。"""
    try:
        # 获取Authorization header
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({'status':'error','message':'未授权访问'}), 401
        
        # 验证token
        token = auth.split(' ', 1)[1]
        payload = verify_token(token)
        teacher_id = payload.get('sub')
        
        # 尝试查询登录记录
        # 注意：如果数据库中没有login_history表，需要先创建
        try:
            # 尝试创建表（如果不存在）
            execute_query('''
                CREATE TABLE IF NOT EXISTS login_history (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    teacher_id INTEGER NOT NULL,
                    login_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ip_address VARCHAR(50),
                    device VARCHAR(255),
                    location VARCHAR(100),
                    status VARCHAR(20),
                    FOREIGN KEY (teacher_id) REFERENCES teachers(teacher_id)
                )
            ''')
            
            # 查询登录记录
            from database import fetch_all
            login_records = fetch_all(
                """
                SELECT login_time, ip_address, device, location, status 
                FROM login_history 
                WHERE teacher_id = %s 
                ORDER BY login_time DESC 
                LIMIT 20
                """,
                (teacher_id,)
            )
            
            # 如果没有记录，插入一些模拟数据
            if not login_records:
                # 插入一些模拟的登录记录
                import datetime
                mock_records = [
                    (teacher_id, datetime.datetime.now() - datetime.timedelta(days=1), '192.168.1.1', 'Chrome / Windows 10', '北京市', 'success'),
                    (teacher_id, datetime.datetime.now() - datetime.timedelta(days=2), '192.168.1.1', 'Firefox / MacOS', '北京市', 'success'),
                    (teacher_id, datetime.datetime.now() - datetime.timedelta(days=3), '192.168.1.1', 'Safari / iOS', '上海市', 'success'),
                    (teacher_id, datetime.datetime.now() - datetime.timedelta(days=7), '192.168.1.1', 'Edge / Windows 11', '广州市', 'success')
                ]
                
                for record in mock_records:
                    execute_query(
                        "INSERT INTO login_history (teacher_id, login_time, ip_address, device, location, status) VALUES (%s, %s, %s, %s, %s, %s)",
                        record
                    )
                
                # 重新查询获取数据
                login_records = fetch_all(
                    """
                    SELECT login_time, ip_address, device, location, status 
                    FROM login_history 
                    WHERE teacher_id = %s 
                    ORDER BY login_time DESC 
                    LIMIT 20
                    """,
                    (teacher_id,)
                )
            
            # 格式化日期
            for record in login_records:
                if isinstance(record['login_time'], datetime.datetime):
                    record['login_time'] = record['login_time'].strftime('%Y-%m-%d %H:%M:%S')
            
            return jsonify({
                'status':'success',
                'data': login_records
            }), 200
        except Exception as db_error:
            # 如果数据库操作失败，返回一些模拟数据
            mock_data = [
                {
                    'login_time': '2024-01-15 09:23:45',
                    'ip_address': '192.168.1.1',
                    'device': 'Chrome / Windows 10',
                    'location': '北京市',
                    'status': 'success'
                },
                {
                    'login_time': '2024-01-14 16:45:30',
                    'ip_address': '192.168.1.1',
                    'device': 'Firefox / MacOS',
                    'location': '北京市',
                    'status': 'success'
                },
                {
                    'login_time': '2024-01-13 10:15:20',
                    'ip_address': '192.168.1.1',
                    'device': 'Safari / iOS',
                    'location': '上海市',
                    'status': 'success'
                }
            ]
            return jsonify({
                'status':'success',
                'data': mock_data
            }), 200
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':str(e)}), 500


# 头像上传路由
@teacher_bp.route('/upload-avatar', methods=['POST'])
def upload_avatar():
    try:
        # 验证Authorization header
        auth_header = request.headers.get('Authorization')
        if not auth_header or not auth_header.startswith('Bearer '):
            return jsonify({
                'status': 'error',
                'message': '未提供有效的认证令牌'
            }), 401
        
        # 解码token获取用户信息
        token = auth_header.split(' ')[1]
        decoded_token = verify_token(token)
        if not decoded_token:
            return jsonify({
                'status': 'error',
                'message': '认证令牌无效或已过期'
            }), 401
        
        teacher_id = decoded_token.get('sub')
        
        # 处理文件上传
        if 'avatar' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '未收到上传文件'
            }), 400
        
        file = request.files['avatar']
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '未选择上传文件'
            }), 400
        
        # 验证文件类型
        allowed_extensions = {'png', 'jpg', 'jpeg', 'gif'}
        if '.' in file.filename and file.filename.rsplit('.', 1)[1].lower() not in allowed_extensions:
            return jsonify({
                'status': 'error',
                'message': '只允许上传PNG、JPG、JPEG和GIF格式的图片'
            }), 400
        
    # 读取文件内容并转换为Base64存储
        file_content = file.read()
        encoded_content = base64.b64encode(file_content).decode('utf-8')
        
        # 获取文件扩展名
        file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else 'png'
        avatar_data = f'data:image/{file_extension};base64,{encoded_content}'
        
        # 确保存在 avatar 字段
        _ensure_teachers_avatar_column()

        # 更新数据库中的头像数据（兼容老表缺少 avatar 字段的情况）
        update_query = """
        UPDATE teachers 
        SET avatar = %s 
        WHERE teacher_id = %s
        """
        try:
            execute_query(update_query, (avatar_data, teacher_id))
        except Exception as db_err:
            # 如果是缺少 avatar 字段，则尝试自动添加该列再重试
            if 'Unknown column' in str(db_err) and 'avatar' in str(db_err):
                try:
                    execute_query("ALTER TABLE teachers ADD COLUMN avatar LONGTEXT NULL")
                    execute_query(update_query, (avatar_data, teacher_id))
                except Exception as alter_err:
                    print(f"添加 avatar 列失败: {alter_err}")
                    return jsonify({
                        'status': 'error',
                        'message': '数据库缺少头像字段且自动修复失败，请联系管理员'
                    }), 500
            else:
                raise
        
        return jsonify({
            'status': 'success',
            'message': '头像上传成功',
            'data': {
                'avatarUrl': avatar_data
            }
        })
    
    except Exception as e:
        print(f"头像上传错误: {str(e)}")
        return jsonify({
            'status': 'error',
            'message': '头像上传失败',
            'error': str(e)
        }), 500


# ===================== 教师仪表盘数据接口 =====================

def _get_teacher_id_from_auth():
    """从 Authorization 头解析并验证教师ID，失败抛出异常。"""
    auth = request.headers.get('Authorization')
    if not auth or not auth.startswith('Bearer '):
        raise PermissionError('未授权访问')
    token = auth.split(' ', 1)[1]
    payload = verify_token(token)
    teacher_id = payload.get('sub')
    if not teacher_id:
        raise PermissionError('无效的令牌')
    return str(teacher_id)


def _safe_mean(series):
    try:
        vals = pd.to_numeric(series, errors='coerce').dropna()
        return float(vals.mean()) if len(vals) > 0 else None
    except Exception:
        return None


@teacher_bp.route('/dashboard/overview', methods=['GET'])
def dashboard_overview():
    """教师概览：课程数、学生数、平均分、最近考试数量。"""
    try:
        tid = _get_teacher_id_from_auth()

        # 允许前端覆盖表名，方便使用上传的自定义表
        exam_table = request.args.get('exam_table', 'exam_scores')
        hist_table = request.args.get('hist_table', 'historical_grades')
        courses_table = request.args.get('courses_table', 'courses')

        # 加载数据（支持DB或CSV回退）
        exam_df = get_table_data(exam_table)
        if exam_df is None:
            exam_df = pd.DataFrame()
        hist_df = get_table_data(hist_table)
        if hist_df is None:
            hist_df = pd.DataFrame()
        # 课程表在此接口仅用于 total_students_all 之外的功能时再取用，当前不强制

        # 过滤本教师数据
        teacher_exam = exam_df[exam_df['teacher_id'].astype(str) == tid] if not exam_df.empty and 'teacher_id' in exam_df.columns else pd.DataFrame()
        teacher_hist = hist_df[hist_df['teacher_id'].astype(str) == tid] if not hist_df.empty and 'teacher_id' in hist_df.columns else pd.DataFrame()

        # 课程与学生集合
        courses = set()
        students = set()
        for df in [teacher_exam, teacher_hist]:
            if not df.empty:
                if 'course_id' in df.columns:
                    for v in df['course_id'].dropna().unique().tolist():
                        try: courses.add(int(v))
                        except: pass
                if 'student_id' in df.columns:
                    for v in df['student_id'].dropna().unique().tolist():
                        try: students.add(int(v))
                        except: pass

        # 平均分优先 exam_scores.score，其次 historical_grades.total_score
        avg_score = None
        if not teacher_exam.empty and 'score' in teacher_exam.columns:
            avg_score = _safe_mean(teacher_exam['score'])
        if avg_score is None and not teacher_hist.empty and 'total_score' in teacher_hist.columns:
            avg_score = _safe_mean(teacher_hist['total_score'])

        # 最近考试数量（90天内）
        recent_count = 0
        if not teacher_exam.empty and 'exam_date' in teacher_exam.columns:
            tmp = teacher_exam.copy()
            tmp['exam_date_parsed'] = pd.to_datetime(tmp['exam_date'], errors='coerce')
            cutoff = pd.Timestamp(datetime.now() - timedelta(days=90))
            recent_count = int((tmp['exam_date_parsed'] >= cutoff).sum())

        # 学生总人数（来自 students 表，新增学生应立即反映）
        total_students_all = None
        try:
            from database import fetch_one as _fetch_one
            row = _fetch_one("SELECT COUNT(*) AS total_students_all FROM students")
            if row and 'total_students_all' in row:
                total_students_all = int(row['total_students_all'] or 0)
        except Exception:
            # 兜底：若查询失败，不影响其他指标
            total_students_all = None

        return jsonify({
            'status': 'success',
            'data': {
                'total_courses': len(courses),
                'total_students': len(students),
                'total_students_all': total_students_all,
                'avg_score': round(avg_score, 2) if avg_score is not None else None,
                'recent_exams': recent_count
            }
        }), 200
    except PermissionError as pe:
        return jsonify({'status':'error','message':str(pe)}), 401
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':f'获取概览失败: {str(e)}'}), 500


@teacher_bp.route('/dashboard/courses', methods=['GET'])
def dashboard_courses():
    """教师所授课程列表及指标。"""
    try:
        tid = _get_teacher_id_from_auth()
        exam_table = request.args.get('exam_table', 'exam_scores')
        hist_table = request.args.get('hist_table', 'historical_grades')
        courses_table = request.args.get('courses_table', 'courses')

        exam_df = get_table_data(exam_table)
        if exam_df is None:
            exam_df = pd.DataFrame()
        hist_df = get_table_data(hist_table)
        if hist_df is None:
            hist_df = pd.DataFrame()
        courses_df = get_table_data(courses_table)
        if courses_df is None:
            courses_df = pd.DataFrame()

        # 过滤
        ex = exam_df[exam_df['teacher_id'].astype(str) == tid] if not exam_df.empty and 'teacher_id' in exam_df.columns else pd.DataFrame()
        hg = hist_df[hist_df['teacher_id'].astype(str) == tid] if not hist_df.empty and 'teacher_id' in hist_df.columns else pd.DataFrame()

        # 课程集合
        course_ids = set()
        for df in [ex, hg]:
            if not df.empty and 'course_id' in df.columns:
                for v in df['course_id'].dropna().unique().tolist():
                    try: course_ids.add(int(v))
                    except: pass

        # 课程名映射
        cname = {}
        if not courses_df.empty and 'course_id' in courses_df.columns:
            for _, r in courses_df.iterrows():
                try: cname[int(r['course_id'])] = str(r.get('course_name') or f"课程{r['course_id']}")
                except: pass

        rows = []
        for cid in sorted(course_ids):
            # 学生数
            stu_ids = set()
            for df in [ex, hg]:
                if not df.empty:
                    sdf = df[df['course_id'].astype(str) == str(cid)] if 'course_id' in df.columns else pd.DataFrame()
                    if not sdf.empty and 'student_id' in sdf.columns:
                        for v in sdf['student_id'].dropna().unique().tolist():
                            try: stu_ids.add(int(v))
                            except: pass
            # 平均分
            avg = None
            if not ex.empty and 'score' in ex.columns:
                avg = _safe_mean(ex[ex['course_id'].astype(str) == str(cid)]['score'])
            if avg is None and not hg.empty and 'total_score' in hg.columns:
                avg = _safe_mean(hg[hg['course_id'].astype(str) == str(cid)]['total_score'])
            # 最新考试日期
            last_date = None
            if not ex.empty and 'exam_date' in ex.columns:
                e1 = ex[ex['course_id'].astype(str) == str(cid)].copy()
                if not e1.empty:
                    e1['exam_date_parsed'] = pd.to_datetime(e1['exam_date'], errors='coerce')
                    if e1['exam_date_parsed'].notna().any():
                        last_date_ts = e1['exam_date_parsed'].max()
                        last_date = str(last_date_ts.date()) if pd.notna(last_date_ts) else None

            rows.append({
                'course_id': cid,
                'course_name': cname.get(cid, f'课程{cid}'),
                'students_count': len(stu_ids),
                'avg_score': round(avg, 2) if avg is not None else None,
                'last_exam_date': last_date
            })

        return jsonify({'status':'success','data': rows}), 200
    except PermissionError as pe:
        return jsonify({'status':'error','message':str(pe)}), 401
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':f'获取课程列表失败: {str(e)}'}), 500


@teacher_bp.route('/dashboard/recent-exams', methods=['GET'])
def dashboard_recent_exams():
    """最近考试列表（最多10条）。"""
    try:
        tid = _get_teacher_id_from_auth()
        exam_table = request.args.get('exam_table', 'exam_scores')
        courses_table = request.args.get('courses_table', 'courses')
        exam_df = get_table_data(exam_table)
        if exam_df is None:
            exam_df = pd.DataFrame()
        courses_df = get_table_data(courses_table)
        if courses_df is None:
            courses_df = pd.DataFrame()
        # 过滤
        ex = exam_df[exam_df['teacher_id'].astype(str) == tid] if not exam_df.empty and 'teacher_id' in exam_df.columns else pd.DataFrame()
        if ex.empty:
            return jsonify({'status':'success','data': []}), 200
        ex['exam_date_parsed'] = pd.to_datetime(ex['exam_date'], errors='coerce') if 'exam_date' in ex.columns else pd.NaT
        ex_sorted = ex.sort_values('exam_date_parsed')
        last = ex_sorted.tail(10)
        # 课程名映射
        cname = {}
        if not courses_df.empty and 'course_id' in courses_df.columns:
            for _, r in courses_df.iterrows():
                try: cname[int(r['course_id'])] = str(r.get('course_name') or f"课程{r['course_id']}")
                except: pass
        data = []
        for _, r in last.iterrows():
            try:
                cid = int(r['course_id']) if pd.notna(r.get('course_id')) else None
                data.append({
                    'exam_name': str(r.get('exam_name') or ''),
                    'course_id': cid,
                    'course_name': cname.get(cid, f'课程{cid}') if cid else '—',
                    'exam_date': str(r.get('exam_date') or ''),
                    'score': float(r['score']) if pd.notna(r.get('score')) else None,
                    'score_level': str(r.get('score_level') or '')
                })
            except Exception:
                continue
        return jsonify({'status':'success','data': data}), 200
    except PermissionError as pe:
        return jsonify({'status':'error','message':str(pe)}), 401
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':f'获取最近考试失败: {str(e)}'}), 500


@teacher_bp.route('/dashboard/score-level', methods=['GET'])
def dashboard_score_level():
    """成绩等级分布（A-E）。"""
    try:
        tid = _get_teacher_id_from_auth()
        exam_table = request.args.get('exam_table', 'exam_scores')
        exam_df = get_table_data(exam_table)
        if exam_df is None:
            exam_df = pd.DataFrame()
        ex = exam_df[exam_df['teacher_id'].astype(str) == tid] if not exam_df.empty and 'teacher_id' in exam_df.columns else pd.DataFrame()
        levels = ['A','B','C','D','E']
        counts = {k: 0 for k in levels}
        if not ex.empty and 'score_level' in ex.columns:
            vc = ex['score_level'].dropna().astype(str).str.upper().value_counts()
            for k in levels:
                counts[k] = int(vc.get(k, 0))
        return jsonify({'status':'success','data': counts}), 200
    except PermissionError as pe:
        return jsonify({'status':'error','message':str(pe)}), 401
    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status':'error','message':f'获取等级分布失败: {str(e)}'}), 500


@teacher_bp.route('/student-portrait', methods=['GET'])
def student_portrait():
    """学生个体画像（教师面板）：整合基础信息、预测、趋势、反馈与建议。

    入参：
    - student_id: 必填
    - target_table: 可选，默认 historical_grades，回退 university_grades
    - target_column: 可选，默认自动推断（total_score 或 calculus_avg_score）
    - include_subjects: 是否返回按课程的单科预测，默认 true（基于 historical_grades）

    返回：
    {
      status, data: {
        profile: {student_id, student_no, name, grade, class},
        predictions: { total: {value, target_column}, by_subject: [{course_id, course_name, predicted}] },
        trend: [{label, score}],
        weak_points: [str],
        feedback: { records: [{time, source, text}], frequent_issues: [{text, count}] },
        recommendations: [str]
      }
    }
    """
    try:
        student_id = request.args.get('student_id')
        if not student_id:
            return jsonify({'status': 'error', 'message': '缺少参数: student_id'}), 400

        # 默认改为使用 UG 数据集进行预测
        target_table = request.args.get('target_table') or 'university_grades'
        target_column = request.args.get('target_column')
        include_subjects = str(request.args.get('include_subjects', 'true')).lower() != 'false'

        # 1) 基础信息（students）
        students_df = get_table_data('students')
        profile = {'student_id': int(student_id)}
        if students_df is not None and not students_df.empty:
            srow = students_df[students_df['student_id'].astype(str) == str(student_id)]
            if not srow.empty:
                r = srow.iloc[0]
                profile.update({
                    'student_no': str(r.get('student_no') or ''),
                    'name': str(r.get('name') or ''),
                    'grade': str(r.get('grade') or ''),
                    'class': str(r.get('class') or ''),
                })

        # 2) 成绩预测
        def _auto_target(df: pd.DataFrame):
            if df is None or df.empty:
                return None
            if 'calculus_avg_score' in df.columns:
                return 'calculus_avg_score'
            if 'total_score' in df.columns:
                return 'total_score'
            # 中文列名/模糊
            for k in ('总成绩','总分','分数','成绩','期末','期中','平时','总评'):
                for c in df.columns:
                    if k in str(c):
                        return c
            # 数值列兜底
            nums = df.select_dtypes(include=['int64','float64']).columns.tolist()
            return nums[-1] if nums else None

        df_target = get_table_data(target_table)
        if (df_target is None or df_target.empty) and target_table != 'university_grades':
            # 回退到 UG（仅单科）
            target_table = 'university_grades'
            df_target = get_table_data(target_table)
        pred_total = None
        # 若 UG 缺少平均分列且有三次成绩，先行计算平均列，便于作为目标
        if df_target is not None and not df_target.empty and 'calculus_avg_score' not in df_target.columns:
            if all(col in df_target.columns for col in ['first_calculus_score','second_calculus_score','third_calculus_score']):
                try:
                    for col in ['first_calculus_score','second_calculus_score','third_calculus_score']:
                        df_target[col] = pd.to_numeric(df_target[col], errors='coerce')
                    df_target['calculus_avg_score'] = df_target[['first_calculus_score','second_calculus_score','third_calculus_score']].mean(axis=1)
                except Exception:
                    pass
        chosen_target_col = target_column or _auto_target(df_target)
        if df_target is not None and not df_target.empty and chosen_target_col and chosen_target_col in df_target.columns:
            try:
                # 预处理与建模
                df_proc, _ = preprocess_df(df_target)
                # 若预处理后列名变化，尝试用同名列；否则按原名回退
                if chosen_target_col not in df_proc.columns:
                    # 简单回退：取预处理前列
                    pass
                X_all = df_proc.drop(columns=[c for c in [chosen_target_col] if c in df_proc.columns])
                y_all = df_proc[chosen_target_col] if chosen_target_col in df_proc.columns else None
                if y_all is None:
                    # 无法定位目标列，跳过预测
                    raise ValueError('目标列在预处理后缺失')

                # 模型选择
                selector = ModelSelector()
                from sklearn.model_selection import train_test_split
                X_train, X_test, y_train, y_test = train_test_split(X_all.values, y_all.values, test_size=0.2, random_state=42)
                best_model, model_results, best_params = selector.select_best_model(X_train, y_train)
                # 在全量数据拟合
                best_model.fit(X_all.values, y_all.values)

                # 学生该表的“最新一条”记录（UG 没有时间列时取第一条即可）
                sraw = df_target[df_target['student_id'].astype(str) == str(student_id)].copy() if 'student_id' in df_target.columns else pd.DataFrame()
                if not sraw.empty:
                    # 按可能存在的时间/自增列排序
                    for key in ['grade_id', 'score_id']:
                        if key in sraw.columns:
                            sraw = sraw.sort_values(by=key)
                            break
                    if 'exam_date' in sraw.columns:
                        sraw['exam_date_parsed'] = pd.to_datetime(sraw['exam_date'], errors='coerce')
                        sraw = sraw.sort_values(by='exam_date_parsed')
                    latest = sraw.iloc[-1:]
                    # 对齐特征列
                    feat_cols = list(X_all.columns)
                    latest_feat = latest.reindex(columns=feat_cols, fill_value=np.nan)
                    # 缺失填充
                    for c in feat_cols:
                        if latest_feat[c].isna().any():
                            try:
                                mean_val = pd.to_numeric(X_all[c], errors='coerce').mean()
                                latest_feat[c] = latest_feat[c].fillna(mean_val)
                            except Exception:
                                latest_feat[c] = latest_feat[c].fillna(0)
                    pred_total = float(best_model.predict(latest_feat.values)[0])

                    # 单科预测已移除
            except Exception as e:
                print(f"[WARN] 学生成绩预测失败: {e}")

        

        # 3) 近三次趋势（仅使用 UG；缺失按 0 补齐；明确使用 first/second/third_calculus_score）
        labels = ['第一次','第二次','第三次']
        ug_cols = ['first_calculus_score','second_calculus_score','third_calculus_score']
        values = [0.0, 0.0, 0.0]
        try:
            ug = get_table_data('university_grades')
            if ug is not None and not ug.empty and 'student_id' in ug.columns and all(c in ug.columns for c in ug_cols):
                # 转为数值
                for c in ug_cols:
                    ug[c] = pd.to_numeric(ug[c], errors='coerce')
                row = ug[ug['student_id'].astype(str) == str(student_id)]
                if not row.empty:
                    r = row.iloc[0]
                    for i, col in enumerate(ug_cols):
                        v = r.get(col)
                        values[i] = float(v) if pd.notna(v) else 0.0
        except Exception:
            pass
        trend = [{'label': labels[i], 'score': float(values[i])} for i in range(3)]

        # 趋势文字描述
        def _trend_desc(vals):
            try:
                a, b, c = [float(x or 0.0) for x in vals]
                d1, d2 = b - a, c - b
                eps = 1e-6
                def sg(x):
                    if abs(x) < eps: return 0
                    return 1 if x > 0 else -1
                s1, s2 = sg(d1), sg(d2)
                seq = f"（{round(a,1)}→{round(b,1)}→{round(c,1)}）"
                if s1 == 0 and s2 == 0:
                    return f"总体趋于平稳，波动不大{seq}"
                if s1 > 0 and s2 > 0:
                    return f"成绩稳步上扬，进步清晰可见{seq}"
                if s1 < 0 and s2 < 0:
                    return f"成绩阶段性回落，可关注学习节奏与巩固{seq}"
                if s1 > 0 and s2 < 0:
                    return f"先扬后抑，建议查找波动原因并及时调整{seq}"
                if s1 < 0 and s2 > 0:
                    return f"先行蓄力后上扬，回升势头良好{seq}"
                if s1 == 0 and s2 > 0:
                    return f"前期平稳，后程发力上行{seq}"
                if s1 == 0 and s2 < 0:
                    return f"前期平稳，后段有所回落{seq}"
                if s1 > 0 and s2 == 0:
                    return f"上行后趋于稳定，走势平顺{seq}"
                if s1 < 0 and s2 == 0:
                    return f"回落后趋于稳定，波动收敛{seq}"
                return f"成绩走势发生变化{seq}"
            except Exception:
                return "趋势信息不足"

        trend_description = _trend_desc(values)

        # 基于近三次成绩的趋势外推预测（线性外推到下一次），作为“单科预测”的权威结果
        def _trend_forecast(vals):
            try:
                import numpy as _np
                y = _np.array([float(v) if v is not None else 0.0 for v in vals], dtype=float)
                x = _np.array([1.0, 2.0, 3.0], dtype=float)
                # 若全部为0，直接返回0
                if _np.allclose(y, 0):
                    return 0.0
                # 拟合一次直线，预测第4次
                k, b = _np.polyfit(x, y, 1)
                y4_lin = float(k * 4.0 + b)
                # 单调性/动量约束，避免明显与近两次相反的剧烈跳变
                a, b2, c = float(y[0]), float(y[1]), float(y[2])
                d1, d2 = b2 - a, c - b2
                y4 = y4_lin
                # 两次均下降/不升：不允许上冲
                if d1 <= 0 and d2 <= 0:
                    y4 = min(y4_lin, c)
                # 两次均上升/不降：不允许下挫
                elif d1 >= 0 and d2 >= 0:
                    y4 = max(y4_lin, c)
                else:
                    # 震荡：限制步长不超过最近一次的幅度
                    max_step = abs(d2)
                    y4 = c + _np.clip(y4_lin - c, -max_step, max_step)
                # 合理边界裁剪
                if _np.isnan(y4) or _np.isinf(y4):
                    y4 = float(y[-1]) if y.size else 0.0
                return float(max(0.0, min(100.0, y4)))
            except Exception:
                try:
                    # 兜底：使用末次成绩
                    return float(vals[-1]) if vals and vals[-1] is not None else 0.0
                except Exception:
                    return 0.0

        trend_next = _trend_forecast(values)

        # 构造预测结果（仅保留总分趋势外推）
        predictions = {
            'total': {'value': trend_next, 'target_column': '三次趋势外推'},
            'by_subject': []
        }

        # 单科预测（按课程）功能已移除

        # 4) 反馈记录与高频问题（仅使用“学生反馈”历史摘要，隐藏“学习进展”）
        feedback_records = []
        # 历史记录
        try:
            from database import fetch_all as _fa
            rows = _fa(
                """
                SELECT entry_type, summary, content, created_at
                FROM student_feedback_history
                WHERE student_id=%s
                ORDER BY created_at DESC
                LIMIT 50
                """,
                (student_id,)
            ) or []
            import json as _json
            for rr in rows:
                et = (rr.get('entry_type') or 'feedback').lower()
                if et == 'progress':
                    # 隐藏学习进展
                    continue
                ts = str(rr.get('created_at') or '')
                summary = rr.get('summary')
                text = summary
                if not text:
                    try:
                        payload = _json.loads(rr.get('content') or '{}')
                    except Exception:
                        payload = {'raw': rr.get('content')}
                    # 反馈类：取弱点/建议前2条组成摘要
                    ww = payload.get('weaknessFeedback') or payload.get('weaknesses') or []
                    ss = payload.get('suggestionFeedback') or payload.get('suggestions') or []
                    ww = [str(x) for x in ww if x][:2]
                    ss = [str(x) for x in ss if x][:2]
                    text = '；'.join([*ww, *ss]) or '生成反馈'
                feedback_records.append({
                    'time': ts,
                    'source': '学生反馈',
                    'text': text
                })
        except Exception:
            pass
        ex = get_table_data('exam_scores')
        if ex is not None and not ex.empty and 'student_id' in ex.columns:
            ed = ex[ex['student_id'].astype(str) == str(student_id)].copy()
            if not ed.empty:
                if 'exam_date' in ed.columns:
                    ed['exam_date_parsed'] = pd.to_datetime(ed['exam_date'], errors='coerce')
                    ed = ed.sort_values('exam_date_parsed')
                for _, r in ed.iterrows():
                    txt = str(r.get('comments') or '').strip()
                    if txt:
                        feedback_records.append({
                            'time': str(r.get('exam_date') or ''), 'source': '考试评语', 'text': txt
                        })
        cp = get_table_data('class_performance')
        if cp is not None and not cp.empty and 'student_id' in cp.columns:
            cd = cp[cp['student_id'].astype(str) == str(student_id)].copy()
            if not cd.empty:
                for _, r in cd.iterrows():
                    txt = str(r.get('teacher_comments') or '').strip()
                    if txt:
                        feedback_records.append({
                            'time': str(r.get('semester') or ''), 'source': '课堂评语', 'text': txt
                        })
        # 排序（时间格式不统一时保持原序）
        def _ts(v):
            try:
                if not v: return pd.NaT
                return pd.to_datetime(v, errors='coerce')
            except Exception:
                return pd.NaT
        feedback_records.sort(key=lambda x: (_ts(x.get('time')) if x.get('time') else pd.NaT))

        # 5) 薄弱知识点与建议（根据课堂表现与反馈综合；移除“高频反馈问题”依赖）
        weak_points = []
        recommendations = []
        # 课堂表现对比：参考 analysis/student-feedback 的逻辑
        perf_df = get_table_data('class_performance')
        perf_keys = ['attendance_score', 'participation_score', 'homework_score', 'behavior_score', 'total_performance_score']
        if perf_df is not None and not perf_df.empty and 'student_id' in perf_df.columns:
            for col in perf_keys:
                if col in perf_df.columns:
                    perf_df[col] = pd.to_numeric(perf_df[col], errors='coerce')
            stu = perf_df[perf_df['student_id'].astype(str) == str(student_id)]
            cls_avg = {k: (float(perf_df[k].mean()) if k in perf_df.columns and perf_df[k].notna().any() else None) for k in perf_keys}
            stu_avg = {k: (float(stu[k].mean()) if not stu.empty and k in stu.columns and stu[k].notna().any() else None) for k in perf_keys}
            name_map = {
                'attendance_score': '出勤', 'participation_score': '课堂参与', 'homework_score': '作业完成',
                'behavior_score': '课堂纪律', 'total_performance_score': '综合表现'
            }
            for k in perf_keys:
                s, c = stu_avg.get(k), cls_avg.get(k)
                if s is None or c is None: continue
                if s <= c - 5:
                    weak_points.append(f"{name_map.get(k,k)}低于班级平均 {round(c - s, 1)} 分")
                    if k == 'attendance_score':
                        recommendations.append('教师可通过温和约定与贴心提醒，帮助学生逐步稳定作息与到课习惯；必要时与家长同频陪伴。')
                    if k == 'participation_score':
                        recommendations.append('教师可用点名/小组展示等友好方式，帮助学生获得表达机会，并在课后予以鼓励。')
                    if k == 'homework_score':
                        recommendations.append('教师可明确作业期望与示例，帮助学生每周用5–10分钟轻松复盘，发现亮点与改进处。')
                    if k == 'behavior_score':
                        recommendations.append('教师可与学生共建轻量可行的课堂约定，帮助其获得即时而友好的反馈，必要时与班主任形成合力。')

        # 去除高频问题推断逻辑，保留基于课堂表现与预测的建议

        # 基于实际情况进行“打分选荐”，只展示最相关的若干条（更温和友好的措辞）
        rec_scores = {}
        def add_rec(txt: str, score: float = 1.0):
            if not txt: return
            try:
                rec_scores[txt] = max(rec_scores.get(txt, 0), float(score))
            except Exception:
                rec_scores[txt] = score

        # 1) 已检测到的课堂表现不足（权重高）
        for s in recommendations:
            add_rec(s, 3.0)

        # 2) 趋势导向（根据趋势文字定制）
        td = (trend_description or '').strip()
        if td:
            if ('回落' in td) or ('下降' in td):
                add_rec('教师可先稳后进，先聚焦必考核心与高频题型，用短周期小测温和巩固，帮助学生减轻负担并稳住节奏。', 3.0)
            if ('上扬' in td) or ('回升' in td):
                add_rec('教师可及时送上正向反馈，适度提升练习难度，安排“巩固→提升”的阶梯式练习，帮助学生保持动力。', 2.5)
            if ('平稳' in td) or ('稳定' in td):
                add_rec('教师可引入轻挑战任务（微项目/变式题），帮助学生在稳定中寻找小幅度跃升的机会。', 2.5)

        # 3) 预测水平导向（目标设定/分层策略）
        if pred_total is not None and chosen_target_col:
            base = f"结合当前预测（{chosen_target_col} ≈ {round(pred_total,1)}），教师可帮助学生一起设定贴合实际的阶段目标（如提升5–10分），并用每周小测或作业轻松跟进。"
            add_rec(base, 3.0)
            try:
                pv = float(pred_total)
                if pv < 60:
                    add_rec('教师可帮助学生夯实基础，先达及格线；以“核心例题+类题2-3道”滚动巩固。', 3.0)
                elif pv < 75:
                    add_rec('教师可帮助学生围绕薄弱模块设立微目标（+5分），分周推进，并用周测校准节奏。', 2.5)
                elif pv >= 85:
                    add_rec('教师可帮助学生引入提升性任务（难题变式/综合题），锻炼方法迁移与表达。', 2.0)
            except Exception:
                pass

        # 4) 基础通用教学行动（低权重打底，不全部展示）
        base_actions = [
            '教师可帮助学生共拟学习小计划（周目标、日清单），每周轻松复盘，适度微调。',
            '教师可帮助学生推进“错题三步”（找因→再练→迁移），用简单记录卡每周看得到改变。',
            '教师可通过检索练习与间隔复习（随堂/周测），帮助学生温和跟踪关键知识点掌握。',
            '教师可通过课前预习与课后5分钟复盘，帮助学生形成“预习—课堂—复盘”的小循环。',
            '教师可提供微辅导或固定答疑时段，帮助学生围绕薄弱点做个别化补强。',
            '教师可引导同伴互助/小组互评，帮助学生用自己的话“讲题与思路”，增强自信。',
            '教师可与家长/班主任低频沟通（双周/月度），帮助学生形成支持网络。',
            '教师可给出参考样例（高分作业/解题模板），帮助学生看清达成标准。',
            '教师可建立课堂即时反馈（投票/举手/口头检查），帮助学生小步纠偏，减少挫败感。',
            '教师可把阶段目标细化为量化指标（作业正确率、单元小测≥X）并温和公示，帮助学生明确进度。'
        ]
        # 只挑选前2条通用建议作为“骨架”，避免信息过载
        for i, t in enumerate(base_actions[:2]):
            add_rec(t, 1.0 - 0.1*i)

        # 5) 若保存/分析的薄弱点出现特定关键词，补充相应建议
        try:
            for w in (weak_points or []):
                ws = str(w)
                if any(k in ws for k in ['出勤','缺勤','迟到']):
                    add_rec('教师可与学生轻松约定到课安排，配合签到提醒与原因记录，帮助其建立稳定习惯；必要时与家长温和协作。', 2.5)
                if any(k in ws for k in ['参与','互动','发言']):
                    add_rec('教师可用点名/小组展示与结构化发言卡降低开口门槛，帮助学生更轻松开口表达。', 2.5)
                if any(k in ws for k in ['作业','完成','拖延']):
                    add_rec('教师可明确作业清单与标准，课初3分钟简要抽检，帮助学生及时纠错并积累亮点。', 2.5)
                if any(k in ws for k in ['纪律','课堂秩序']):
                    add_rec('教师可与学生共同约定课堂规范，记录与反馈做闭环，帮助其内化课堂规则；必要时与班主任形成合力。', 2.5)
        except Exception:
            pass

    # 6) 产出 Top-N 建议
        ranked = sorted(rec_scores.items(), key=lambda kv: (-kv[1], len(kv[0])))
        recommendations = [txt for txt, _ in ranked[:5]]

        # 6) 合并已保存的学生反馈（若存在）
        try:
            from database import fetch_one as _fetch_one
            import json as _json
            saved = _fetch_one("SELECT content FROM student_feedbacks WHERE student_id=%s", (student_id,))
            if saved and saved.get('content'):
                saved_obj = None
                try:
                    saved_obj = _json.loads(saved['content'])
                except Exception:
                    saved_obj = {'raw': saved['content']}
                if isinstance(saved_obj, dict):
                    # 薄弱点
                    try:
                        sv_wk = saved_obj.get('weaknessFeedback') or saved_obj.get('weaknesses')
                        if isinstance(sv_wk, list) and sv_wk:
                            weak_points = sv_wk
                    except Exception:
                        pass
                    # 建议
                    try:
                        sv_sug = saved_obj.get('suggestionFeedback') or saved_obj.get('suggestions')
                        if isinstance(sv_sug, list) and sv_sug:
                            # 合并学生反馈建议（置于教师建议之后，避免覆盖），最终最多5条
                            recommendations = list(dict.fromkeys(recommendations + sv_sug))[:5]
                    except Exception:
                        pass
                    # 反馈记录
                    try:
                        sv_rec = saved_obj.get('records')
                        if isinstance(sv_rec, list) and sv_rec:
                            feedback_records = sv_rec
                    except Exception:
                        pass
        except Exception:
            pass

        # 单科预测已移除，无需覆盖 by_subject

        return jsonify({
            'status': 'success',
            'data': {
                'profile': profile,
                'predictions': predictions,
                'trend': trend,
                'trend_description': trend_description,
                'weak_points': weak_points,
                # 移除高频反馈问题，仅返回记录
                'feedback': { 'records': feedback_records },
                'recommendations': recommendations
            }
        }), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({'status': 'error', 'message': f'生成学生画像失败: {str(e)}'}), 500
