import aiosqlite

DB_PATH = "rlec_database.db"

async def get_db():
    return await aiosqlite.connect(DB_PATH)

async def init_db():
    """Initialise les tables de la base de données"""
    async with get_db() as db:
        await db.execute('''CREATE TABLE IF NOT EXISTS config (
            guild_id INTEGER PRIMARY KEY,
            welcome_channel INTEGER,
            ticket_category INTEGER,
            logs_channel INTEGER,
            auto_role INTEGER
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS teams (
            team_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            name TEXT,
            captain_id INTEGER,
            game TEXT
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS players (
            user_id INTEGER PRIMARY KEY,
            guild_id INTEGER,
            team_id INTEGER,
            wins INTEGER DEFAULT 0,
            losses INTEGER DEFAULT 0
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS tickets (
            ticket_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            user_id INTEGER,
            channel_id INTEGER,
            type TEXT,
            status TEXT DEFAULT 'open'
        )''')
        await db.execute('''CREATE TABLE IF NOT EXISTS matches (
            match_id INTEGER PRIMARY KEY AUTOINCREMENT,
            guild_id INTEGER,
            team1 TEXT,
            team2 TEXT,
            scheduled_time TEXT,
            score1 INTEGER DEFAULT 0,
            score2 INTEGER DEFAULT 0,
            status TEXT DEFAULT 'scheduled'
        )''')
        await db.commit()
