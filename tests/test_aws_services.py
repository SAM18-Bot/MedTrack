import pytest
import boto3
import io
import os
from moto import mock_aws
from app.services.storage_service import StorageService

@pytest.fixture
def s3_setup(aws_credentials):
    with mock_aws():
        s3 = boto3.client('s3', region_name='us-east-1')
        bucket = os.environ.get('S3_BUCKET_NAME', 'medtrack-documents-local')
        s3.create_bucket(Bucket=bucket)
        if bucket != 'medtrack-documents-local':
            try:
                s3.create_bucket(Bucket='medtrack-documents-local')
            except Exception:
                pass
        yield

def test_upload_and_presign(s3_setup):
    svc = StorageService()
    file_obj = io.BytesIO(b"dummy pdf content")
    success = svc.upload_file(file_obj, "test.pdf")
    assert success is True
    
    url = svc.get_presigned_url("test.pdf")
    assert url is not None
    assert "AWSAccessKeyId" in url
