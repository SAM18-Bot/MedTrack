import os

readme = """# MedTrack - AWS Cloud Practitioner Capstone

![MedTrack Hero](https://via.placeholder.com/1200x400.png?text=MedTrack+-+Cloud+Healthcare+System)

MedTrack is a production-grade, highly available Cloud Healthcare Management System designed as an AWS Capstone project. It bridges the gap between healthcare providers and patients using modern cloud-native technologies.

## 🏗️ Architecture & AWS Integrations
- **Compute:** Amazon EC2 instances running Amazon Linux 2023. Served via Gunicorn + Nginx reverse proxy using Systemd.
- **Database:** Amazon DynamoDB (On-Demand) with 16 entity tables, Global Secondary Indexes (GSIs), conditional transactions (to prevent double-booking), and exponential backoff retry layers.
- **Storage:** Amazon S3 for storing patient medical records and dynamically generated prescription PDFs. All access is secured via short-lived Presigned URLs.
- **Notifications:** Amazon SNS for dispatching Email and SMS alerts for OTPs and appointment reminders.
- **Automation:** AWS EventBridge Cron rules triggering AWS Lambda functions to batch-process daily appointment reminders.
- **Web Framework:** Python 3.11, Flask (Application Factory, Blueprints), Flask-WTF, Flask-Limiter.

## 🚀 Core Features
- **Role-Based Access Control (RBAC):** Three distinct portals (Patient, Doctor, Admin) routing through a unified authentication gateway.
- **Advanced Booking Engine:** Double-booking prevention enforced at the database level using DynamoDB `TransactWriteItems` with condition expressions (`attribute_not_exists`).
- **Digital Prescriptions:** Dynamically renders PDF prescriptions on the fly using `ReportLab` and archives them directly into S3.
- **Vitals Tracking:** Interactive health charting utilizing `Chart.js` rendering historical patient DynamoDB metrics.
- **Comprehensive Security:** PBKDF2:SHA256 password hashing, CSRF protection across all forms, in-memory rate limiting, and 15-minute account lockouts after 5 failed attempts.
- **Audit Trails:** Immutable audit logging for every sensitive action within the platform.

## 🛠️ Local Development Setup

1. **Clone & Environment:**
   ```bash
   git clone https://github.com/SAM18-Bot/MedTrack.git
   cd MedTrack
   python -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

2. **Configuration:**
   Copy `.env.example` to `.env` and fill in your AWS credentials.

3. **Database Scaffold:**
   Run the DynamoDB table generator script. Ensure AWS credentials have DynamoDB full access.
   ```bash
   python scripts/create_tables.py
   python scripts/seed_admin.py
   ```

4. **Run Server:**
   ```bash
   flask run --debug
   ```

## 📦 Production Deployment (EC2)
*Configurations are provided in the `/deploy` directory.*
1. Clone repository to `/opt/medtrack`.
2. Symlink `deploy/nginx.conf` to `/etc/nginx/conf.d/medtrack.conf` and restart Nginx.
3. Symlink `deploy/medtrack.service` to `/etc/systemd/system/medtrack.service`.
4. Enable and start the service: `systemctl enable medtrack && systemctl start medtrack`.

## 🧪 Testing
The project leverages `pytest` and `moto` for comprehensive unit and integration testing against mocked AWS services.
```bash
pytest tests/
```
"""

os.makedirs('deploy', exist_ok=True)

with open('README.md', 'w', encoding='utf-8') as f:
    f.write(readme)
    
gunicorn_conf = """bind = "127.0.0.1:8000"
workers = 3
threads = 2
timeout = 120
"""
with open('gunicorn_config.py', 'w') as f:
    f.write(gunicorn_conf)

nginx_conf = """server {
    listen 80;
    server_name _;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    location /static {
        alias /opt/medtrack/app/static;
    }
}
"""
with open('deploy/nginx.conf', 'w') as f:
    f.write(nginx_conf)

systemd_conf = """[Unit]
Description=Gunicorn instance to serve MedTrack
After=network.target

[Service]
User=ec2-user
Group=www-data
WorkingDirectory=/opt/medtrack
Environment="PATH=/opt/medtrack/venv/bin"
EnvironmentFile=/opt/medtrack/.env
ExecStart=/opt/medtrack/venv/bin/gunicorn --config gunicorn_config.py run:app

[Install]
WantedBy=multi-user.target
"""
with open('deploy/medtrack.service', 'w') as f:
    f.write(systemd_conf)

errors = {
    "400": ("Bad Request", "The server could not understand the request due to invalid syntax."),
    "401": ("Unauthorized", "You must be authenticated to access this resource."),
    "403": ("Forbidden", "You do not have permission to view this directory or page using the credentials that you supplied."),
    "404": ("Not Found", "The medical record or page you are looking for does not exist."),
    "429": ("Too Many Requests", "You have exceeded your rate limit. Please wait a moment and try again."),
    "500": ("Internal Server Error", "The server encountered an internal error or misconfiguration and was unable to complete your request.")
}
os.makedirs('app/templates/errors', exist_ok=True)
for code, (title, desc) in errors.items():
    content = f"{{% extends 'base.html' %}}\n{{% block content %}}\n<div class='text-center py-5'>\n<h1 class='display-1 text-primary'>{code}</h1>\n<h2>{title}</h2>\n<p class='lead'>{desc}</p>\n<a href='/' class='btn btn-primary mt-3'>Return to Home</a>\n</div>\n{{% endblock %}}"
    with open(f"app/templates/errors/{code}.html", 'w') as f:
        f.write(content)
