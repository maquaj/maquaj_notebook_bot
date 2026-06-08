import telebot
from config import TOKEN
from database import init_db, get_connection
from utils import parse_datetime, extract_reminder_text
from datetime import datetime
import reminders
import notes
import shopping
import birthdays
import todo
import time

# Инициализация
bot = telebot.TeleBot(TOKEN)
init_db()

# Регистрируем обработчики из модулей
notes.register_handlers(bot)
shopping.register_handlers(bot)
birthdays.register_handlers(bot)
reminders.register_handlers(bot)
todo.register_handlers(bot)

# Запускаем фоновые проверки
reminders.start_reminder_checker(bot)
birthdays.start_birthday_checker(bot)

# ========== КНОПОЧНОЕ МЕНЮ ==========

@bot.message_handler(func=lambda m: m.text and m.text.lower() == 'меню')
def show_menu(message):
    keyboard = telebot.types.ReplyKeyboardMarkup(resize_keyboard=True, row_width=2)
    
    buttons = [
        "📝 Список дел",
        "🛒 Покупки", 
        "🎂 Дни рождения",
        "⏰ Напоминания",
        "📋 Задачи",
        "❌ Закрыть меню"
    ]
    
    keyboard.add(*buttons)
    
    bot.reply_to(message, 
                 "📱 *Главное меню*\n\n"
                 "Выберите нужный раздел:",
                 parse_mode='Markdown',
                 reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text and m.text == '❌ Закрыть меню')
def close_menu(message):
    remove_keyboard = telebot.types.ReplyKeyboardRemove()
    bot.reply_to(message, "🔒 Меню закрыто", reply_markup=remove_keyboard)

@bot.message_handler(func=lambda m: m.text and m.text == '📝 Список дел')
def menu_notes(message):
    notes.show_notes(message)

@bot.message_handler(func=lambda m: m.text and m.text == '🛒 Покупки')
def menu_shopping(message):
    lists = shopping.get_shopping_lists(message.chat.id)
    if not lists:
        bot.reply_to(message, "🛒 Нет списков покупок.\nСоздайте: *купить: хлеб, молоко*", parse_mode='Markdown')
        return
    
    for list_id, name, items, date in lists:
        msg, keyboard = shopping.format_shopping_list(list_id, name, items, date)
        bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text and m.text == '🎂 Дни рождения')
def menu_birthdays(message):
    msg, keyboard = birthdays.get_birthdays_list(message.chat.id)
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text and m.text == '⏰ Напоминания')
def menu_reminders(message):
    msg, keyboard = reminders.get_reminders_list(message.chat.id)
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

@bot.message_handler(func=lambda m: m.text and m.text == '📋 Задачи')
def menu_todo(message):
    tasks = todo.get_all_tasks(message.chat.id)
    msg, keyboard = todo.format_todo_list(tasks)
    bot.send_message(message.chat.id, msg, parse_mode='Markdown', reply_markup=keyboard)

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
                 "🧠 *Вторая память*\n\n"
                 "📝 *Просто текст* — сохраню как заметку\n"
                 "🛒 *купить: хлеб, молоко* — список покупок\n"
                 "🎂 *др Анна 15.03* — день рождения\n"
                 "⏰ *напомни купить хлеб завтра в 15:00* — напоминание\n"
                 "📋 *сделать задача* или `/todo` — список задач\n"
                 "📱 *меню* — открыть главное меню\n\n"
                 "/list — заметки\n"
                 "/shopping — списки покупок\n"
                 "/birthdays — дни рождения\n"
                 "/reminders — напоминания\n"
                 "/todo — задачи\n"
                 "/help — помощь",
                 parse_mode='Markdown')

# Команда помощи
@bot.message_handler(commands=['help', 'помощь'])
def show_help(message):
    bot.reply_to(message,
                 "📚 *Помощь по командам*\n\n"
                 "📝 *Заметки:* просто отправьте текст\n"
                 "🛒 *Покупки:* `купить: хлеб, молоко`\n"
                 "🎂 *Дни рождения:* `др Анна 15.03`\n"
                 "⏰ *Напоминания:* `напомни ... завтра в 15:00`\n"
                 "📋 *Задачи:* `сделать задача`\n"
                 "📱 *Меню:* напишите `меню`\n\n"
                 "/list или /список — заметки\n"
                 "/shopping или /покупки — покупки\n"
                 "/birthdays или /др — дни рождения\n"
                 "/reminders или /напомнить — напоминания\n"
                 "/todo или /задачи — задачи",
                 parse_mode='Markdown')

@bot.message_handler(content_types=['text'])
def handle_all_messages(message):
    text = message.text.strip()
    
    if text.startswith('/'):
        return
    
    # 1. Дни рождения
    if text.lower().startswith('др'):
        result = birthdays.parse_birthday(text)
        if result:
            name, day, month, year = result
            birthdays.add_birthday(message.chat.id, name, day, month, year)
            year_text = f" {year} г." if year else ""
            bot.reply_to(message, 
                         f"🎂 *Запомнил!*\nДень рождения *{name}* — {day:02d}.{month:02d}{year_text}\n"
                         f"Напомню в 9:00 утра в этот день! 🎉",
                         parse_mode='Markdown')
        else:
            bot.reply_to(message, "🤔 Не понял дату. Пример: `др Анна 15.03`", parse_mode='Markdown')
        return
    
    # 2. Списки покупок
    if text.lower().startswith('купить'):
        shopping.create_shopping_list(message.chat.id, text)
        bot.reply_to(message, "🛒 *Список покупок создан!*\n/shopping — чтобы посмотреть", parse_mode='Markdown')
        return
    
    # 3. Напоминания
    if text.lower().startswith('напомни'):
        try:
            remind_dt = parse_datetime(text)
            remind_text = extract_reminder_text(text)
            reminders.add_reminder(message.chat.id, remind_text, remind_dt)
            time_str = remind_dt.strftime("%d.%m.%Y в %H:%M")
            bot.reply_to(message,
                         f"⏰ *Напоминание установлено!*\n\n"
                         f"📝 {remind_text}\n"
                         f"🕐 Напомню {time_str}",
                         parse_mode='Markdown')
        except Exception as e:
            bot.reply_to(message, f"🤔 Не понял дату. Пример: `напомни купить хлеб завтра в 15:00`", 
                        parse_mode='Markdown')
        return
    
    # 4. Задачи (Todo)
    if text.lower().startswith('сделать'):
        task = text[7:].strip()
        if task:
            todo.add_task(message.chat.id, task)
            bot.reply_to(message, f"📋 *Добавлена задача!*\n\n{task}\n\n/todo — посмотреть список", 
                        parse_mode='Markdown')
        else:
            bot.reply_to(message, "📝 Что нужно сделать? Пример: `сделать купить хлеб`", parse_mode='Markdown')
        return
    
    # 5. Обычная заметка
    notes.add_note(message.chat.id, text)
    bot.reply_to(message, f"✅ Сохранил: {text[:50]}")

# ========== ОБРАБОТКА КНОПОК ==========

# Удаление напоминания из списка /reminders
@bot.callback_query_handler(func=lambda call: call.data.startswith('rem_del_'))
def handle_delete_reminder(call):
    rem_id = int(call.data.split('_')[2])
    if reminders.delete_reminder(rem_id, call.message.chat.id):
        bot.answer_callback_query(call.id, "⏰ Напоминание удалено!")
        bot.delete_message(call.message.chat.id, call.message.message_id)

# Кнопка "Я увидел" в напоминании
@bot.callback_query_handler(func=lambda call: call.data.startswith('rem_ack_'))
def handle_reminder_ack(call):
    rem_id = int(call.data.split('_')[2])
    reminders.mark_reminder_sent(rem_id)
    
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

# Кнопка "Добавить задачу" в todo
@bot.callback_query_handler(func=lambda call: call.data == 'todo_add_prompt')
def handle_todo_add_prompt(call):
    todo.set_waiting_for_task(call.message.chat.id)
    bot.send_message(call.message.chat.id, 
                    "📝 *Добавление задачи*\n\n"
                    "Напишите текст задачи одним сообщением:",
                    parse_mode='Markdown')
    bot.answer_callback_query(call.id)

# Обработчик ввода задачи после нажатия кнопки "Добавить задачу"
@bot.message_handler(func=lambda m: m.text and not m.text.startswith('/') and todo.is_waiting_for_task(m.chat.id))
def handle_task_input(message):
    task = message.text.strip()
    if task:
        todo.add_task(message.chat.id, task)
        bot.reply_to(message, f"✅ Добавлена задача: *{task}*\n\n/todo — посмотреть список", 
                    parse_mode='Markdown')
    else:
        bot.reply_to(message, "❌ Задача не может быть пустой")
    todo.clear_waiting_for_task(message.chat.id)

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🤖 Бот «Вторая память» запущен!")
    print("🛒 купить: хлеб, молоко")
    print("🎂 др Анна 15.03")
    print("⏰ напомни купить хлеб завтра в 15:00")
    print("📋 сделать задача")
    print("📱 меню — открыть меню")
    print("📝 Просто текст — заметка")
    print("⏳ Задержка 5 секунд перед запуском polling...")
    
    # Задержка для предотвращения конфликта экземпляров
    time.sleep(5)
    
    # Сброс вебхука (если был установлен)
    try:
        bot.remove_webhook()
        print("✅ Вебхук удалён")
    except Exception as e:
        print(f"⚠️ Ошибка удаления вебхука: {e}")
    
    print("🚀 Запуск polling...")
    
    # Бесконечный цикл с переподключением при ошибке
    while True:
        try:
            bot.infinity_polling(skip_pending=True, timeout=60, long_polling_timeout=60)
        except Exception as e:
            print(f"❌ Ошибка polling: {e}")
            print("🔄 Перезапуск через 10 секунд...")
            time.sleep(10)
