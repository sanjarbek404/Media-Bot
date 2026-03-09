import aiosqlite
import uuid

DB_FILE = "database.db"

async def init_db():
    async with aiosqlite.connect(DB_FILE) as db:
        # Table for URL mapping (Inline buttons)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS url_mapping (
                short_id TEXT PRIMARY KEY,
                original_url TEXT
            )
        ''')
        # Table for tracking Users (for Broadcast)
        await db.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                first_name TEXT,
                username TEXT,
                language TEXT DEFAULT 'uz'
            )
        ''')
        # Table for mandatory Channels
        await db.execute('''
            CREATE TABLE IF NOT EXISTS channels (
                channel_id TEXT PRIMARY KEY,
                channel_url TEXT
            )
        ''')
        # Migration: add language column if missing (for existing databases)
        try:
            await db.execute("ALTER TABLE users ADD COLUMN language TEXT DEFAULT 'uz'")
        except Exception:
            pass  # Column already exists
        await db.commit()

async def save_url_mapping(url: str) -> str:
    short_id = uuid.uuid4().hex[:8]
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('INSERT INTO url_mapping (short_id, original_url) VALUES (?, ?)', (short_id, url))
        await db.commit()
    return short_id

async def get_url_from_mapping(short_id: str) -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT original_url FROM url_mapping WHERE short_id = ?', (short_id,)) as cursor:
            row = await cursor.fetchone()
            if row:
                return row[0]
            return None

# --- User Management (Admin) ---
async def user_exists(user_id: int) -> bool:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT 1 FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row is not None

async def add_user(user_id: int, first_name: str, username: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            INSERT OR IGNORE INTO users (user_id, first_name, username) 
            VALUES (?, ?, ?)
        ''', (user_id, first_name, username))
        await db.commit()

async def get_all_users():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT user_id FROM users') as cursor:
            rows = await cursor.fetchall()
            return [row[0] for row in rows]

async def set_user_lang(user_id: int, lang: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('UPDATE users SET language = ? WHERE user_id = ?', (lang, user_id))
        await db.commit()

async def get_user_lang(user_id: int) -> str:
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT language FROM users WHERE user_id = ?', (user_id,)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 'uz'

async def get_user_count():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT COUNT(*) FROM users') as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

# --- Channel Management (Admin) ---
async def add_channel(channel_id: str, channel_url: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('''
            INSERT OR REPLACE INTO channels (channel_id, channel_url) 
            VALUES (?, ?)
        ''', (channel_id, channel_url))
        await db.commit()

async def remove_channel(channel_id: str):
    async with aiosqlite.connect(DB_FILE) as db:
        await db.execute('DELETE FROM channels WHERE channel_id = ?', (channel_id,))
        await db.commit()

async def get_all_channels():
    async with aiosqlite.connect(DB_FILE) as db:
        async with db.execute('SELECT channel_id, channel_url FROM channels') as cursor:
            rows = await cursor.fetchall()
            return [{"id": row[0], "url": row[1]} for row in rows]
