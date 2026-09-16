import boto3
import os
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.s3 = boto3.client('s3', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
        self.bucket = os.environ.get('S3_BUCKET_NAME', 'medtrack-documents-local')

    def upload_file(self, file_obj, object_name, content_type=None):
        extra_args = {}
        if content_type:
            extra_args['ContentType'] = content_type
        try:
            self.s3.upload_fileobj(file_obj, self.bucket, object_name, ExtraArgs=extra_args)
            return True
        except ClientError as e:
            logger.error(e)
            return False

    def get_presigned_url(self, object_name, expiration=3600):
        try:
            response = self.s3.generate_presigned_url('get_object',
                                                    Params={'Bucket': self.bucket, 'Key': object_name},
                                                    ExpiresIn=expiration)
        except ClientError as e:
            logger.error(e)
            return None
        return response
