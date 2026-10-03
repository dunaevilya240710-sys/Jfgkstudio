# JFGK Studio

Flask-сайт JFGK Studio.

## Локальный запуск

```bash
pip install -r requirements.txt
python app.py
```

После запуска: http://127.0.0.1:5000

## Размещение

Для хостинга, который поддерживает Python/Flask, команда запуска:

```bash
gunicorn app:app
```

Переменная окружения `JFGK_SECRET_KEY` рекомендуется для постоянного секретного ключа.
Переменная `PORT` используется хостингом для номера порта.
