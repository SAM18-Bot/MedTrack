import os
import pytest
import boto3
from moto import mock_aws
from scripts.create_tables import create_tables
from app.repositories.user_repository import UserRepository
from app.utils import DecimalEncoder
import json
from decimal import Decimal

@pytest.fixture(autouse=True)
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_PREFIX'] = 'TestTrack-'

@pytest.fixture
def dynamodb_setup():
    with mock_aws():
        create_tables()
        yield

def test_user_repository(dynamodb_setup):
    repo = UserRepository()
    repo.create_user("u1", "test@example.com", "hash", "Patient")
    
    user = repo.get_user("u1")
    assert user['Email'] == "test@example.com"
    assert user['IsDeleted'] is False
    
    repo.soft_delete(repo.TABLE, {"UserID": "u1"})
    deleted_user = repo.get_user("u1")
    assert deleted_user is None
    
def test_decimal_encoder():
    d = Decimal("10.5")
    res = json.dumps({"val": d}, cls=DecimalEncoder)
    assert res == '{"val": 10.5}'
