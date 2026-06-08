import os
import time

# Переменные окружения
DATABASE_URL = os.environ.get('DATABASE_URL', None)
USE_POSTGRES = DATABASE_URL is not None

print(f"🔍 DATABASE_URL найден: {'✅ Да' if USE_POSTGRES else '❌ Нет'}")

conn_pool = None

def init_db():
    global conn_pool
    if USE_POSTGRES:
        try:
            print("🔄 Подключение к PostgreSQL...")
            import psycopg2
            from psycopg2.pool import SimpleConnectionPool
            
            # Увеличим пул до 10 соединений
            conn_pool = SimpleConnectionPool(2, 10, DATABASE_URL)
            conn = conn_pool.getconn()
            cursor = conn.cursor()
            
            # Создание таблиц
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS notes (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    text TEXT,
                    date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS shopping_lists (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    name TEXT,
                    items TEXT,
                    date TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS birthdays (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    name TEXT,
                    day INTEGER,
                    month INTEGER,
                    year INTEGER,
                    date_text TEXT
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS reminders (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    text TEXT,
                    remind_time TIMESTAMP,
                    is_sent INTEGER DEFAULT 0,
                    attempts INTEGER DEFAULT 0
                )
            ''')
            
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS todos (
                    id SERIAL PRIMARY KEY,
                    user_id BIGINT,
                    task TEXT,
                    is_done INTEGER DEFAULT 0,
                    date TEXT
                )
            ''')
            
            conn.commit()
            cursor.close()
            conn_pool.putconn(conn)
            print("✅ PostgreSQL база данных инициализирована")
            
        except Exception as e:
            print(f"❌ Ошибка подключения к PostgreSQL: {e}")
            print("🔄 Переключаемся на SQLite...")
            init_sqlite()
    else:
        print("📁 Используем SQLite (локальная база данных)")
        init_sqlite()

def init_sqlite():
    global conn_pool
    import sqlite3
    
    try:
        conn = sqlite3.connect('pamyat.db', check_same_thread=False)
        cursor = conn.cursor()
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                date TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS shopping_lists (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                name TEXT,
                items TEXT,
                date TEXT
            )
        ''')
        
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
        
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS reminders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                text TEXT,
                remind_time TEXT,
                is_sent INTEGER DEFAULT 0,
                attempts INTEGER DEFAULT 0
            )
        ''')
        
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
        conn.close()
        print("✅ SQLite база данных инициализирована")
        
    except Exception as e:
        print(f"❌ Ошибка инициализации SQLite: {e}")

def get_connection():
    """Возвращает соединение с БД"""
    if USE_POSTGRES and conn_pool is not None:
        try:
            conn = conn_pool.getconn()
            cursor = conn.cursor()
            return conn, cursor
        except Exception as e:
            print(f"❌ Ошибка получения соединения PostgreSQL: {e}")
            import sqlite3
            conn = sqlite3.connect('pamyat.db', check_same_thread=False)
            cursor = conn.cursor()
            return conn, cursor
    else:
        import sqlite3
        conn = sqlite3.connect('pamyat.db', check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor

def put_connection(conn):
    """Возвращает соединение обратно в пул"""
    if USE_POSTGRES and conn_pool is not None:
        try:
            conn_pool.putconn(conn)
        except Exception as e:
            print(f"⚠️ Ошибка возврата соединения: {e}")
            try:
                conn.close()
            except:
                pass
    else:
        try:
            conn.close()
        except:
            pass

def execute_query(query, params=None, fetch_one=False, fetch_all=False):
    """Удобная функция для выполнения запросов с автоматическим возвратом соединения"""
    conn, cursor = get_connection()
    try:
        if params:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        
        conn.commit()
        
        result = None
        if fetch_one:
            result = cursor.fetchone()
        elif fetch_all:
            result = cursor.fetchall()
        
        return result
    except Exception as e:
        conn.rollback()
        print(f"❌ Ошибка запроса: {e}")
        raise e
    finally:
        put_connection(conn)

def close_connection():
    global conn_pool
    if conn_pool is not None:
        try:
            conn_pool.closeall()
        except:
            pass
        conn_pool = None
    print("🔌 Соединение с БД закрыто")

print("📦 Модуль database.py загружен")
