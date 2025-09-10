# Document Repository (Flask)

A Flask document repository with upload, versioning, search, and role/department-based access control.

## Setup (Windows)
```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

App runs at `http://127.0.0.1:5000/`.

Optional: create `backend/.env` with `SECRET_KEY=change-me`.
