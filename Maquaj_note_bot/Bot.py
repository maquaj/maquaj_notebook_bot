import telebot
from config import TELEGRAM_TOKEN
from database import init_db, get_connection
from utils import parse_datetime, extract_reminder_text
from datetime import datetime
import reminders
import notes
import shopping
import birthdays
import todo

# Инициализация
bot = telebot.TeleBot(TELEGRAM_TOKEN)
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

# ========== ГЛАВНЫЙ ОБРАБОТЧИК ==========
# Команда /start (уже есть, оставляем)
@bot.message_handler(commands=['start'])
def send_welcome(message):
    bot.reply_to(message, 
                 "🧠 *Вторая память*\n\n"
                 "📝 *Просто текст* — сохраню как заметку\n"
                 "🛒 *купить: хлеб, молоко* — список покупок\n"
                 "🎂 *др Анна 15.03* — день рождения\n"
                 "⏰ *напомни купить хлеб завтра в 15:00* — напоминание\n"
                 "📋 *сделать задача* или `/todo` — список задач\n\n"
                 "🇬🇧 *Команды:*\n"
                 "/list или /список — заметки\n"
                 "/shopping или /покупки — списки покупок\n"
                 "/birthdays или /др — дни рождения\n"
                 "/reminders или /напомнить — напоминания\n"
                 "/todo или /задачи — список задач\n"
                 "/check или /проверка — отладка",
                 parse_mode='Markdown')

# ========== КОМАНДЫ С РУССКИМИ АЛЬТЕРНАТИВАМИ ==========

# /list и /список
@bot.message_handler(commands=['list', 'список'])
def show_notes_command(message):
    notes.show_notes(message)

# /shopping и /покупки
@bot.message_handler(commands=['shopping', 'покупки'])
def show_shopping_command(message):
    shopping.show_shopping_lists(message)

# /birthdays и /др
@bot.message_handler(commands=['birthdays', 'др'])
def show_birthdays_command(message):
    birthdays.show_birthdays(message)

# /reminders и /напомнить
@bot.message_handler(commands=['reminders', 'напомнить'])
def show_reminders_command(message):
    reminders.show_reminders(message)

# /todo и /задачи
@bot.message_handler(commands=['todo', 'задачи'])
def show_todo_command(message):
    todo.show_todo(message)

# /check и /проверка
@bot.message_handler(commands=['check', 'проверка'])
def check_reminders_command(message):
    pending = reminders.get_pending_reminders()
    if pending:
        bot.reply_to(message, f"📋 Найдено {len(pending)} ожидающих напоминаний.")
        for rem_id, user_id, text, remind_time in pending:
            dt = datetime.fromisoformat(remind_time)
            bot.send_message(message.chat.id, f"⏰ *Ожидает:* {text} (на {dt.strftime('%d.%m.%Y %H:%M')})",
                           parse_mode='Markdown')
    else:
        bot.reply_to(message, "📭 Нет ожидающих напоминаний")

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

# ========== ДОПОЛНИТЕЛЬНЫЕ КОМАНДЫ ==========

# Команда помощи (на русском)
@bot.message_handler(commands=['help', 'помощь'])
def show_help(message):
    bot.reply_to(message,
                 "📚 *Помощь по командам*\n\n"
                 "🎂 *Дни рождения:*\n"
                 "`др Анна 15.03` — добавить\n"
                 "`/др` или `/birthdays` — список\n\n"
                 "🛒 *Покупки:*\n"
                 "`купить: хлеб, молоко` — добавить\n"
                 "`/покупки` или `/shopping` — список\n\n"
                 "⏰ *Напоминания:*\n"
                 "`напомни ... завтра в 15:00` — добавить\n"
                 "`/напомнить` или `/reminders` — список\n\n"
                 "📋 *Задачи:*\n"
                 "`сделать купить хлеб` — добавить\n"
                 "`/задачи` или `/todo` — список\n\n"
                 "📝 *Заметки:*\n"
                 "`Просто текст` — добавить\n"
                 "`/список` или `/list` — посмотреть\n\n"
                 "🔍 *Отладка:*\n"
                 "`/проверка` или `/check` — проверить напоминания",
                 parse_mode='Markdown')

# ========== ЗАПУСК ==========
if __name__ == "__main__":
    print("🤖 Бот «Вторая память» запущен!")
    print("🛒 купить: хлеб, молоко")
    print("🎂 др Анна 15.03")
    print("⏰ напомни купить хлеб завтра в 15:00")
    print("📋 сделать задача")
    print("📝 Просто текст — заметка")
    print("\n🇷🇺 Русские команды:")
    print("/список, /покупки, /др, /напомнить, /задачи, /помощь")
    print("🇬🇧 Английские команды:")
    print("/list, /shopping, /birthdays, /reminders, /todo, /help")
    bot.infinity_polling()
