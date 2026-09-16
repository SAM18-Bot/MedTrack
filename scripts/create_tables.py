import os
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
