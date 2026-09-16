import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.sns = boto3.client('sns', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.topic_arn = os.environ.get('SNS_TOPIC_ARN', None)

    def send_otp(self, phone: str, otp: str) -> bool:
        message = f"Your MedTrack OTP is: {otp}. It is valid for 10 minutes."
        if not self.topic_arn:
            logger.info(f"Simulating SMS to {phone}: {message}")
            return True
        try:
            self.sns.publish(PhoneNumber=phone, Message=message)
            return True
        except ClientError as e:
            logger.error(f"Failed to send OTP via SNS: {e}")
            return False
