import os

files = {
    "app/utils.py": """import json
from decimal import Decimal
from datetime import datetime, timezone

class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

def get_utc_now():
    return datetime.now(timezone.utc).isoformat()
""",
    "app/repositories/__init__.py": "",
    "app/repositories/base_repository.py": """import os
import time
import logging
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

class BaseRepository:
    def __init__(self):
        self.dynamodb = boto3.resource(
            'dynamodb',
            region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1')
        )
        self.table_prefix = os.environ.get('DYNAMODB_PREFIX', 'MedTrack-')

    def _get_table(self, table_name):
        return self.dynamodb.Table(f"{self.table_prefix}{table_name}")

    def _execute_with_retry(self, operation, *args, **kwargs):
        max_retries = 3
        base_delay = 0.5
        for attempt in range(max_retries):
            try:
                return operation(*args, **kwargs)
            except ClientError as e:
                error_code = e.response['Error']['Code']
                if error_code in ['ProvisionedThroughputExceededException', 'ThrottlingException']:
                    if attempt == max_retries - 1:
                        logger.error(f"Max retries reached for {error_code}.")
                        raise ValueError("Service is currently busy. Please try again later.")
                    time.sleep(base_delay * (2 ** attempt))
                else:
                    logger.error(f"DynamoDB ClientError: {error_code} - {str(e)}")
                    raise ValueError(f"Database operation failed: {error_code}")
            except Exception as e:
                logger.error(f"Unexpected error: {str(e)}")
                raise ValueError("An unexpected error occurred.")

    def get_item(self, table_name, key):
        table = self._get_table(table_name)
        response = self._execute_with_retry(table.get_item, Key=key)
        item = response.get('Item')
        if not item:
            return None
        if item.get('IsDeleted'):
            return None
        return item

    def put_item(self, table_name, item, condition_expression=None):
        table = self._get_table(table_name)
        kwargs = {'Item': item}
        if condition_expression:
            kwargs['ConditionExpression'] = condition_expression
        self._execute_with_retry(table.put_item, **kwargs)
        return item

    def update_item(self, table_name, key, update_expression, expression_attribute_values, expression_attribute_names=None):
        table = self._get_table(table_name)
        kwargs = {
            'Key': key,
            'UpdateExpression': update_expression,
            'ExpressionAttributeValues': expression_attribute_values,
            'ReturnValues': 'ALL_NEW'
        }
        if expression_attribute_names:
            kwargs['ExpressionAttributeNames'] = expression_attribute_names
        response = self._execute_with_retry(table.update_item, **kwargs)
        return response.get('Attributes')

    def query_index(self, table_name, index_name, key_condition_expression, expression_attribute_values):
        table = self._get_table(table_name)
        response = self._execute_with_retry(
            table.query,
            IndexName=index_name,
            KeyConditionExpression=key_condition_expression,
            ExpressionAttributeValues=expression_attribute_values
        )
        items = response.get('Items', [])
        return [item for item in items if not item.get('IsDeleted')]

    def soft_delete(self, table_name, key):
        from app.utils import get_utc_now
        return self.update_item(
            table_name=table_name,
            key=key,
            update_expression="SET IsDeleted = :val, UpdatedAt = :updated",
            expression_attribute_values={
                ':val': True,
                ':updated': get_utc_now()
            }
        )
""",
    "app/repositories/user_repository.py": """from app.repositories.base_repository import BaseRepository
from app.utils import get_utc_now

class UserRepository(BaseRepository):
    TABLE = "Users"

    def get_user(self, user_id):
        return self.get_item(self.TABLE, {"UserID": user_id})

    def get_user_by_email(self, email):
        items = self.query_index(
            self.TABLE,
            "email-index",
            "Email = :email",
            {":email": email}
        )
        return items[0] if items else None

    def create_user(self, user_id, email, password_hash, role, phone=None):
        item = {
            "UserID": user_id,
            "Email": email,
            "PasswordHash": password_hash,
            "Role": role,
            "Phone": phone,
            "IsDeleted": False,
            "CreatedAt": get_utc_now(),
            "UpdatedAt": get_utc_now()
        }
        self.put_item(self.TABLE, item, condition_expression="attribute_not_exists(UserID)")
        return item
""",
    "scripts/create_tables.py": """import os
import boto3
from botocore.exceptions import ClientError
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_tables():
    dynamodb = boto3.client('dynamodb', region_name=os.environ.get('AWS_DEFAULT_REGION', 'us-east-1'))
    prefix = os.environ.get('DYNAMODB_PREFIX', 'MedTrack-')

    tables_def = [
        {
            "TableName": f"{prefix}Users",
            "AttributeDefinitions": [
                {"AttributeName": "UserID", "AttributeType": "S"},
                {"AttributeName": "Email", "AttributeType": "S"},
                {"AttributeName": "Role", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "UserID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "email-index", "KeySchema": [{"AttributeName": "Email", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "role-index", "KeySchema": [{"AttributeName": "Role", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Patients",
            "AttributeDefinitions": [
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "Email", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "email-index", "KeySchema": [{"AttributeName": "Email", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Doctors",
            "AttributeDefinitions": [
                {"AttributeName": "DoctorID", "AttributeType": "S"},
                {"AttributeName": "Email", "AttributeType": "S"},
                {"AttributeName": "SpecializationID", "AttributeType": "S"},
                {"AttributeName": "Status", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "DoctorID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "email-index", "KeySchema": [{"AttributeName": "Email", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "specialization-index", "KeySchema": [{"AttributeName": "SpecializationID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "status-index", "KeySchema": [{"AttributeName": "Status", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}DoctorAvailability",
            "AttributeDefinitions": [
                {"AttributeName": "DoctorID", "AttributeType": "S"},
                {"AttributeName": "Date", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "DoctorID", "KeyType": "HASH"},
                {"AttributeName": "Date", "KeyType": "RANGE"}
            ]
        },
        {
            "TableName": f"{prefix}Appointments",
            "AttributeDefinitions": [
                {"AttributeName": "AppointmentID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "DoctorID", "AttributeType": "S"},
                {"AttributeName": "ScheduledAt", "AttributeType": "S"},
                {"AttributeName": "Status", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "AppointmentID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}, {"AttributeName": "ScheduledAt", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "doctor-index", "KeySchema": [{"AttributeName": "DoctorID", "KeyType": "HASH"}, {"AttributeName": "ScheduledAt", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "status-index", "KeySchema": [{"AttributeName": "Status", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Prescriptions",
            "AttributeDefinitions": [
                {"AttributeName": "PrescriptionID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "AppointmentID", "AttributeType": "S"},
                {"AttributeName": "DoctorID", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "PrescriptionID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "appointment-index", "KeySchema": [{"AttributeName": "AppointmentID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "doctor-index", "KeySchema": [{"AttributeName": "DoctorID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}DiagnosisReports",
            "AttributeDefinitions": [
                {"AttributeName": "ReportID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "AppointmentID", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "ReportID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "appointment-index", "KeySchema": [{"AttributeName": "AppointmentID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}MedicalDocuments",
            "AttributeDefinitions": [
                {"AttributeName": "DocumentID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "DocumentID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Vitals",
            "AttributeDefinitions": [
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "RecordedAt", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "PatientID", "KeyType": "HASH"},
                {"AttributeName": "RecordedAt", "KeyType": "RANGE"}
            ]
        },
        {
            "TableName": f"{prefix}Invoices",
            "AttributeDefinitions": [
                {"AttributeName": "InvoiceID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"},
                {"AttributeName": "Status", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "InvoiceID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "status-index", "KeySchema": [{"AttributeName": "Status", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Reviews",
            "AttributeDefinitions": [
                {"AttributeName": "ReviewID", "AttributeType": "S"},
                {"AttributeName": "DoctorID", "AttributeType": "S"},
                {"AttributeName": "PatientID", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "ReviewID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "doctor-index", "KeySchema": [{"AttributeName": "DoctorID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "patient-index", "KeySchema": [{"AttributeName": "PatientID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}Notifications",
            "AttributeDefinitions": [
                {"AttributeName": "NotificationID", "AttributeType": "S"},
                {"AttributeName": "UserID", "AttributeType": "S"},
                {"AttributeName": "CreatedAt", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "NotificationID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "user-index", "KeySchema": [{"AttributeName": "UserID", "KeyType": "HASH"}, {"AttributeName": "CreatedAt", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}SupportTickets",
            "AttributeDefinitions": [
                {"AttributeName": "TicketID", "AttributeType": "S"},
                {"AttributeName": "UserID", "AttributeType": "S"},
                {"AttributeName": "Status", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "TicketID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "user-index", "KeySchema": [{"AttributeName": "UserID", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}},
                {"IndexName": "status-index", "KeySchema": [{"AttributeName": "Status", "KeyType": "HASH"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}AuditLogs",
            "AttributeDefinitions": [
                {"AttributeName": "LogID", "AttributeType": "S"},
                {"AttributeName": "UserID", "AttributeType": "S"},
                {"AttributeName": "Timestamp", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "LogID", "KeyType": "HASH"}],
            "GlobalSecondaryIndexes": [
                {"IndexName": "user-index", "KeySchema": [{"AttributeName": "UserID", "KeyType": "HASH"}, {"AttributeName": "Timestamp", "KeyType": "RANGE"}], "Projection": {"ProjectionType": "ALL"}}
            ]
        },
        {
            "TableName": f"{prefix}LoginHistory",
            "AttributeDefinitions": [
                {"AttributeName": "UserID", "AttributeType": "S"},
                {"AttributeName": "LoginAt", "AttributeType": "S"}
            ],
            "KeySchema": [
                {"AttributeName": "UserID", "KeyType": "HASH"},
                {"AttributeName": "LoginAt", "KeyType": "RANGE"}
            ]
        },
        {
            "TableName": f"{prefix}Specializations",
            "AttributeDefinitions": [
                {"AttributeName": "SpecializationID", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "SpecializationID", "KeyType": "HASH"}]
        },
        {
            "TableName": f"{prefix}SiteContent",
            "AttributeDefinitions": [
                {"AttributeName": "ContentKey", "AttributeType": "S"}
            ],
            "KeySchema": [{"AttributeName": "ContentKey", "KeyType": "HASH"}]
        }
    ]

    for table in tables_def:
        table['BillingMode'] = 'PAY_PER_REQUEST'
        try:
            logger.info(f"Creating table {table['TableName']}...")
            dynamodb.create_table(**table)
            logger.info(f"Successfully requested creation of {table['TableName']}")
        except ClientError as e:
            if e.response['Error']['Code'] == 'ResourceInUseException':
                logger.info(f"Table {table['TableName']} already exists.")
            else:
                logger.error(f"Error creating {table['TableName']}: {e}")
                
    logger.info("Table creation script completed.")

if __name__ == '__main__':
    create_tables()
""",
    "scripts/seed_admin.py": """import uuid
import os
import sys
from werkzeug.security import generate_password_hash

# Adjust path so we can import app modules
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app.repositories.user_repository import UserRepository

def seed_admin():
    repo = UserRepository()
    email = os.environ.get('ADMIN_EMAIL', 'admin@medtrack.local')
    password = os.environ.get('ADMIN_PASSWORD', 'Admin@123!')
    
    existing = repo.get_user_by_email(email)
    if existing:
        print(f"Admin {email} already exists.")
        return

    user_id = str(uuid.uuid4())
    password_hash = generate_password_hash(password, method='pbkdf2:sha256')
    
    repo.create_user(user_id, email, password_hash, 'Admin')
    print(f"Admin user {email} seeded successfully.")

if __name__ == '__main__':
    seed_admin()
""",
    "tests/test_db.py": """import os
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
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
