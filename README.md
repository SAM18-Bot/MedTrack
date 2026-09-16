# MedTrack

Production-Grade Cloud Healthcare Management System (AWS Cloud Practitioner Capstone).

## Setup
1. Create virtual environment: `python -m venv venv`
2. Activate it: `.\venv\Scripts\Activate.ps1`
3. Install dependencies: `pip install -r requirements.txt`
4. Run the app: `flask run`

## Phases Completed
- **Phase 1 (Scaffold):** Set up Flask application factory, blueprints, error pages, and design system.
- **Phase 2 (Database):** Created DynamoDB schema scripts, repository layer with exponential backoff, and admin seed script.
- **Phase 3 (Auth):** Implemented registration, login, lockouts, OTP, audit logging, and role-based routing.
- **Phase 4 (Public & Legal):** Marketing pages, substantive legal copies (DPDP/HIPAA), Support ticketing integration with SNS.
- **Phase 5 (Patient Portal):** Dashboard, doctor search, double-book protected appointment scheduling via DynamoDB conditional transactions, and Chart.js vitals tracker.
- **Phase 6 (Doctor Portal):** Availability manager, appointment queue, and split-screen consultation interface for diagnostics/prescriptions.
- **Phase 7 (Admin Portal):** Doctor verifications, user suspension, specialization CRUD, support desk routing, and full system audit logs.
