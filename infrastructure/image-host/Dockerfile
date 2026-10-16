FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r requirements.txt && useradd --create-home --uid 10001 imagehost && mkdir -p /data/images && chown -R imagehost:imagehost /data
COPY infrastructure/image-host/server.py /app/server.py
USER imagehost
ENV IMAGE_DIRECTORY=/data/images PORT=8080
EXPOSE 8080
CMD ["python", "-B", "server.py"]
