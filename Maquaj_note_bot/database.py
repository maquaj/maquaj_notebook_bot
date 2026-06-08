import os
import psycopg2
from psycopg2.extensions import connection
from psycopg2.pool import SimpleConnectionPool

# Переменные окружения
DATABASE_URL = os.environ.get('DATABASE_URL', 'pamyat.db')
USE_POSTGRES = DATABASE_URL != 'pamyat.db'

conn_pool = None

def init_db():
    global conn_pool
    if USE_POSTGRES:
        # PostgreSQL
        conn_pool = SimpleConnectionPool(1, 5, DATABASE_URL)
        conn = conn_pool.getconn()
        cursor = conn.cursor()
        
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
    else:
        # SQLite (локально)
        import sqlite3
        conn = sqlite3.connect('pamyat.db', check_same_thread=False)
        cursor = conn.cursor()
        # ... создание таблиц как раньше ...
        conn.commit()
    
    print("✅ База данных инициализирована")

def get_connection():
    if USE_POSTGRES:
        conn = conn_pool.getconn()
        cursor = conn.cursor()
        return conn, cursor
    else:
        import sqlite3
        conn = sqlite3.connect('pamyat.db', check_same_thread=False)
        cursor = conn.cursor()
        return conn, cursor

def put_connection(conn):
    if USE_POSTGRES:
        conn_pool.putconn(conn)
