FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY cloud_app.py cloud_store.py deepseek_recipe.py importer.py search_recipe.py url_recipe.py ./
RUN useradd --uid 10001 --create-home recipe
USER recipe
EXPOSE 8080
# One worker preserves candidate cache and AI request locks across requests.
CMD ["gunicorn", "--bind", "0.0.0.0:8080", "--workers", "1", "--threads", "4", "--timeout", "120", "--access-logfile", "-", "cloud_app:application"]
