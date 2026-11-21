"""
PC3 - Cognitive Computing: Aplicación de Tienda Virtual
Flask web app conectada a servicios emulados de AWS en LocalStack (DynamoDB, S3, SQS).
"""

import io
import json
import os
import uuid
from datetime import datetime
from decimal import Decimal
from functools import wraps

import boto3
from flask import (
    Flask, render_template, request, redirect,
    url_for, session, flash, Response
)

app = Flask(__name__)
app.secret_key = 'pc3-tienda-secret-key-2024'

# ---------------------------------------------------------------------------
# AWS helpers – Conexión a LocalStack (puerto 4566)
# ---------------------------------------------------------------------------
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

def get_dynamodb():
    return boto3.resource('dynamodb', **AWS_KWARGS)

def get_s3():
    return boto3.client('s3', **AWS_KWARGS)

def get_sqs():
    return boto3.client('sqs', **AWS_KWARGS)


# ---------------------------------------------------------------------------
# Auth helpers
# ---------------------------------------------------------------------------
ADMIN_USER = 'admin'
ADMIN_PASS = 'admin123'

def login_required(f):
    """Decorador que restringe el acceso al perfil de administrador."""
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('logged_in'):
            flash('Debes iniciar sesión para acceder a esta página.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated


# ---------------------------------------------------------------------------
# Context processor – Carrito y avatar disponibles en todos los templates
# ---------------------------------------------------------------------------
@app.context_processor
def inject_globals():
    cart = session.get('carrito', [])
    cart_count = sum(item.get('cantidad', 1) for item in cart)
    user_avatar = session.get('avatar_url', '/s3/usuarios/admin.svg')
    return dict(cart_count=cart_count, user_avatar=user_avatar)


# ---------------------------------------------------------------------------
# Helper: convierte tipos Decimal de DynamoDB a float para visualización
# ---------------------------------------------------------------------------
def decimal_to_float(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    if isinstance(obj, dict):
        return {k: decimal_to_float(v) for k, v in obj.items()}
    if isinstance(obj, list):
        return [decimal_to_float(i) for i in obj]
    return obj


# ---------------------------------------------------------------------------
# Rutas Principales
# ---------------------------------------------------------------------------

@app.route('/')
def index():
    """Redirecciona directamente al catálogo de la tienda."""
    return redirect(url_for('catalogo'))


@app.route('/login', methods=['GET', 'POST'])
def login():
    """Módulo de autenticación para perfil administrador."""
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '').strip()
        if username == ADMIN_USER and password == ADMIN_PASS:
            session['logged_in'] = True
            session['username'] = username
            session['avatar_url'] = '/s3/usuarios/admin.svg'
            flash('¡Bienvenido, Administrador!', 'success')
            return redirect(url_for('admin'))
        flash('Credenciales incorrectas.', 'danger')
    return render_template('login.html')


@app.route('/logout')
def logout():
    session.pop('logged_in', None)
    session.pop('username', None)
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('catalogo'))


@app.route('/catalogo')
def catalogo():
    """Muestra los productos cargados desde DynamoDB en LocalStack."""
    try:
        db = get_dynamodb()
        table = db.Table('Productos')
        response = table.scan()
        productos = [decimal_to_float(p) for p in response.get('Items', [])]
        productos.sort(key=lambda x: x.get('nombre', ''))
    except Exception as e:
        productos = []
        flash(f'Error al conectar con DynamoDB en LocalStack: {e}', 'danger')
    return render_template('catalogo.html', productos=productos)


@app.route('/agregar/<producto_id>')
def agregar(producto_id):
    """Agrega un producto al carrito de compras en sesión."""
    try:
        db = get_dynamodb()
        table = db.Table('Productos')
        resp = table.get_item(Key={'productoId': producto_id})
        item = resp.get('Item')
        if not item:
            flash('Producto no encontrado.', 'warning')
            return redirect(url_for('catalogo'))

        item = decimal_to_float(item)
        cart = session.get('carrito', [])

        for entry in cart:
            if entry['productoId'] == producto_id:
                entry['cantidad'] = entry.get('cantidad', 1) + 1
                session['carrito'] = cart
                flash(f'Se agregó otra unidad de "{item["nombre"]}".', 'success')
                return redirect(url_for('catalogo'))

        cart.append({
            'productoId': item['productoId'],
            'nombre': item['nombre'],
            'precio': item['precio'],
            'imagen': item.get('imagen', ''),
            'cantidad': 1,
        })
        session['carrito'] = cart
        flash(f'"{item["nombre"]}" agregado al carrito.', 'success')
    except Exception as e:
        flash(f'Error al agregar producto: {e}', 'danger')
    return redirect(url_for('catalogo'))


@app.route('/quitar/<producto_id>')
def quitar(producto_id):
    """Disminuye o elimina un producto del carrito."""
    cart = session.get('carrito', [])
    new_cart = []
    removed = False
    for entry in cart:
        if entry['productoId'] == producto_id and not removed:
            if entry.get('cantidad', 1) > 1:
                entry['cantidad'] -= 1
                new_cart.append(entry)
            removed = True
        else:
            new_cart.append(entry)
    session['carrito'] = new_cart
    if removed:
        flash('Producto eliminado del carrito.', 'info')
    return redirect(url_for('carrito'))


@app.route('/carrito')
def carrito():
    """Visualiza el carrito de compras y opción de pago."""
    cart = session.get('carrito', [])
    total = sum(item['precio'] * item.get('cantidad', 1) for item in cart)
    return render_template('carrito.html', carrito=cart, total=round(total, 2))


@app.route('/comprar', methods=['POST'])
def comprar():
    """Checkout: guarda en DynamoDB y envía mensaje a cola SQS en LocalStack."""
    cart = session.get('carrito', [])
    if not cart:
        flash('El carrito está vacío.', 'warning')
        return redirect(url_for('catalogo'))

    cliente = request.form.get('cliente', 'Cliente anónimo').strip() or 'Cliente anónimo'
    total = sum(item['precio'] * item.get('cantidad', 1) for item in cart)
    pedido_id = str(uuid.uuid4())
    fecha_actual = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')

    try:
        # 1. Guardar en DynamoDB (Tabla Pedidos en LocalStack)
        db = get_dynamodb()
        table = db.Table('Pedidos')
        order = {
            'pedidoId': pedido_id,
            'cliente': cliente,
            'productos': json.dumps(cart),
            'total': Decimal(str(round(total, 2))),
            'estado': 'PENDIENTE',
            'fecha': fecha_actual,
        }
        table.put_item(Item=order)

        # 2. Enviar a cola SQS (cola-pedidos en LocalStack)
        sqs = get_sqs()
        queue_url = sqs.get_queue_url(QueueName='cola-pedidos')['QueueUrl']
        sqs.send_message(
            QueueUrl=queue_url,
            MessageBody=json.dumps({
                'pedidoId': pedido_id,
                'cliente': cliente,
                'productos': cart,
                'total': round(total, 2),
                'fecha': fecha_actual,
            }),
        )

        session['carrito'] = []
        flash(f'¡Compra exitosa! Pedido ID: {pedido_id[:8]} guardado en DynamoDB y enviado a SQS (LocalStack).', 'success')
    except Exception as e:
        flash(f'Error al procesar compra con LocalStack: {e}', 'danger')

    return redirect(url_for('catalogo'))


@app.route('/admin', methods=['GET', 'POST'])
@login_required
def admin():
    """Panel de administración: listar y crear productos."""
    db = get_dynamodb()
    table = db.Table('Productos')

    if request.method == 'POST':
        nombre = request.form.get('nombre', '').strip()
        precio = request.form.get('precio', '0')
        descripcion = request.form.get('descripcion', '').strip()
        imagen_file = request.files.get('imagen')

        if not nombre:
            flash('El nombre del producto es obligatorio.', 'warning')
            return redirect(url_for('admin'))

        producto_id = f"prod-{str(uuid.uuid4())[:6]}"
        imagen_url = ''

        # Subir imagen a S3 en LocalStack
        s3 = get_s3()
        if imagen_file and imagen_file.filename:
            ext = imagen_file.filename.rsplit('.', 1)[-1].lower() if '.' in imagen_file.filename else 'png'
            key = f'productos/{producto_id}.{ext}'
            content_type = imagen_file.content_type or 'image/png'
            s3.upload_fileobj(
                imagen_file,
                S3_BUCKET,
                key,
                ExtraArgs={'ContentType': content_type},
            )
            imagen_url = f'/s3/{key}'
        else:
            # Generar placeholder SVG almacenado en S3
            color = f'#{abs(hash(nombre)) % 0xFFFFFF:06x}'
            svg = (
                f'<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300">'
                f'<rect width="400" height="300" rx="16" fill="{color}"/>'
                f'<text x="200" y="155" font-size="26" fill="white" '
                f'text-anchor="middle" font-family="Arial,sans-serif" font-weight="bold">{nombre[:20]}</text></svg>'
            )
            key = f'productos/{producto_id}.svg'
            s3.put_object(
                Bucket=S3_BUCKET,
                Key=key,
                Body=svg.encode('utf-8'),
                ContentType='image/svg+xml',
            )
            imagen_url = f'/s3/{key}'

        try:
            table.put_item(Item={
                'productoId': producto_id,
                'nombre': nombre,
                'precio': Decimal(str(round(float(precio), 2))),
                'descripcion': descripcion,
                'imagen': imagen_url,
            })
            flash(f'Producto "{nombre}" creado en DynamoDB e imagen guardada en S3 (LocalStack).', 'success')
        except Exception as e:
            flash(f'Error al crear producto: {e}', 'danger')

        return redirect(url_for('admin'))

    # GET – Listar productos
    try:
        productos = [decimal_to_float(p) for p in table.scan().get('Items', [])]
        productos.sort(key=lambda x: x.get('nombre', ''))
    except Exception:
        productos = []
    return render_template('admin.html', productos=productos)


@app.route('/admin/perfil', methods=['POST'])
@login_required
def admin_perfil():
    """Almacenar imagen de usuario en bucket S3 Local (Requisito PC3)."""
    avatar_file = request.files.get('avatar')
    if avatar_file and avatar_file.filename:
        try:
            s3 = get_s3()
            ext = avatar_file.filename.rsplit('.', 1)[-1].lower() if '.' in avatar_file.filename else 'png'
            key = f'usuarios/admin.{ext}'
            content_type = avatar_file.content_type or 'image/png'
            s3.upload_fileobj(
                avatar_file,
                S3_BUCKET,
                key,
                ExtraArgs={'ContentType': content_type},
            )
            session['avatar_url'] = f'/s3/{key}'
            flash('¡Imagen de perfil de usuario actualizada en S3 (LocalStack) con éxito!', 'success')
        except Exception as e:
            flash(f'Error al subir imagen a S3: {e}', 'danger')
    else:
        flash('No se seleccionó ninguna imagen.', 'warning')
    return redirect(url_for('admin'))


@app.route('/s3/<path:key>')
def serve_s3(key):
    """Endpoint puente para servir objetos directamente desde el bucket S3 en LocalStack."""
    try:
        s3 = get_s3()
        response = s3.get_object(Bucket=S3_BUCKET, Key=key)
        content_type = response.get('ContentType', 'application/octet-stream')
        data = response['Body'].read()
        return Response(data, mimetype=content_type)
    except Exception as e:
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="300" height="200">'
            '<rect width="300" height="200" fill="#e2e8f0"/>'
            '<text x="150" y="105" font-size="16" fill="#64748b" text-anchor="middle">S3 Image (LocalStack)</text></svg>'
        )
        return Response(svg, mimetype='image/svg+xml')


# ---------------------------------------------------------------------------
if __name__ == '__main__':
    # Escucha en 0.0.0.0 para acceso dentro y fuera de Docker
    app.run(host='0.0.0.0', port=5000, debug=True)
