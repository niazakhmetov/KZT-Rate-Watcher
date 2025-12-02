import requests
import xml.etree.ElementTree as ET
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple

# --- КОНСТАНТЫ ---
NBK_RATES_URL = "https://nationalbank.kz/rss/get_rates.cfm?fdate="
OUTPUT_FILENAME = 'public/data/latest_rates.json'

def log_status(success: bool, message: str):
    """
    Фиксирует статус импорта данных с точной датой и временем.
    """
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    status = "УСПЕШНО" if success else "НЕУСПЕШНО"
    print(f"[{timestamp}] Статус импорта: {status}. Сообщение: {message}")

def get_target_date() -> str:
    """
    Определяет дату для запроса: **текущий день**.
    """
    # Запрос на ТЕКУЩУЮ дату
    target_date = datetime.now()
    return target_date.strftime("%d.%m.%Y")

def fetch_and_parse_rates(date_str: str) -> Tuple[Optional[Dict], Optional[List[Dict]]]:
    """
    Загружает курсы валют НБК для указанной даты и парсит XML.
    """
    url = f"{NBK_RATES_URL}{date_str}"
    
    # ... (код для запроса и обработки ошибок requests остается прежним) ...

    try:
        response = requests.get(url, timeout=15)
        response.raise_for_status() 
    except requests.exceptions.RequestException as e:
        log_status(False, f"Ошибка при HTTP-запросе {date_str}: {e}")
        return None, None
    
    try:
        root = ET.fromstring(response.content)
        rates_list = []
        
        metadata = {
            "date": root.find('date').text if root.find('date') is not None else date_str,
            "title": root.find('title').text,
            "generator": root.find('generator').text,
            "link": root.find('link').text,
            "description": root.find('description').text,
            "copyright": root.find('copyright').text,
            "retrieved_at": datetime.now().isoformat() # Время фактической загрузки
        }
        
        # 1. Проверка на сообщение "информации нет"
        info_tag = root.find('info')
        if info_tag is not None and "информации нет" in info_tag.text:
            log_status(False, f"Данные на {metadata['date']} еще не опубликованы.")
            return metadata, rates_list # rates_list будет пустым []

        # 2. Парсинг курсов
        for item in root.findall('item'):
            # ... (логика парсинга item остается прежней) ...
            fullname = item.find('fullname').text
            code = item.find('title').text
            rate_text = item.find('description').text
            quant_text = item.find('quant').text
            index_text = item.find('index').text
            change_text = item.find('change').text

            try:
                rate = float(rate_text) if rate_text else 0.0
                quant = int(quant_text) if quant_text else 1
                change = float(change_text) if change_text else 0.0
            except (ValueError, TypeError):
                continue

            rate_data = {
                "fullname": fullname.strip(),
                "code": code.strip(),
                "rate": rate,
                "quant": quant,
                "index": index_text.strip() if index_text else "NONE",
                "change": change
            }
            rates_list.append(rate_data)
        
        # Проверка, что были спарсены фактические курсы
        if len(rates_list) > 0:
            log_status(True, f"Успешно спарсено {len(rates_list)} курсов на дату {metadata['date']}.")
            return metadata, rates_list
        else:
            log_status(False, f"XML-файл не содержит курсов на {metadata['date']}.")
            return metadata, rates_list

    except ET.ParseError as e:
        log_status(False, f"Ошибка при парсинге XML: {e}")
        return None, None
    except Exception as e:
        log_status(False, f"Непредвиденная ошибка в процессе парсинга: {e}")
        return None, None

def save_rates_to_json(metadata: Dict, rates_data: List[Dict], filename: str):
    """
    Сохраняет метаданные и курсы в единый JSON-файл ТОЛЬКО ЕСЛИ ЕСТЬ ДАННЫЕ.
    """
    # 💥 ИСПРАВЛЕНИЕ: Строгая проверка на наличие курсов 💥
    if not rates_data or len(rates_data) == 0:
        log_status(True, f"Сохранение JSON-файла пропущено, так как список курсов пуст.")
        return

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
    
    # 💥 Упрощенная логика запуска 💥
    if metadata and current_rates is not None:
        save_rates_to_json(metadata, current_rates, OUTPUT_FILENAME)
    else:
        log_status(False, "Не удалось получить метаданные. Обновление JSON-файла пропущено.")
