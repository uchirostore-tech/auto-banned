import sqlite3
import asyncio
import json
from datetime import datetime, timezone, timedelta
from typing import Optional, Dict, Any, List

DEFAULT_TIERS = [
    {"max_days": 1, "ban_days": 365, "label": "Joined < 1 Day (Left Today)", "desc": "1 Year Ban"},
    {"max_days": 7, "ban_days": 90, "label": "Joined 1 - 7 Days (1 Week)", "desc": "3 Months Ban"},
    {"max_days": 30, "ban_days": 30, "label": "Joined 1 - 4 Weeks (1 Month)", "desc": "1 Month Ban"},
    {"max_days": 180, "ban_days": 14, "label": "Joined 1 - 6 Months", "desc": "2 Weeks Ban"},
    {"max_days": None, "ban_days": 0, "label": "Joined > 6 Months", "desc": "Forever / Custom Ban"},
]

class Database:
    def __init__(self, db_path: str):
        self.db_path = db_path

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.row_factory = sqlite3.Row
        # Blazing fast WAL mode and cache pragmas
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA synchronous = NORMAL;")
        conn.execute("PRAGMA cache_size = -64000;")  # 64MB cache
        return conn

    def _init_sync(self):
        conn = self._connect()
        try:
            with conn:
                # Active members table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS members (
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        username TEXT,
                        full_name TEXT,
                        joined_at TEXT NOT NULL,
                        PRIMARY KEY (user_id, chat_id)
                    )
                """)
                # Ban logs table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS ban_logs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        user_id INTEGER NOT NULL,
                        chat_id INTEGER NOT NULL,
                        channel_title TEXT,
                        username TEXT,
                        full_name TEXT,
                        joined_at TEXT,
                        left_at TEXT NOT NULL,
                        days_joined REAL,
                        ban_duration_days INTEGER DEFAULT 0,
                        ban_until_date TEXT,
                        unbanned INTEGER DEFAULT 0,
                        unbanned_at TEXT,
                        unbanned_by INTEGER
                    )
                """)
                # Settings table
                conn.execute("""
                    CREATE TABLE IF NOT EXISTS settings (
                        key TEXT PRIMARY KEY,
                        value TEXT NOT NULL
                    )
                """)
                # Fast indexes
                conn.execute("CREATE INDEX IF NOT EXISTS idx_members_joined_at ON members(joined_at ASC);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_members_chat_user ON members(chat_id, user_id);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ban_logs_left ON ban_logs(left_at);")
                conn.execute("CREATE INDEX IF NOT EXISTS idx_ban_logs_user ON ban_logs(chat_id, user_id);")

                # Default settings initialization if missing
                default_settings = {
                    "language": "km",  # "km" (Khmer) or "en" (English)
                    "auto_ban_enabled": "true",
                    "ban_mode": "tiered",  # "tiered", "forever", "1_year", "3_months", "1_month", "1_week"
                    "daily_report_enabled": "true",
                    "report_hour_utc": "0",  # 00:00 UTC
                    "tiered_rules": json.dumps(DEFAULT_TIERS)
                }
                for k, v in default_settings.items():
                    conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))
        finally:
            conn.close()

    async def init(self):
        await asyncio.to_thread(self._init_sync)

    # --- Settings Management ---
    def _get_setting_sync(self, key: str, default: Optional[str] = None) -> Optional[str]:
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default
        finally:
            conn.close()

    async def get_setting(self, key: str, default: Optional[str] = None) -> Optional[str]:
        return await asyncio.to_thread(self._get_setting_sync, key, default)

    def _set_setting_sync(self, key: str, value: str):
        conn = self._connect()
        try:
            with conn:
                conn.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, value))
        finally:
            conn.close()

    async def set_setting(self, key: str, value: str):
        await asyncio.to_thread(self._set_setting_sync, key, value)

    async def get_tiered_rules(self) -> List[Dict[str, Any]]:
        raw = await self.get_setting("tiered_rules")
        if raw:
            try:
                return json.loads(raw)
            except Exception:
                pass
        return DEFAULT_TIERS

    async def get_language(self) -> str:
        lang = await self.get_setting("language", "km")
        return lang if lang in ["km", "en"] else "km"

    async def set_language(self, lang: str):
        if lang in ["km", "en"]:
            await self.set_setting("language", lang)

    # --- Member Tracking ---
    def _record_join_sync(self, user_id: int, chat_id: int, username: Optional[str], full_name: str, joined_at: datetime):
        joined_str = joined_at.isoformat()
        conn = self._connect()
        try:
            with conn:
                conn.execute("""
                    INSERT INTO members (user_id, chat_id, username, full_name, joined_at)
                    VALUES (?, ?, ?, ?, ?)
                    ON CONFLICT(user_id, chat_id) DO UPDATE SET
                        username = excluded.username,
                        full_name = excluded.full_name,
                        joined_at = excluded.joined_at
                """, (user_id, chat_id, username, full_name, joined_str))
        finally:
            conn.close()

    async def record_join(self, user_id: int, chat_id: int, username: Optional[str], full_name: str, joined_at: datetime):
        await asyncio.to_thread(self._record_join_sync, user_id, chat_id, username, full_name, joined_at)

    def _get_member_sync(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        conn = self._connect()
        try:
            cursor = conn.execute("""
                SELECT user_id, chat_id, username, full_name, joined_at
                FROM members
                WHERE user_id = ? AND chat_id = ?
            """, (user_id, chat_id))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    async def get_member(self, user_id: int, chat_id: int) -> Optional[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_member_sync, user_id, chat_id)

    def _remove_member_sync(self, user_id: int, chat_id: int):
        conn = self._connect()
        try:
            with conn:
                conn.execute("DELETE FROM members WHERE user_id = ? AND chat_id = ?", (user_id, chat_id))
        finally:
            conn.close()

    async def remove_member(self, user_id: int, chat_id: int):
        await asyncio.to_thread(self._remove_member_sync, user_id, chat_id)

    # --- Ban Logging ---
    def _record_ban_sync(
        self,
        user_id: int,
        chat_id: int,
        channel_title: str,
        username: Optional[str],
        full_name: str,
        joined_at: Optional[datetime],
        left_at: datetime,
        days_joined: Optional[float],
        ban_duration_days: int,
        ban_until_date: Optional[datetime]
    ) -> int:
        joined_str = joined_at.isoformat() if joined_at else None
        left_str = left_at.isoformat()
        ban_until_str = ban_until_date.isoformat() if ban_until_date else None

        conn = self._connect()
        try:
            with conn:
                cursor = conn.execute("""
                    INSERT INTO ban_logs (
                        user_id, chat_id, channel_title, username, full_name,
                        joined_at, left_at, days_joined, ban_duration_days,
                        ban_until_date, unbanned
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
                """, (
                    user_id, chat_id, channel_title, username, full_name,
                    joined_str, left_str, days_joined, ban_duration_days,
                    ban_until_str
                ))
                return cursor.lastrowid
        finally:
            conn.close()

    async def record_ban(
        self,
        user_id: int,
        chat_id: int,
        channel_title: str,
        username: Optional[str],
        full_name: str,
        joined_at: Optional[datetime],
        left_at: datetime,
        days_joined: Optional[float],
        ban_duration_days: int = 0,
        ban_until_date: Optional[datetime] = None
    ) -> int:
        return await asyncio.to_thread(
            self._record_ban_sync,
            user_id,
            chat_id,
            channel_title,
            username,
            full_name,
            joined_at,
            left_at,
            days_joined,
            ban_duration_days,
            ban_until_date
        )

    def _mark_unbanned_sync(self, chat_id: int, user_id: int, unbanned_by: int) -> bool:
        now_str = datetime.now(timezone.utc).isoformat()
        conn = self._connect()
        try:
            with conn:
                cursor = conn.execute("""
                    UPDATE ban_logs
                    SET unbanned = 1, unbanned_at = ?, unbanned_by = ?
                    WHERE chat_id = ? AND user_id = ? AND unbanned = 0
                """, (now_str, unbanned_by, chat_id, user_id))
                return cursor.rowcount > 0
        finally:
            conn.close()

    async def mark_unbanned(self, chat_id: int, user_id: int, unbanned_by: int) -> bool:
        return await asyncio.to_thread(self._mark_unbanned_sync, chat_id, user_id, unbanned_by)

    # --- Scan: Top 20 Oldest & Loyal Members ---
    def _get_top_oldest_members_sync(self, chat_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        conn = self._connect()
        try:
            if chat_id:
                query = """
                    SELECT user_id, chat_id, username, full_name, joined_at
                    FROM members
                    WHERE chat_id = ?
                    ORDER BY joined_at ASC
                    LIMIT ?
                """
                cursor = conn.execute(query, (chat_id, limit))
            else:
                query = """
                    SELECT user_id, chat_id, username, full_name, joined_at
                    FROM members
                    ORDER BY joined_at ASC
                    LIMIT ?
                """
                cursor = conn.execute(query, (limit,))
            rows = cursor.fetchall()
            now = datetime.now(timezone.utc)
            results = []
            for row in rows:
                item = dict(row)
                try:
                    joined_dt = datetime.fromisoformat(item["joined_at"])
                    if joined_dt.tzinfo is None:
                        joined_dt = joined_dt.replace(tzinfo=timezone.utc)
                    days_active = max(0, (now - joined_dt).total_seconds() / 86400.0)
                    item["days_active"] = round(days_active, 1)
                except Exception:
                    item["days_active"] = 0
                results.append(item)
            return results
        finally:
            conn.close()

    async def get_top_oldest_members(self, chat_id: Optional[int] = None, limit: int = 20) -> List[Dict[str, Any]]:
        return await asyncio.to_thread(self._get_top_oldest_members_sync, chat_id, limit)

    # --- Analytics & Daily Summary ---
    def _get_daily_summary_sync(self, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        if target_date is None:
            target_date = datetime.now(timezone.utc)

        start_of_day = target_date.replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        end_of_day = (target_date.replace(hour=0, minute=0, second=0, microsecond=0) + timedelta(days=1)).isoformat()

        conn = self._connect()
        try:
            # Joins today
            cursor = conn.execute("SELECT COUNT(*) FROM members WHERE joined_at >= ? AND joined_at < ?", (start_of_day, end_of_day))
            joins_count = cursor.fetchone()[0]

            # Leaves / Bans today
            cursor = conn.execute("SELECT COUNT(*) FROM ban_logs WHERE left_at >= ? AND left_at < ?", (start_of_day, end_of_day))
            bans_count = cursor.fetchone()[0]

            # Unbans today
            cursor = conn.execute("SELECT COUNT(*) FROM ban_logs WHERE unbanned_at >= ? AND unbanned_at < ?", (start_of_day, end_of_day))
            unbans_count = cursor.fetchone()[0]

            # Current total members tracked
            cursor = conn.execute("SELECT COUNT(*) FROM members")
            total_members = cursor.fetchone()[0]

            # Total historical bans
            cursor = conn.execute("SELECT COUNT(*) FROM ban_logs")
            total_bans = cursor.fetchone()[0]

            net_change = joins_count - bans_count

            return {
                "date": target_date.strftime("%Y-%m-%d"),
                "joins": joins_count,
                "leaves": bans_count,
                "bans": bans_count,
                "unbans": unbans_count,
                "net_change": net_change,
                "total_tracked": total_members,
                "total_historical_bans": total_bans,
            }
        finally:
            conn.close()

    async def get_daily_summary(self, target_date: Optional[datetime] = None) -> Dict[str, Any]:
        return await asyncio.to_thread(self._get_daily_summary_sync, target_date)

    # --- Lookup & Search ---
    def _lookup_user_sync(self, query: str) -> Dict[str, Any]:
        conn = self._connect()
        try:
            # Try numeric ID or username
            is_digit = query.lstrip("-").isdigit()
            user_id = int(query) if is_digit else None
            clean_username = query.lstrip("@").lower()

            # Check active members
            if user_id:
                cursor = conn.execute("SELECT * FROM members WHERE user_id = ?", (user_id,))
            else:
                cursor = conn.execute("SELECT * FROM members WHERE LOWER(username) = ?", (clean_username,))
            member = cursor.fetchone()

            # Check ban logs
            if user_id:
                cursor = conn.execute("SELECT * FROM ban_logs WHERE user_id = ? ORDER BY id DESC LIMIT 5", (user_id,))
            else:
                cursor = conn.execute("SELECT * FROM ban_logs WHERE LOWER(username) = ? ORDER BY id DESC LIMIT 5", (clean_username,))
            bans = [dict(r) for r in cursor.fetchall()]

            return {
                "member": dict(member) if member else None,
                "bans": bans
            }
        finally:
            conn.close()

    async def lookup_user(self, query: str) -> Dict[str, Any]:
        return await asyncio.to_thread(self._lookup_user_sync, query)

    # --- CSV Exports ---
    def _export_members_csv_sync(self) -> str:
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT user_id, chat_id, username, full_name, joined_at FROM members ORDER BY joined_at ASC")
            rows = cursor.fetchall()
            lines = ["user_id,chat_id,username,full_name,joined_at"]
            for r in rows:
                full_name_clean = (r["full_name"] or "").replace('"', '""')
                lines.append(f'{r["user_id"]},{r["chat_id"]},"{r["username"] or ""}","{full_name_clean}",{r["joined_at"]}')
            return "\n".join(lines)
        finally:
            conn.close()

    async def export_members_csv(self) -> str:
        return await asyncio.to_thread(self._export_members_csv_sync)

    def _export_bans_csv_sync(self) -> str:
        conn = self._connect()
        try:
            cursor = conn.execute("SELECT id, user_id, chat_id, channel_title, username, full_name, joined_at, left_at, days_joined, ban_duration_days, ban_until_date, unbanned FROM ban_logs ORDER BY id DESC")
            rows = cursor.fetchall()
            lines = ["id,user_id,chat_id,channel_title,username,full_name,joined_at,left_at,days_joined,ban_duration_days,ban_until_date,unbanned"]
            for r in rows:
                full_name_clean = (r["full_name"] or "").replace('"', '""')
                channel_clean = (r["channel_title"] or "").replace('"', '""')
                lines.append(f'{r["id"]},{r["user_id"]},{r["chat_id"]},"{channel_clean}","{r["username"] or ""}","{full_name_clean}",{r["joined_at"] or ""},{r["left_at"]},{r["days_joined"] or 0},{r["ban_duration_days"] or 0},{r["ban_until_date"] or ""},{r["unbanned"]}')
            return "\n".join(lines)
        finally:
            conn.close()

    async def export_bans_csv(self) -> str:
        return await asyncio.to_thread(self._export_bans_csv_sync)
