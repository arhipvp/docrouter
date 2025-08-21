## План глобальной переработки

**Что сохраняем**:

- `file_utils.py`
- полезные функции `data_processing_common.py` (`sanitize_filename`, обход директорий)
- `output_filter.py`

**Что переписываем**:

- `main.py`
- `image_data_processing.py`
- `text_data_processing.py`
- логика построения пути в `data_processing_common.py`

**Первостепенные задачи**:

1. Централизованная конфигурация (`config.yml` + `.env`).
2. Новый конвейер в `main.py` (OCR, LLM, JSON, `dry-run`, `Unsorted`).
3. Построение пути и запись `.json` в отдельном модуле.
4. OCR и LLM в `image_data_processing.py`.
5. Заменить эвристики на LLM в `text_data_processing.py`.
6. Обработка ошибок/лимитов API и вывод в лог.

