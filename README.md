# Markify Bot 🎨

[![Python](https://img.shields.io/badge/Python-3.12%2B-blue.svg?logo=python&logoColor=white)](https://python.org)
[![aiogram](https://img.shields.io/badge/aiogram-3.x-2CA5E0.svg?logo=telegram&logoColor=white)](https://github.com/aiogram/aiogram)
[![Pillow](https://img.shields.io/badge/Pillow-PIL-green.svg)](https://python-pillow.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg?logo=docker&logoColor=white)](https://www.docker.com/)

**Markify Bot** — это Telegram-бот для автоматического брендирования фотографий: наложение логотипа в правый нижний угол с адаптивным масштабированием и опциональная автоцветокоррекция.

---

## ✨ Ключевые возможности

- 📐 **Адаптивное масштабирование водяного знака**:
  - Логотип **всегда сохраняет пропорции** и выглядит визуально одинаково независимо от разрешения и формата снимка (4K, Full HD, вертикальные Stories/Reels 9:16, горизонтальные 16:9 или квадратные посты 1:1).
  - Располагается строго в **правом нижнем углу** с пропорциональным безопасным отступом.
- 🪄 **Интеллектуальная автоцветокоррекция**:
  - Автоматическая балансировка динамического диапазона (`autocontrast`), легкое усиление сочности и резкости.
  - Можно включать и выключать в один клик в настройках.
- 🛡️ **Конфиденциальность (Zero-Storage)**:
  - Обрабатываемые фото пользователей **не сохраняются на диск сервера**.
  - Весь пайплайн выполняется в потоках оперативной памяти (`BytesIO`) и удаляется сразу после отправки.
- 👤 **Пользовательские логотипы**:
  - Каждый пользователь может загрузить свой PNG-логотип (с прозрачным фоном).
  - Бот автоматически генерирует мгновенное тестовое превью.
  - При отсутствии своего логотипа используется стильный базовый водяной знак.
- ⚙️ **Гибкое управление через инлайн-меню**:
  - Выбор масштаба логотипа: `Маленький (14%)`, `Средний (18%)`, `Большой (25%)`.
  - Регулировка прозрачности логотипа: `100%`, `80%`, `60%`.
  - Поддержка отправки как обычных сжатых фото, так и несжатых файлов-документов.

---

## 📁 Структура репозитория

```
markify-bot/
├── .env.example              # Шаблон конфигурации окружения
├── .gitignore                 # Игнорируемые файлы Git
├── Dockerfile                 # Docker образ для развертывания
├── docker-compose.yml         # Манифест Docker Compose
├── requirements.txt           # Зависимости Python
├── README.md                  # Документация проекта
├── assets/                    # Статические ресурсы (дефолтный логотип)
│   └── default_logo.png
├── data/                      # Хранилище данных (не коммитится в Git)
│   ├── markify.db             # База данных SQLite
│   └── logos/                 # Пользовательские логотипы
├── src/                       # Исходный код приложения
│   ├── config.py              # Загрузка настроек окружения (pydantic-settings)
│   ├── main.py                # Точка входа, регистрация роутеров и запуск бота
│   ├── database/              # Асинхронная БД (aiosqlite)
│   │   ├── db.py
│   │   └── models.py
│   ├── handlers/              # Обработчики Telegram
│   │   ├── common.py          # /start, /help, навигация
│   │   ├── settings.py        # Меню настроек, FSM загрузки логотипа
│   │   └── image.py           # Пайплайн обработки фото и документов
│   ├── keyboards/             # Инлайн-клавиатуры
│   │   └── inline.py
│   └── services/              # Ядро обработки изображений
│       ├── color_correction.py
│       └── watermark.py
└── tests/                     # Автоматические юнит-тесты
    ├── test_database.py
    └── test_watermark.py
```

---

## 🚀 Быстрый старт

### 1. Получение токена бота
1. Откройте [@BotFather](https://t.me/BotFather) в Telegram.
2. Отправьте команду `/newbot` и следуйте инструкциям.
3. Скопируйте полученный API-токен.

---

### Вариант A: Запуск через Docker (Рекомендуется)

1. Клонируйте репозиторий:
   ```bash
   git clone https://github.com/your-username/markify-bot.git
   cd markify-bot
   ```

2. Создайте файл `.env`:
   ```bash
   cp .env.example .env
   ```
   Укажите ваш токен в переменной `BOT_TOKEN`:
   ```env
   BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyz
   ```

3. Запустите контейнер:
   ```bash
   docker compose up -d --build
   ```

4. Просмотр логов:
   ```bash
   docker compose logs -f
   ```

---

### Вариант B: Локальный запуск (Python 3.12+)

1. Подготовьте виртуальное окружение:
   ```bash
   python -m venv .venv
   ```

   Активируйте окружение:
   - **Windows (PowerShell):**
     ```powershell
     .venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source .venv/bin/activate
     ```

2. Установите зависимости:
   ```bash
   pip install -r requirements.txt
   ```

3. Настройте конфигурацию:
   ```bash
   cp .env.example .env
   ```
   Впишите ваш `BOT_TOKEN` в `.env`.

4. Запустите бота:
   ```bash
   python -m src.main
   ```

---

## 🧪 Запуск тестов

Проект покрыт автоматическими юнит-тестами для проверки корректности алгоритмов масштабирования, EXIF-ориентации и базы данных:

```bash
python -m unittest discover tests
```

---

## 📜 Лицензия

Проект распространяется под лицензией MIT.
