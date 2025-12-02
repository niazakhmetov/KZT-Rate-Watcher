// --- КОНСТАНТЫ ---
// Путь к JSON-файлу с курсами (относительно корня GitHub Pages)
const RATES_JSON_URL = '/KZT-Rate-Watcher/data/latest_rates.json';

// Элементы DOM
const ratesBody = document.getElementById('rates-body');
const currentDateSpan = document.getElementById('current-date');
const searchInput = document.getElementById('search-input');

// Сохраненные данные (глобальная переменная для поиска)
let currentRatesData = [];

// Заголовки таблицы на русском языке (для data-label на мобильных)
const columnLabels = {
    'code': 'Код',
    'fullname': 'Валюта',
    'rate': 'Курс (за ед.)',
    'quant': 'Кол-во',
    'change': 'Изменение'
};

/**
 * 1. Загружает JSON-данные с курсами валют.
 * @returns {Promise<Object|null>} Обещание с данными или null в случае ошибки.
 */
async function fetchRates() {
    ratesBody.innerHTML = '<tr><td colspan="5">Загрузка данных...</td></tr>';
    
    try {
        const response = await fetch(RATES_JSON_URL);
        
        if (!response.ok) {
            // Если файл не найден (404) или другая ошибка HTTP
            throw new Error(`Ошибка загрузки данных: ${response.status} ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data || !data.rates || data.rates.length === 0) {
            throw new Error("Файл загружен, но данные о курсах отсутствуют.");
        }
        
        return data;

    } catch (error) {
        console.error('Ошибка при получении и обработке данных:', error);
        ratesBody.innerHTML = `<tr><td colspan="5" class="index-down">
                                ❌ Ошибка: Не удалось загрузить или обработать актуальные курсы. 
                                Проверьте файл ${RATES_JSON_URL}.
                                </td></tr>`;
        return null;
    }
}

/**
 * 2. Отображает курсы валют в HTML-таблице.
 * @param {Array<Object>} rates Список объектов с курсами.
 */
function displayRates(rates) {
    if (!rates || rates.length === 0) {
        ratesBody.innerHTML = '<tr><td colspan="5">Нет доступных курсов на выбранную дату.</td></tr>';
        return;
    }

    ratesBody.innerHTML = ''; // Очистка предыдущего содержимого
    
    rates.forEach(item => {
        const row = document.createElement('tr');
        
        // Форматирование изменения курса и определение класса
        const changeValue = parseFloat(item.change);
        let changeText = '';
        let changeClass = 'index-none';
        
        if (changeValue > 0) {
            changeText = `▲ +${changeValue.toFixed(4)}`;
            changeClass = 'index-up';
        } else if (changeValue < 0) {
            changeText = `▼ ${changeValue.toFixed(4)}`;
            changeClass = 'index-down';
        } else {
            changeText = '— 0.00';
            changeClass = 'index-none';
        }

        // 3. Создание и вставка ячеек
        row.innerHTML = `
            <td data-label="${columnLabels.code}">${item.code}</td>
            <td data-label="${columnLabels.fullname}">${item.fullname}</td>
            <td data-label="${columnLabels.rate}">${item.rate.toFixed(4)}</td>
            <td data-label="${columnLabels.quant}">${item.quant}</td>
            <td data-label="${columnLabels.change}" class="${changeClass}">${changeText}</td>
        `;
        
        ratesBody.appendChild(row);
    });
}

/**
 * 4. Устанавливает слушатель событий для поля поиска.
 */
function setupSearch() {
    // Делаем поиск нечувствительным к регистру и пробелам
    searchInput.addEventListener('keyup', () => {
        const query = searchInput.value.trim().toLowerCase();
        
        if (!currentRatesData || currentRatesData.length === 0) {
            return;
        }

        const filteredRates = currentRatesData.filter(rate => {
            // Поиск по коду (title) или полному названию (fullname)
            const matchesCode = rate.code.toLowerCase().includes(query);
            const matchesName = rate.fullname.toLowerCase().includes(query);
            return matchesCode || matchesName;
        });
        
        displayRates(filteredRates);
    });
}


/**
 * 5. Основная функция инициализации платформы.
 */
async function init() {
    const dataContainer = await fetchRates();
    
    if (dataContainer) {
        // Установка текущей даты из метаданных
        if (dataContainer.metadata && dataContainer.metadata.date) {
            currentDateSpan.textContent = dataContainer.metadata.date;
        }

        // Сохраняем полные данные для последующей фильтрации
        currentRatesData = dataContainer.rates;
        
        // Отображение всех курсов по умолчанию
        displayRates(currentRatesData);
        
        // Активация функции поиска
        setupSearch();
    }
}

// Запуск инициализации при загрузке страницы
document.addEventListener('DOMContentLoaded', init);
