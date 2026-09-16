import boto3
import os
import time
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class NotificationService:
    def __init__(self):
        self.sns = boto3.client('sns', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.topic_arn = os.environ.get('SNS_TOPIC_ARN')

    def _publish_with_backoff(self, **kwargs):
        retries = 3
        for i in range(retries):
            try:
                self.sns.publish(**kwargs)
                return True
            except ClientError as e:
                if i == retries - 1:
                    logger.error(f"SNS publish failed after {retries} attempts: {e}")
                    return False
                time.sleep((2 ** i))
        return False

    def send_otp(self, phone: str, otp: str) -> bool:
        message = f"Your MedTrack OTP is: {otp}. It is valid for 10 minutes."
        if not self.topic_arn:
            logger.info(f"Simulating SMS to {phone}: {message}")
            return True
        return self._publish_with_backoff(PhoneNumber=phone, Message=message)

    def notify_admin(self, subject: str, message: str) -> bool:
        if not self.topic_arn:
            logger.info(f"Simulating Admin Alert - {subject}: {message}")
            return True
        return self._publish_with_backoff(TopicArn=self.topic_arn, Subject=subject, Message=message)
