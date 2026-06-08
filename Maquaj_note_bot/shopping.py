import telebot
import json
from database import get_connection
from datetime import datetime

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def create_shopping_list(user_id, text):
    conn, cursor = get_connection()
    raw = text.lower().replace('купить', '', 1).strip(': ').strip()
    items_raw = [item.strip() for item in raw.split(',') if item.strip()]
    if len(items_raw) == 1 and ' ' in items_raw[0]:
        items_raw = items_raw[0].split()
    
    items = [{"name": item, "checked": False} for item in items_raw]
    
    cursor.execute('''
        INSERT INTO shopping_lists (user_id, name, items, date) 
        VALUES (?, ?, ?, ?)
    ''', (user_id, raw[:50], json.dumps(items, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M")))
    conn.commit()
    return cursor.lastrowid

def get_shopping_lists(user_id):
    conn, cursor = get_connection()
    cursor.execute('SELECT id, name, items, date FROM shopping_lists WHERE user_id = ? ORDER BY id DESC', (user_id,))
    return cursor.fetchall()

def update_shopping_item(list_id, user_id, item_index, checked):
    conn, cursor = get_connection()
    cursor.execute('SELECT items FROM shopping_lists WHERE id = ? AND user_id = ?', (list_id, user_id))
    row = cursor.fetchone()
    if row:
        items = json.loads(row[0])
        if 0 <= item_index < len(items):
            items[item_index]["checked"] = checked
            cursor.execute('UPDATE shopping_lists SET items = ? WHERE id = ? AND user_id = ?',
                          (json.dumps(items, ensure_ascii=False), list_id, user_id))
            conn.commit()
            return True
    return False

def delete_shopping_list(list_id, user_id):
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM shopping_lists WHERE id = ? AND user_id = ?', (list_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def format_all_shopping_lists(user_id):
    """Форматирует ВСЕ списки покупок в ОДНОМ сообщении"""
    lists = get_shopping_lists(user_id)
    if not lists:
        return None, None
    
    message = "🛒 *Все списки покупок*\n\n"
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=2)
    
    for list_id, name, items_json, date in lists:
        items = json.loads(items_json)
        checked_count = sum(1 for i in items if i["checked"])
        total_count = len(items)
        
        # Заголовок списка
        status_icon = "✅" if checked_count == total_count and total_count > 0 else "🔄"
        message += f"{status_icon} *{name}*\n📅 {date}\n"
        
        # Пункты списка с галочками слева
        for i, item in enumerate(items):
            check = "✅" if item["checked"] else "⬜"
            message += f"{check} {item['name']}\n"
            # Кнопка с дублированием названия
            btn_text = f"{'🔄' if item['checked'] else '✅'} {item['name']}"
            keyboard.add(telebot.types.InlineKeyboardButton(
                btn_text, callback_data=f"shop_toggle_{list_id}_{i}"
            ))
        
        message += f"\n📊 {checked_count}/{total_count} куплено\n"
        message += "─" * 20 + "\n"
        
        # Кнопка удаления списка
        keyboard.add(telebot.types.InlineKeyboardButton(
            f"🗑 Удалить список: {name}", callback_data=f"shop_del_{list_id}"
        ))
        keyboard.row()  # новая строка
    
    return message, keyboard

def register_handlers(bot):
    
    @bot.message_handler(commands=['shopping', 'покупки'])
    def show_shopping_lists_command(message):
        msg, keyboard = format_all_shopping_lists(message.chat.id)
        if msg is None:
            bot.reply_to(message, "🛒 Нет списков покупок.\nСоздайте: *купить: хлеб, молоко*", parse_mode='Markdown')
            return
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('shop_toggle_'))
    def handle_toggle(call):
        parts = call.data.split('_')
        list_id = int(parts[2])
        item_index = int(parts[3])
        
        update_shopping_item(list_id, call.message.chat.id, item_index, None)
        
        # Получаем текущий статус и переключаем
        conn, cursor = get_connection()
        cursor.execute('SELECT items FROM shopping_lists WHERE id = ? AND user_id = ?', 
                      (list_id, call.message.chat.id))
        row = cursor.fetchone()
        if row:
            items = json.loads(row[0])
            if 0 <= item_index < len(items):
                new_status = not items[item_index]["checked"]
                update_shopping_item(list_id, call.message.chat.id, item_index, new_status)
                
                # Обновляем всё сообщение
                msg, keyboard = format_all_shopping_lists(call.message.chat.id)
                if msg:
                    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                         parse_mode='Markdown', reply_markup=keyboard)
                    bot.answer_callback_query(call.id, "✅ Статус обновлён")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('shop_del_'))
    def handle_delete_list(call):
        list_id = int(call.data.split('_')[2])
        if delete_shopping_list(list_id, call.message.chat.id):
            # Обновляем сообщение
            msg, keyboard = format_all_shopping_lists(call.message.chat.id)
            if msg:
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                     parse_mode='Markdown', reply_markup=keyboard)
            else:
                bot.edit_message_text("🛒 Все списки покупок удалены", 
                                     call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "🗑 Список удалён!")
