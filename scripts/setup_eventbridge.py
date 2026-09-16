import boto3
import json

def setup_eventbridge(lambda_arn):
    events = boto3.client('events')
    
    # Create rule to trigger daily at 8:00 AM UTC
    rule_response = events.put_rule(
        Name='MedTrackDailyReminders',
        ScheduleExpression='cron(0 8 * * ? *)',
        State='ENABLED',
        Description='Triggers daily appointment reminders'
    )
    
    # Add lambda as target
    events.put_targets(
        Rule='MedTrackDailyReminders',
        Targets=[
            {
                'Id': 'ReminderLambdaTarget',
                'Arn': lambda_arn
            }
        ]
    )
    print("EventBridge Rule established successfully.")

if __name__ == '__main__':
    # usage: python setup_eventbridge.py
    # NOTE: requires an actual Lambda ARN to be functional in a real AWS env.
    print("Setup script loaded. Pass your deployed Lambda ARN to run.")
