import boto3
import json
import datetime
import os

# ==== Recursos AWS ====
ddb = boto3.resource('dynamodb')
ws_table = ddb.Table(os.environ.get("WS_CONNECTIONS", "WebSocketConnections"))

ses = boto3.client("ses")
sns = boto3.client("sns")


# ========================================================
# Helper: enviar mensaje por WebSocket (broadcast)
# ========================================================
def send_ws_notification(domain, stage, payload):
    apigw = boto3.client(
        "apigatewaymanagementapi",
        endpoint_url=f"https://{domain}/{stage}"
    )

    conexiones = ws_table.scan().get("Items", [])

    for conn in conexiones:
        try:
            apigw.post_to_connection(
                ConnectionId=conn["connectionId"],
                Data=json.dumps(payload).encode("utf-8")
            )
        except Exception as e:
            print(f"Conexión inválida {conn['connectionId']}: {e}")


# ========================================================
# Helper: enviar correo (SES)
# ========================================================
def send_email(to_email, subject, message):
    ses.send_email(
        Source=os.environ.get("EMAIL_SOURCE"),
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": subject},
            "Body": {
                "Text": {"Data": message}
            }
        }
    )


# ========================================================
# Helper: enviar SMS (SNS)
# ========================================================
def send_sms(phone_number, message):
    sns.publish(
        PhoneNumber=phone_number,
        Message=message
    )


# ========================================================
# Handler principal
# ========================================================
def handler(event, context):
    print("EVENTO RECIBIDO:", event)

    body = json.loads(event.get("body", "{}"))

    tipo = body.get("tipo")               # "ws", "email", "sms" o "all"
    payload = body.get("payload", {})
    email = body.get("email")
    telefono = body.get("telefono")

    # === Construir mensaje estándar ===
    mensaje_generico = f"""
        Notificación AlertaUTEC
        Tipo: {payload.get('tipo')}
        Incidente ID: {payload.get('incidente_id')}
        Descripción: {payload.get('mensaje')}
        Fecha: {datetime.datetime.utcnow().isoformat()} UTC
        """

    # === Obtener dominio y stage para WS ===
    domain = event["requestContext"]["domainName"]
    stage = event["requestContext"]["stage"]

    # =====================================================
    # ROUTING de notificaciones
    # =====================================================

    # --- WebSocket ---
    if tipo in ["ws", "all"]:
        ws_payload = {
            "type": "notificacion",
            "data": payload
        }
        send_ws_notification(domain, stage, ws_payload)

    # --- Correo ---
    if tipo in ["email", "all"] and email:
        send_email(
            to_email=email,
            subject="Nueva Notificación AlertaUTEC",
            message=mensaje_generico
        )

    # --- SMS ---
    if tipo in ["sms", "all"] and telefono:
        send_sms(
            phone_number=telefono,
            message=payload.get("mensaje", "Nueva notificación AlertaUTEC")
        )

    return {
        "statusCode": 200,
        "body": json.dumps({"status": "ok"})
    }
