import telebot
from database import execute_query, get_connection
from datetime import datetime

# Временное хранилище для ожидания ввода задачи
waiting_for_task = {}

def set_waiting_for_task(user_id):
    waiting_for_task[user_id] = True

def clear_waiting_for_task(user_id):
    if user_id in waiting_for_task:
        del waiting_for_task[user_id]

def is_waiting_for_task(user_id):
    return user_id in waiting_for_task

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_task(user_id, task):
    query = '''
        INSERT INTO todos (user_id, task, is_done, date) 
        VALUES (%s, %s, 0, %s)
    '''
    execute_query(query, (user_id, task, datetime.now().strftime("%Y-%m-%d %H:%M")))
    return True

def get_all_tasks(user_id):
    query = '''
        SELECT id, task, is_done, date 
        FROM todos 
        WHERE user_id = %s 
        ORDER BY is_done ASC, id DESC
    '''
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []

def toggle_task(task_id, user_id):
    select_query = 'SELECT is_done FROM todos WHERE id = %s AND user_id = %s'
    row = execute_query(select_query, (task_id, user_id), fetch_one=True)
    
    if row:
        new_status = 0 if row[0] else 1
        update_query = 'UPDATE todos SET is_done = %s WHERE id = %s AND user_id = %s'
        execute_query(update_query, (new_status, task_id, user_id))
        return True
    return False

def delete_task(task_id, user_id):
    query = 'DELETE FROM todos WHERE id = %s AND user_id = %s'
    execute_query(query, (task_id, user_id))
    return True

def delete_all_done_tasks(user_id):
    query = 'DELETE FROM todos WHERE user_id = %s AND is_done = 1'
    execute_query(query, (user_id,))
    return True

def format_todo_list(tasks):
    if not tasks:
        return "📭 *Нет задач*\n\nДобавьте: `сделать купить хлеб` или через `/todo`", None
    
    total = len(tasks)
    done = sum(1 for t in tasks if t[2])
    undone = total - done
    
    message = f"📋 *Список задач*\n"
    message += f"📊 Всего: {total} | ✅ Выполнено: {done} | ⬜ Осталось: {undone}\n\n"
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    for task_id, task, is_done, date in tasks:
        status = "✅" if is_done else "⬜"
        task_display = f"~~{task}~~" if is_done else task
        message += f"{status} {task_display}\n"
        
        if is_done:
            keyboard.add(telebot.types.InlineKeyboardButton(
                f"🔄 Вернуть: {task[:30]}", callback_data=f"todo_toggle_{task_id}"
            ))
        else:
            keyboard.add(telebot.types.InlineKeyboardButton(
                f"✅ Выполнить: {task[:30]}", callback_data=f"todo_toggle_{task_id}"
            ))
    
    keyboard.row(
        telebot.types.InlineKeyboardButton("🗑 Удалить все выполненные", callback_data="todo_clear_done"),
        telebot.types.InlineKeyboardButton("➕ Добавить задачу", callback_data="todo_add_prompt")
    )
    
    return message, keyboard

def register_handlers(bot):
    
    @bot.message_handler(commands=['todo', 'задачи'])
    def show_todo_command(message):
        tasks = get_all_tasks(message.chat.id)
        msg, keyboard = format_todo_list(tasks)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.message_handler(commands=['todo_add'])
    def add_task_command(message):
        task = message.text.replace('/todo_add', '', 1).strip()
        if task:
            add_task(message.chat.id, task)
            bot.reply_to(message, f"✅ Добавлена задача: *{task}*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "📝 Используйте: `/todo_add купить хлеб`", parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('todo_toggle_'))
    def handle_todo_toggle(call):
        task_id = int(call.data.split('_')[2])
        if toggle_task(task_id, call.message.chat.id):
            tasks = get_all_tasks(call.message.chat.id)
            msg, keyboard = format_todo_list(tasks)
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=keyboard)
            bot.answer_callback_query(call.id, "✅ Статус обновлён")
    
    @bot.callback_query_handler(func=lambda call: call.data == 'todo_clear_done')
    def handle_clear_done(call):
        delete_all_done_tasks(call.message.chat.id)
        tasks = get_all_tasks(call.message.chat.id)
        msg, keyboard = format_todo_list(tasks)
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown', reply_markup=keyboard)
        bot.answer_callback_query(call.id, "🗑 Выполненные задачи удалены")

print("📦 Модуль todo.py загружен")
