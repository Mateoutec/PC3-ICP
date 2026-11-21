#!/usr/bin/env python3
"""
procesar_pedidos.py — Lee pedidos de la cola SQS 'cola-pedidos' en LocalStack,
los guarda en DynamoDB (tabla 'Pedidos') con estado='PROCESADO'
y elimina el mensaje de la cola.
"""

import json
import os
from decimal import Decimal

import boto3

# ---------------------------------------------------------------------------
# Configuración AWS (LocalStack)
# ---------------------------------------------------------------------------
ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")

QUEUE_NAME = "cola-pedidos"
TABLE_NAME = "Pedidos"


def _float_to_decimal(obj):
    """Convierte floats a Decimal recursivamente para DynamoDB."""
    if isinstance(obj, float):
        return Decimal(str(obj))
    if isinstance(obj, dict):
        return {k: _float_to_decimal(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [_float_to_decimal(i) for i in obj]
    return obj


def main():
    print("=" * 60)
    print("  PROCESADOR DE PEDIDOS SQS ➔ DynamoDB (LocalStack)")
    print("=" * 60)
    print(f"  Endpoint AWS   : {ENDPOINT_URL}")
    print(f"  Cola SQS       : {QUEUE_NAME}")
    print(f"  Tabla DynamoDB : {TABLE_NAME}")
    print("=" * 60)

    sqs = boto3.client(
        "sqs",
        endpoint_url=ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    dynamodb = boto3.resource(
        "dynamodb",
        endpoint_url=ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    try:
        resp = sqs.get_queue_url(QueueName=QUEUE_NAME)
        queue_url = resp["QueueUrl"]
    except Exception:
        print(f"\n  ✗ La cola '{QUEUE_NAME}' no existe en LocalStack. Ejecuta primero simular_pedidos.py")
        return

    table = dynamodb.Table(TABLE_NAME)
    try:
        table.load()
    except Exception:
        print(f"\n  ⚠  Tabla '{TABLE_NAME}' no encontrada. Creándola en DynamoDB...")
        table = dynamodb.create_table(
            TableName=TABLE_NAME,
            KeySchema=[{"AttributeName": "pedidoId", "KeyType": "HASH"}],
            AttributeDefinitions=[{"AttributeName": "pedidoId", "AttributeType": "S"}],
            BillingMode="PAY_PER_REQUEST",
        )
        table.wait_until_exists()

    print(f"\n  Leyendo mensajes desde: {queue_url}\n")

    procesados = 0
    rondas_vacias = 0
    MAX_RONDAS_VACIAS = 3

    while rondas_vacias < MAX_RONDAS_VACIAS:
        response = sqs.receive_message(
            QueueUrl=queue_url,
            MaxNumberOfMessages=10,
            WaitTimeSeconds=2,
        )

        messages = response.get("Messages", [])

        if not messages:
            rondas_vacias += 1
            continue

        rondas_vacias = 0

        for msg in messages:
            receipt_handle = msg["ReceiptHandle"]
            cuerpo = json.loads(msg["Body"])

            pedido_id = cuerpo.get("pedidoId", "sin-id")
            cliente   = cuerpo.get("cliente", "Desconocido")
            total     = cuerpo.get("total", 0.0)
            fecha     = cuerpo.get("fecha", "")

            # Guardar en DynamoDB con estado PROCESADO
            item = {
                "pedidoId": pedido_id,
                "cliente": cliente,
                "productos": json.dumps(cuerpo.get("productos", []), ensure_ascii=False),
                "total": Decimal(str(total)),
                "estado": "PROCESADO",
                "fecha": fecha,
            }

            try:
                table.put_item(Item=_float_to_decimal(item))

                # Eliminar de la cola SQS
                sqs.delete_message(
                    QueueUrl=queue_url,
                    ReceiptHandle=receipt_handle,
                )
                procesados += 1
                print(f"  [✓] Pedido {pedido_id[:8]}... | Cliente: {cliente:<20} | Total: ${total:>8.2f} ➔ DynamoDB [PROCESADO]")
            except Exception as e:
                print(f"  [✗] Error procesando pedido {pedido_id}: {e}")

    print("\n" + "=" * 60)
    print("  RESUMEN DE PROCESAMIENTO")
    print("=" * 60)
    print(f"  Total de pedidos procesados y guardados en DynamoDB : {procesados}")
    print("  Cola SQS vaciada correctamente.")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
