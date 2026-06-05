import telebot
from database import get_connection
from datetime import datetime

# Глобальная переменная для бота (устанавливается из bot.py)
bot = None

def set_bot(bot_instance):
    """Устанавливает экземпляр бота для отправки сообщений"""
    global bot
    bot = bot_instance

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_note(user_id, text):
    """Добавляет новую заметку"""
    conn, cursor = get_connection()
    cursor.execute('INSERT INTO notes (user_id, text, date) VALUES (?, ?, ?)',
                   (user_id, text, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()

def get_notes(user_id):
    """Получает все заметки пользователя"""
    conn, cursor = get_connection()
    cursor.execute('SELECT id, text, date FROM notes WHERE user_id = ? ORDER BY id DESC', (user_id,))
    return cursor.fetchall()

def delete_note(note_id, user_id):
    """Удаляет заметку по ID"""
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM notes WHERE id = ? AND user_id = ?', (note_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def show_notes(message):
    """Показывает заметки (вызывается из bot.py для команд /list и /список)"""
    notes_list = get_notes(message.chat.id)
    if not notes_list:
        bot.reply_to(message, "📭 Нет заметок")
        return
    
    for note_id, text, date in notes_list:
        keyboard = telebot.types.InlineKeyboardMarkup()
        keyboard.add(telebot.types.InlineKeyboardButton("❌ Удалить", callback_data=f"del_note_{note_id}"))
        bot.send_message(message.chat.id, f"📌 *{date}*\n{text}", 
                        parse_mode='Markdown', reply_markup=keyboard)

def register_handlers(bot_instance):
    """Регистрирует обработчики команд и кнопок для заметок"""
    global bot
    bot = bot_instance
    
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