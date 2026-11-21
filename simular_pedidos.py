#!/usr/bin/env python3
"""
simular_pedidos.py — Genera 100 pedidos simulados y los envía a la cola SQS 'cola-pedidos' en LocalStack.
"""

import json
import os
import random
import sys
import uuid
from datetime import datetime, timedelta

import boto3

# ---------------------------------------------------------------------------
# Configuración AWS (LocalStack)
# ---------------------------------------------------------------------------
ENDPOINT_URL = os.environ.get("AWS_ENDPOINT_URL", "http://localhost:4566")
AWS_REGION = os.environ.get("AWS_DEFAULT_REGION", "us-east-1")
AWS_ACCESS_KEY_ID = os.environ.get("AWS_ACCESS_KEY_ID", "test")
AWS_SECRET_ACCESS_KEY = os.environ.get("AWS_SECRET_ACCESS_KEY", "test")

QUEUE_NAME = "cola-pedidos"
TOTAL_PEDIDOS = 100

# ---------------------------------------------------------------------------
# Datos realistas para la simulación
# ---------------------------------------------------------------------------
NOMBRES = [
    "María García", "Juan Rodríguez", "Ana Martínez", "Carlos López",
    "Laura Hernández", "Pedro Sánchez", "Sofía Ramírez", "Diego Torres",
    "Valentina Flores", "Andrés Morales", "Camila Díaz", "Miguel Álvarez",
    "Isabella Ruiz", "Alejandro Jiménez", "Lucía Romero", "Daniel Vargas",
    "Gabriela Mendoza", "Fernando Castro", "Paula Ortiz", "Roberto Guerrero",
    "Elena Reyes", "Javier Moreno", "Mariana Peña", "Sebastián Medina",
    "Carolina Herrera", "Luis Aguilar", "Natalia Cruz", "Emilio Ramos",
    "Daniela Vega", "Tomás Navarro",
]

PRODUCTOS = [
    {"nombre": "Laptop Lenovo IdeaPad",   "precio": 899.99},
    {"nombre": "Monitor Samsung 27\"",     "precio": 349.99},
    {"nombre": "Teclado mecánico Logitech","precio": 129.99},
    {"nombre": "Mouse inalámbrico Razer",  "precio": 59.99},
    {"nombre": "Auriculares Sony WH-1000", "precio": 279.99},
    {"nombre": "Webcam Logitech C920",     "precio": 79.99},
    {"nombre": "Disco SSD Samsung 1TB",    "precio": 109.99},
    {"nombre": "Memoria USB 128GB",        "precio": 19.99},
    {"nombre": "Hub USB-C 7 puertos",      "precio": 44.99},
    {"nombre": "Cargador portátil 20000mAh","precio": 39.99},
    {"nombre": "Cable HDMI 2.1 3m",        "precio": 14.99},
    {"nombre": "Silla ergonómica",         "precio": 499.99},
    {"nombre": "Lámpara LED escritorio",   "precio": 34.99},
    {"nombre": "Alfombrilla gaming XL",    "precio": 24.99},
    {"nombre": "Soporte para laptop",      "precio": 54.99},
]


def generar_pedido(idx: int) -> dict:
    """Genera un pedido aleatorio con datos realistas."""
    num_items = random.randint(1, 5)
    items_elegidos = random.sample(PRODUCTOS, num_items)

    productos = []
    total = 0.0
    for item in items_elegidos:
        cantidad = random.randint(1, 3)
        subtotal = round(item["precio"] * cantidad, 2)
        total += subtotal
        productos.append({
            "nombre": item["nombre"],
            "precio": item["precio"],
            "cantidad": cantidad,
            "subtotal": subtotal,
        })

    dias_atras = random.randint(0, 30)
    fecha = (datetime.now() - timedelta(days=dias_atras)).strftime("%Y-%m-%d %H:%M:%S")

    return {
        "pedidoId": str(uuid.uuid4()),
        "cliente": random.choice(NOMBRES),
        "productos": productos,
        "total": round(total, 2),
        "fecha": fecha,
    }


def main():
    print("=" * 60)
    print("  SIMULADOR DE 100 PEDIDOS — LocalStack SQS (PC3)")
    print("=" * 60)
    print(f"  Endpoint AWS : {ENDPOINT_URL}")
    print(f"  Cola SQS     : {QUEUE_NAME}")
    print(f"  Total Pedidos: {TOTAL_PEDIDOS}")
    print("=" * 60)

    sqs = boto3.client(
        "sqs",
        endpoint_url=ENDPOINT_URL,
        region_name=AWS_REGION,
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
    )

    try:
        resp = sqs.get_queue_url(QueueName=QUEUE_NAME)
        queue_url = resp["QueueUrl"]
    except Exception:
        print(f"\n  ⚠  Cola '{QUEUE_NAME}' no encontrada. Creándola en LocalStack...")
        resp = sqs.create_queue(QueueName=QUEUE_NAME)
        queue_url = resp["QueueUrl"]

    print(f"\n  Enviando pedidos a: {queue_url}\n")

    enviados = 0
    errores = 0

    for i in range(1, TOTAL_PEDIDOS + 1):
        pedido = generar_pedido(i)
        cuerpo = json.dumps(pedido, ensure_ascii=False)

        try:
            sqs.send_message(
                QueueUrl=queue_url,
                MessageBody=cuerpo,
            )
            enviados += 1
        except Exception as e:
            errores += 1
            print(f"\n  ✗ Error al enviar pedido #{i}: {e}")

        # Barra de progreso visual en consola
        progreso = int((i / TOTAL_PEDIDOS) * 40)
        barra = "█" * progreso + "░" * (40 - progreso)
        porcentaje = (i / TOTAL_PEDIDOS) * 100
        sys.stdout.write(f"\r  [{barra}] {porcentaje:5.1f}% ({i}/{TOTAL_PEDIDOS})")
        sys.stdout.flush()

    print("\n\n" + "=" * 60)
    print("  RESUMEN DE SIMULACIÓN")
    print("=" * 60)
    print(f"  Pedidos generados y enviados con éxito : {enviados}")
    print(f"  Errores                               : {errores}")

    try:
        attrs = sqs.get_queue_attributes(
            QueueUrl=queue_url,
            AttributeNames=["ApproximateNumberOfMessages"],
        )
        n_mensajes = attrs.get("Attributes", {}).get("ApproximateNumberOfMessages", "?")
        print(f"  Mensajes disponibles en cola SQS       : {n_mensajes}")
    except Exception:
        pass

    print("=" * 60)
    print("  ✓ Simulación completada con éxito en LocalStack.\n")


if __name__ == "__main__":
    main()
