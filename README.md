# MedTrack - AWS Cloud Practitioner Capstone

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
- **Phase 10 (IAM & Hardening):** Strict least-privilege AWS IAM policies, Systems Manager Parameter Store setups, and Rate Limiting.
- **Phase 11 (Testing):** Robust Concurrency transaction testing in DynamoDB and RBAC route enforcement verifications.
- **Phase 12 (Deployment & Documentation):** EC2 bootstrap automation, CloudWatch metric dashboards, Mermaid architecture diagrams, and formal Capstone demo scripts.
