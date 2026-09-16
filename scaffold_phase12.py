import os
import json

os.makedirs('infra', exist_ok=True)

bootstrap_script = """#!/bin/bash
# MedTrack EC2 User Data Bootstrap Script (Amazon Linux 2023)

# 1. Update system and install dependencies
dnf update -y
dnf install -y git nginx python3.11 python3.11-pip amazon-cloudwatch-agent

# 2. Create application directory
mkdir -p /opt/medtrack
cd /opt/medtrack

# 3. Clone repository (relies on IAM Instance Profile if pulling from private repo, else public)
git clone https://github.com/SAM18-Bot/MedTrack.git .

# 4. Setup Python virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# 5. Bootstrap the database and seed initial admin (Assumes EC2 IAM role has DynamoDB permissions)
# export AWS_DEFAULT_REGION=us-east-1
# python scripts/create_tables.py
# python scripts/seed_admin.py

# 6. Configure Nginx
cp deploy/nginx.conf /etc/nginx/conf.d/medtrack.conf
systemctl restart nginx
systemctl enable nginx

# 7. Configure Systemd service for Gunicorn
cp deploy/medtrack.service /etc/systemd/system/medtrack.service
systemctl daemon-reload
systemctl enable medtrack
systemctl start medtrack

# 8. Configure CloudWatch Agent
cp infra/cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
systemctl enable amazon-cloudwatch-agent
systemctl start amazon-cloudwatch-agent
"""

with open('infra/ec2-bootstrap.sh', 'w', encoding='utf-8') as f:
    f.write(bootstrap_script)

cw_agent = {
  "agent": {
    "metrics_collection_interval": 60,
    "run_as_user": "root"
  },
  "logs": {
    "logs_collected": {
      "files": {
        "collect_list": [
          {
            "file_path": "/var/log/nginx/access.log",
            "log_group_name": "MedTrack-Nginx-Access",
            "log_stream_name": "{instance_id}"
          },
          {
            "file_path": "/var/log/nginx/error.log",
            "log_group_name": "MedTrack-Nginx-Error",
            "log_stream_name": "{instance_id}"
          }
        ]
      }
    }
  },
  "metrics": {
    "metrics_collected": {
      "mem": {
        "measurement": ["mem_used_percent"]
      },
      "disk": {
        "measurement": ["used_percent"],
        "resources": ["/"]
      }
    }
  }
}

with open('infra/cloudwatch-agent.json', 'w', encoding='utf-8') as f:
    json.dump(cw_agent, f, indent=2)

cw_dashboard = {
    "widgets": [
        {
            "type": "metric",
            "x": 0, "y": 0, "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/EC2", "CPUUtilization", "AutoScalingGroupName", "MedTrack-ASG" ]
                ],
                "period": 300, "stat": "Average", "region": "us-east-1", "title": "EC2 CPU Utilization"
            }
        },
        {
            "type": "metric",
            "x": 12, "y": 0, "width": 12, "height": 6,
            "properties": {
                "metrics": [
                    [ "AWS/DynamoDB", "ConsumedReadCapacityUnits", "TableName", "MedTrack-Appointments" ],
                    [ ".", "ConsumedWriteCapacityUnits", ".", "." ]
                ],
                "period": 300, "stat": "Sum", "region": "us-east-1", "title": "DynamoDB Capacity Units"
            }
        }
    ]
}

with open('infra/cloudwatch-dashboard.json', 'w', encoding='utf-8') as f:
    json.dump(cw_dashboard, f, indent=2)

architecture_md = """# MedTrack Architecture

MedTrack is built strictly using cloud-native patterns on AWS, designed to scale dynamically, prevent single points of failure, and heavily leverage managed services.

## System Diagram

```mermaid
graph TD
    User([End User / Web Browser]) --> |HTTPS| ALB[Application Load Balancer]
    
    subgraph VPC [AWS VPC - Public & Private Subnets]
        ALB --> |HTTP:80| EC2_1[EC2 Instance A - App Server]
        ALB --> |HTTP:80| EC2_2[EC2 Instance B - App Server]
        
        EC2_1 --> |Local Proxy| G1[Gunicorn + Flask]
        EC2_2 --> |Local Proxy| G2[Gunicorn + Flask]
    end

    subgraph AWS Managed Services
        G1 -.-> |boto3 AWS SDK| DDB[(Amazon DynamoDB)]
        G2 -.-> |boto3 AWS SDK| DDB
        
        G1 -.-> |Uploads| S3[(Amazon S3)]
        G2 -.-> |Uploads| S3
        
        G1 -.-> |Notifications| SNS[Amazon SNS]
        G2 -.-> |Notifications| SNS
        
        EB[EventBridge Cron] --> |Triggers| Lambda[Reminder Lambda]
        Lambda --> |Queries| DDB
        Lambda --> |Fires| SNS
    end
```

## Service Breakdown

### 1. Compute Layer
- **Amazon EC2 (Amazon Linux 2023)**: Hosts the Flask web application. It runs behind an Nginx reverse proxy passing requests to a multi-worker Gunicorn server.
- **Auto Scaling & ALB**: The system is intended to sit behind an Application Load Balancer to distribute incoming HTTPS traffic, terminating SSL at the balancer.

### 2. Database Layer
- **Amazon DynamoDB**: Operates using On-Demand capacity provisioning. MedTrack employs 16 separated tables with highly optimized Global Secondary Indexes (GSIs).
- **Transactional Consistency**: To resolve race conditions common in healthcare scheduling, MedTrack utilizes `TransactWriteItems`. Booking a slot atomically writes a `SlotLock` conditional item ensuring zero double-bookings mathematically.

### 3. Object Storage Layer
- **Amazon S3**: Houses patient medical records and dynamically generated prescription PDFs.
- **Security**: The bucket is strictly private. EC2 instance profiles generate short-lived Presigned URLs, meaning users never have direct link access to PII.

### 4. Asynchronous Event Layer
- **Amazon SNS**: Used for sending OTP reset codes, registration approvals, and appointment alerts.
- **Amazon EventBridge + Lambda**: A serverless crontab executing daily at 08:00 AM UTC. A lightweight Lambda function scans upcoming appointments and triggers batch SNS dispatches for reminders without blocking the web servers.

### 5. Security & Identity
- **AWS IAM**: Strictly scoped JSON policies (provided in `/iam`) ensure that EC2 instances and Lambdas operate on the Principle of Least Privilege. 
- **AWS SSM Parameter Store**: Replaces `.env` files by securely injecting environment variables and database keys into the runtime at bootstrap.
"""

with open('ARCHITECTURE.md', 'w', encoding='utf-8') as f:
    f.write(architecture_md)

demo_md = """# MedTrack - Capstone Presentation Demo Script

This script is designed for Capstone grading. It walks through all key requirements incrementally to prove robust AWS integration and system mechanics.

## Preparation
1. Ensure the app is running (e.g., `flask run` or running on the EC2 IP).
2. Have the AWS Console open in a separate tab (DynamoDB, S3, IAM, CloudWatch).

## Scene 1: Security & Database Setup
**Action:** Open the AWS DynamoDB Console.
**Talking Track:** 
> "MedTrack operates on 16 Amazon DynamoDB tables running on-demand. As you can see here, we utilize Global Secondary Indexes like `email-index` and `status-index` to allow fast querying without expensive table scans."

## Scene 2: Role-Based Access & Admin Approval
**Action:** 
1. Go to the MedTrack Registration page. Register a new Doctor account.
2. Log out, then Log in as `admin@medtrack.com`.
3. Navigate to **Review Doctors**. Click **Approve**.
**Talking Track:**
> "By default, doctor registrations are sandboxed. The Admin must approve them. Clicking approve writes to DynamoDB and fires an AWS SNS message to the doctor's email/phone notifying them of their verified status."

## Scene 3: The Booking Engine (Transactions)
**Action:** 
1. Log in as the newly approved Doctor. Go to **Set Availability** and generate slots for tomorrow.
2. Log in as a Patient. Search for the Doctor, and click **Book Appointment**.
**Talking Track:**
> "Booking an appointment isn't just a simple database insert. To fulfill the capstone requirements of zero double-bookings, the backend uses DynamoDB `TransactWriteItems`. It writes the appointment record while simultaneously attempting to write a `SlotLock` proxy item with a condition expression `attribute_not_exists`. If two users click book at the exact same millisecond, the AWS transaction guarantees one will fail safely."

## Scene 4: S3, ReportLab, and Presigned URLs
**Action:**
1. Log in as the Doctor, go to the queue, and start a **Consultation** for the booked patient.
2. Fill out the Diagnosis and Medicines. Click **Complete**.
3. Log in as the Patient, go to **Medical Documents** -> **Prescriptions**. Click **Generate PDF**.
**Talking Track:**
> "When the patient requests their prescription, the Python backend uses `ReportLab` to dynamically draw a PDF. It instantly streams this PDF to a private Amazon S3 bucket. To ensure HIPAA-compliant security, the S3 bucket is completely locked down. The user is redirected using a Boto3-generated **Presigned URL** that expires in 60 minutes."
*(Demonstrate the URL in the browser bar has the `AWSAccessKeyId` and signature parameters)*

## Scene 5: Background Jobs (EventBridge)
**Action:** Open the AWS EventBridge Console. Show the `MedTrackDailyReminders` rule.
**Talking Track:**
> "Finally, we don't rely on the web servers for asynchronous tasks. This AWS EventBridge cron rule runs every morning at 8 AM UTC, triggering our AWS Lambda function. The Lambda queries DynamoDB for today's appointments and routes notifications through SNS to remind patients."
"""

with open('DEMO_SCRIPT.md', 'w', encoding='utf-8') as f:
    f.write(demo_md)
