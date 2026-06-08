import telebot
from database import execute_query, get_connection, put_connection
from utils import parse_datetime, extract_reminder_text
from datetime import datetime
import threading
import time

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_reminder(user_id, text, remind_time):
    query = '''
        INSERT INTO reminders (user_id, text, remind_time, is_sent, attempts)
        VALUES (%s, %s, %s, 0, 0)
        RETURNING id
    '''
    # Убедитесь, что remind_time в правильном формате
    formatted_time = remind_time.strftime("%Y-%m-%d %H:%M:%S")
    result = execute_query(query, (user_id, text, formatted_time), fetch_one=True)
    return result[0] if result else None

def get_pending_reminders():
    now = datetime.now().isoformat()
    query = '''
        SELECT id, user_id, text, remind_time, attempts 
        FROM reminders 
        WHERE is_sent = 0 AND remind_time <= %s AND attempts < 3
    '''
    result = execute_query(query, (now,), fetch_all=True)
    return result if result else []

def increment_attempt(reminder_id):
    query = 'UPDATE reminders SET attempts = attempts + 1 WHERE id = %s'
    execute_query(query, (reminder_id,))

def mark_reminder_sent(reminder_id):
    query = 'UPDATE reminders SET is_sent = 1 WHERE id = %s'
    execute_query(query, (reminder_id,))

def reschedule_failed_reminder(reminder_id):
    query = 'UPDATE reminders SET remind_time = remind_time + interval \'10 minutes\' WHERE id = %s'
    execute_query(query, (reminder_id,))
    print(f"⏰ Напоминание #{reminder_id} перенесено на +10 минут")

def delete_reminder(reminder_id, user_id):
    query = 'DELETE FROM reminders WHERE id = %s AND user_id = %s'
    execute_query(query, (reminder_id, user_id))
    return True

def get_all_future_reminders(user_id):
    query = '''
        SELECT id, text, remind_time 
        FROM reminders 
        WHERE user_id = %s AND is_sent = 0
        ORDER BY remind_time
    '''
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []

def format_reminder_time(reminder_time):
    if isinstance(reminder_time, str):
        dt = datetime.fromisoformat(reminder_time)
    else:
        dt = reminder_time
    return dt.strftime("%d.%m.%Y в %H:%M")

def get_reminders_list(user_id):
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
    print("⏰ Инициализация потока напоминаний...")
    
    def checker():
        print("⏰ Поток напоминаний запущен и работает")
        last_debug = time.time()
        
        while True:
            try:
                if time.time() - last_debug > 30:
                    print("⏰ Поток напоминаний активен, проверяю...")
                    last_debug = time.time()
                
                reminders = get_pending_reminders()
                if reminders:
                    print(f"📋 Найдено {len(reminders)} напоминаний для отправки")
                
                for rem_id, user_id, text, remind_time, attempts in reminders:
                    try:
                        time_str = format_reminder_time(remind_time)
                        print(f"🔔 Отправка напоминания #{rem_id} пользователю {user_id}: '{text}' на {time_str}")
                        
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
                        print(f"✅ Напоминание #{rem_id} отправлено и помечено")
                        
                    except Exception as e:
                        print(f"❌ Ошибка отправки #{rem_id}, попытка {attempts+1}/3: {e}")
                        increment_attempt(rem_id)
                        
                        if attempts + 1 >= 3:
                            reschedule_failed_reminder(rem_id)
                            
            except Exception as e:
                print(f"❌ Критическая ошибка в checker: {e}")
            
            time.sleep(30)
    
    thread = threading.Thread(target=checker, daemon=True)
    thread.start()
    print("⏰ Поток напоминаний успешно запущен")

print("📦 Модуль reminders.py загружен")
