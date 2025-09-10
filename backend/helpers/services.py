from datetime import datetime
from database import db
from models import *
from werkzeug.security import generate_password_hash
import os
from werkzeug.utils import secure_filename
from flask import jsonify
import uuid

FILES_DIR = "./files"

# %% not used 
# def create_department(name: str) -> Department:
    
#     department = Department(name=name)
#     db.session.add(department)
#     db.session.commit()
#     return department


# def create_role(name: str) -> Role:
    
#     role = Role(name=name)
#     db.session.add(role)
#     db.session.commit()
#     return role
#%%

def create_employee(username: str,email: str, password: str, role_name: str, department_name: str) -> Employee:
    """Create an employee, auto-creating role/department if they don’t exist."""
    username = username.strip().lower()
    role_name = role_name.strip().lower()
    department_name = department_name.strip().lower()
    # Find or create role
    role = Role.query.filter_by(name=role_name).first()
    if not role:
        role = Role(name=role_name)
        db.session.add(role)
        db.session.commit()

    # Find or create department
    department = Department.query.filter_by(name=department_name).first()
    if not department:
        department = Department(name=department_name)
        db.session.add(department)
        db.session.commit()

    # Hash password
    password_hash = generate_password_hash(password)

    # Create employee
    employee = Employee(
        name=username,
        email=email,
        password_hash=password_hash,
        role_id=role.id,
        department_id=department.id,
    )

    db.session.add(employee)
    db.session.commit()

    return employee


def handle_document_upload(
    title: str,
    uploader_name: str,
    file,  # this should be a FileStorage object from Flask
    version_number: float,
    departments: list[str],
    tags: list[str],
):
    # uploader_name = uploader_name.strip().lower()
    departments = sorted(set([d.strip().lower()
                         for d in departments or [] if d and d.strip()]))
    
    tags = sorted(set([t.strip().lower() for t in tags or [] if t and t.strip()]))
    uploader_name = uploader_name.strip().lower()
    
    os.makedirs(FILES_DIR, exist_ok=True)
    print("Departments:", departments)
    print("Tags:", tags)
    # 2. Find uploader
    uploader = Employee.query.filter_by(name=uploader_name).first()
    if not uploader:
        raise ValueError(f"Uploader '{uploader_name}' not found")

    # 3. Secure filename and save the file
    filename = secure_filename(file.filename)

    base_name, ext = os.path.splitext(filename)
    candidate = filename if filename else f"upload_{uuid.uuid4().hex}{ext}"
    filepath = os.path.join(FILES_DIR, candidate)

    # Ensure unique filename to avoid collisions
    if os.path.exists(filepath):
        unique_suffix = f"_{datetime.now().strftime('%Y%m%d%H%M%S')}_{uuid.uuid4().hex[:8]}"
        candidate = f"{base_name}{unique_suffix}{ext}"
        filepath = os.path.join(FILES_DIR, candidate)

    # Save file using the final unique name
    file.save(filepath)
    filename = candidate
    
    # 4. Check if document already exists (based on title)
    document = Document.query.filter_by(title=title).first()

    if not document:
        # New Document
        new_version = DocumentVersion(
            document_id=-1,  # we’ll set later
            version_number=version_number,
            filepath=filepath,
            filename=filename,
            uploaded_at=datetime.now(),
            uploader_id=uploader.id,
        )
        db.session.add(new_version)
        db.session.flush()  # so new_version.id is available

        document = Document(
            title=title,
            uploader_id=uploader.id,
            created_at=datetime.now(),
            current_version_id=new_version.id,
        )
        db.session.add(document)
        db.session.flush()

        # link version with document
        new_version.document_id = document.id

        # Permissions
        if not departments:
            exists = db.session.query(DocumentPermission).filter_by(
                document_id=document.id).first()
            if not exists:
                db.session.add(DocumentPermission(
                    document_id=document.id, department_id=None))
        else:
            set_document_department_permission(document.id, uploader.department_id)
            for dep_name in departments:
                dep = Department.query.filter_by(name=dep_name).first()
                if not dep:
                    dep = Department(name=dep_name)
                    db.session.add(dep)
                    db.session.flush()
                set_document_department_permission(document.id, dep.id)

        # Tags
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            add_document_tag_if_missing(document.id, tag.id)

    else:
        # Existing Document → Add new version
        new_version = DocumentVersion(
            document_id=document.id,
            version_number=version_number,
            filepath=filepath,
            filename=filename,
            uploaded_at=datetime.now(),
            uploader_id=uploader.id,
        )
        db.session.add(new_version)
        db.session.flush()

        # Update current version in Document
        document.current_version_id = new_version.id

        # Permissions update
        if departments:
            for dep_name in departments:
                dep = Department.query.filter_by(name=dep_name).first()
                if not dep:
                    dep = Department(name=dep_name)
                    db.session.add(dep)
                    db.session.flush()
                set_document_department_permission(document.id, dep.id)

        # Tags update
        for tag_name in tags:
            tag = Tag.query.filter_by(name=tag_name).first()
            if not tag:
                tag = Tag(name=tag_name)
                db.session.add(tag)
                db.session.flush()
            
            add_document_tag_if_missing(document.id, tag.id)

    # Commit all changes
    db.session.commit()
    return document


def set_document_department_permission(document_id: int, department_id: int) -> None:
    """
    - Remove 'public' (NULL) permission for the document if it exists
    - Add (document_id, department_id) if it does not already exist
    """
    # Remove public access (NULL department)
    db.session.query(DocumentPermission).filter_by(
        document_id=document_id, department_id=None
    ).delete(synchronize_session=False)

    # Add specific department permission if missing
    exists = db.session.query(DocumentPermission).filter_by(
        document_id=document_id, department_id=department_id
    ).first()

    if not exists:
        db.session.add(DocumentPermission(
            document_id=document_id, department_id=department_id
        ))

    db.session.commit()


def add_document_tag_if_missing(document_id: int, tag_id: int) -> bool:
    """
    Insert (document_id, tag_id) into document_tags if it does not already exist.
    Returns True if inserted, False if it already existed.
    """
    exists = DocumentTag.query.filter_by(
        document_id=document_id, tag_id=tag_id
    ).first()

    if exists:
        return False

    db.session.add(DocumentTag(document_id=document_id, tag_id=tag_id))
    db.session.commit()
    return True


def search_documents(title: str, tags: list[str], uploader_names: list[str], username: str):
    # Find requesting user
    user = Employee.query.filter_by(name=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")

    # Base query: join document + latest version + uploader
    query = Document.query

    # Filter by title (smart partial search)
    if title:
        query = query.filter(Document.title.ilike(f"%{title}%"))

    # Filter by uploader names
    if uploader_names:
        query = query.join(Employee, Employee.id == Document.uploader_id)\
                     .filter(Employee.name.in_(uploader_names))


# Filter by tags (must match ALL provided tags)
    if tags:
        # Use a subquery approach to avoid duplicate joins
        for tag_name in tags:
            tag_subquery = (
                db.session.query(DocumentTag.document_id)
                .join(Tag, Tag.id == DocumentTag.tag_id)
                .filter(Tag.name == tag_name)
                .subquery().select()
            )
            query = query.filter(Document.id.in_(tag_subquery))

    # Permissions: user’s department OR public (null)
    query = query.join(DocumentPermission, Document.id == DocumentPermission.document_id)\
                 .filter(
                     (DocumentPermission.department_id == user.department_id) |
                     (DocumentPermission.department_id.is_(None))
    )

    # Remove duplicates (in case of joins)
    query = query.distinct()

    results = query.all()
    return [doc.title for doc in results]


def get_document_version_history(title: str):
    
    # Find document
    document = Document.query.filter_by(title=title).first()
    if not document:
        return {"error": f"Document with title '{title}' not found"}

    # Query all versions with uploader info
    versions = (
        db.session.query(
            DocumentVersion.id.label("version_id"),
            DocumentVersion.version_number,
            DocumentVersion.filename,
            DocumentVersion.filepath,
            DocumentVersion.uploaded_at,
            Employee.name.label("uploader_name")
        )
        .join(Employee, Employee.id == DocumentVersion.uploader_id)
        .filter(DocumentVersion.document_id == document.id)
        .order_by(DocumentVersion.version_number.desc())  # newest first
        .all()
    )

    # Query uploader (creator) of the document
    creator = db.session.query(Employee.name).filter(Employee.id == document.uploader_id).first()
    creator_name = creator.name if creator else None

    # Query document tags
    tag_rows = (
        db.session.query(Tag.name)
        .join(DocumentTag, Tag.id == DocumentTag.tag_id)
        .filter(DocumentTag.document_id == document.id)
        .all()
    )
    doc_tags = [t.name for t in tag_rows]

    # Format result as JSON
    result = {
        "document_title": document.title,
        "uploader_name": creator_name,
        "tags": doc_tags,
        "versions": [
            {
                "version_id": v.version_id,
                "version_number": v.version_number,
                "filename": v.filename,
                "filepath": v.filepath,
                "uploaded_at": v.uploaded_at.isoformat(),
                "uploader_name": v.uploader_name,
            }
            for v in versions
        ],
    }

    return result


def get_document_file(title: str, version_number: int = None):
    
    # Find document
    document = Document.query.filter_by(title=title).first()
    if not document:
        return {"error": f"Document with title '{title}' not found"}, None

    query = (
        db.session.query(
            DocumentVersion.id.label("version_id"),
            DocumentVersion.version_number,
            DocumentVersion.filename,
            DocumentVersion.filepath,
            DocumentVersion.uploaded_at,
            Employee.name.label("uploader_name"),
        )
        .join(Employee, Employee.id == DocumentVersion.uploader_id)
        .filter(DocumentVersion.document_id == document.id)
    )

    if version_number is not None:
        query = query.filter(DocumentVersion.version_number == version_number)
    else:
        query = query.order_by(DocumentVersion.version_number.desc()).limit(1)

    version = query.first()

    if not version:
        return {"error": f"Version {version_number} not found for document '{title}'"}, None

    # Build response
    metadata = {
        "document_title": title,
        "version_id": version.version_id,
        "version_number": version.version_number,
        "filename": version.filename,
        "uploaded_at": version.uploaded_at.isoformat(),
        "uploader_name": version.uploader_name,
    }

    file_path = version.filepath if os.path.exists(version.filepath) else None

    return metadata, file_path


def get_accessible_tags_for_user(username: str):
    """
    Returns a list of unique tag names for documents accessible by the given user.
    Accessible = documents public or in user's department.
    """
    # Find the user
    user = Employee.query.filter_by(name=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")

    # Query all accessible documents (public or user's department)
    accessible_docs = (
        db.session.query(Document.id)
        .join(DocumentPermission, Document.id == DocumentPermission.document_id)
        .filter(
            (DocumentPermission.department_id == user.department_id) |
            (DocumentPermission.department_id.is_(None))
        )
        .distinct()
        .subquery().select()
    )

    # Query all tags for those documents
    tags = (
        db.session.query(Tag.name)
        .join(DocumentTag, Tag.id == DocumentTag.tag_id)
        .filter(DocumentTag.document_id.in_(accessible_docs))
        .distinct()
        .all()
    )

    # Return as a flat list of tag names
    return [tag.name for tag in tags]


def get_accessible_uploaders_for_user(username: str):
    """
    Returns a list of unique uploader names for documents accessible by the given user.
    Accessible = documents public or in user's department.
    """
    # Find the user
    user = Employee.query.filter_by(name=username).first()
    if not user:
        raise ValueError(f"User '{username}' not found")

    # Query all accessible documents (public or user's department)
    accessible_docs = (
        db.session.query(Document.id)
        .join(DocumentPermission, Document.id == DocumentPermission.document_id)
        .filter(
            (DocumentPermission.department_id == user.department_id) |
            (DocumentPermission.department_id.is_(None))
        )
        .distinct()
        .subquery().select()
    )

    # Query all unique uploader names for those documents
    uploaders = (
        db.session.query(Employee.name)
        .join(Document, Employee.id == Document.uploader_id)
        .filter(Document.id.in_(accessible_docs))
        .distinct()
        .all()
    )

    # Return as a flat list of uploader names
    return [uploader.name for uploader in uploaders]


def get_accessible_tags_uploaders(userName: str):
    
    tags = get_accessible_tags_for_user(userName)
    uploaders = get_accessible_uploaders_for_user(userName)
    return {"tags": tags, "uploaders": uploaders}


def verify_user_document_access(username: str, document_title: str) -> bool:
    
    # Find the user
    user = Employee.query.filter_by(name=username).first()
    if not user:
        return False
    
    # Find the document
    document = Document.query.filter_by(title=document_title).first()
    if not document:
        return False
    
    # Check if user has access to the document
    # Access is granted if:
    # 1. Document is public (department_id is None in DocumentPermission)
    # 2. User's department has permission to access the document
    
    has_access = (
        db.session.query(DocumentPermission)
        .filter(DocumentPermission.document_id == document.id)
        .filter(
            (DocumentPermission.department_id == user.department_id) |
            (DocumentPermission.department_id.is_(None))
        )
        .first()
    ) is not None
    
    return has_access