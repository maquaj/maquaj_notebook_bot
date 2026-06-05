import telebot
from database import get_connection
from datetime import datetime

# Временное хранилище для ожидания ввода задачи (будет заполняться из bot.py)
waiting_for_task = {}

def set_waiting_for_task(user_id):
    """Устанавливает флаг, что пользователь ожидает ввода задачи"""
    waiting_for_task[user_id] = True

def clear_waiting_for_task(user_id):
    """Убирает флаг ожидания"""
    if user_id in waiting_for_task:
        del waiting_for_task[user_id]

def is_waiting_for_task(user_id):
    """Проверяет, ожидает ли пользователь ввода задачи"""
    return user_id in waiting_for_task

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def add_task(user_id, task):
    """Добавляет новую задачу"""
    conn, cursor = get_connection()
    cursor.execute('''
        INSERT INTO todos (user_id, task, is_done, date) 
        VALUES (?, ?, 0, ?)
    ''', (user_id, task, datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    return cursor.lastrowid

def get_all_tasks(user_id):
    """Получает все задачи пользователя"""
    conn, cursor = get_connection()
    cursor.execute('''
        SELECT id, task, is_done, date 
        FROM todos 
        WHERE user_id = ? 
        ORDER BY is_done ASC, id DESC
    ''', (user_id,))
    return cursor.fetchall()

def toggle_task(task_id, user_id):
    """Переключает статус задачи (сделано/не сделано)"""
    conn, cursor = get_connection()
    cursor.execute('SELECT is_done FROM todos WHERE id = ? AND user_id = ?', (task_id, user_id))
    row = cursor.fetchone()
    if row:
        new_status = 0 if row[0] else 1
        cursor.execute('UPDATE todos SET is_done = ? WHERE id = ? AND user_id = ?', 
                      (new_status, task_id, user_id))
        conn.commit()
        return True
    return False

def delete_task(task_id, user_id):
    """Удаляет задачу"""
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM todos WHERE id = ? AND user_id = ?', (task_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def delete_all_done_tasks(user_id):
    """Удаляет все выполненные задачи"""
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM todos WHERE user_id = ? AND is_done = 1', (user_id,))
    conn.commit()
    return cursor.rowcount

def format_todo_list(tasks):
    """Форматирует список задач в одно сообщение с кнопками"""
    if not tasks:
        return "📭 *Нет задач*\n\nДобавьте: `сделать купить хлеб` или через `/todo`", None
    
    # Считаем статистику
    total = len(tasks)
    done = sum(1 for t in tasks if t[2])
    undone = total - done
    
    message = f"📋 *Список задач*\n"
    message += f"📊 Всего: {total} | ✅ Выполнено: {done} | ⬜ Осталось: {undone}\n\n"
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    for task_id, task, is_done, date in tasks:
        status = "✅" if is_done else "⬜"
        # Зачёркиваем выполненные задачи
        task_display = f"~~{task}~~" if is_done else task
        message += f"{status} {task_display}\n"
        
        # Кнопки для каждой задачи
        if is_done:
            keyboard.add(telebot.types.InlineKeyboardButton(
                f"🔄 Вернуть #{task_id}", callback_data=f"todo_toggle_{task_id}"
            ))
        else:
            keyboard.add(telebot.types.InlineKeyboardButton(
                f"✅ Выполнить #{task_id}", callback_data=f"todo_toggle_{task_id}"
            ))
    
    # Добавляем кнопки управления внизу
    keyboard.row(
        telebot.types.InlineKeyboardButton("🗑 Удалить все выполненные", callback_data="todo_clear_done"),
        telebot.types.InlineKeyboardButton("➕ Добавить задачу", callback_data="todo_add_prompt")
    )
    
    return message, keyboard

def register_handlers(bot):
    
    @bot.message_handler(commands=['todo'])
    def show_todo(message):
        """Показывает список задач"""
        tasks = get_all_tasks(message.chat.id)
        msg, keyboard = format_todo_list(tasks)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.message_handler(commands=['todo_add'])
    def add_task_command(message):
        """Добавляет задачу через команду: /todo_add купить хлеб"""
        task = message.text.replace('/todo_add', '', 1).strip()
        if task:
            add_task(message.chat.id, task)
            bot.reply_to(message, f"✅ Добавлена задача: *{task}*", parse_mode='Markdown')
        else:
            bot.reply_to(message, "📝 Используйте: `/todo_add купить хлеб`", parse_mode='Markdown')
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('todo_toggle_'))
    def handle_todo_toggle(call):
        """Обработка нажатия на кнопку выполнения/возврата задачи"""
        task_id = int(call.data.split('_')[2])
        if toggle_task(task_id, call.message.chat.id):
            # Обновляем сообщение
            tasks = get_all_tasks(call.message.chat.id)
            msg, keyboard = format_todo_list(tasks)
            bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                 parse_mode='Markdown', reply_markup=keyboard)
            bot.answer_callback_query(call.id, "✅ Статус обновлён")
    
    @bot.callback_query_handler(func=lambda call: call.data == 'todo_clear_done')
    def handle_clear_done(call):
        """Удаляет все выполненные задачи"""
        count = delete_all_done_tasks(call.message.chat.id)
        tasks = get_all_tasks(call.message.chat.id)
        msg, keyboard = format_todo_list(tasks)
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                             parse_mode='Markdown', reply_markup=keyboard)
        bot.answer_callback_query(call.id, f"🗑 Удалено {count} выполненных задач")