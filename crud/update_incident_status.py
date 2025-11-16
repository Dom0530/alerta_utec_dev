import json
import boto3
from datetime import datetime

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('Incidents')


def lambda_handler(event, context):
    try:
        # Parsear el body del request
        body = json.loads(event['body']) if isinstance(event.get('body'), str) else event

        incident_id = body.get('incidentId')
        new_status = body.get('status')

        if not incident_id or not new_status:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'incidentId y status son requeridos'
                })
            }

        # Obtener el incidente actual
        response = table.get_item(Key={'incidentId': incident_id})

        if 'Item' not in response:
            return {
                'statusCode': 404,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'Incidente no encontrado'
                })
            }

        incident = response['Item']
        old_status = incident.get('status', 'pendiente')
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Crear nueva entrada en el historial
        new_history_entry = {
            'action': 'status_change',
            'from': old_status,
            'to': new_status,
            'timestamp': timestamp
        }

        # Actualizar el incidente
        table.update_item(
            Key={'incidentId': incident_id},
            UpdateExpression='SET #status = :new_status, updatedAt = :updated_at, history = list_append(history, :new_history)',
            ExpressionAttributeNames={
                '#status': 'status'
            },
            ExpressionAttributeValues={
                ':new_status': new_status,
                ':updated_at': timestamp,
                ':new_history': [new_history_entry]
            }
        )

        # mandar a websocket
        lambda_client = boto3.client("lambda")
        lambda_client.invoke(
            FunctionName="ws_broadcast_update",
            InvocationType="Event",  # asincrónico
            Payload=json.dumps({
                "data": {
                    "incidentId": incident_id,
                    "status": new_status,
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
                'message': 'Estado actualizado exitosamente',
                'incidentId': incident_id,
                'oldStatus': old_status,
                'newStatus': new_status,
                'updatedAt': timestamp
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
                'message': 'Error al actualizar estado',
                'error': str(e)
            })
        }