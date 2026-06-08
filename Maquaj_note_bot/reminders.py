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
        INSERT INTO reminders (user_id, text, remind_time, is_sent, attempts)
        VALUES (?, ?, ?, 0, 0)
    ''', (user_id, text, remind_time.isoformat()))
    conn.commit()
    return cursor.lastrowid

def get_pending_reminders():
    conn, cursor = get_connection()
    now = datetime.now().isoformat()
    cursor.execute('''
        SELECT id, user_id, text, remind_time, attempts 
        FROM reminders 
        WHERE is_sent = 0 AND remind_time <= ? AND attempts < 3
    ''', (now,))
    return cursor.fetchall()

def increment_attempt(reminder_id):
    conn, cursor = get_connection()
    cursor.execute('UPDATE reminders SET attempts = attempts + 1 WHERE id = ?', (reminder_id,))
    conn.commit()

def mark_reminder_sent(reminder_id):
    conn, cursor = get_connection()
    cursor.execute('UPDATE reminders SET is_sent = 1 WHERE id = ?', (reminder_id,))
    conn.commit()

def reschedule_failed_reminder(reminder_id):
    conn, cursor = get_connection()
    cursor.execute('''
        UPDATE reminders 
        SET remind_time = datetime(remind_time, '+10 minutes')
        WHERE id = ?
    ''', (reminder_id,))
    conn.commit()

def delete_reminder(reminder_id, user_id):
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM reminders WHERE id = ? AND user_id = ?', (reminder_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def get_all_future_reminders(user_id):
    conn, cursor = get_connection()
    cursor.execute('''
        SELECT id, text, remind_time 
        FROM reminders 
        WHERE user_id = ? AND is_sent = 0
        ORDER BY remind_time
    ''', (user_id,))
    return cursor.fetchall()

def format_reminder_time(reminder_time):
    dt = datetime.fromisoformat(reminder_time)
    return dt.strftime("%d.%m.%Y в %H:%M")

def get_reminders_list(user_id):
    """Возвращает отформатированный список напоминаний и клавиатуру"""
    reminders = get_all_future_reminders(user_id)
    if not reminders:
        return "⏰ Нет активных напоминаний.\nСоздайте: *напомни купить хлеб завтра в 15:00*", None
    
    msg = "⏰ *Ваши напоминания:*\n\n"
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for rem_id, text, rem_time in reminders:
        time_str = format_reminder_time(rem_time)
        msg += f"• *{text}* — {time_str}\n"
        keyboard.add(telebot.types.InlineKeyboardButton(
            f"❌ {text[:25]} ({time_str})", callback_data=f"rem_del_{rem_id}"
        ))
    
    return msg, keyboard

def register_handlers(bot):
    
    @bot.message_handler(commands=['reminders', 'напомнить'])
    def show_reminders_command(message):
        """Показывает напоминания по команде"""
        msg, keyboard = get_reminders_list(message.chat.id)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rem_del_'))
    def handle_delete_reminder(call):
        rem_id = int(call.data.split('_')[2])
        if delete_reminder(rem_id, call.message.chat.id):
            bot.answer_callback_query(call.id, "⏰ Напоминание удалено!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('rem_ack_'))
    def handle_reminder_ack(call):
        rem_id = int(call.data.split('_')[2])
        mark_reminder_sent(rem_id)
        
        try:
            bot.edit_message_text(
                f"✅ *Подтверждено*\n\nВы увидели напоминание.",
                call.message.chat.id,
                call.message.message_id,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"Ошибка редактирования сообщения: {e}")
        
        bot.answer_callback_query(call.id, "👍 Отлично!")

def start_reminder_checker(bot):
    def checker():
        print("⏰ Поток напоминаний запущен")
        while True:
            try:
                reminders = get_pending_reminders()
                if reminders:
                    print(f"📋 Найдено {len(reminders)} напоминаний")
                
                for rem_id, user_id, text, remind_time, attempts in reminders:
                    try:
                        dt = datetime.fromisoformat(remind_time)
                        time_str = dt.strftime("%d.%m.%Y в %H:%M")
                        
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
                        
                        mark_reminder_sent(rem_id)
                        print(f"✅ Напоминание {rem_id} отправлено")
                        
                    except Exception as e:
                        print(f"❌ Ошибка отправки {rem_id}, попытка {attempts+1}/3: {e}")
                        increment_attempt(rem_id)
                        
                        if attempts + 1 >= 3:
                            reschedule_failed_reminder(rem_id)
                            print(f"⏰ Напоминание {rem_id} перенесено на +10 минут")
                            
            except Exception as e:
                print(f"❌ Ошибка в checker: {e}")
            time.sleep(30)
    
    thread = threading.Thread(target=checker, daemon=True)
    thread.start()
    print("⏰ Поток напоминаний успешно запущен")
