# MediAid

MediAid is a Flask-based healthcare web application designed to help users discover hospitals, doctors, and medical information in a simple and user-friendly interface.

The app includes user authentication, hospital and doctor profile sections, emergency information, and a medical suggestion landing page.

## Features

- User registration and login
- Password hashing using Werkzeug
- Hospital and doctor information pages
- Medical suggestion interface
- Emergency information section
- MySQL-backed data persistence via Flask-SQLAlchemy

## Tech Stack

- Python
- Flask
- Flask-SQLAlchemy
- Flask-Login
- PyMySQL
- MySQL

## Project Structure

```text
MediAid/
├── mediaidmain.py         # Main Flask application
├── static/                # CSS, JS, images, and frontend assets
├── templates/             # HTML templates for the app
├── README.md              # Project documentation
└── .gitignore             # Git ignore rules (if present)
```

## Prerequisites

Before running the app, make sure you have:

- Python 3.9 or higher
- MySQL Server installed and running
- pip for installing Python packages

## Installation

1. Clone the repository:

```bash
git clone https://github.com/zulkar-nain/MediAid.git
cd MediAid
```

2. Create and activate a virtual environment:

```bash
python -m venv .venv
```

On Windows:

```bash
.venv\Scripts\activate
```

On macOS/Linux:

```bash
source .venv/bin/activate
```

3. Install the required packages:

```bash
python -m pip install -r requirements.txt
```

## Database Setup

The app uses MySQL/MariaDB by default. Make sure the server and `mediaid` database exist. Create the database if needed:

```sql
CREATE DATABASE mediaid;
```

Configure the connection string and a persistent secret key in your shell before starting the app. Do not commit credentials or secret keys:

```powershell
$env:MEDIAID_DATABASE_URI = "mysql+pymysql://USER:PASSWORD@127.0.0.1:3306/mediaid"
$env:MEDIAID_SECRET_KEY = "<a long random value>"
```

For local development without a MySQL server, you can instead set `MEDIAID_DATABASE_URI` to `sqlite:///mediaid-local.sqlite`.

When you start the app with `python mediaidmain.py`, it creates missing tables and adds the admin-related columns to existing provider and user tables. This is safe to run repeatedly and does not delete existing data. Back up the database before deploying schema changes.

If you already created the `user` table before this update, expand its password column once so it can store secure password hashes:

```sql
ALTER TABLE user MODIFY password VARCHAR(255) NULL;
```

## Creating the Initial Super Administrator

After configuring the database connection, bootstrap the first global administrator through Flask's interactive CLI:

```powershell
flask --app mediaidmain create-super-admin
```

The command prompts for an email, username, and password. Use a unique password with at least 12 characters. It creates a new account or promotes the matching existing account. There is no public admin-registration page.

## Administration and Privacy

The super administrator can create organizations, add existing registered accounts to organizations, assign tenant-admin roles, manage provider listings, inspect contact messages, and review security/admin audit events. Global administrators can also view private user notes; opening that page is recorded as an audit event.

Tenant administrators are restricted to their organization. They can add existing accounts to that organization, manage its provider listings, and promote members to tenant admins. Users may belong to multiple organizations and switch their active organization from the site navigation; a submitted organization is accepted only when the account belongs to it. Tenant administrators can see basic account details for members of their organization but **cannot view private user notes**. The app records authentication security and administrative events; it does not record general page browsing.

## Running the App

From the project root, run:

```bash
python mediaidmain.py
```

Then open your browser and visit:

```text
http://127.0.0.1:5000/
```

## Main Routes

- `/` - Landing page
- `/login` - User login
- `/register` - New user registration
- `/profiles` - User profile
- `/hospital-area` - Hospital area
- `/hospital-subject` - Hospital subject page
- `/doctor-area` - Doctor area
- `/doctor-subject` - Doctor subject page
- `/emergency-info` - Emergency information
- `/medisugg` - Searchable medical topics and specialties
- `/topics/<slug>` - Educational medical specialty guide
- `/logout` - Logout
- `/about` - About MediAid
- `/faq` - Frequently asked questions
- `/contact` - Website feedback form
- `/privacy` - Privacy overview
- `/emergency-info` - Public emergency guidance
- `/admin` - Administration dashboard (authorized accounts only)
- `/admin/organizations` - Organization management (super admin only)
- `/admin/members` - Active organization membership and roles
- `/admin/providers/hospitals` - Hospital listing management
- `/admin/providers/doctors` - Doctor listing management
- `/admin/users` - Authorized account profile metadata
- `/admin/audit` - Security and administration audit events
- `/admin/notes` - Private notes (super admin only; access audited)
- `/admin/messages` - Contact inbox (super admin only)

## Notes

- The app currently uses `debug=False` in the main entry point. For local development, you may change it to `debug=True` if needed.
- Set a persistent `MEDIAID_SECRET_KEY` and a production database URI through environment variables. Keep them out of source control.
- This project appears to be a template-driven Flask app using static assets and HTML templates under the `templates/` folder.

## License

This project does not currently include a license file. If you plan to distribute or publish it publicly, add an appropriate open-source license.
## Pages and privacy

The public website includes the home page, About, FAQ, Contact, Privacy overview, emergency guidance, and searchable medical topic pages. Medical topics are general education and link to MedlinePlus for reviewed health information; they do not diagnose conditions or recommend treatment. Contact-form submissions are stored in the `contact_message` database table; do not use the form to share medical or other sensitive information. The application creates this table automatically when it starts.

The account profile is available after signing in. The provider-assistance pages require an account, while general information and the public support pages can be browsed without one.

Hospital and doctor directory pages now read from their database tables instead of showing hard-coded sample cards. Add verified provider records to populate those pages. Emergency guidance is public and does not display unverified phone numbers.
