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

    # Проверяем и добавляем колонку attempts в reminders (для старых баз)
    cursor.execute("PRAGMA table_info(reminders)")
    columns = [col[1] for col in cursor.fetchall()]
    if 'attempts' not in columns:
        cursor.execute('ALTER TABLE reminders ADD COLUMN attempts INTEGER DEFAULT 0')
        print("✅ Добавлена колонка attempts в таблицу reminders")
    
    conn.commit()
    print("✅ База данных инициализирована, все таблицы готовы")

def get_connection():
    """Возвращает соединение и курсор для работы с БД"""
    global conn, cursor
    if conn is None:
        init_db()
    return conn, cursor

def close_connection():
    """Закрывает соединение с БД"""
    global conn, cursor
    if conn:
        conn.close()
        conn = None
        cursor = None
        print("🔌 Соединение с БД закрыто")
        
