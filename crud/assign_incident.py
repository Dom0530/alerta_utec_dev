import json
import boto3
import os
from datetime import datetime

# Cliente de DynamoDB
dynamodb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = dynamodb.Table(table_name)


def lambda_handler(event, context):
    try:
        # Parsear el body del request
        # body siempre será un dict después de esto
        body = {}
        if 'body' in event:
            if isinstance(event['body'], str):
                body = json.loads(event['body'])
            elif isinstance(event['body'], dict):
                body = event['body']
        else:
            body = event  # fallback

    incident_id = body.get('incidentId')
    new_status = body.get('status')

        if not incident_id or not assigned_to:
            return {
                'statusCode': 400,
                'headers': {
                    'Content-Type': 'application/json',
                    'Access-Control-Allow-Origin': '*'
                },
                'body': json.dumps({
                    'message': 'incidentId y assignedTo son requeridos'
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
        old_assigned = incident.get('assignedTo', '')
        timestamp = datetime.utcnow().isoformat() + 'Z'

        # Crear nueva entrada en el historial
        new_history_entry = {
            'action': 'assigned',
            'from': old_assigned,
            'to': assigned_to,
            'timestamp': timestamp
        }

        # Actualizar el incidente
        table.update_item(
            Key={'incidentId': incident_id},
            UpdateExpression='SET assignedTo = :assigned_to, updatedAt = :updated_at, history = list_append(history, :new_history)',
            ExpressionAttributeValues={
                ':assigned_to': assigned_to,
                ':updated_at': timestamp,
                ':new_history': [new_history_entry]
            }
        )
        
        return {
            'statusCode': 200,
            'headers': {
                'Content-Type': 'application/json',
                'Access-Control-Allow-Origin': '*'
            },
            'body': json.dumps({
                'message': 'Incidente asignado exitosamente',
                'incidentId': incident_id,
                'oldAssignedTo': old_assigned,
                'newAssignedTo': assigned_to,
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
                'message': 'Error al asignar incidente',
                'error': str(e)
            })

        }

