from datetime import datetime
from database import db


class Department(db.Model):
    __tablename__ = "departments"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Role(db.Model):
    __tablename__ = "roles"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class Employee(db.Model):
    __tablename__ = "employees"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(150), unique=True ,nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)

    role_id = db.Column(db.Integer, db.ForeignKey("roles.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey("departments.id"))

    role = db.relationship("Role", backref="employees", lazy=True)
    department = db.relationship("Department", backref="employees", lazy=True)


class Document(db.Model):
    __tablename__ = "documents"

    id = db.Column(db.Integer, primary_key=True)
    current_version_id = db.Column(
        db.Integer, db.ForeignKey("document_versions.id"))
    title = db.Column(db.String(200), nullable=False)
    uploader_id = db.Column(db.Integer, db.ForeignKey(
        "employees.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.now)

    uploader = db.relationship("Employee", backref="documents", lazy=True)

    # Explicitly tell which FK links to DocumentVersion
    current_version = db.relationship(
        "DocumentVersion",
        foreign_keys=[current_version_id],
        post_update=True
    )


class DocumentVersion(db.Model):
    __tablename__ = "document_versions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey(
        "documents.id"), nullable=False)
    version_number = db.Column(db.Float, nullable=False)
    filepath = db.Column(db.String(255), nullable=False)  # updated field
    filename = db.Column(db.String(255), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.now)
    uploader_id = db.Column(db.Integer, db.ForeignKey(
        "employees.id"), nullable=False)

    # ✅ Specify the foreign key here
    document = db.relationship(
        "Document",
        backref="versions",
        lazy=True,
        foreign_keys=[document_id]
    )

    uploader = db.relationship(
        "Employee", backref="uploaded_versions", lazy=True)


class Tag(db.Model):
    __tablename__ = "tags"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)


class DocumentTag(db.Model):
    __tablename__ = "document_tags"

    document_id = db.Column(db.Integer, db.ForeignKey(
        "documents.id"), primary_key=True)
    tag_id = db.Column(db.Integer, db.ForeignKey("tags.id"), primary_key=True)

    # ✅ Relationships
    document = db.relationship("Document", backref="document_tags", lazy=True)
    tag = db.relationship("Tag", backref="document_tags", lazy=True)


class DocumentPermission(db.Model):
    __tablename__ = "document_permissions"

    id = db.Column(db.Integer, primary_key=True)
    document_id = db.Column(db.Integer, db.ForeignKey(
        "documents.id"), nullable=False)
    department_id = db.Column(db.Integer, db.ForeignKey(
        "departments.id"), nullable=True)


