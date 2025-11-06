"""
数据库访问工具

职责：
- 管理 MySQL 连接与基础 CRUD 封装
- 从 .env 或环境变量读取连接配置

注意：
- 本模块不持久化连接，每次操作新建与关闭（简单可靠，适合中小项目）
- 生产环境可引入连接池（如 mysql-connector pooling）
"""

# flask_backend/database.py
# 尝试导入 mysql-connector，若不可用则进入降级模式（CSV/只读端点可继续运行）
try:
    import mysql.connector
    from mysql.connector import Error
    HAS_MYSQL = True
except Exception as e:
    HAS_MYSQL = False
    mysql = None
    class Error(Exception):
        pass
    print("[WARN] mysql-connector-python 未安装或导入失败，将以降级模式运行（优先使用 CSV 数据）。")
    print("       建议安装: pip install mysql-connector-python")
import os
from pathlib import Path

# 尝试加载环境变量（如果安装了 python-dotenv）
try:
    from dotenv import load_dotenv
    # 获取当前文件所在目录（flask_backend）
    env_path = Path(__file__).parent / '.env'
    if env_path.exists():
        load_dotenv(dotenv_path=env_path, override=True)
        # 避免在部分 Windows 终端（GBK 编码）下因特殊符号导致编码错误
        print(f"[OK] 已加载环境变量文件: {env_path}")
    else:
        print(f"[WARN] .env 文件不存在于 {env_path}")
        print("  请创建 .env 文件并配置数据库连接信息")
        # 尝试从项目根目录加载
        root_env_path = Path(__file__).parent.parent / '.env'
        if root_env_path.exists():
            load_dotenv(dotenv_path=root_env_path, override=True)
            print(f"[OK] 已从项目根目录加载环境变量文件: {root_env_path}")
except ImportError:
    # 如果没有安装 python-dotenv，使用系统环境变量
    print("[WARN] python-dotenv 未安装，使用系统环境变量")
    print("  建议运行: pip install python-dotenv")


def get_connection():
    """建立并返回一个新的数据库连接。

    优先从环境变量读取：DB_HOST, DB_USER, DB_PASSWORD, DB_NAME。
    注意：不要将生产密码写入代码；当前默认值仅用于开发便捷。
    """
    host = os.getenv('DB_HOST', 'localhost')
    user = os.getenv('DB_USER', 'root')
    # 警告：默认密码仅用于开发，请通过 .env 配置真实密码
    password = os.getenv('DB_PASSWORD', 'Wh800817')
    database = os.getenv('DB_NAME', 'student_grades')

    # 调试信息（仅在环境变量 FLASK_DEBUG 为 true 时输出）
    if os.getenv('FLASK_DEBUG', '').lower() == 'true':
        print(f"数据库连接配置: host={host}, user={user}, database={database}, password={'*' * len(password) if password else '(空)'}")

    try:
        if not HAS_MYSQL:
            raise ConnectionError(
                "未检测到 mysql-connector-python，无法建立数据库连接。\n"
                "请运行: pip install mysql-connector-python，或配置 .env 关闭数据库依赖。"
            )
        return mysql.connector.connect(
            host=host,
            user=user,
            password=password,
            database=database,
            charset='utf8mb4',
            use_unicode=True,
            collation='utf8mb4_unicode_ci'
        )
    except Error as e:
        # 提供更友好的错误信息
        raise ConnectionError(
            f"数据库连接失败: {str(e)}\n"
            f"请检查:\n"
            f"1. MySQL 服务是否已启动\n"
            f"2. .env 文件中的数据库配置是否正确\n"
            f"3. 数据库 '{database}' 是否已创建\n"
            f"当前配置: host={host}, user={user}, database={database}"
        ) from e


def execute_query(query, params=None):
    """执行写操作（INSERT/UPDATE/DELETE）。"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
    finally:
        cur.close()
        conn.close()


def execute_many(query, seq_params):
    """批量执行写操作（INSERT/UPDATE/DELETE）。"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.executemany(query, seq_params or [])
        conn.commit()
    finally:
        cur.close()
        conn.close()


def execute_insert_return_id(query, params=None):
    """执行INSERT并返回自增ID。"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute(query, params or ())
        conn.commit()
        return cur.lastrowid
    finally:
        cur.close()
        conn.close()


def fetch_one(query, params=None):
    """查询一条记录，返回 dict。"""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        r = cur.fetchone()
        return r
    finally:
        cur.close()
        conn.close()


def fetch_all(query, params=None):
    """查询多条记录，返回 list[dict]。"""
    conn = get_connection()
    cur = conn.cursor(dictionary=True)
    try:
        cur.execute(query, params or ())
        r = cur.fetchall()
        return r
    finally:
        cur.close()
        conn.close()


def get_tables():
    """获取数据库中的所有表名。"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        cur.execute("SHOW TABLES")
        tables = [table[0] for table in cur.fetchall()]
        return tables
    finally:
        cur.close()
        conn.close()


def get_columns(table_name: str):
    """获取指定表的所有列名。"""
    conn = get_connection()
    cur = conn.cursor()
    try:
        # 使用 INFORMATION_SCHEMA 查询当前数据库的列
        cur.execute(
            """
            SELECT COLUMN_NAME
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = DATABASE() AND TABLE_NAME = %s
            ORDER BY ORDINAL_POSITION
            """,
            (table_name,)
        )
        cols = [row[0] for row in cur.fetchall()]
        return cols
    finally:
        cur.close()
        conn.close()
