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
    ''', (user_id, raw[:50], json.dumps(items), datetime.now().strftime("%Y-%m-%d %H:%M")))
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
                          (json.dumps(items), list_id, user_id))
            conn.commit()
            return True
    return False

def delete_shopping_list(list_id, user_id):
    conn, cursor = get_connection()
    cursor.execute('DELETE FROM shopping_lists WHERE id = ? AND user_id = ?', (list_id, user_id))
    conn.commit()
    return cursor.rowcount > 0

def format_shopping_list(list_id, name, items_json, date):
    items = json.loads(items_json)
    message = f"🛒 *{name}*\n📅 {date}\n\n"
    
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for i, item in enumerate(items):
        status = "✅" if item["checked"] else "⬜"
        message += f"{status} {item['name']}\n"
        btn_text = "✔️ Куплено" if not item["checked"] else "🔄 Вернуть"
        keyboard.add(telebot.types.InlineKeyboardButton(
            btn_text, callback_data=f"shop_toggle_{list_id}_{i}"
        ))
    
    message += f"\n📊 {sum(1 for i in items if i['checked'])} из {len(items)} куплено"
    keyboard.add(telebot.types.InlineKeyboardButton("🗑 Удалить список", callback_data=f"shop_del_{list_id}"))
    
    return message, keyboard

def show_shopping_lists(message):
    """Показывает списки покупок (вызывается из bot.py для команд и меню)"""
    lists = get_shopping_lists(message.chat.id)
    if not lists:
        # Импортируем bot глобально или используем переданный
        from bot import bot
        bot.reply_to(message, "🛒 Нет списков покупок.\nСоздайте: *купить: хлеб, молоко*", parse_mode='Markdown')
        return
    
    from bot import bot
    for list_id, name, items, date in lists:
        msg, keyboard = format_shopping_list(list_id, name, items, date)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

def register_handlers(bot):
    
    @bot.message_handler(commands=['shopping', 'покупки'])
    def show_shopping_lists_command(message):
        """Показывает списки покупок по команде"""
        lists = get_shopping_lists(message.chat.id)
        if not lists:
            bot.reply_to(message, "🛒 Нет списков покупок.\nСоздайте: *купить: хлеб, молоко*", parse_mode='Markdown')
            return
        
        for list_id, name, items, date in lists:
            msg, keyboard = format_shopping_list(list_id, name, items, date)
            bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('shop_toggle_'))
    def handle_toggle(call):
        parts = call.data.split('_')
        list_id = int(parts[2])
        item_index = int(parts[3])
        
        conn, cursor = get_connection()
        cursor.execute('SELECT items FROM shopping_lists WHERE id = ? AND user_id = ?', 
                      (list_id, call.message.chat.id))
        row = cursor.fetchone()
        if row:
            items = json.loads(row[0])
            if 0 <= item_index < len(items):
                new_status = not items[item_index]["checked"]
                update_shopping_item(list_id, call.message.chat.id, item_index, new_status)
                
                cursor.execute('SELECT name, items, date FROM shopping_lists WHERE id = ?', (list_id,))
                new_row = cursor.fetchone()
                if new_row:
                    msg, keyboard = format_shopping_list(list_id, new_row[0], new_row[1], new_row[2])
                    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                         parse_mode='Markdown', reply_markup=keyboard)
                    bot.answer_callback_query(call.id, "✅ Статус обновлён")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('shop_del_'))
    def handle_delete_list(call):
        list_id = int(call.data.split('_')[2])
        if delete_shopping_list(list_id, call.message.chat.id):
            bot.answer_callback_query(call.id, "🗑 Список удалён!")
            bot.delete_message(call.message.chat.id, call.message.message_id)
