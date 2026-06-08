import telebot
from database import execute_query, get_connection
from datetime import datetime
import re
import threading
import time

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def parse_birthday(text):
    text_lower = text.lower()
    clean = re.sub(r'^др\s*', '', text_lower)
    
    patterns = [
        r'(\w+)\s+(\d{1,2})\.(\d{1,2})(?:\.(\d{4}))?',
        r'(\w+)\s+(\d{1,2})\s+(\w+)',
        r'(\w+)\s+(\d{1,2})\s+(\w+)\s+(\d{4})',
    ]
    
    for pattern in patterns:
        match = re.search(pattern, clean)
        if match:
            groups = match.groups()
            name = groups[0].capitalize()
            day = int(groups[1])
            
            if len(groups) >= 3:
                month_str = groups[2]
                if month_str.isdigit():
                    month = int(month_str)
                else:
                    months = {
                        'января': 1, 'февраля': 2, 'марта': 3, 'апреля': 4,
                        'мая': 5, 'июня': 6, 'июля': 7, 'августа': 8,
                        'сентября': 9, 'октября': 10, 'ноября': 11, 'декабря': 12
                    }
                    month = months.get(month_str, 1)
            
            year = int(groups[3]) if len(groups) >= 4 and groups[3] and groups[3].isdigit() else None
            return name, day, month, year
    return None

def add_birthday(user_id, name, day, month, year=None):
    date_text = f"{day:02d}.{month:02d}" + (f".{year}" if year else "")
    query = '''
        INSERT INTO birthdays (user_id, name, day, month, year, date_text)
        VALUES (%s, %s, %s, %s, %s, %s)
    '''
    execute_query(query, (user_id, name, day, month, year, date_text))
    return True

def get_birthdays(user_id):
    query = 'SELECT id, name, day, month, year, date_text FROM birthdays WHERE user_id = %s ORDER BY month, day'
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []

def delete_birthday(bday_id, user_id):
    query = 'DELETE FROM birthdays WHERE id = %s AND user_id = %s'
    execute_query(query, (bday_id, user_id))
    return True

def get_today_birthdays():
    today = datetime.now()
    query = 'SELECT user_id, name, date_text, year FROM birthdays WHERE day = %s AND month = %s'
    result = execute_query(query, (today.day, today.month), fetch_all=True)
    return result if result else []

def get_birthdays_list(user_id):
    birthdays = get_birthdays(user_id)
    if not birthdays:
        return "🎂 Нет сохранённых дней рождения.\nДобавьте: *др Анна 15.03*", None
    
    msg = "🎂 *Сохранённые дни рождения:*\n\n"
    keyboard = telebot.types.InlineKeyboardMarkup()
    
    for bday_id, name, day, month, year, date_text in birthdays:
        year_text = f" ({year} г.)" if year else ""
        msg += f"• *{name}* — {date_text}{year_text}\n"
        keyboard.add(telebot.types.InlineKeyboardButton(f"❌ {name}", callback_data=f"bday_del_{bday_id}"))
    
    return msg, keyboard

def register_handlers(bot):
    
    @bot.message_handler(commands=['birthdays', 'др'])
    def show_birthdays_command(message):
        msg, keyboard = get_birthdays_list(message.chat.id)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('bday_del_'))
    def handle_delete_bday(call):
        bday_id = int(call.data.split('_')[2])
        if delete_birthday(bday_id, call.message.chat.id):
            bot.answer_callback_query(call.id, "🎂 День рождения удалён!")
            bot.delete_message(call.message.chat.id, call.message.message_id)

def start_birthday_checker(bot):
    def checker():
        last_date = None
        while True:
            try:
                now = datetime.now()
                if now.hour == 9 and now.minute == 0 and last_date != now.date():
                    birthdays = get_today_birthdays()
                    for user_id, name, date_text, year in birthdays:
                        age = now.year - year if year else None
                        age_text = f" — {age} лет 🎂" if age else ""
                        try:
                            bot.send_message(user_id,
                                f"🎉 *Напоминание о дне рождения!*\n\n"
                                f"Сегодня день рождения у *{name}*{age_text}!\n"
                                f"📅 {date_text}\n\n"
                                f"Не забудьте поздравить! 🎁",
                                parse_mode='Markdown')
                        except Exception as e:
                            print(f"Ошибка отправки ДР: {e}")
                    last_date = now.date()
            except Exception as e:
                print(f"Ошибка в birthday checker: {e}")
            time.sleep(60)
    
    thread = threading.Thread(target=checker, daemon=True)
    thread.start()

print("📦 Модуль birthdays.py загружен")
