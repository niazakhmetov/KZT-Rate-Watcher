import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

# --- КОНСТАНТЫ ---
# URL-шаблон для запроса курсов НБК
NBK_RATES_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate="
# Путь для сохранения результирующего JSON-файла
OUTPUT_FILENAME = 'data/latest_rates.json'

def get_target_date() -> str:
    """
    Определяет дату, для которой нужно запросить курс.
    
    НБК обычно публикует курсы на следующий рабочий день.
    Для простоты и надежности в автоматическом скрипте, 
    запускаемом рано утром, запрашиваем курс на ТЕКУЩУЮ дату.
    Если курс на текущую дату еще не доступен, можно запросить вчерашний, 
    но чаще всего курс на ТЕКУЩУЮ дату публикуется заранее.
    
    Возвращает дату в формате 'ДД.ММ.ГГГГ'.
    """
    # Получаем текущую дату (на момент запуска скрипта)
    today = datetime.now()
    
    # Можно добавить логику, чтобы запросить "завтрашнюю" дату, 
    # если скрипт запускается после публикации (например, после 15:00).
    # Но для первой версии просто используем сегодняшнюю дату.
    target_date = today.strftime("%d.%m.%Y")
    
    return target_date

def fetch_and_parse_rates(date_str: str) -> Optional[List[Dict]]:
    """
    Загружает курсы валют НБК для указанной даты и парсит XML.
    date_str: Дата в формате 'ДД.ММ.ГГГГ'.
    
    Возвращает список словарей с данными о курсах или None в случае ошибки.
    """
    url = f"{NBK_RATES_URL}{date_str}"
    print(f"Запрос данных с НБК для даты: {date_str} по URL: {url}")
    
    try:
        # Устанавливаем таймаут, чтобы избежать зависания
        response = requests.get(url, timeout=15)
        # Проверяем статус код ответа
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        print(f"❌ Ошибка при выполнении HTTP-запроса: {e}")
        return None

    try:
        # Парсинг XML-содержимого
        root = ET.fromstring(response.content)
        rates_list = []
        
        # Получаем дату курса из самого XML-файла (это самая точная дата)
        rates_date = root.find('date').text if root.find('date') is not None else date_str

        for item in root.findall('item'):
            # Извлекаем данные из тегов <item>
            fullname = item.find('fullname').text
            code = item.find('title').text
            rate_text = item.find('description').text
            quant_text = item.find('quant').text
            index_text = item.find('index').text
            change_text = item.find('change').text

            # Обрабатываем возможные отсутствующие или пустые значения
            try:
                rate = float(rate_text) if rate_text else 0.0
                quant = int(quant_text) if quant_text else 1
                change = float(change_text) if change_text else 0.0
            except (ValueError, TypeError) as ve:
                print(f"⚠️ Ошибка конвертации данных для {code}: {ve}. Пропускаем.")
                continue

            rate_data = {
                "date": rates_date,
                "fullname": fullname.strip(),
                "code": code.strip(),
                "rate": rate,
                "quant": quant,
                "index": index_text.strip() if index_text else "NONE",
                "change": change
            }
            rates_list.append(rate_data)
        
        print(f"✅ Успешно спарсено {len(rates_list)} курсов.")
        return rates_list

    except ET.ParseError as e:
        print(f"❌ Ошибка при парсинге XML: {e}")
        return None
    except Exception as e:
        print(f"❌ Непредвиденная ошибка в процессе парсинга: {e}")
        return None

def save_rates_to_json(rates_data: List[Dict], filename: str):
    """
    Сохраняет список словарей с курсами в JSON-файл.
    """
    try:
        # Используем ensure_ascii=False для корректного сохранения кириллицы
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(rates_data, f, ensure_ascii=False, indent=4)
        print(f"✅ Данные успешно сохранены в файл: {filename}")
    except Exception as e:
        print(f"❌ Ошибка при сохранении JSON-файла: {e}")


if __name__ == "__main__":
    # Шаг 1: Получаем целевую дату
    target_date_str = get_target_date()
    
    # Шаг 2: Загружаем и парсим данные
    current_rates = fetch_and_parse_rates(target_date_str)
    
    if current_rates:
        # Шаг 3: Сохраняем результат в JSON-файл
        # Файл будет находиться в корневой директории репозитория
        # (или там, где его ожидает GitHub Action)
        save_rates_to_json(current_rates, OUTPUT_FILENAME)
    else:
        print("Операция завершена с ошибкой: данные не были получены или спарсены.")
