import telebot
from database import get_connection
from utils import parse_datetime, extract_reminder_text
from datetime import datetime
import threading
import time

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_reminder(user_id, text, remind_time):
    conn, cursor = get_connection()
    cursor.execute('''
        INSERT INTO reminders (user_id, text, remind_time, is_sent)
        VALUES (?, ?, ?, 0)
    ''', (user_id, text, remind_time.isoformat()))
    conn.commit()
    return cursor.lastrowid

def get_pending_reminders():
    conn, cursor = get_connection()
    now = datetime.now().isoformat()
    cursor.execute('''
        SELECT id, user_id, text, remind_time 
        FROM reminders 
        WHERE is_sent = 0 AND remind_time <= ?
    ''', (now,))
    return cursor.fetchall()

def mark_reminder_sent(reminder_id):
    conn, cursor = get_connection()
    cursor.execute('UPDATE reminders SET is_sent = 1 WHERE id = ?', (reminder_id,))
    conn.commit()

def get_all_future_reminders(user_id):
    conn, cursor = get_connection()
    cursor.execute('''
        SELECT id, text, remind_time 
        FROM reminders 
        WHERE user_id = ? AND is_sent = 0
        ORDER BY remind_time
    ''', (user_id,))
    return cursor.fetchall()

def delete_reminder(reminder_id, user_id):
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM reminders WHERE id = ? AND user_id = ?', (reminder_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def format_reminder_time(reminder_time):
    dt = datetime.fromisoformat(reminder_time)
    return dt.strftime("%d.%m.%Y в %H:%M")

def register_handlers(bot):
    
    @bot.message_handler(commands=['reminders'])
    def show_reminders(message):
        reminders = get_all_future_reminders(message.chat.id)
        if not reminders:
            bot.reply_to(message, "⏰ Нет активных напоминаний.\nСоздайте: *напомни купить хлеб завтра в 15:00*", 
                        parse_mode='Markdown')
            return
        
        msg = "⏰ *Ваши напоминания:*\n\n"
        keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
        
        for rem_id, text, rem_time in reminders:
            time_str = format_reminder_time(rem_time)
            msg += f"• *{text}* — {time_str}\n"
            keyboard.add(telebot.types.InlineKeyboardButton(
                f"❌ {text[:25]} ({time_str})", callback_data=f"rem_del_{rem_id}"
            ))
        
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

def start_reminder_checker(bot):
    """Фоновый поток для проверки и отправки напоминаний"""
    def checker():
        print("⏰ Поток напоминаний запущен и работает")
        while True:
            try:
                reminders = get_pending_reminders()
                if reminders:
                    print(f"📋 Найдено {len(reminders)} напоминаний для отправки")
                for rem_id, user_id, text, remind_time in reminders:
                    try:
                        dt = datetime.fromisoformat(remind_time)
                        time_str = dt.strftime("%d.%m.%Y в %H:%M")
                        print(f"🔔 Отправка: пользователю {user_id}, текст: {text}, время: {time_str}")
                        
                        keyboard = telebot.types.InlineKeyboardMarkup()
                        keyboard.add(telebot.types.InlineKeyboardButton(
                            "✅ Я увидел", callback_data=f"rem_ack_{rem_id}"
                        ))
                        
                        bot.send_message(user_id,
                            f"⏰ *Напоминание!*\n\n"
                            f"📝 {text}\n"
                            f"🕐 Запланировано на {time_str}",
                            parse_mode='Markdown',
                            reply_markup=keyboard)
                        
                        print(f"✅ Напоминание {rem_id} отправлено, ожидает подтверждения")
                    except Exception as e:
                        print(f"❌ Ошибка отправки напоминания {rem_id}: {e}")
            except Exception as e:
                print(f"❌ Ошибка в checker: {e}")
            time.sleep(30)
    
    thread = threading.Thread(target=checker, daemon=True)
    thread.start()
    print("⏰ Поток напоминаний успешно запущен")