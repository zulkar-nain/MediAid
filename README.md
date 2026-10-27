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

The app connects to a MySQL database named `mediaid`. Make sure MySQL is running and that the database exists. Create it if needed:

```sql
CREATE DATABASE mediaid;
```

When you start the app with `python mediaidmain.py`, it creates any missing tables from the application models. This is safe to run repeatedly; it does not delete existing data.

If you already created the `user` table before this update, expand its password column once so it can store secure password hashes:

```sql
ALTER TABLE user MODIFY password VARCHAR(255) NULL;
```

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
- `/medisugg` - Medical suggestion page
- `/logout` - Logout
- `/about` - About MediAid
- `/faq` - Frequently asked questions
- `/contact` - Website feedback form
- `/privacy` - Privacy overview
- `/emergency-info` - Public emergency guidance

## Notes

- The app currently uses `debug=False` in the main entry point. For local development, you may change it to `debug=True` if needed.
- The database credentials and secret key are hardcoded in the app, so they should be moved to environment variables before production deployment.
- This project appears to be a template-driven Flask app using static assets and HTML templates under the `templates/` folder.

## License

This project does not currently include a license file. If you plan to distribute or publish it publicly, add an appropriate open-source license.
## Pages and privacy

The public website includes the home page, About, FAQ, Contact, and Privacy overview pages. Contact-form submissions are stored in the `contact_message` database table; do not use the form to share medical or other sensitive information. The application creates this table automatically when it starts.

The account profile is available after signing in. The provider-assistance pages require an account, while general information and the public support pages can be browsed without one.

Hospital and doctor directory pages now read from their database tables instead of showing hard-coded sample cards. Add verified provider records to populate those pages. Emergency guidance is public and does not display unverified phone numbers.
