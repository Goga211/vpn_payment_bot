# syntax=docker/dockerfile:1

FROM python:3.12-slim

# .pyc не пишем, stdout не буферизуем — логи сразу видны в `docker logs`.
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

# Зависимости ставим первым слоём — кешируется, пока requirements.txt не меняется.
COPY requirements.txt .
RUN pip install -r requirements.txt

# Затем код бота (меняется чаще — отдельный слой).
COPY bot ./bot

# Непривилегированный пользователь: внутрь контейнера ничего не пишем, root не нужен.
RUN useradd --create-home --uid 10001 appuser
USER appuser

# Бот работает на long-polling: входящих портов нет, EXPOSE не требуется.
CMD ["python", "-m", "bot"]
