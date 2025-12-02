import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# --- КОНСТАНТЫ ---
NBK_RATES_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate="
OUTPUT_FILENAME = 'data/latest_rates.json'

def log_status(success: bool, message: str):
    """
    Фиксирует статус импорта данных с точной датой и временем.
    В реальном приложении это отправлялось бы в лог-файл или систему мониторинга (например, ElasticSearch).
    Здесь выводим в консоль (которую GitHub Actions фиксирует).
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "УСПЕШНО" if success else "НЕУСПЕШНО"
    print(f"[{timestamp}] Статус импорта: {status}. Сообщение: {message}")

def get_target_date() -> str:
    """
    Определяет дату для запроса. 
    
    НБК обычно публикует курсы на следующий рабочий день во второй половине дня.
    Чтобы увеличить шанс получить актуальный курс, запрашиваем:
    1. 'Завтрашний' курс (на следующий день). 
    2. Если 'завтрашний' курс не найден (нет данных), переходим к 'сегодняшнему'.
    
    Для простоты скрипта, запущенного ежедневно: 
    запрашиваем завтрашний день (в надежде, что он уже опубликован).
    """
    # Запрос на завтрашнюю дату (наиболее вероятный актуальный курс)
    target_date = datetime.now() + timedelta(days=1)
    return target_date.strftime("%d.%m.%Y")

def fetch_and_parse_rates(date_str: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
    """
    Загружает курсы валют НБК для указанной даты и парсит XML.
    
    Возвращает: (metadata, rates_list)
    metadata: Словарь с общими данными о файле (генератор, дата, описание).
    rates_list: Список словарей с данными о курсах.
    """
    url = f"{NBK_RATES_URL}{date_str}"
    
    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        log_status(False, f"Ошибка при HTTP-запросе {date_str}: {e}")
        return None, None

    try:
        # XML-декларация и первая строка игнорируются парсером ET.fromstring()
        root = ET.fromstring(response.content)
        rates_list = []
        
        # 2. Сбор метаданных
        metadata = {
            "date": root.find('date').text if root.find('date') is not None else date_str,
            "title": root.find('title').text,
            "generator": root.find('generator').text,
            "link": root.find('link').text,
            "description": root.find('description').text,
            "copyright": root.find('copyright').text,
            "retrieved_at": datetime.now().isoformat() # Время фактической загрузки
        }
        
        # Обработка случая "нет информации"
        if root.find('info') is not None and "информации нет" in root.find('info').text:
            log_status(False, f"Данные на {metadata['date']} еще не опубликованы.")
            return metadata, [] # Возвращаем метаданные, но пустой список курсов

        # 3. Сбор данных по валютам
        for item in root.findall('item'):
            rate_data = {
                # 3.1. Используем все поля
                "fullname": item.find('fullname').text,
                "code": item.find('title').text,             
                # description - это курс
                "rate": float(item.find('description').text),
                "quant": int(item.find('quant').text),
                "index": item.find('index').text if item.find('index') is not None else "NONE",
                "change": float(item.find('change').text) if item.find('change').text else 0.0
            }
            rates_list.append(rate_data)
        
        log_status(True, f"Успешно спарсено {len(rates_list)} курсов на дату {metadata['date']}.")
        return metadata, rates_list

    except ET.ParseError as e:
        log_status(False, f"Ошибка при парсинге XML: {e}")
        return None, None
    except Exception as e:
        log_status(False, f"Непредвиденная ошибка в процессе парсинга: {e}")
        return None, None

def save_rates_to_json(metadata: Dict, rates_data: List[Dict], filename: str):
    """
    Сохраняет метаданные и курсы в единый JSON-файл.
    """
    if not rates_data and "информации нет" in metadata.get('description', ''):
        log_status(False, f"Не сохраняем JSON, так как актуальные данные отсутствуют.")
        return

    # Структура для JSON-файла
    final_data = {
        "metadata": metadata,
        "rates": rates_data
    }
    
    try:
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(final_data, f, ensure_ascii=False, indent=4)
        log_status(True, f"Данные (включая метаданные) сохранены в {filename}. Дата курсов: {metadata['date']}.")
    except Exception as e:
        log_status(False, f"Ошибка при сохранении JSON-файла: {e}")


if __name__ == "__main__":
    target_date_str = get_target_date()
    
    metadata, current_rates = fetch_and_parse_rates(target_date_str)
    
    if metadata and current_rates is not None:
        save_rates_to_json(metadata, current_rates, OUTPUT_FILENAME)
    elif metadata and not current_rates:
        # Если метаданные есть, но курсов нет (случай "нет информации"),
        # нужно принять решение: сохранять старый файл или не обновлять его.
        # В данном случае, мы не вызываем save_rates_to_json, если курсов нет, 
        # чтобы сохранить предыдущий актуальный файл.
        log_status(True, "Обновление JSON-файла пропущено, так как данных на целевую дату нет.")
    else:
        log_status(False, "Не удалось получить метаданные. Обновление JSON-файла пропущено.")
