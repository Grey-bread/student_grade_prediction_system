"""
应用入口（Flask）

职责：
- 创建 Flask 应用并开启 CORS
- 注册各业务蓝图（预测、教师面板、分析、训练）
- 统一异常处理，返回一致结构的 JSON 错误信息

注意：
- 不在此处做业务逻辑；仅进行应用级 wiring
- JSON_AS_ASCII=False 以支持中文返回
"""

# -*- coding: utf-8 -*-
from flask import Flask, jsonify
from flask_cors import CORS
import traceback, sys, logging
import os

# 设置环境变量以支持中文（部分底层库读取该变量）
os.environ['NLS_LANG'] = 'SIMPLIFIED CHINESE_CHINA.UTF8'

# 路由蓝图（模块内包含各自的业务端点）
from routes.prediction_routes import prediction_bp
from routes.teacher_routes import teacher_bp
from routes.analysis_routes import analysis_bp
from routes.training_routes import training_bp

app = Flask(__name__)
# 确保 JSON 响应能够正确处理中文
app.config['JSON_AS_ASCII'] = False
# 允许跨域访问（开发阶段常用，生产环境可按域配置）
CORS(app, resources={r"/*": {"origins": "*"}})

# 注册蓝图（注意前缀与前端代理保持一致）
app.register_blueprint(prediction_bp, url_prefix="/api")
app.register_blueprint(teacher_bp, url_prefix="/api/teacher")
app.register_blueprint(analysis_bp, url_prefix="/api/analysis")
app.register_blueprint(training_bp, url_prefix="/api/training")

# 简单日志配置
logging.basicConfig(level=logging.DEBUG)
app.logger.setLevel(logging.DEBUG)

@app.errorhandler(Exception)
def handle_exception(e):
    """全局异常捕获，避免未处理异常导致服务器崩溃。"""
    print("🔥 捕获到全局异常：", str(e))
    traceback.print_exc(file=sys.stdout)
    return jsonify({'status': 'error', 'message': f'服务器内部错误: {str(e)}'}), 500

@app.route('/')
def home():
    """健康检查/欢迎页。"""
    return "🎯 学生成绩预测系统后端已启动"

if __name__ == '__main__':
    # Windows/开发环境下默认 5000 端口；生产环境建议使用 WSGI（如 gunicorn+nginx）
    app.run(debug=True, host='0.0.0.0', port=5000)
