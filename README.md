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

This project connects to a MySQL database configured in `mediaidmain.py`:

```python
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://mediaidctrl:abcd1234@localhost:3306/mediaid'
```

Make sure MySQL is running and that a database named `mediaid` exists.

You can create it with:

```sql
CREATE DATABASE mediaid;
```

If needed, you can also create a matching MySQL user and adjust the connection string in the app.

## Initializing the Database Tables

The application defines models for users and hospital/doctor records, but the tables are not created automatically unless you run the following command in a Python shell:

```python
from mediaidmain import app, db
with app.app_context():
    db.create_all()
```

This will create the required tables in the configured database.

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

## Notes

- The app currently uses `debug=False` in the main entry point. For local development, you may change it to `debug=True` if needed.
- The database credentials and secret key are hardcoded in the app, so they should be moved to environment variables before production deployment.
- This project appears to be a template-driven Flask app using static assets and HTML templates under the `templates/` folder.

## License

This project does not currently include a license file. If you plan to distribute or publish it publicly, add an appropriate open-source license.
