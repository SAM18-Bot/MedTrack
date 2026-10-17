#!/bin/bash
# MedTrack EC2 Bootstrap Script (Amazon Linux 2023)
set -e

echo "=== [1/8] Updating packages and installing prerequisites ==="
dnf update -y
dnf install -y git nginx python3.11 python3.11-pip amazon-cloudwatch-agent

echo "=== [2/8] Setting up application directory ==="
mkdir -p /opt/medtrack
cd /opt/medtrack

echo "=== [3/8] Cloning repository ==="
if [ ! -d "/opt/medtrack/.git" ]; then
    git clone https://github.com/SAM18-Bot/MedTrack.git .
else
    git pull origin main
fi

echo "=== [4/8] Setting up Python virtual environment ==="
python3.11 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

echo "=== [5/8] Configuring environment (.env) ==="
if [ ! -f "/opt/medtrack/.env" ]; then
    cp .env.example .env
    # Generate secure random secret key
    RANDOM_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
    sed -i "s/SECRET_KEY=.*/SECRET_KEY=${RANDOM_SECRET}/" .env
    sed -i "s/FLASK_ENV=.*/FLASK_ENV=production/" .env
fi

echo "=== [6/8] Initializing DynamoDB tables and Seeding Admin ==="
export AWS_DEFAULT_REGION=${AWS_DEFAULT_REGION:-us-east-1}
python scripts/create_tables.py || echo "Warning: Table creation reported an error or tables already exist."
python scripts/seed_admin.py || echo "Warning: Admin seed reported an error or already exists."

echo "=== [7/8] Configuring Nginx Reverse Proxy ==="
# On Amazon Linux 2023, disable default server block if present to avoid port 80 collision
if grep -q "server {" /etc/nginx/nginx.conf; then
    sed -i '/server {/,/^[[:space:]]*}/d' /etc/nginx/nginx.conf || true
fi
cp deploy/nginx.conf /etc/nginx/conf.d/medtrack.conf
nginx -t
systemctl restart nginx
systemctl enable nginx

echo "=== [8/8] Configuring Systemd and CloudWatch ==="
chown -R ec2-user:ec2-user /opt/medtrack

cp deploy/medtrack.service /etc/systemd/system/medtrack.service
systemctl daemon-reload
systemctl enable medtrack
systemctl restart medtrack

if [ -f "infra/cloudwatch-agent.json" ]; then
    cp infra/cloudwatch-agent.json /opt/aws/amazon-cloudwatch-agent/etc/amazon-cloudwatch-agent.json
    systemctl enable amazon-cloudwatch-agent || true
    systemctl restart amazon-cloudwatch-agent || true
fi

echo "=== MedTrack Deployment Complete! System is LIVE ==="
