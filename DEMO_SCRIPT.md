# MedTrack - Capstone Presentation Demo Script

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
