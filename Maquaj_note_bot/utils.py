import re
from datetime import datetime, timedelta

def parse_datetime(text):
    """
    Парсит текст и возвращает datetime для напоминания.
    Примеры:
        "напомни купить хлеб завтра в 15:00"
        "напомни позвонить маме в пятницу 14:30"
        "напомни оплатить налоги 25.06 в 18:00"
        "напомни сделать зарядку через 2 часа"
        "напомни в 15:30"  # сегодня в 15:30
        "напомни в 17-22"  # сегодня в 17:22
    """
    now = datetime.now()
    
    # Убираем слово "напомни" из начала (регистронезависимо)
    clean = re.sub(r'^напомни\s*', '', text.lower(), flags=re.IGNORECASE)
    clean = re.sub(r'^в\s*', '', clean)  # убираем "в" в начале
    
    # Параметры по умолчанию
    target_time = None
    target_date = None
    relative_minutes = None
    
    # 1. Сначала ищем относительное время "через X минут/часов"
    relative_pattern = r'через\s+(\d+)\s*(минут|минуты|минуту|час|часов|часа)'
    relative_match = re.search(relative_pattern, clean)
    if relative_match:
        value = int(relative_match.group(1))
        unit = relative_match.group(2)
        if unit.startswith('час'):
            relative_minutes = value * 60
        else:
            relative_minutes = value
        clean = re.sub(relative_pattern, '', clean)
    
    # 2. Ищем время (15:00, 15-00, 15.00, 15ч00м)
    # Важно: не путаем с датами (25.06) — время ищем строже
    time_pattern = r'(\d{1,2})[:\.\-ч](\d{2})'
    time_match = re.search(time_pattern, clean)
    if time_match:
        hour = int(time_match.group(1))
        minute = int(time_match.group(2))
        # Проверяем корректность времени
        if 0 <= hour <= 23 and 0 <= minute <= 59:
            target_time = (hour, minute)
            # Удаляем найденное время из строки, чтобы не мешать поиску даты
            clean = re.sub(time_pattern, '', clean, count=1)
    
    # 3. Ищем время без минут (только час: "в 17")
    hour_pattern = r'(?<!\d)(\d{1,2})(?:\s*час(?:ов|а)?)?\s*(?:$|,| )'
    # Но только если нет минут в остатке
    if target_time is None:
        hour_match = re.search(r'(\d{1,2})\s*$', clean)
        if hour_match and not re.search(r'\d{2}', clean.replace(hour_match.group(0), '')):
            hour = int(hour_match.group(1))
            if 0 <= hour <= 23:
                target_time = (hour, 0)
                clean = re.sub(hour_match.group(0), '', clean)
    
    # 4. Ищем относительные даты
    if 'сегодня' in clean:
        target_date = now.date()
    elif 'завтра' in clean:
        target_date = now.date() + timedelta(days=1)
    elif 'послезавтра' in clean:
        target_date = now.date() + timedelta(days=2)
    else:
        # Дни недели
        weekdays = {
            'понедельник': 0, 'пн': 0,
            'вторник': 1, 'вт': 1,
            'среда': 2, 'ср': 2,
            'четверг': 3, 'чт': 3,
            'пятница': 4, 'пт': 4,
            'суббота': 5, 'сб': 5,
            'воскресенье': 6, 'вс': 6
        }
        for day_name, day_num in weekdays.items():
            if day_name in clean:
                days_ahead = (day_num - now.weekday() + 7) % 7
                if days_ahead == 0:
                    days_ahead = 7
                target_date = now.date() + timedelta(days=days_ahead)
                break
        
        # Конкретная дата: 25.06, 25-06, 25/06
        # Осторожно: не путаем с временем 15-22 (где 22 — минуты)
        if not target_date:
            # Ищем дату только если после неё нет похожего на время
            date_pattern = r'(\d{1,2})[\.\-/](\d{1,2})(?:[\.\-/](\d{2,4}))?'
            date_match = re.search(date_pattern, clean)
            if date_match:
                day = int(date_match.group(1))
                month = int(date_match.group(2))
                year = None
                if date_match.group(3):
                    year = int(date_match.group(3))
                    if year < 100:
                        year += 2000
                else:
                    year = now.year
                
                # Проверяем, что это действительно дата, а не время
                # Если день > 31 или месяц > 12 — это не дата
                if day <= 31 and month <= 12:
                    # Если месяц уже прошёл в этом году — берём следующий год
                    if month < now.month or (month == now.month and day < now.day):
                        year = now.year + 1
                    try:
                        target_date = datetime(year, month, day).date()
                        clean = re.sub(date_pattern, '', clean, count=1)
                    except:
                        pass
    
    # 5. Если дата не найдена — сегодня
    if target_date is None and relative_minutes is None:
        target_date = now.date()
    
    # 6. Если время не найдено — 09:00
    if target_time is None:
        target_time = (9, 0)
    
    # 7. Формируем результат
    if relative_minutes is not None:
        # Относительное время: через X минут/часов
        result = now + timedelta(minutes=relative_minutes)
    else:
        # Абсолютное время
        try:
            result = datetime(target_date.year, target_date.month, target_date.day, 
                              target_time[0], target_time[1])
            # Если время уже прошло сегодня — переносим на завтра
            if result < now and target_date == now.date():
                result += timedelta(days=1)
        except Exception as e:
            # Если ошибка (например, 31 февраля) — ставим завтра
            result = now + timedelta(days=1)
            result = result.replace(hour=target_time[0], minute=target_time[1])
    
    return result

def extract_reminder_text(text):
    """Извлекает текст напоминания (всё, что идёт после даты/времени)"""
    # Убираем слово "напомни"
    clean = re.sub(r'^напомни\s*', '', text, flags=re.IGNORECASE)
    clean = re.sub(r'^в\s*', '', clean)
    
    # Убираем все найденные паттерны дат/времён
    patterns = [
        r'через\s+\d+\s*(минут|минуты|минуту|час|часов|часа)',
        r'\d{1,2}[:\.\-ч]\d{2}',  # время 15:30
        r'сегодня|завтра|послезавтра',
        r'понедельник|вторник|среда|четверг|пятница|суббота|воскресенье',
        r'пн|вт|ср|чт|пт|сб|вс',
        r'\d{1,2}[\.\-/]\d{1,2}(?:[\.\-/]\d{2,4})?'  # дата 25.06
    ]
    
    for pattern in patterns:
        clean = re.sub(pattern, '', clean, flags=re.IGNORECASE)
    
    # Убираем лишние пробелы и слова-заглушки
    clean = re.sub(r'\s+', ' ', clean).strip()
    clean = re.sub(r'^в\s+', '', clean)
    
    return clean if clean else "Напоминание"

# Тестовая функция (можно удалить после проверки)
if __name__ == "__main__":
    test_commands = [
        "напомни в 17-22",
        "напомни в 15:30",
        "напомни завтра в 10:00",
        "напомни через 5 минут",
        "напомни в пятницу 14:00",
    ]
    for cmd in test_commands:
        dt = parse_datetime(cmd)
        text = extract_reminder_text(cmd)
        print(f"{cmd} -> {dt.strftime('%d.%m.%Y %H:%M')} | текст: '{text}'")