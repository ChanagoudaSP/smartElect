# Smart-Elect: Secure E-Voting System

A secure electronic voting system built with Flask and MySQL for account-based voter registration and ballot management.

## Features
- Email/password authentication
- Secure vote encryption
- Real-time election results
- Admin dashboard
- User registration and management
- Multiple election support

## Requirements
- Python 3.8+
- MySQL
- OpenCV
- Flask
- Other dependencies (see requirements.txt)

## Setup Instructions
1. Create a virtual environment:
```bash
python -m venv env
source env/bin/activate  # On Windows: .\env\Scripts\activate
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up MySQL database:
- Install MySQL
- Create a database named 'smart_elect' or use the default 'evoting_db'
- Run setup_database.py to initialize the database schema

4. Generate security keys:
```bash
python generate_keys.py
```

5. Run the application:
```bash
python run.py
```

## Project Structure
```
smart-elect/
├── app/
│   ├── models/
│   ├── routes/
│   ├── static/
│   ├── templates/
│   └── utils/
├── requirements.txt
├── run.py
└── README.md
```

## Security Features
- Secure account authentication
- End-to-end vote encryption
- Secure session management
- Protection against common web vulnerabilities

## License
MIT License 