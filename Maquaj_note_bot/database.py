import sqlite3

conn = None
cursor = None

def init_db():
    global conn, cursor
    conn = sqlite3.connect('pamyat.db', check_same_thread=False)
    cursor = conn.cursor()
    
    # Заметки
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS notes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            date TEXT
        )
    ''')
    
    # Списки покупок
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS shopping_lists (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            items TEXT,
            date TEXT
        )
    ''')
    
    # Дни рождения
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS birthdays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT,
            day INTEGER,
            month INTEGER,
            year INTEGER,
            date_text TEXT
        )
    ''')
    
    # Напоминания (новая таблица)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS reminders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            text TEXT,
            remind_time TEXT,  -- ISO формат "2026-06-15 15:00:00"
            is_sent INTEGER DEFAULT 0
        )
    ''')

        # Список задач (Todo)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS todos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            task TEXT,
            is_done INTEGER DEFAULT 0,
            date TEXT
        )
    ''')
    
    conn.commit()

def get_connection():
    return conn, cursor