#!/bin/bash
set -e

echo "⏳ Esperando a que LocalStack esté listo..."

# Wait for localstack to be ready
TARGET_URL="${AWS_ENDPOINT_URL:-http://localstack:4566}"
MAX_RETRIES=40
RETRY_COUNT=0

until curl -s "${TARGET_URL}/_localstack/health" | grep -q "\"status\": \"running\"" || curl -s "${TARGET_URL}/_localstack/health" > /dev/null 2>&1 || curl -s "${TARGET_URL}" > /dev/null 2>&1; do
  RETRY_COUNT=$((RETRY_COUNT + 1))
  if [ "$RETRY_COUNT" -ge "$MAX_RETRIES" ]; then
    echo "❌ LocalStack no respondió después de $MAX_RETRIES intentos. Abortando."
    exit 1
  fi
  echo "  Intento $RETRY_COUNT/$MAX_RETRIES - LocalStack inicializando, reintentando en 3s..."
  sleep 3
done

echo "✅ LocalStack está listo y operativo!"

# Initialize AWS resources (DynamoDB tables, S3 buckets, SQS queues, seed data)
echo "🔧 Inicializando recursos AWS en LocalStack (tablas DynamoDB, bucket S3, cola SQS)..."
python init_data.py
echo "✅ Recursos AWS inicializados correctamente."

# Start the Flask application
echo "🚀 Iniciando la aplicación Flask en http://0.0.0.0:5000..."
exec python app.py
