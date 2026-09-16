import os

files = {
    "iam/ec2_instance_profile.json": """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:PutItem",
                "dynamodb:GetItem",
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:UpdateItem",
                "dynamodb:DeleteItem",
                "dynamodb:TransactWriteItems"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/MedTrack-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "s3:PutObject",
                "s3:GetObject"
            ],
            "Resource": [
                "arn:aws:s3:::medtrack-documents-*/*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "arn:aws:sns:*:*:MedTrack-*"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "ssm:GetParameter",
                "ssm:GetParametersByPath"
            ],
            "Resource": [
                "arn:aws:ssm:*:*:parameter/medtrack/*"
            ]
        }
    ]
}""",
    "iam/lambda_execution_role.json": """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "logs:CreateLogGroup",
                "logs:CreateLogStream",
                "logs:PutLogEvents"
            ],
            "Resource": "arn:aws:logs:*:*:*"
        },
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:Query"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/MedTrack-Appointments"
            ]
        },
        {
            "Effect": "Allow",
            "Action": [
                "sns:Publish"
            ],
            "Resource": [
                "arn:aws:sns:*:*:MedTrack-Alerts"
            ]
        }
    ]
}""",
    "iam/auditor_read_only.json": """{
    "Version": "2012-10-17",
    "Statement": [
        {
            "Effect": "Allow",
            "Action": [
                "dynamodb:Scan",
                "dynamodb:Query",
                "dynamodb:GetItem"
            ],
            "Resource": [
                "arn:aws:dynamodb:*:*:table/MedTrack-AuditLogs"
            ]
        }
    ]
}""",
    "scripts/setup_ssm.py": """import boto3
import argparse

def set_parameter(name, value, ptype="SecureString"):
    ssm = boto3.client('ssm')
    ssm.put_parameter(
        Name=f"/medtrack/prod/{name}",
        Description=f"MedTrack Prod Parameter: {name}",
        Value=value,
        Type=ptype,
        Overwrite=True
    )
    print(f"Set parameter: /medtrack/prod/{name}")

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Configure AWS Systems Manager Parameter Store for MedTrack")
    parser.add_argument("--secret-key", help="Flask SECRET_KEY")
    parser.add_argument("--s3-bucket", help="S3 Bucket Name")
    args = parser.parse_args()

    if args.secret_key:
        set_parameter("SECRET_KEY", args.secret_key)
    if args.s3_bucket:
        set_parameter("S3_BUCKET_NAME", args.s3_bucket, "String")
    
    if not args.secret_key and not args.s3_bucket:
        print("Usage: python setup_ssm.py --secret-key <key> --s3-bucket <bucket>")
"""
}

for path, content in files.items():
    dir_name = os.path.dirname(path)
    if dir_name:
        os.makedirs(dir_name, exist_ok=True)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
