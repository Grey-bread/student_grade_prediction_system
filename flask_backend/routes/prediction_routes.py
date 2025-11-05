# flask_backend/routes/prediction_routes.py
from flask import Blueprint, request, jsonify
import pandas as pd
import traceback, sys
from datetime import datetime
from services.prediction import PredictionService
from services.auth import verify_token
from database import execute_query, fetch_one

prediction_bp = Blueprint('prediction_bp', __name__)
prediction_service = PredictionService()

@prediction_bp.route('/predict', methods=['POST'])
def predict():
    try:
        # 验证用户身份（可选）
        auth = request.headers.get('Authorization')
        user = None
        if auth and auth.startswith('Bearer '):
            token = auth.split(' ',1)[1]
            try:
                payload = verify_token(token)
                user = payload.get('sub')
            except Exception:
                pass

        # 文件处理
        file = request.files.get('file')
        if file is None:
            return jsonify({'status':'error','message':'未收到文件'}), 400
            
        filename = file.filename.lower()
        try:
            if filename.endswith('.xlsx') or filename.endswith('.xls'):
                df = pd.read_excel(file)
            else:
                df = pd.read_csv(file)
        except Exception as e:
            return jsonify({
                'status': 'error',
                'message': f'文件读取失败: {str(e)}'
            }), 400

        if df.empty:
            return jsonify({
                'status': 'error',
                'message': '文件不包含任何数据'
            }), 400

        # 运行预测分析
        result = prediction_service.train_predict(df)
        
        # 如果用户已登录，保存预测记录
        if user:
            try:
                execute_query(
                    """INSERT INTO prediction_records 
                       (teacher_id, filename, metrics, created_at) 
                       VALUES (%s, %s, %s, %s)""",
                    (user, filename, str(result['metrics']), datetime.now())
                )
            except Exception as e:
                print(f"保存预测记录失败: {str(e)}")

        return jsonify({
            'status': 'success',
            **result
        }), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@prediction_bp.route('/history', methods=['GET'])
def get_prediction_history():
    """获取预测历史记录"""
    try:
        auth = request.headers.get('Authorization')
        if not auth or not auth.startswith('Bearer '):
            return jsonify({
                'status': 'error',
                'message': '需要登录'
            }), 401

        token = auth.split(' ', 1)[1]
        try:
            payload = verify_token(token)
            user = payload.get('sub')
        except Exception:
            return jsonify({
                'status': 'error',
                'message': 'token无效'
            }), 401

        records = fetch_one(
            """SELECT * FROM prediction_records 
               WHERE teacher_id = %s 
               ORDER BY created_at DESC 
               LIMIT 10""",
            (user,)
        )

        return jsonify({
            'status': 'success',
            'records': records
        }), 200

    except Exception as e:
        traceback.print_exc(file=sys.stdout)
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500
