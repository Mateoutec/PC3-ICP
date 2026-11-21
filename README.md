# PC3 - Tienda Virtual con Servicios AWS Locales (LocalStack)

## Descripción del proyecto

Tienda virtual desarrollada con **Flask (Python)** e integrada con los servicios AWS simulados localmente mediante **LocalStack** y **Docker Compose**. El proyecto implementa catálogo de productos, carrito de compras, creación de pedidos, autenticación de administrador y almacenamiento de imágenes de usuario.

- **DynamoDB:** tablas `Productos` y `Pedidos`.
- **S3:** bucket `tienda-imagenes`, con objetos bajo `usuarios/` y `productos/`.
- **SQS:** cola `cola-pedidos`, utilizada en el checkout y en la simulación de 100 pedidos.
- **Flask:** aplicación web publicada en el puerto 8080.

> **Entorno exigido por la PC3:** el enunciado del docente pide despliegue en WSL (Ubuntu) con Docker. Este repositorio incluye instrucciones para WSL. El funcionamiento reportado por el autor se probó inicialmente en macOS con Docker; ese entorno no sustituye la verificación en WSL.

## Requisitos

- Docker Desktop y Docker Compose.
- Cuenta de LocalStack con un token de autenticación vigente (plan Hobby u otro plan compatible).
- Git para clonar el repositorio.
- Opcional: Python 3.10+ y AWS CLI v2 para realizar comprobaciones desde el host.

## Instalación y arranque

En macOS o en la terminal Ubuntu de WSL, ejecuta:

```bash
git clone https://github.com/Mateoutec/PC3-ICP.git
cd PC3-ICP
cp .env.example .env
```

Abre `.env` con tu editor y coloca **tu propio token** de LocalStack:

```dotenv
LOCALSTACK_AUTH_TOKEN=TU_TOKEN_PERSONAL
```

> Nunca subas `.env` ni tu token a GitHub. El archivo `.env.example` debe permanecer sin credenciales.

Luego:

```bash
docker compose up --build -d
docker compose ps
```

Abre la aplicación en **http://localhost:8080** y comprueba la salud de LocalStack en **http://localhost:4566/_localstack/health**.

### Acceso al administrador (solo para la demostración académica)

- URL: http://localhost:8080/login
- Usuario: `admin`
- Contraseña de demostración: `admin123`

Estas credenciales están definidas en el código para uso local en clase. **No despliegues esta configuración en Internet** sin sustituir el sistema de autenticación y la clave de sesión.

## Despliegue en WSL (Ubuntu)

En Windows, instala WSL 2 y Ubuntu, configura Docker Desktop para integrarse con la distribución Ubuntu y abre una terminal WSL:

```powershell
wsl -d Ubuntu
```

Dentro de Ubuntu, instala Git si falta, comprueba que `docker ps` funcione y sigue los pasos de instalación anteriores. El proyecto está configurado con una red Docker (`tienda-net`) y con el endpoint interno `http://localstack:4566`.

La comprobación del requisito WSL debe realizarse efectivamente en una instancia WSL y quedar documentada en las evidencias del curso.

## Ejecutar los 100 pedidos simulados

Para evitar instalar paquetes Python en el host, utiliza el contenedor ya iniciado:

```bash
docker compose exec tienda python simular_pedidos.py
```

El script envía **100 pedidos** a la cola `cola-pedidos`. Después, para consumirlos y guardarlos en DynamoDB:

```bash
docker compose exec tienda python procesar_pedidos.py
```

**Importante:** captura primero la evidencia de SQS con los mensajes pendientes; el procesador elimina de la cola los mensajes que haya procesado correctamente.

## Verificación de servicios y evidencias

Contenedores Docker:

```bash
docker compose ps
```

Comprobar que LocalStack está disponible:

```bash
curl http://localhost:4566/_localstack/health
```

Comprobar tablas DynamoDB y bucket S3 desde el contenedor:

```bash
docker compose exec tienda python -c "import boto3; c=dict(endpoint_url='http://localstack:4566',region_name='us-east-1'); print('TABLAS DYNAMODB:',boto3.client('dynamodb',**c).list_tables()['TableNames']); print('BUCKETS S3:',[b['Name'] for b in boto3.client('s3',**c).list_buckets()['Buckets']])"
```

Comprobar número de productos y pedidos:

```bash
docker compose exec tienda python -c "import boto3; d=boto3.client('dynamodb',endpoint_url='http://localstack:4566',region_name='us-east-1'); print('Productos:',d.scan(TableName='Productos',Select='COUNT')['Count']); print('Pedidos:',d.scan(TableName='Pedidos',Select='COUNT')['Count'])"
```

Las evidencias solicitadas por el profesor incluyen Docker, AWS/LocalStack, DynamoDB, S3 y SQS. Complementa esas capturas con una prueba de catálogo, carrito, compra, panel administrador y carga de imagen de perfil, preferiblemente en el video.

## Arquitectura

```text
Navegador
   |
   v
Flask (tienda-app:5000; host:8080)
   |
   +---- DynamoDB: Productos / Pedidos
   |
   +---- S3: tienda-imagenes (usuarios/ y productos/)
   |
   +---- SQS: cola-pedidos
              |
              v
        procesar_pedidos.py ----> DynamoDB: Pedidos
                 Servicios simulados en LocalStack:4566
```

## Estructura

```text
.
├── .env.example
├── .gitignore
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── app.py
├── init_data.py
├── simular_pedidos.py
├── procesar_pedidos.py
├── README.md
├── GUION_VIDEO.md
└── templates/
    ├── base.html
    ├── catalogo.html
    ├── carrito.html
    ├── login.html
    └── admin.html
```

## Entrega académica

Además del repositorio, la PC3 requiere documentación técnica, evidencias de infraestructura y un **video demostrativo de máximo 5 minutos**. Consulta [GUION_VIDEO.md](GUION_VIDEO.md) para planificarlo.

## Advertencias de seguridad

La aplicación y sus credenciales de administrador son una demostración académica. La clave de sesión y la contraseña de administrador deben trasladarse a variables de entorno y protegerse correctamente antes de cualquier despliegue público. El token de LocalStack nunca debe quedar versionado.
