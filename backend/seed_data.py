from models import *
from werkzeug.security import generate_password_hash


def seed_data():
    """Insert sample data if tables are empty."""
    if Role.query.first():
        return  # Already seeded

    # Roles (lowercase)
    admin_role = Role(name="admin")
    user_role = Role(name="user")
    manager_role = Role(name="manager")

    # Departments (lowercase)
    hr = Department(name="hr")
    it = Department(name="it")
    finance = Department(name="finance")
    legal = Department(name="legal")
    sales = Department(name="sales")

    db.session.add_all([admin_role, user_role, manager_role, hr, it, finance, legal, sales])
    db.session.commit()

    # Employees (usernames lowercase)
    employees = [
        Employee(name="alice admin", email="alice@siemens.com", password_hash=generate_password_hash("admin123"), role_id=admin_role.id, department_id=it.id),
        Employee(name="bob hr", email="bob@siemens.com", password_hash=generate_password_hash("bob123"), role_id=user_role.id, department_id=hr.id),
        Employee(name="charlie it", email="charlie@siemens.com", password_hash=generate_password_hash("password123"), role_id=user_role.id, department_id=it.id),
        Employee(name="diana finance", email="diana@siemens.com", password_hash=generate_password_hash("password123"), role_id=manager_role.id, department_id=finance.id),
        Employee(name="eve legal", email="eve@siemens.com", password_hash=generate_password_hash("password123"), role_id=user_role.id, department_id=legal.id),
        Employee(name="frank sales", email="frank@siemens.com", password_hash=generate_password_hash("password123"), role_id=user_role.id, department_id=sales.id),
        Employee(name="grace hr", email="grace@siemens.com", password_hash=generate_password_hash("password123"), role_id=user_role.id, department_id=hr.id),
        Employee(name="henry it", email="henry@siemens.com", password_hash=generate_password_hash("password123"), role_id=manager_role.id, department_id=it.id),
    ]
    db.session.add_all(employees)
    db.session.commit()

    # Find helper by name
    def emp(name):
        return Employee.query.filter_by(name=name).first()

    # Tags (lowercase)
    tags = [
        Tag(name="policy"), Tag(name="hr"), Tag(name="finance"), Tag(name="security"),
        Tag(name="onboarding"), Tag(name="compliance"), Tag(name="technical"), Tag(name="sales")
    ]
    db.session.add_all(tags)
    db.session.commit()

    def tag(name):
        return Tag.query.filter_by(name=name).first()

    # Documents with multiple versions (uploader names and tag names lowercase)
    docs = [
        {"title": "Employee Handbook", "versions": [
            {"version": 1.0, "file": "Final_Documentation.pdf", "uploader": "alice admin"},
            {"version": 1.1, "file": "Technical_Assessment.pdf", "uploader": "bob hr"},
        ], "tags": ["policy", "hr"], "permissions": [hr]},
        {"title": "IT Security Policy", "versions": [
            {"version": 1.0, "file": "Technical_Assessment.pdf", "uploader": "henry it"},
            {"version": 2.0, "file": "Final_Documentation.pdf", "uploader": "charlie it"},
        ], "tags": ["security", "compliance", "technical"], "permissions": [it]},
        {"title": "Quarterly Finance Report", "versions": [
            {"version": 1.0, "file": "Exam_report.pdf", "uploader": "diana finance"},
            {"version": 1.1, "file": "Final_Documentation.pdf", "uploader": "diana finance"},
        ], "tags": ["finance", "compliance"], "permissions": [finance]},
        {"title": "Sales Playbook", "versions": [
            {"version": 1.0, "file": "Final_Documentation.pdf", "uploader": "frank sales"},
        ], "tags": ["sales"], "permissions": [sales]},
        {"title": "Legal Guidelines", "versions": [
            {"version": 1.0, "file": "Final_Documentation.pdf", "uploader": "eve legal"},
        ], "tags": ["compliance"], "permissions": [legal]},
        {"title": "Onboarding Checklist", "versions": [
            {"version": 1.0, "file": "Final_Documentation.pdf", "uploader": "grace hr"},
            {"version": 1.2, "file": "Exam_report.pdf", "uploader": "bob hr"},
        ], "tags": ["onboarding", "hr"], "permissions": [hr, None]},
        {"title": "Infrastructure Overview", "versions": [
            {"version": 1.0, "file": "Technical_Assessment.pdf", "uploader": "henry it"},
        ], "tags": ["technical"], "permissions": [it, None]},
        {"title": "Company Policies", "versions": [
            {"version": 1.0, "file": "Final_Documentation.pdf", "uploader": "alice admin"},
        ], "tags": ["policy", "compliance"], "permissions": [None]},
        {"title": "Benefits Overview", "versions": [
            {"version": 1.0, "file": "Exam_report.pdf", "uploader": "grace hr"},
        ], "tags": ["hr"], "permissions": [hr, None]},
        {"title": "Network Topology", "versions": [
            {"version": 1.0, "file": "Technical_Assessment.pdf", "uploader": "charlie it"},
            {"version": 1.1, "file": "Final_Documentation.pdf", "uploader": "henry it"},
        ], "tags": ["technical", "security"], "permissions": [it]},
    ]

    created_docs = []
    for d in docs:
        # Create document by first version uploader
        creator = emp(d["versions"][0]["uploader"])
        doc = Document(title=d["title"], uploader_id=creator.id)
        db.session.add(doc)
        db.session.flush()

        current_version_id = None
        for ver in d["versions"]:
            uploader_emp = emp(ver["uploader"])
            filename = ver["file"]
            filepath = f"files/{filename}"
            v = DocumentVersion(
                document_id=doc.id,
                version_number=ver["version"],
                filepath=filepath,
                filename=filename,
                uploader_id=uploader_emp.id,
            )
            db.session.add(v)
            db.session.flush()
            current_version_id = v.id  # last one is current

        # Set current version
        doc.current_version_id = current_version_id
        db.session.add(doc)
        db.session.flush()

        # Tags
        for t in d["tags"]:
            t_row = tag(t)
            if t_row:
                db.session.add(DocumentTag(document_id=doc.id, tag_id=t_row.id))

        # Permissions: allow None for public
        for dep in d["permissions"]:
            if dep is None:
                db.session.add(DocumentPermission(document_id=doc.id, department_id=None))
            else:
                db.session.add(DocumentPermission(document_id=doc.id, department_id=dep.id))

        created_docs.append(doc)

    db.session.commit()

    print("✅ Database seeded with rich sample data!")
