# DocRouter

Сервис для сортировки и обработки документов через веб‑интерфейс.

## Запуск

DocRouter можно запускать в контейнере Docker или напрямую через Python. Скопируйте `env.example` в `.env`, затем выберите вариант запуска:

### Docker

```bash
docker compose up --build
```

### Python

Установите проект в режиме разработки и запустите сервер:

```bash
pip install -e .
python -m docrouter
# или через main.py
python main.py
# или через созданный скрипт
docrouter
```

После старта интерфейс будет доступен по адресу [http://localhost:8000](http://localhost:8000), где можно загружать, просматривать и скачивать документы.

## Установка Tesseract

Для распознавания текста DocRouter использует движок [Tesseract OCR](https://tesseract-ocr.github.io/). Если он не установлен, функции OCR будут недоступны. Если исполняемый файл Tesseract отсутствует в `PATH`, укажите его путь через переменную `TESSERACT_CMD`.

### Windows

Скачайте [установщик](https://github.com/UB-Mannheim/tesseract/wiki) и установите его в `C:\\Program Files\\Tesseract-OCR`. Затем добавьте путь к программе и языковым данным:

```powershell
setx PATH "$Env:PATH;C:\\Program Files\\Tesseract-OCR"
setx TESSDATA_PREFIX "C:\\Program Files\\Tesseract-OCR\\tessdata"
setx TESSERACT_CMD "C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

### Linux

Установите пакет из репозитория и укажите путь к данным:

```bash
sudo apt install tesseract-ocr tesseract-ocr-rus
export TESSDATA_PREFIX=/usr/share/tesseract-ocr/5/tessdata
export TESSERACT_CMD=/usr/bin/tesseract
```

### macOS

Установите через Homebrew и задайте переменные окружения:

```bash
brew install tesseract
export TESSDATA_PREFIX="$(brew --prefix)/share/tessdata"
```

В `.env` можно задать язык распознавания и путь к бинарнику:

```
TESSERACT_LANG=rus
# Linux
TESSERACT_CMD=/usr/bin/tesseract
# Windows
# TESSERACT_CMD="C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
```

## Настройка

Все настройки выполняются через веб‑интерфейс. При загрузке можно выбрать язык документа для корректного OCR.

Для документов без владельца используется папка с именем по умолчанию `Shared`. Изменить её можно через переменную окружения `GENERAL_FOLDER_NAME` в `.env`.

### Аутентификация

Сервис открыт — загрузка и скачивание файлов не требуют авторизации.

### Хранилище

Все метаданные сохраняются в базе SQLite (`web_app/db.sqlite`) и не пропадают между запусками, если база не сбрасывается.

### Подтверждение создания папок

При загрузке документ может потребовать создания новой иерархии папок. В этом
случае сервис возвращает статус `pending` и список отсутствующих директорий в
поле `missing`. После подтверждения пользователь может вызвать
`POST /files/{id}/finalize` с тем же списком и `{"confirm": true}`. Этот же
endpoint используется в интерфейсе просмотра файла для окончательного
подтверждения. Каталоги будут созданы, файл переместится в нужное место, а
статус записи сменится на `processed`. Если не подтверждать, файл остаётся во
временном каталоге со статусом `pending`.

## API

### Получение списка файлов

`GET /files` — возвращает список файлов. Если нужно принудительно пересканировать выходной каталог, добавьте параметр `?force=1`.

### Метаданные

Для каждого файла сохраняются метаданные. Помимо основных полей присутствуют:

- `summary` — краткая сводка по документу;
- `description` — произвольное описание.

### Просмотр текста

`GET /files/{id}/text` — возвращает полный извлечённый текст документа. В веб‑интерфейсе ссылка «текст» рядом с «json» открывает этот адрес в новой вкладке.

