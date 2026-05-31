import aiosqlite
from datetime import datetime, timedelta


DB_PATH = "database.db"


async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS owners (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tg_user_id INTEGER UNIQUE NOT NULL,
                username TEXT,
                full_name TEXT,
                created_at TEXT NOT NULL
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS subscriptions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER UNIQUE NOT NULL,
                status TEXT NOT NULL,
                plan TEXT NOT NULL,
                started_at TEXT NOT NULL,
                paid_until TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES owners(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS leads (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                client_tg_user_id INTEGER,
                client_username TEXT,
                name TEXT NOT NULL,
                contact TEXT NOT NULL,
                comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY (owner_id) REFERENCES owners(id)
            )
        """)

        await db.execute("""
            CREATE TABLE IF NOT EXISTS payments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                owner_id INTEGER NOT NULL,
                amount INTEGER NOT NULL,
                plan TEXT NOT NULL,
                status TEXT NOT NULL,
                provider_payment_id TEXT,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY (owner_id) REFERENCES owners(id)
            )
        """)

        await db.commit()


async def get_or_create_owner(
    tg_user_id: int,
    username: str | None,
    full_name: str | None,
):
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id
            FROM owners
            WHERE tg_user_id = ?
            """,
            (tg_user_id,)
        )
        owner = await cursor.fetchone()

        if owner:
            return owner[0]

        cursor = await db.execute(
            """
            INSERT INTO owners (tg_user_id, username, full_name, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (tg_user_id, username, full_name, now)
        )

        owner_id = cursor.lastrowid
        await db.commit()

        return owner_id


async def get_owner_by_id(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, tg_user_id, username, full_name, created_at
            FROM owners
            WHERE id = ?
            """,
            (owner_id,)
        )
        return await cursor.fetchone()


async def get_owner_by_tg_user_id(tg_user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id, tg_user_id, username, full_name, created_at
            FROM owners
            WHERE tg_user_id = ?
            """,
            (tg_user_id,)
        )
        return await cursor.fetchone()


async def activate_trial(owner_id: int):
    now = datetime.now()
    paid_until = now + timedelta(days=3)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT id
            FROM subscriptions
            WHERE owner_id = ?
            """,
            (owner_id,)
        )
        subscription = await cursor.fetchone()

        if subscription:
            return False

        await db.execute(
            """
            INSERT INTO subscriptions (
                owner_id,
                status,
                plan,
                started_at,
                paid_until
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                "trial",
                "trial",
                now.isoformat(),
                paid_until.isoformat(),
            )
        )

        await db.commit()
        return True


async def get_subscription_by_owner_id(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT status, plan, started_at, paid_until
            FROM subscriptions
            WHERE owner_id = ?
            """,
            (owner_id,)
        )
        return await cursor.fetchone()


async def get_subscription_by_tg_user_id(tg_user_id: int):
    owner = await get_owner_by_tg_user_id(tg_user_id)

    if not owner:
        return None

    owner_id = owner[0]
    return await get_subscription_by_owner_id(owner_id)


async def has_active_access_by_owner_id(owner_id: int) -> bool:
    subscription = await get_subscription_by_owner_id(owner_id)

    if not subscription:
        return False

    status, plan, started_at, paid_until = subscription
    paid_until_dt = datetime.fromisoformat(paid_until)

    return datetime.now() <= paid_until_dt


async def has_active_access_by_tg_user_id(tg_user_id: int) -> bool:
    owner = await get_owner_by_tg_user_id(tg_user_id)

    if not owner:
        return False

    owner_id = owner[0]
    return await has_active_access_by_owner_id(owner_id)


async def save_lead(
    owner_id: int,
    client_tg_user_id: int,
    client_username: str | None,
    name: str,
    contact: str,
    comment: str | None,
):
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO leads (
                owner_id,
                client_tg_user_id,
                client_username,
                name,
                contact,
                comment,
                created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                owner_id,
                client_tg_user_id,
                client_username,
                name,
                contact,
                comment,
                now,
            )
        )

        await db.commit()


async def get_all_leads(owner_id: int, limit: int = 10):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT name, contact, comment, created_at
            FROM leads
            WHERE owner_id = ?
            ORDER BY id DESC
            LIMIT ?
            """,
            (owner_id, limit)
        )
        return await cursor.fetchall()


async def get_unique_clients(owner_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT name, contact, COUNT(*) as leads_count
            FROM leads
            WHERE owner_id = ?
            GROUP BY contact
            ORDER BY leads_count DESC
            """,
            (owner_id,)
        )
        return await cursor.fetchall()


async def get_leads_stats(owner_id: int):
    now = datetime.now()
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    week_start = now - timedelta(days=7)

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE owner_id = ?
            """,
            (owner_id,)
        )
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE owner_id = ? AND created_at >= ?
            """,
            (owner_id, today_start.isoformat())
        )
        today = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """
            SELECT COUNT(*)
            FROM leads
            WHERE owner_id = ? AND created_at >= ?
            """,
            (owner_id, week_start.isoformat())
        )
        week = (await cursor.fetchone())[0]

        return {
            "today": today,
            "week": week,
            "total": total,
        }


async def extend_subscription(tg_user_id: int, days: int):
    owner = await get_owner_by_tg_user_id(tg_user_id)

    if not owner:
        return False

    owner_id = owner[0]
    now = datetime.now()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT paid_until
            FROM subscriptions
            WHERE owner_id = ?
            """,
            (owner_id,)
        )
        row = await cursor.fetchone()

        if row:
            current_paid_until = datetime.fromisoformat(row[0])

            if current_paid_until > now:
                new_paid_until = current_paid_until + timedelta(days=days)
            else:
                new_paid_until = now + timedelta(days=days)

            await db.execute(
                """
                UPDATE subscriptions
                SET status = ?, plan = ?, paid_until = ?
                WHERE owner_id = ?
                """,
                ("active", "manual", new_paid_until.isoformat(), owner_id)
            )
        else:
            new_paid_until = now + timedelta(days=days)

            await db.execute(
                """
                INSERT INTO subscriptions (
                    owner_id,
                    status,
                    plan,
                    started_at,
                    paid_until
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    owner_id,
                    "active",
                    "manual",
                    now.isoformat(),
                    new_paid_until.isoformat(),
                )
            )

        await db.commit()
        return True


async def create_payment(owner_id: int, amount: int, plan: str):
    now = datetime.now().isoformat()

    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            INSERT INTO payments (
                owner_id,
                amount,
                plan,
                status,
                created_at
            )
            VALUES (?, ?, ?, ?, ?)
            """,
            (owner_id, amount, plan, "pending", now)
        )

        payment_id = cursor.lastrowid

        await db.commit()

        return payment_id