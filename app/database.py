import aiosqlite
from datetime import datetime, timedelta


DB_PATH = "database.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL,
                comment TEXT NOT NULL,
                tg_user_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor = await db.execute("PRAGMA table_info(leads)")
        columns = [row[1] for row in await cursor.fetchall()]

        if "owner_id" not in columns:
            await db.execute("ALTER TABLE leads ADD COLUMN owner_id INTEGER DEFAULT 0")

        await db.commit()


async def save_lead(owner_id: int, name: str, phone: str, comment: str, tg_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO leads (owner_id, name, phone, comment, tg_user_id)
            VALUES (?, ?, ?, ?, ?)
            """,
            (owner_id, name, phone, comment, tg_user_id),
        )
        await db.commit()


async def get_all_leads(owner_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT name, phone, comment, created_at
            FROM leads
            WHERE owner_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (owner_id, limit),
        )
        return await cursor.fetchall()


async def get_leads_stats(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT COUNT(*) FROM leads WHERE owner_id = ?",
            (owner_id,),
        )
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE owner_id = ?
            AND date(created_at) = date('now', 'localtime')
            """,
            (owner_id,),
        )
        today = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE owner_id = ?
            AND datetime(created_at) >= datetime('now', '-7 days')
            """,
            (owner_id,),
        )
        week = (await cursor.fetchone())[0]

        return {
            "today": today,
            "week": week,
            "total": total,
        }


async def get_unique_clients(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT name, phone, COUNT(*) as leads_count
            FROM leads
            WHERE owner_id = ?
            GROUP BY name, phone
            ORDER BY leads_count DESC, name ASC
            """,
            (owner_id,),
        )
        return await cursor.fetchall()


async def init_subscription():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id INTEGER NOT NULL UNIQUE,
                status TEXT NOT NULL,
                started_at TEXT NOT NULL,
                paid_until TEXT NOT NULL
            )
        """)
        await db.commit()


async def get_or_create_subscription(tg_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT status, started_at, paid_until
            FROM subscriptions
            WHERE tg_user_id = ?
            """,
            (tg_user_id,),
        )
        row = await cursor.fetchone()

        if row:
            return row

        now = datetime.now()
        trial_until = now + timedelta(days=3)

        await db.execute(
            """
            INSERT INTO subscriptions (tg_user_id, status, started_at, paid_until)
            VALUES (?, ?, ?, ?)
            """,
            (tg_user_id, "trial", now.isoformat(), trial_until.isoformat()),
        )
        await db.commit()

        return ("trial", now.isoformat(), trial_until.isoformat())


async def get_subscription(tg_user_id: int):
    return await get_or_create_subscription(tg_user_id)


async def has_active_access(tg_user_id: int):
    subscription = await get_or_create_subscription(tg_user_id)

    status, started_at, paid_until = subscription
    paid_until_dt = datetime.fromisoformat(paid_until)
    now = datetime.now()

    return now <= paid_until_dt and status in ("trial", "active")


async def extend_subscription(tg_user_id: int, days: int = 30):
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now()
        paid_until = now + timedelta(days=days)

        await db.execute(
            """
            INSERT INTO subscriptions (tg_user_id, status, started_at, paid_until)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(tg_user_id)
            DO UPDATE SET
                status = excluded.status,
                paid_until = excluded.paid_until
            """,
            (tg_user_id, "active", now.isoformat(), paid_until.isoformat()),
        )

        await db.commit()