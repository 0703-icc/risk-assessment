"""SQLite数据库操作模块

管理评估报告和风险项的持久化存储。
"""

import sqlite3
import json
import os
from datetime import datetime
from typing import Optional, List, Dict, Any


# 注册 datetime 适配器（Python 3.12+ 推荐方式）
def _adapt_datetime(dt: datetime) -> str:
    return dt.isoformat()


def _convert_datetime(ts: bytes) -> datetime:
    return datetime.fromisoformat(ts.decode())


sqlite3.register_adapter(datetime, _adapt_datetime)
sqlite3.register_converter("TIMESTAMP", _convert_datetime)


def get_db_connection(db_path: str = "data/risk_assessment.db") -> sqlite3.Connection:
    """获取数据库连接"""
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    conn = sqlite3.connect(db_path, detect_types=sqlite3.PARSE_DECLTYPES)
    conn.row_factory = sqlite3.Row
    return conn


def init_db(db_path: str = "data/risk_assessment.db") -> None:
    """初始化数据库，创建reports和risk_items表"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    # 评估报告主表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS reports (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_name TEXT NOT NULL,
            evaluation_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            data_sources TEXT,
            overall_status TEXT
        )
    """)

    # 风险项明细表
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS risk_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            report_id INTEGER NOT NULL,
            item_code TEXT NOT NULL,
            item_name TEXT NOT NULL,
            item_type TEXT NOT NULL,
            severity TEXT,
            status TEXT NOT NULL,
            trigger_time TIMESTAMP,
            data_source TEXT,
            evidence_url TEXT,
            description TEXT,
            match_count INTEGER DEFAULT 0,
            total_data INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (report_id) REFERENCES reports(id)
        )
    """)

    # 兼容升级：为旧表添加量化字段
    try:
        cursor.execute("ALTER TABLE risk_items ADD COLUMN match_count INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass
    try:
        cursor.execute("ALTER TABLE risk_items ADD COLUMN total_data INTEGER DEFAULT 0")
    except sqlite3.OperationalError:
        pass

    conn.commit()
    conn.close()


def save_report(
    company_name: str,
    data_sources: List[str],
    overall_status: str,
    db_path: str = "data/risk_assessment.db"
) -> int:
    """保存评估报告，返回报告ID"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO reports (company_name, evaluation_time, data_sources, overall_status) VALUES (?, ?, ?, ?)",
        (company_name, datetime.now(), json.dumps(data_sources), overall_status)
    )

    report_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return report_id


def save_risk_item(
    report_id: int,
    item_code: str,
    item_name: str,
    item_type: str,
    status: str,
    severity: Optional[str] = None,
    trigger_time: Optional[datetime] = None,
    data_source: Optional[str] = None,
    evidence_url: Optional[str] = None,
    description: Optional[str] = None,
    match_count: int = 0,
    total_data: int = 0,
    db_path: str = "data/risk_assessment.db"
) -> int:
    """保存风险项明细，返回明细ID"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        """INSERT INTO risk_items
           (report_id, item_code, item_name, item_type, severity, status,
            trigger_time, data_source, evidence_url, description,
            match_count, total_data)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (report_id, item_code, item_name, item_type, severity, status,
         trigger_time, data_source, evidence_url, description,
         match_count, total_data)
    )

    item_id = cursor.lastrowid
    conn.commit()
    conn.close()
    return item_id


def get_latest_report(
    company_name: str,
    db_path: str = "data/risk_assessment.db"
) -> Optional[Dict[str, Any]]:
    """获取指定公司的最近一次评估报告"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM reports WHERE company_name = ? ORDER BY evaluation_time DESC LIMIT 1",
        (company_name,)
    )

    row = cursor.fetchone()
    conn.close()

    if row is None:
        return None

    return dict(row)


def get_report_risk_items(
    report_id: int,
    db_path: str = "data/risk_assessment.db"
) -> List[Dict[str, Any]]:
    """获取指定报告的所有风险项明细"""
    conn = get_db_connection(db_path)
    cursor = conn.cursor()

    cursor.execute(
        "SELECT * FROM risk_items WHERE report_id = ? ORDER BY id",
        (report_id,)
    )

    rows = cursor.fetchall()
    conn.close()

    return [dict(row) for row in rows]