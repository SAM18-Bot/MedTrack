import boto3
import os
import io
import logging
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class StorageService:
    def __init__(self):
        self.bucket = os.environ.get('S3_BUCKET_NAME')
        self.region = os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        self._s3 = None
        # Base directory for local disk storage fallback
        self.local_upload_dir = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
        )
        os.makedirs(self.local_upload_dir, exist_ok=True)

    @property
    def s3(self):
        if not self._s3 and self.bucket:
            try:
                self._s3 = boto3.client('s3', region_name=self.region)
            except Exception as e:
                logger.warning(f"Could not initialize S3 client: {e}")
        return self._s3

    def upload_file(self, file_obj, object_name, content_type=None):
        data = None
        if hasattr(file_obj, 'read'):
            try:
                data = file_obj.read()
                if hasattr(file_obj, 'seek'):
                    file_obj.seek(0)
            except Exception:
                data = None
        elif isinstance(file_obj, (bytes, bytearray)):
            data = file_obj

        # 1. Try S3 if bucket is configured
        if self.bucket and self.s3:
            try:
                extra_args = {'ContentType': content_type} if content_type else {}
                body_stream = io.BytesIO(data) if data is not None else file_obj
                self.s3.upload_fileobj(body_stream, self.bucket, object_name, ExtraArgs=extra_args)
                return True
            except (ClientError, Exception) as e:
                logger.warning(f"S3 upload failed ({e}), falling back to local disk storage.")

        # 2. Local disk fallback
        try:
            local_path = os.path.join(self.local_upload_dir, object_name)
            os.makedirs(os.path.dirname(local_path), exist_ok=True)
            with open(local_path, 'wb') as f:
                if data is not None:
                    f.write(data)
                elif hasattr(file_obj, 'read') and not getattr(file_obj, 'closed', False):
                    f.write(file_obj.read())
            return True
        except Exception as e:
            logger.error(f"Local storage write failed: {e}")
            return False

    def get_presigned_url(self, object_name, expiration=3600, filename=None):
        # 1. Try S3 if bucket is configured
        if self.bucket and self.s3:
            try:
                params = {'Bucket': self.bucket, 'Key': object_name}
                if filename:
                    params['ResponseContentDisposition'] = f'attachment; filename="{filename}"'
                return self.s3.generate_presigned_url('get_object', Params=params, ExpiresIn=expiration)
            except (ClientError, Exception) as e:
                logger.warning(f"S3 presigned URL failed ({e}), falling back to local download URL.")

        # 2. Local disk download URL
        return f"/patient/files/{object_name}"
