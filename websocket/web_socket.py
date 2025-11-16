import boto3, json, datetime, os

ddb = boto3.resource('dynamodb')
table_name = os.environ.get('TABLE_NAME')
table = ddb.Table(table_name)

def ws_connect(event, context):
    connection_id = event['requestContext']['connectionId']
    table.put_item(Item={
        'connectionId': connection_id,
        'timestamp': datetime.datetime.utcnow().isoformat()
    })
    return { 'statusCode': 200 }

def ws_disconnect(event, context):
    connection_id = event['requestContext']['connectionId']
    table.delete_item(Key={'connectionId': connection_id})
    return { 'statusCode': 200 }

def ws_send_message(event, context):
    body = json.loads(event.get('body', '{}'))
    target_connection_id = body.get('connectionId')
    message = body.get('message', 'Hola desde WebSocket')

    apigw = boto3.client("apigatewaymanagementapi",
        endpoint_url=f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
    )   

    apigw.post_to_connection(
        ConnectionId=target_connection_id,
        Data=json.dumps({ "type": "mensaje", "content": message }).encode('utf-8')
    )
    return { 'statusCode': 200 }

def ws_broadcast_update(event, context):
    body = json.loads(event.get('body', '{}'))
    mensaje = {
        "type": "incidente_update",
        "data": body.get("data", {})
    }

    apigw = boto3.client("apigatewaymanagementapi",
        endpoint_url=f"https://{event['requestContext']['domainName']}/{event['requestContext']['stage']}"
    )

    # Recorrer todos los connectionId guardados en DynamoDB
    conexiones = table.scan().get("Items", [])
    for conn in conexiones:
        try:
            apigw.post_to_connection(
                ConnectionId=conn["connectionId"],
                Data=json.dumps(mensaje).encode("utf-8")
            )
        except Exception as e:
            print(f"Error enviando a {conn['connectionId']}: {e}")

    return { 'statusCode': 200 }

