import os
import pytest
from moto import mock_aws
from scripts.create_tables import create_tables
from app import create_app
from app.config import TestConfig

@pytest.fixture(autouse=True)
def aws_credentials():
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    os.environ['AWS_DEFAULT_REGION'] = 'us-east-1'
    os.environ['DYNAMODB_PREFIX'] = 'TestTrack-'

@pytest.fixture
def dynamodb_setup(aws_credentials):
    with mock_aws():
        create_tables()
        yield

@pytest.fixture
def app(dynamodb_setup):
    app = create_app(TestConfig)
    app.config['SECRET_KEY'] = 'test-secret'
    yield app

@pytest.fixture
def client(app):
    return app.test_client()
