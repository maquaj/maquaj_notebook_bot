import telebot
from database import execute_query, get_connection
from datetime import datetime

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_note(user_id, text):
    query = 'INSERT INTO notes (user_id, text, date) VALUES (%s, %s, %s)'
    execute_query(query, (user_id, text, datetime.now().strftime("%Y-%m-%d %H:%M")))

def get_notes(user_id):
    query = 'SELECT id, text, date FROM notes WHERE user_id = %s ORDER BY id DESC'
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []

def delete_note(note_id, user_id):
    query = 'DELETE FROM notes WHERE id = %s AND user_id = %s'
    execute_query(query, (note_id, user_id))
    return True

def show_notes(message):
    from bot import bot
    notes_list = get_notes(message.chat.id)
    if not notes_list:
        bot.reply_to(message, "📭 Нет заметок")
        return
    
    for note_id, text, date in notes_list:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("❌ Удалить", callback_data=f"del_note_{note_id}"))
        bot.send_message(message.chat.id, f"📌 *{date}*\n{text}", 
                        parse_mode='Markdown', reply_markup=keyboard)

def register_handlers(bot):
    
    @bot.message_handler(commands=['list', 'список'])
    def list_command(message):
        show_notes(message)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('del_note_'))
    def handle_delete_note(call):
        note_id = int(call.data.split('_')[2])
        if delete_note(note_id, call.message.chat.id):
            bot.answer_callback_query(call.id, "🗑 Заметка удалена!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
        else:
            bot.answer_callback_query(call.id, "❌ Ошибка при удалении")

print("📦 Модуль notes.py загружен")
