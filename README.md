# DocRouter (MVP, Family)
Локальный сервис для личного/семейного архива: загрузка через веб, локальный OCR, (опциональный) перевод, краткие заметки ИИ и раскладка по папкам.
Теперь с **подпапками по поставщику/сервису**: Amazon, REWE, Vodafone, Schule №…, и т.д.

## Категории и подпапки (bucket)
- Purchases/Invoices → YYYY/MM/**{vendor}**
- Family/Utilities → **{provider}**/YYYY/MM
- Subscriptions → **{service}**/YYYY/MM
- Personal/Education → **{school|kita}**/YYYY
- Activities → **{club}**/YYYY
- Travel → YYYY/**{trip}**
- Vehicle → **{plate}**
- Остальные без bucket (или General)

## Быстрый старт
```bash
sudo apt update && sudo apt install -y \
  tesseract-ocr tesseract-ocr-deu tesseract-ocr-eng tesseract-ocr-rus \
  ocrmypdf img2pdf poppler-utils imagemagick
cp .env.example .env
make up
```
Открой: http://localhost:8080
