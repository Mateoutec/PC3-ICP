"""
init_data.py – Inicialización de recursos AWS en LocalStack y carga de datos iniciales.
Crea tablas en DynamoDB, bucket en S3 y cola en SQS.
"""

import json
import os
import boto3
from decimal import Decimal

AWS_ENDPOINT_URL = os.environ.get('AWS_ENDPOINT_URL', 'http://localhost:4566')
AWS_REGION = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
AWS_ACCESS_KEY_ID = os.environ.get('AWS_ACCESS_KEY_ID', 'test')
AWS_SECRET_ACCESS_KEY = os.environ.get('AWS_SECRET_ACCESS_KEY', 'test')

AWS_KWARGS = dict(
    endpoint_url=AWS_ENDPOINT_URL,
    region_name=AWS_REGION,
    aws_access_key_id=AWS_ACCESS_KEY_ID,
    aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
)

S3_BUCKET = 'tienda-imagenes'

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def create_table_if_not_exists(dynamodb_client, table_name, key_schema, attr_defs):
    existing = dynamodb_client.list_tables()['TableNames']
    if table_name in existing:
        print(f'  Tabla "{table_name}" ya existe en LocalStack, omitiendo.')
        return
    dynamodb_client.create_table(
        TableName=table_name,
        KeySchema=key_schema,
        AttributeDefinitions=attr_defs,
        BillingMode='PAY_PER_REQUEST',
    )
    print(f'  Tabla "{table_name}" creada en DynamoDB (LocalStack).')


def generate_svg(label, color):
    """Genera un SVG simple para productos."""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
        f'<rect width="400" height="300" rx="16" fill="{color}"/>'
        f'<text x="200" y="155" font-size="28" fill="white" '
        f'text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-weight="bold">{label}</text></svg>'
    )


def generate_avatar_svg(name, color="#4f46e5"):
    """Genera un avatar SVG para usuarios (S3)."""
    initials = "".join([part[0].upper() for part in name.split()[:2]]) or "AD"
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="200" height="200">'
        f'<circle cx="100" cy="100" r="95" fill="{color}"/>'
        f'<text x="100" y="115" font-size="64" fill="white" '
        f'text-anchor="middle" font-family="Arial,sans-serif" '
        f'font-weight="bold">{initials}</text></svg>'
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    print(f"Conectando a LocalStack en: {AWS_ENDPOINT_URL} ({AWS_REGION})")
    dynamo = boto3.client('dynamodb', **AWS_KWARGS)
    dynamo_res = boto3.resource('dynamodb', **AWS_KWARGS)
    s3 = boto3.client('s3', **AWS_KWARGS)
    sqs = boto3.client('sqs', **AWS_KWARGS)

    # -- DynamoDB tables -----------------------------------------------------
    print('[1/4] Creando tablas DynamoDB en LocalStack...')
    create_table_if_not_exists(
        dynamo, 'Productos',
        [{'AttributeName': 'productoId', 'KeyType': 'HASH'}],
        [{'AttributeName': 'productoId', 'AttributeType': 'S'}],
    )
    create_table_if_not_exists(
        dynamo, 'Pedidos',
        [{'AttributeName': 'pedidoId', 'KeyType': 'HASH'}],
        [{'AttributeName': 'pedidoId', 'AttributeType': 'S'}],
    )

    # -- S3 bucket -----------------------------------------------------------
    print(f'[2/4] Creando bucket S3 "{S3_BUCKET}" en LocalStack...')
    try:
        s3.create_bucket(Bucket=S3_BUCKET)
        print('  Bucket S3 creado con éxito.')
    except Exception as e:
        if 'BucketAlreadyOwnedByYou' in str(e) or 'BucketAlreadyExists' in str(e):
            print('  Bucket S3 ya existe, omitiendo.')
        else:
            raise

    # Subir imagen de perfil de usuario (Admin) a S3 (Requisito PC3: Imágenes de usuario en S3)
    admin_avatar = generate_avatar_svg("Admin Usuario", "#4f46e5")
    s3.put_object(
        Bucket=S3_BUCKET,
        Key='usuarios/admin.svg',
        Body=admin_avatar.encode(),
        ContentType='image/svg+xml',
    )
    print('  ✓ Avatar de usuario administrador guardado en S3: usuarios/admin.svg')

    # -- SQS queue -----------------------------------------------------------
    print('[3/4] Creando cola SQS "cola-pedidos" en LocalStack...')
    try:
        sqs.create_queue(QueueName='cola-pedidos')
        print('  Cola SQS creada con éxito.')
    except Exception as e:
        if 'QueueAlreadyExists' in str(e):
            print('  Cola SQS ya existe, omitiendo.')
        else:
            raise

    # -- Seed products -------------------------------------------------------
    print('[4/4] Cargando catálogo inicial de productos con imágenes en S3...')

    products = [
        {
            'productoId': 'prod-001',
            'nombre': 'Laptop ProMax 15"',
            'precio': Decimal('1299.99'),
            'descripcion': 'Laptop ultradelgada con procesador de última generación, 16 GB RAM, 512 GB SSD.',
            'color': '#2563eb',
        },
        {
            'productoId': 'prod-002',
            'nombre': 'Auriculares Bluetooth',
            'precio': Decimal('79.99'),
            'descripcion': 'Auriculares inalámbricos con cancelación de ruido activa y 30 h de batería.',
            'color': '#7c3aed',
        },
        {
            'productoId': 'prod-003',
            'nombre': 'Monitor Curvo 27"',
            'precio': Decimal('449.50'),
            'descripcion': 'Monitor QHD 165 Hz con panel VA curvo, ideal para gaming y productividad.',
            'color': '#059669',
        },
        {
            'productoId': 'prod-004',
            'nombre': 'Teclado Mecánico RGB',
            'precio': Decimal('129.00'),
            'descripcion': 'Teclado mecánico con switches Cherry MX, retroiluminación RGB por tecla.',
            'color': '#dc2626',
        },
        {
            'productoId': 'prod-005',
            'nombre': 'Mouse Ergonómico',
            'precio': Decimal('59.99'),
            'descripcion': 'Mouse inalámbrico ergonómico con sensor de 16 000 DPI y carga rápida.',
            'color': '#ea580c',
        },
        {
            'productoId': 'prod-006',
            'nombre': 'Webcam 4K',
            'precio': Decimal('149.00'),
            'descripcion': 'Cámara web 4K con enfoque automático, micrófono dual y luz anular integrada.',
            'color': '#0891b2',
        },
        {
            'productoId': 'prod-007',
            'nombre': 'Tablet 10" WiFi',
            'precio': Decimal('349.99'),
            'descripcion': 'Tablet de 10 pulgadas con pantalla IPS, 128 GB de almacenamiento y stylus incluido.',
            'color': '#4f46e5',
        },
        {
            'productoId': 'prod-008',
            'nombre': 'Cargador USB-C 65 W',
            'precio': Decimal('39.99'),
            'descripcion': 'Cargador compacto GaN de 65 W con 2 puertos USB-C y 1 USB-A.',
            'color': '#be185d',
        },
    ]

    table = dynamo_res.Table('Productos')

    for p in products:
        svg = generate_svg(p['nombre'][:20], p['color'])
        key = f'productos/{p["productoId"]}.svg'
        s3.put_object(
            Bucket=S3_BUCKET,
            Key=key,
            Body=svg.encode(),
            ContentType='image/svg+xml',
        )
        imagen_url = f'/s3/{key}'

        table.put_item(Item={
            'productoId': p['productoId'],
            'nombre': p['nombre'],
            'precio': p['precio'],
            'descripcion': p['descripcion'],
            'imagen': imagen_url,
        })
        print(f'  ✓ {p["nombre"]}')

    print('\n¡Inicialización completada con éxito en LocalStack!')


if __name__ == '__main__':
    main()
