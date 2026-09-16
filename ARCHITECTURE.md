# MedTrack Architecture

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
