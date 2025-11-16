import json
import boto3
import uuid
import os
from datetime import datetime

# Clientes de AWS
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)

def lambda_handler(event, context):
    try:
        # Parsear el body del request
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event

        # Generar ID único para el incidente
        timestamp = datetime.utcnow().isoformat() + 'Z'
        incident_id = f"INC#{timestamp}"

        # Crear el incidente
        incident = {
            'incidentId': incident_id,
            'type': body.get('type', 'otro'),
            'urgency': body.get('urgency', 'media'),
            'location': body.get('location', ''),
            'description': body.get('description', ''),
            'status': 'pendiente',
            'createdAt': timestamp,
            'updatedAt': timestamp,
            'createdBy': body.get('createdBy', 'anonymous'),
            'assignedTo': body.get('assignedTo', ''),
            'history': [
                {
                    'action': 'created',
                    'timestamp': timestamp
                }
            ]
        }

        # Guardar en DynamoDB
        table.put_item(Item=incident)

        # Mandar a websocket
        broadcast_function_name = os.environ.get('WS_BROADCAST_LAMBDA')
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName="ws_broadcast_update",
            InvocationType="Event",  # asincrónico
            Payload=json.dumps({
                "data": {
                    "incidentId": incident_id,
                    "status": 'pendiente',
                    "updatedAt": timestamp
                }
            })
        )
       
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Incidente creado exitosamente',
                'incidentId': incident_id,
                'incident': incident
            })
        }

    except Exception as e:
        print(f"Error: {str(e)}")
        return {
            'statusCode': 500,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Error al crear incidente',
                'error': str(e)
            })

        }

