import os
import boto3
import time
from botocore.exceptions import ClientError
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns', region_name='us-east-1')
TABLE_NAME = os.environ.get('APPOINTMENT_TABLE', 'MedTrack-Appointments')
TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    
    try:
        response = table.scan(
            FilterExpression="begins_with(ScheduledAt, :t) AND #st = :s",
            ExpressionAttributeValues={":t": tomorrow, ":s": "Confirmed"},
            ExpressionAttributeNames={"#st": "Status"}
        )
    except ClientError as e:
        print(f"Scan failed: {e}")
        return {"statusCode": 500}
        
    count = 0
    for item in response.get('Items', []):
        patient_id = item['PatientID']
        msg = f"Reminder: You have a MedTrack appointment tomorrow at {item['ScheduledAt']}"
        
        # Exponential backoff for SNS
        retries = 3
        for i in range(retries):
            try:
                sns.publish(TopicArn=TOPIC_ARN, Message=msg)
                count += 1
                break
            except ClientError as e:
                if i == retries - 1:
                    print(f"Failed to send SMS to patient {patient_id}: {e}")
                else:
                    time.sleep((2 ** i))
                
    return {"statusCode": 200, "body": f"Sent {count} reminders."}
