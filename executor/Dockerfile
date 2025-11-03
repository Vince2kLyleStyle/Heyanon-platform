FROM python:3.11-slim
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
COPY copy_executor.py /app/copy_executor.py
RUN pip install --no-cache-dir requests prometheus_client
EXPOSE 9102
CMD ["python", "copy_executor.py"]
