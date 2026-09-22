FROM python:3.12-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 PORT=8501
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app.py .
COPY src ./src
COPY scripts/run_server.py ./scripts/run_server.py
COPY .streamlit/config.toml ./.streamlit/config.toml
COPY data/processed/avscope_mvp_domestic.parquet ./data/processed/avscope_mvp_domestic.parquet
COPY data/processed/dim_airports.parquet ./data/processed/dim_airports.parquet
RUN useradd --create-home avscope && chown -R avscope:avscope /app
USER avscope
EXPOSE 8501
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s CMD python -c "import os, urllib.request; urllib.request.urlopen('http://127.0.0.1:'+os.environ.get('PORT','8501')+'/_stcore/health', timeout=4)"
CMD ["python", "scripts/run_server.py"]
