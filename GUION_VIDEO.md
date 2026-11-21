# Guion para video demostrativo — PC3 Cognitive Computing

**Proyecto:** Tienda virtual Flask + Docker + LocalStack (DynamoDB, S3 y SQS)  
**Duración objetivo:** 3–4 minutos. **Máximo permitido por el profesor: 5 minutos.**

> **Importante:** muestra el sistema operativo que realmente utilizaste. La aplicación se ha probado en macOS con Docker. El enunciado pide WSL (Ubuntu), así que no afirmes en el video haber usado WSL salvo que hayas repetido el despliegue en una instancia WSL real o el profesor haya aprobado una alternativa.

## 0:00–0:25 | Introducción

**Pantalla:** repositorio y diagrama del README.

**Guion:** «Presento la PC3 de Introducción a Cognitive Computing. Desarrollé una tienda virtual con Python y Flask, contenerizada con Docker y conectada a los servicios AWS simulados con LocalStack: DynamoDB, S3 y SQS».

## 0:25–0:55 | Infraestructura

**Pantalla:** terminal con:

```bash
docker compose ps
curl http://localhost:4566/_localstack/health
```

**Guion:** «Docker Compose inicia dos contenedores: LocalStack en el puerto 4566 y la tienda Flask en el puerto 8080. La aplicación se comunica con LocalStack por una red interna de Docker. Los tres servicios AWS requeridos están operativos».

## 0:55–1:45 | Funcionalidad web

**Pantalla:** http://localhost:8080

Demuestra, en este orden:
1. Catálogo de productos obtenido de DynamoDB.
2. Inicio de sesión del administrador.
3. Panel de usuario y carga de avatar a S3.
4. Selección de productos y carrito.
5. Confirmación de compra.

**Guion:** «El catálogo se consulta desde DynamoDB. El administrador accede a su panel y puede subir su foto de perfil al bucket de S3. Desde el catálogo agrego productos al carrito y realizo un pedido. El pedido se guarda en DynamoDB y también se envía como mensaje a SQS».

## 1:45–2:20 | Simulación de 100 pedidos

**Pantalla:** terminal:

```bash
docker compose exec tienda python simular_pedidos.py
```

**Guion:** «Este script genera cien pedidos simulados con clientes, productos y montos. Los envía a la cola SQS y presenta el total exitoso y los errores, que en las pruebas realizadas fueron cien envíos exitosos y cero errores».

**Consejo:** si los 100 mensajes ya fueron consumidos durante las pruebas, vuelve a ejecutar el script solo cuando quieras volver a mostrar una cola con mensajes disponibles.

## 2:20–2:50 | Verificación de datos AWS

**Pantalla:** terminal, mostrando las tablas y el bucket:

```bash
docker compose exec tienda python -c "import boto3; c=dict(endpoint_url='http://localstack:4566',region_name='us-east-1'); print('DynamoDB:',boto3.client('dynamodb',**c).list_tables()['TableNames']); print('S3:',[b['Name'] for b in boto3.client('s3',**c).list_buckets()['Buckets']])"
```

Para probar el procesamiento SQS → DynamoDB:

```bash
docker compose exec tienda python procesar_pedidos.py
```

**Guion:** «En DynamoDB se registran los productos y pedidos. S3 contiene las imágenes de usuario y de productos. SQS recibe las solicitudes simuladas y el procesador las consume y persiste en DynamoDB».

## 2:50–3:10 | Cierre

**Pantalla:** repositorio GitHub.

**Guion:** «En conclusión, demostré una tienda contenerizada, con administración, carrito, compra y comunicación con DynamoDB, S3 y SQS simulados en LocalStack. El código y la documentación están en el repositorio. Gracias».

## Entregables adicionales

- README y URL del repositorio.
- Capturas de contenedores Docker, LocalStack, DynamoDB, S3 y SQS.
- Video demostrativo de máximo cinco minutos.
- Evidencia de ejecución real en WSL si el docente mantiene ese requisito; Docker en macOS no lo sustituye automáticamente.
