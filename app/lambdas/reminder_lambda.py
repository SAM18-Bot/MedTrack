import os
import boto3
from datetime import datetime, timedelta

dynamodb = boto3.resource('dynamodb')
sns = boto3.client('sns')
TABLE_NAME = os.environ.get('APPOINTMENT_TABLE', 'MedTrack-Appointments')
TOPIC_ARN = os.environ.get('SNS_TOPIC_ARN')

def lambda_handler(event, context):
    table = dynamodb.Table(TABLE_NAME)
    tomorrow = (datetime.utcnow() + timedelta(days=1)).strftime('%Y-%m-%d')
    response = table.scan(
        FilterExpression="begins_with(ScheduledAt, :t) AND #st = :s",
        ExpressionAttributeValues={":t": tomorrow, ":s": "Confirmed"},
        ExpressionAttributeNames={"#st": "Status"}
    )
    
    count = 0
    for item in response.get('Items', []):
        patient_id = item['PatientID']
        msg = f"Reminder: You have a MedTrack appointment tomorrow at {item['ScheduledAt']}"
        if TOPIC_ARN:
            try:
                sns.publish(TopicArn=TOPIC_ARN, Message=msg)
                count += 1
            except Exception as e:
                print(f"Failed to send SMS to patient {patient_id}: {e}")
                
    return {"statusCode": 200, "body": f"Sent {count} reminders."}
