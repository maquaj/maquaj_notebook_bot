import telebot
import json
from database import execute_query, get_connection
from datetime import datetime

def get_cursor():
    conn, cursor = get_connection()
    return conn, cursor

def create_shopping_list(user_id, text):
    raw = text.lower().replace('купить', '', 1).strip(': ').strip()
    items_raw = [item.strip() for item in raw.split(',') if item.strip()]
    if len(items_raw) == 1 and ' ' in items_raw[0]:
        items_raw = items_raw[0].split()
    
    items = [{"name": item, "checked": False} for item in items_raw]
    
    query = '''
        INSERT INTO shopping_lists (user_id, name, items, date) 
        VALUES (%s, %s, %s, %s)
    '''
    execute_query(query, (user_id, raw[:50], json.dumps(items, ensure_ascii=False), datetime.now().strftime("%Y-%m-%d %H:%M")))
    return True

def get_shopping_lists(user_id):
    query = 'SELECT id, name, items, date FROM shopping_lists WHERE user_id = %s ORDER BY id DESC'
    result = execute_query(query, (user_id,), fetch_all=True)
    return result if result else []

def update_shopping_item(list_id, user_id, item_index, checked):
    select_query = 'SELECT items FROM shopping_lists WHERE id = %s AND user_id = %s'
    row = execute_query(select_query, (list_id, user_id), fetch_one=True)
    
    if row:
        items = json.loads(row[0])
        if 0 <= item_index < len(items):
            items[item_index]["checked"] = checked
            update_query = 'UPDATE shopping_lists SET items = %s WHERE id = %s AND user_id = %s'
            execute_query(update_query, (json.dumps(items, ensure_ascii=False), list_id, user_id))
            return True
    return False

def delete_shopping_list(list_id, user_id):
    query = 'DELETE FROM shopping_lists WHERE id = %s AND user_id = %s'
    execute_query(query, (list_id, user_id))
    return True

def format_all_shopping_lists(user_id):
    """Форматирует ВСЕ списки покупок в ОДНОМ сообщении (упрощённо)"""
    lists = get_shopping_lists(user_id)
    if not lists:
        return None, None
    
    message = "🛒 *Мои покупки*\n\n"
    keyboard = telebot.types.InlineKeyboardMarkup(row_width=1)
    
    for list_id, name, items_json, date in lists:
        items = json.loads(items_json)
        checked_count = sum(1 for i in items if i["checked"])
        total_count = len(items)
        
        # Заголовок списка (только название)
        message += f"📋 *{name}*\n"
        
        # Пункты списка с галочками
        for i, item in enumerate(items):
            check = "✅" if item["checked"] else "⬜"
            message += f"{check} {item['name']}\n"
            # Кнопка с дублированием названия
            btn_text = f"{'🔄' if item['checked'] else '✅'} {item['name']}"
            keyboard.add(telebot.types.InlineKeyboardButton(
                btn_text, callback_data=f"shop_toggle_{list_id}_{i}"
            ))
        
        # Статистика и дата (компактно)
        message += f"📊 {checked_count}/{total_count}\n"
        message += "─" * 15 + "\n"
        
        # Кнопка удаления списка
        keyboard.add(telebot.types.InlineKeyboardButton(
            f"🗑 Удалить \"{name}\"", callback_data=f"shop_del_{list_id}"
        ))
        keyboard.row()
    
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
        
        select_query = 'SELECT items FROM shopping_lists WHERE id = %s AND user_id = %s'
        row = execute_query(select_query, (list_id, call.message.chat.id), fetch_one=True)
        
        if row:
            items = json.loads(row[0])
            if 0 <= item_index < len(items):
                new_status = not items[item_index]["checked"]
                update_shopping_item(list_id, call.message.chat.id, item_index, new_status)
                
                msg, keyboard = format_all_shopping_lists(call.message.chat.id)
                if msg:
                    bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                         parse_mode='Markdown', reply_markup=keyboard)
                    bot.answer_callback_query(call.id, "✅ Статус обновлён")
    
    @bot.callback_query_handler(func=lambda call: call.data.startswith('shop_del_'))
    def handle_delete_list(call):
        list_id = int(call.data.split('_')[2])
        if delete_shopping_list(list_id, call.message.chat.id):
            msg, keyboard = format_all_shopping_lists(call.message.chat.id)
            if msg:
                bot.edit_message_text(msg, call.message.chat.id, call.message.message_id,
                                     parse_mode='Markdown', reply_markup=keyboard)
            else:
                bot.edit_message_text("🛒 Все списки покупок удалены", 
                                     call.message.chat.id, call.message.message_id)
            bot.answer_callback_query(call.id, "🗑 Список удалён!")

print("📦 Модуль shopping.py загружен")
