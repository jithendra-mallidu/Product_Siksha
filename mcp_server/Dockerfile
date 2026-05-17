FROM python:3.13-slim

WORKDIR /app

RUN pip install --no-cache-dir \
    mcp \
    google-generativeai \
    psycopg2-binary

COPY server.py .

EXPOSE 8080

CMD ["python", "server.py", "--http"]
