#!/bin/bash
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
