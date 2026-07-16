"""
database.py
SQLite(aiosqlite)를 사용한 비동기 데이터베이스 접근 레이어입니다.

테이블 구성
- guild_settings   : 서버별 티켓 시스템 설정
- admins           : 역할 외 추가로 등록된 관리자 목록
- tickets          : 생성된 티켓 정보
- ticket_counters  : 서버별 티켓 순번 카운터
"""

import time
from typing import List, Optional

import aiosqlite

import config


class Database:
    def __init__(self, path: str):
        self.path = path
        self.conn: Optional[aiosqlite.Connection] = None

    async def connect(self) -> None:
        self.conn = await aiosqlite.connect(self.path)
        self.conn.row_factory = aiosqlite.Row
        await self.conn.execute("PRAGMA foreign_keys = ON;")
        await self._create_tables()

    async def close(self) -> None:
        if self.conn:
            await self.conn.close()

    async def _create_tables(self) -> None:
        await self.conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS guild_settings (
                guild_id            INTEGER PRIMARY KEY,
                category_id         INTEGER,
                log_channel_id      INTEGER,
                transcript_channel_id INTEGER,
                admin_role_id       INTEGER,
                ticket_name_format  TEXT DEFAULT 'ticket-{count}'
            );

            CREATE TABLE IF NOT EXISTS admins (
                guild_id INTEGER NOT NULL,
                user_id  INTEGER NOT NULL,
                PRIMARY KEY (guild_id, user_id)
            );

            CREATE TABLE IF NOT EXISTS tickets (
                ticket_id     INTEGER PRIMARY KEY AUTOINCREMENT,
                guild_id      INTEGER NOT NULL,
                channel_id    INTEGER NOT NULL UNIQUE,
                owner_id      INTEGER NOT NULL,
                ticket_number INTEGER NOT NULL,
                status        TEXT NOT NULL DEFAULT 'open',
                created_at    INTEGER NOT NULL,
                closed_at     INTEGER
            );

            CREATE TABLE IF NOT EXISTS ticket_counters (
                guild_id INTEGER PRIMARY KEY,
                count    INTEGER NOT NULL DEFAULT 0
            );
            """
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ #
    # 설정 (guild_settings)
    # ------------------------------------------------------------------ #
    async def get_settings(self, guild_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM guild_settings WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row

    async def ensure_settings(self, guild_id: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO guild_settings (guild_id) VALUES (?)", (guild_id,)
        )
        await self.conn.commit()

    async def set_category(self, guild_id: int, category_id: int) -> None:
        await self.ensure_settings(guild_id)
        await self.conn.execute(
            "UPDATE guild_settings SET category_id = ? WHERE guild_id = ?",
            (category_id, guild_id),
        )
        await self.conn.commit()

    async def set_log_channel(self, guild_id: int, channel_id: int) -> None:
        await self.ensure_settings(guild_id)
        await self.conn.execute(
            "UPDATE guild_settings SET log_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        await self.conn.commit()

    async def set_transcript_channel(self, guild_id: int, channel_id: int) -> None:
        await self.ensure_settings(guild_id)
        await self.conn.execute(
            "UPDATE guild_settings SET transcript_channel_id = ? WHERE guild_id = ?",
            (channel_id, guild_id),
        )
        await self.conn.commit()

    async def set_admin_role(self, guild_id: int, role_id: int) -> None:
        await self.ensure_settings(guild_id)
        await self.conn.execute(
            "UPDATE guild_settings SET admin_role_id = ? WHERE guild_id = ?",
            (role_id, guild_id),
        )
        await self.conn.commit()

    async def set_name_format(self, guild_id: int, fmt: str) -> None:
        await self.ensure_settings(guild_id)
        await self.conn.execute(
            "UPDATE guild_settings SET ticket_name_format = ? WHERE guild_id = ?",
            (fmt, guild_id),
        )
        await self.conn.commit()

    # ------------------------------------------------------------------ #
    # 관리자 (admins)
    # ------------------------------------------------------------------ #
    async def add_admin(self, guild_id: int, user_id: int) -> None:
        await self.conn.execute(
            "INSERT OR IGNORE INTO admins (guild_id, user_id) VALUES (?, ?)",
            (guild_id, user_id),
        )
        await self.conn.commit()

    async def remove_admin(self, guild_id: int, user_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM admins WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        await self.conn.commit()

    async def is_extra_admin(self, guild_id: int, user_id: int) -> bool:
        cur = await self.conn.execute(
            "SELECT 1 FROM admins WHERE guild_id = ? AND user_id = ?",
            (guild_id, user_id),
        )
        row = await cur.fetchone()
        await cur.close()
        return row is not None

    async def list_admins(self, guild_id: int) -> List[int]:
        cur = await self.conn.execute(
            "SELECT user_id FROM admins WHERE guild_id = ?", (guild_id,)
        )
        rows = await cur.fetchall()
        await cur.close()
        return [r["user_id"] for r in rows]

    # ------------------------------------------------------------------ #
    # 티켓 (tickets / ticket_counters)
    # ------------------------------------------------------------------ #
    async def next_ticket_number(self, guild_id: int) -> int:
        await self.conn.execute(
            "INSERT OR IGNORE INTO ticket_counters (guild_id, count) VALUES (?, 0)",
            (guild_id,),
        )
        await self.conn.execute(
            "UPDATE ticket_counters SET count = count + 1 WHERE guild_id = ?",
            (guild_id,),
        )
        await self.conn.commit()
        cur = await self.conn.execute(
            "SELECT count FROM ticket_counters WHERE guild_id = ?", (guild_id,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row["count"]

    async def create_ticket(
        self, guild_id: int, channel_id: int, owner_id: int, ticket_number: int
    ) -> int:
        cur = await self.conn.execute(
            """
            INSERT INTO tickets (guild_id, channel_id, owner_id, ticket_number, status, created_at)
            VALUES (?, ?, ?, ?, 'open', ?)
            """,
            (guild_id, channel_id, owner_id, ticket_number, int(time.time())),
        )
        await self.conn.commit()
        return cur.lastrowid

    async def get_open_ticket_by_owner(
        self, guild_id: int, owner_id: int
    ) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM tickets WHERE guild_id = ? AND owner_id = ? AND status = 'open'",
            (guild_id, owner_id),
        )
        row = await cur.fetchone()
        await cur.close()
        return row

    async def get_ticket_by_channel(self, channel_id: int) -> Optional[aiosqlite.Row]:
        cur = await self.conn.execute(
            "SELECT * FROM tickets WHERE channel_id = ?", (channel_id,)
        )
        row = await cur.fetchone()
        await cur.close()
        return row

    async def close_ticket(self, channel_id: int) -> None:
        await self.conn.execute(
            "UPDATE tickets SET status = 'closed', closed_at = ? WHERE channel_id = ?",
            (int(time.time()), channel_id),
        )
        await self.conn.commit()

    async def reopen_ticket(self, channel_id: int) -> None:
        await self.conn.execute(
            "UPDATE tickets SET status = 'open', closed_at = NULL WHERE channel_id = ?",
            (channel_id,),
        )
        await self.conn.commit()

    async def delete_ticket(self, channel_id: int) -> None:
        await self.conn.execute(
            "DELETE FROM tickets WHERE channel_id = ?", (channel_id,)
        )
        await self.conn.commit()


# 프로젝트 전역에서 공유하는 단일 데이터베이스 인스턴스
db = Database(config.DB_PATH)
