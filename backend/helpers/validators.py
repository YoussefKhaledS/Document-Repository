import re
import os
from werkzeug.datastructures import FileStorage
from models import Document,DocumentVersion

def validate_user_input(email: str, username: str, password: str, role_name: str, department_name: str) -> list:
    """
    Validate email, username, and password.
    Returns a list of error messages (empty if valid).
    """
    
    if not username or not email or not password or not role_name or not department_name:
        return "All fields are required."

    # --- Email Validation ---
    email_regex = r"^[\w\.-]+@[\w\.-]+\.\w+$"
    if not re.match(email_regex, email or ""):
        return "Invalid email format."

    # --- Username Validation ---
    if not username or len(username.strip()) < 3:
        return "Username must be at least 3 characters long."
    if " " in username:
        return "Username must not contain spaces."

    # --- Password Validation ---
    if not password or len(password) < 8:
        return "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password or ""):
        return "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password or ""):
        return "Password must contain at least one lowercase letter."
    if not re.search(r"[0-9]", password or ""):
        return "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password or ""):
        return "Password must contain at least one special character."

def validate_document(title: str, file: FileStorage, version_number: int) -> list:
    # --- File Validation ---
    if not file:
        return "File is required."
    else:
        # check filename
        filename = file.filename or ""
        if not filename.strip():
            return "Filename cannot be empty."

        # allowed extensions
        allowed_extensions = {"pdf", "doc", "docx", "txt"}
        ext = os.path.splitext(filename)[1].lower().lstrip(".")
        if ext not in allowed_extensions:
            return f"File extension .{ext} is not allowed. Allowed: {allowed_extensions}"

        # max size check (e.g., 10 MB)
        file.stream.seek(0, os.SEEK_END)
        size_mb = file.stream.tell() / (1024 * 1024)
        file.stream.seek(0)  # reset pointer
        if size_mb > 10:
            return "File size exceeds 10 MB."

    # --- Version Validation ---
    if not isinstance(version_number, (int, float)):
        return "Version number must be numeric."
    elif version_number <= 0:
        return "Version number must be positive."
    
    # --- Check for duplicate version number for the document title ---
    document = Document.query.filter_by(title=title).first()
    if document:
        existing_version = DocumentVersion.query.filter_by(
            document_id=document.id, version_number=version_number).first()
        if existing_version:
            return f"Version {version_number} for document '{title}' already exists."

