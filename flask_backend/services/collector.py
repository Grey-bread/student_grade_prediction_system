"""
Background data collector that auto-detects new rows in configured data sources
and invalidates caches so the app reflects fresh data automatically.

Configuration per data source (stored in data_sources.config as JSON):
{
  "table": "historical_grades",        # required: table name to watch
  "key_column": "id",                  # optional: integer auto-increment PK to diff by
  "updated_at_column": "updated_at",   # optional: DATETIME column to diff by if no key_column
  "interval_seconds": 30                # optional: polling interval per source (default 30)
}

If both key_column and updated_at_column exist, key_column takes precedence.

Requirements: APScheduler
"""
from __future__ import annotations
import json
import threading
from typing import Optional, Dict, Any

try:
    from apscheduler.schedulers.background import BackgroundScheduler
except Exception:
    BackgroundScheduler = None  # Soft dependency, app will run without scheduler

from database import fetch_all, fetch_one, execute_query

# Lazy import to avoid circular when app starts before routes are loaded.
# We'll import inside functions when needed.

class DataCollector:
    _instance_lock = threading.Lock()
    _instance: Optional['DataCollector'] = None

    def __init__(self) -> None:
        self.scheduler = None
        self.running = False

    @classmethod
    def instance(cls) -> 'DataCollector':
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = DataCollector()
            return cls._instance

    def start(self) -> None:
        if self.running:
            return
        if BackgroundScheduler is None:
            print('[Collector] APScheduler 未安装，自动采集功能不可用')
            return
        self.scheduler = BackgroundScheduler()
        self.scheduler.add_job(self._scan_and_schedule_jobs, 'interval', seconds=30, id='scan_sources', replace_existing=True)
        self.scheduler.start()
        self.running = True
        print('[Collector] 自动采集调度已启动')

    def shutdown(self) -> None:
        if self.scheduler:
            self.scheduler.shutdown(wait=False)
            self.scheduler = None
        self.running = False

    def _scan_and_schedule_jobs(self):
        try:
            # Ensure state table exists
            self._ensure_state_table()
            # Keep data_sources synced with actual DB tables on each scan
            try:
                from routes.analysis_routes import sync_data_sources_with_db
                sync_data_sources_with_db()
            except Exception:
                pass
            # Load active sources
            rows = fetch_all("SELECT id, name, type, config, active FROM data_sources WHERE active=1") or []
            configured_ids = set()
            for r in rows:
                sid = r.get('id')
                name = r.get('name')
                cfg_raw = r.get('config') or ''
                cfg = self._parse_config(cfg_raw)
                table = cfg.get('table')
                if not sid or not table:
                    continue
                configured_ids.add(sid)
                seconds = int(cfg.get('interval_seconds') or 30)
                job_id = f'source_{sid}'
                if self.scheduler.get_job(job_id):
                    # Update trigger if interval changed
                    self.scheduler.reschedule_job(job_id, trigger='interval', seconds=seconds)
                else:
                    self.scheduler.add_job(self._collect_once, 'interval', seconds=seconds, id=job_id, args=[sid, cfg, name], replace_existing=True)
        except Exception as e:
            print(f'[Collector] 扫描数据源失败: {e}')

    def _parse_config(self, raw: str) -> Dict[str, Any]:
        try:
            cfg = json.loads(raw) if raw and raw.strip().startswith('{') else {}
            return cfg if isinstance(cfg, dict) else {}
        except Exception:
            return {}

    def _ensure_state_table(self):
                execute_query(
            """
            CREATE TABLE IF NOT EXISTS data_sync_state (
              source_id INT PRIMARY KEY,
              table_name VARCHAR(128) NOT NULL,
              last_max_id BIGINT NULL,
              last_max_updated DATETIME NULL,
              updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP
            ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
            """
        )
                # 采集运行日志表，用于前端直观展示自动采集效果
                execute_query(
                        """
                        CREATE TABLE IF NOT EXISTS collection_runs (
                            id INT AUTO_INCREMENT PRIMARY KEY,
                            source_id INT NOT NULL,
                            table_name VARCHAR(128) NOT NULL,
                            run_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                            status VARCHAR(16) NOT NULL,
                            delta_rows INT DEFAULT 0,
                            error TEXT
                        ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
                        """
                )

    def _collect_once(self, source_id: int, cfg: Dict[str, Any], source_name: str = ''):
        try:
            table = cfg.get('table')
            key_col = cfg.get('key_column')
            upd_col = cfg.get('updated_at_column')
            if not table:
                return
            has_new = False
            delta_rows = 0
            if key_col:
                # 通过主键精确计算新增行数
                row = fetch_one(f"SELECT MAX({key_col}) AS max_id FROM {table}")
                max_id = int(row.get('max_id') or 0) if row else 0
                st = fetch_one("SELECT last_max_id FROM data_sync_state WHERE source_id=%s", [source_id])
                last = int(st.get('last_max_id') or 0) if st else None
                if last is None or max_id > last:
                    # 新增数量更精确地以 count 计算
                    try:
                        cnt_row = fetch_one(f"SELECT COUNT(1) AS cnt FROM {table} WHERE {key_col} > %s", [last or 0])
                        delta_rows = int(cnt_row.get('cnt') or 0) if cnt_row else (max_id - (last or 0))
                    except Exception:
                        delta_rows = max_id - (last or 0)
                    has_new = True
                    # upsert
                    if st:
                        execute_query("UPDATE data_sync_state SET last_max_id=%s, table_name=%s WHERE source_id=%s", [max_id, table, source_id])
                    else:
                        execute_query("INSERT INTO data_sync_state (source_id, table_name, last_max_id) VALUES (%s,%s,%s)", [source_id, table, max_id])
            elif upd_col:
                row = fetch_one(f"SELECT MAX({upd_col}) AS max_ts FROM {table}")
                max_ts = row.get('max_ts') if row else None
                st = fetch_one("SELECT last_max_updated FROM data_sync_state WHERE source_id=%s", [source_id])
                last_ts = st.get('last_max_updated') if st else None
                if (max_ts and (not last_ts or str(max_ts) > str(last_ts))):
                    # 计算变更行数（updated_at 大于上次的记录数）
                    try:
                        cnt_row = fetch_one(f"SELECT COUNT(1) AS cnt FROM {table} WHERE {upd_col} > %s", [last_ts or '1970-01-01'])
                        delta_rows = int(cnt_row.get('cnt') or 0) if cnt_row else 0
                    except Exception:
                        delta_rows = 0
                    has_new = True
                    if st:
                        execute_query("UPDATE data_sync_state SET last_max_updated=%s, table_name=%s WHERE source_id=%s", [max_ts, table, source_id])
                    else:
                        execute_query("INSERT INTO data_sync_state (source_id, table_name, last_max_updated) VALUES (%s,%s,%s)", [source_id, table, max_ts])
            else:
                # No diff column, always mark as having updates every run
                has_new = True
                try:
                    cnt_row = fetch_one(f"SELECT COUNT(1) AS cnt FROM {table}")
                    delta_rows = int(cnt_row.get('cnt') or 0) if cnt_row else 0
                except Exception:
                    delta_rows = 0

            # 写入运行日志
            try:
                execute_query(
                    "INSERT INTO collection_runs (source_id, table_name, status, delta_rows) VALUES (%s,%s,%s,%s)",
                    [source_id, table, 'success', int(delta_rows)]
                )
            except Exception:
                pass

            if has_new:
                # mark cache dirty and update last_collection time
                try:
                    from routes.analysis_routes import mark_table_dirty
                    mark_table_dirty(table)
                except Exception:
                    pass
                try:
                    execute_query("UPDATE data_sources SET last_collection=NOW() WHERE id=%s", [source_id])
                except Exception:
                    pass
        except Exception as e:
            print(f"[Collector] 采集失败 source#{source_id} {source_name}: {e}")
            # 记录失败运行日志
            try:
                table = (cfg or {}).get('table') or ''
                execute_query(
                    "INSERT INTO collection_runs (source_id, table_name, status, delta_rows, error) VALUES (%s,%s,%s,%s,%s)",
                    [source_id, table, 'failed', 0, str(e)[:1000]]
                )
            except Exception:
                pass
