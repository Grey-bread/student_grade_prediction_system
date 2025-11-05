# flask_backend/services/auth.py
import time, jwt, os, traceback
from werkzeug.security import generate_password_hash, check_password_hash
from database import execute_query, fetch_one

# secret for JWT - 从环境变量读取，如果不存在则使用默认值
# 注意：生产环境必须设置 JWT_SECRET 环境变量
try:
    from dotenv import load_dotenv
    from pathlib import Path
    # 尝试从flask_backend目录加载.env
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        print(f"[OK] [auth.py] 已加载环境变量文件: {env_path}")
    else:
        # 尝试从项目根目录加载
        root_env_path = Path(__file__).parent.parent / '.env'
        if root_env_path.exists():
            load_dotenv(dotenv_path=root_env_path, override=True)
            print(f"[OK] [auth.py] 已从项目根目录加载环境变量文件: {root_env_path}")
        else:
            print(f"[WARN] [auth.py] .env 文件不存在于 {env_path} 或 {root_env_path}")
except ImportError:
    print("[WARN] [auth.py] python-dotenv 未安装，使用系统环境变量")

JWT_SECRET = os.environ.get('JWT_SECRET', 'default_secret_key_change_in_production')
JWT_ALG = 'HS256'
JWT_EXPIRE = 60 * 60 * 24 * 7  # 延长到7天，避免频繁过期

# 打印JWT_SECRET加载状态（仅用于调试，显示前8个字符用于确认）
secret_preview = JWT_SECRET[:8] + '...' if len(JWT_SECRET) > 8 else JWT_SECRET
is_default = JWT_SECRET == 'default_secret_key_change_in_production'
print(f"[JWT] [auth.py] JWT_SECRET已加载: {'已设置' if not is_default else '使用默认值'} (预览: {secret_preview})")

def create_teacher(username: str, password: str, name: str = '', email: str = '', phone: str = '', title: str = ''):
    # 检查用户名是否已存在
    if fetch_one("SELECT teacher_id FROM teachers WHERE username=%s", (username,)):
        raise ValueError('用户名已存在')
    
    # 生成默认头像（使用Base64编码的简单占位图像）
    default_avatar = "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIyMDAiIGhlaWdodD0iMjAwIiBmaWxsPSIjZmZmZmZmIj4KICA8Y2lyY2xlIGN4PSIxMDAiIGN5PSIxMDAiIHI9IjkwIiByb2xlPSJpbWciIHN0cm9rZT0iI2U0ZTRlNCIgc3Ryb2tlLXdpZHRoPSIyIi8+CiAgPGNpcmNsZSBjeD0iMTAwIiBjeT0iNzAiIHI9IjIwIiByb2xlPSJpbWciIHN0cm9rZT0iIzVmNWY1ZiIgc3Ryb2tlLXdpZHRoPSIxIi8+CiAgPHBhdGggZD0iTTY1IDEzMGMtMTMuMiAwLTI0IDEwLjgtMjQgMjR2NjhjMCAxMy4yIDEwLjggMjQgMjQgMjRoNzBjMTMuMiAwIDI0LTEwLjggMjQtMjR2LTY4YzAtMTMuMi0xMC44LTI0LTI0LTI0eiBNOTAgMjQ2aDIwdi02MGMwLTUuNS00LjUtMTAtMTAtMTBoLTIwYzUtNS41LTEwLTEwLTEwLTEwdjYwYzAtNS41IDQuNS0xMCAxMC0xMHoiIHN0cm9rZT0iI2ZmZmZmZiIgc3Ryb2tlLXdpZHRoPSIyIi8+Cjwvc3ZnPg=="
    
    # 插入教师数据，包括默认头像
    hashed = generate_password_hash(password)
    execute_query(
        "INSERT INTO teachers (username, password, name, email, phone, title, avatar) VALUES (%s,%s,%s,%s,%s,%s,%s)",
        (username, hashed, name, email, phone, title, default_avatar)
    )
    return True

def authenticate_teacher(username: str, password: str):
    row = fetch_one("SELECT * FROM teachers WHERE username=%s", (username,))
    if not row:
        raise ValueError('用户不存在')
    if not check_password_hash(row['password'], password):
        raise ValueError('密码错误')
    now = int(time.time())
    # PyJWT 2.x 要求 sub 为字符串，这里显式转换，后续在 verify_token 中再转回整数
    payload = {
        'sub': str(row['teacher_id']),
        'username': row['username'],
        'iat': now,
        'exp': now + JWT_EXPIRE
    }
    secret_preview = JWT_SECRET[:8] + '...' if len(JWT_SECRET) > 8 else JWT_SECRET
    is_default = JWT_SECRET == 'default_secret_key_change_in_production'
    print(f"[JWT] 生成token，使用JWT_SECRET: {'已设置' if not is_default else '默认值'} (预览: {secret_preview})")
    token = jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALG)
    if isinstance(token, bytes):
        token = token.decode('utf-8')
    print(f"[OK] Token生成成功: {token[:20]}... (长度: {len(token)}, 过期时间: {now + JWT_EXPIRE})")
    return {'token': token, 'teacher': {'teacher_id': row['teacher_id'], 'username': row['username'], 'name': row.get('name'), 'title': row.get('title')}}

def verify_token(token: str):
    try:
        # 首先验证token是否具有正确的格式（JWT应由三个部分组成，用点分隔）
        if not token or '.' not in token or token.count('.') != 2:
            print(f"[ERR] Token格式错误: token存在={bool(token)}, 包含点={'.' in token if token else False}, 点数量={token.count('.') if token else 0}")
            raise ValueError('无效的令牌格式')

        secret_preview = JWT_SECRET[:8] + '...' if len(JWT_SECRET) > 8 else JWT_SECRET
        is_default = JWT_SECRET == 'default_secret_key_change_in_production'
        print(f"[VERIFY] 开始验证token，使用JWT_SECRET: {'已设置' if not is_default else '默认值'} (预览: {secret_preview})")

        # 尝试解码token
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALG])
        if 'sub' in payload:
            try:
                payload['sub'] = int(payload['sub'])
            except (TypeError, ValueError):
                raise ValueError('令牌的用户标识无效')
        print(f"[OK] Token解码成功，payload: {payload}")
        return payload
    except jwt.ExpiredSignatureError as e:
        print(f"[ERR] Token已过期: {str(e)}")
        raise ValueError('Token 已过期')
    except jwt.DecodeError as e:
        print(f"[ERR] Token解码失败: {str(e)}")
        print(f"   可能原因: JWT_SECRET不匹配或token格式错误")
        raise ValueError('令牌解码失败，请重新登录')
    except jwt.InvalidTokenError as e:
        print(f"[ERR] Token无效: {str(e)}")
        raise ValueError('无效的令牌')
    except Exception as e:
        # 打印详细错误信息用于调试
        print(f"[ERR] Token验证异常: {type(e).__name__}: {str(e)}")
        traceback.print_exc()
        raise ValueError('令牌验证失败')
