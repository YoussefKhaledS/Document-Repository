from flask import Blueprint, send_file, request, render_template, session, url_for, jsonify, redirect, flash
from models import *
from helpers.services import *
from helpers.validators import *
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash
from datetime import timedelta

auth_bp = Blueprint("auth", __name__)
main_bp = Blueprint("main", __name__)
helpers_bp = Blueprint("helpers", __name__)

#%% auth routes ------------------------------
@auth_bp.route("/signup", methods=["GET", "POST"])
def signup():
    # Only admins can access signup
    if "role" not in session or session.get("role") != "admin":
        flash("You must be an admin to access signup.", "error")
        return redirect(url_for("auth.login"))
    
    if request.method == "GET":
        return render_template("signup.html")
    data = request.json if request.is_json else request.form
    username = data.get("username", "").strip()
    email = data.get("email", "").strip()
    password = data.get("password", "").strip()
    role_name = data.get("role", "").strip()
    department_name = data.get("department", "").strip()

    # 1️⃣ Validate input (this now checks for required fields too)----------------------------------------
    errors = validate_user_input(
        email, username, password, role_name, department_name)
    if errors:
        return render_template("signup.html", error=errors)

    try:
        # 2️⃣ Create employee
        user = create_employee(username, email, password,
                               role_name, department_name)
        # 3️⃣ On success, tell frontend to redirect
        return redirect("/login")

    except IntegrityError as e:
        if "UNIQUE constraint failed: employees.name" in str(e):
            return render_template("signup.html", error="Username already exists")
        if "UNIQUE constraint failed: employees.email" in str(e):
            return render_template("signup.html", error="Email already exists")
        return render_template("signup.html", error="An error happened, please try again")

    except Exception:
        return render_template("signup.html", error="An error happened, please try again")
        # except Exception as e:
        #     return jsonify({"error": str(e)}), 500


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")

        user = Employee.query.filter_by(name=username).first()
        if user and check_password_hash(user.password_hash, password):
            session["user_id"] = user.id
            session["username"] = user.name
            session["role"] = user.role.name if user.role else None
            return redirect(url_for("main.index"))

        flash("Invalid username or password", "error")
        return render_template("login.html")

    return render_template("login.html")

#%% end auth routes ------------------------------


#%% main routes ------------------------------

@main_bp.route("/upload", methods=["GET", "POST"])
def upload_document():
    # ✅ Check if user is logged in
    if "username" not in session or "role" not in session:
        flash("You must be logged in to upload documents.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        title = request.form.get("title")
        version_number = request.form.get("version_number", type=float)
        departments = request.form.get("departments")  # multiple select
        tags = request.form.get("tags")  # multiple select
        file = request.files.get("file")

        uploader_name = session["username"]
        departments = [dept.strip().lower() for dept in departments.split(",")] if departments else []
        tags = [dept.strip().lower() for dept in tags.split(",")] if tags else []
        # print(departments, tags)
        # ✅ Validate
        error = validate_document(title ,file, version_number)
        if error:
            return render_template("upload.html", error=error)

        try:
            handle_document_upload(
                title=title,
                uploader_name=uploader_name,
                file=file,
                version_number=version_number,
                departments=departments,
                tags=tags,
            )
            flash("Document uploaded successfully!", "success")
            return redirect(url_for("main.index"))

        except sqlalchemy.exc.IntegrityError:
            # Example: duplicate title/version
            return render_template("upload.html", error="A document with the same title or version already exists.")
        except sqlalchemy.exc.SQLAlchemyError:
            # Any other database-related issue
            return render_template("upload.html", error="A database error occurred. Please try again.")
        except Exception:
            # Any other unexpected issue
            return render_template("upload.html", error="An unexpected error occurred. Please try again.")

    return render_template("upload.html")

@main_bp.route("/search", methods=["GET", "POST"])
def index(): #---------------- search documents route -----------------::
    # ✅ Ensure user is logged in
    if "username" not in session:
        flash("You must be logged in to search documents.", "error")
        return redirect(url_for("auth.login"))
    
    

    username = session["username"]

    if request.method == "GET":
        # Return accessible tags and uploaders for form dropdowns
        accessible = get_accessible_tags_uploaders(username)
        return render_template("search.html", accessible=accessible, results=None)

    if request.method == "POST":
        # Get form data
        title = request.form.get("title", "").strip()
        tags = request.form.getlist("tags")  # Multiple select returns a list
        uploader_names = request.form.getlist("uploader_names")  # Multiple select returns a list
        
        # Call service function
        try:
            results = search_documents(
                title=title, tags=tags, uploader_names=uploader_names, username=username)
        except Exception as e :
            results = []
            print(e)
            flash("An error occurred while searching documents.", "error")

        accessible = get_accessible_tags_uploaders(username)
        return render_template("search.html", accessible=accessible, results=results)

@main_bp.route("/document_info", methods=["GET"])
def document_info():
    # Ensure user is logged in
    if "username" not in session:
        flash("You must be logged in to view document details.", "error")
        return redirect(url_for("auth.login"))

    username = session["username"]
    title = request.args.get("title", type=str)

    if not title or not title.strip():
        flash("Missing document title.", "error")
        return redirect(url_for("main.index"))

    # Verify access before revealing metadata
    if not verify_user_document_access(username, title):
        return render_template("document_info.html", error="Access denied.", info=None)

    # Fetch version history
    info = get_document_version_history(title)
    if isinstance(info, dict) and info.get("error"):
        return render_template("document_info.html", error=info.get("error"), info=None)

    return render_template("document_info.html", error=None, info=info)

@main_bp.route("/test_all_route")
def test_all():
    # Only admins can access test data dump
    if "role" not in session or session.get("role") != "admin":
        return jsonify({"error": "Forbidden"}), 403
    data = {
        "employees": [
            {
                "id": e.id,
                "name": e.name,
                "email": e.email,
                "role": e.role.name if e.role else None,
                "department": e.department.name if e.department else None,
            }
            for e in Employee.query.all()
        ],
        "departments": [{"id": d.id, "name": d.name} for d in Department.query.all()],
        "roles": [{"id": r.id, "name": r.name} for r in Role.query.all()],
        "documents": [
            {
                "id": doc.id,
                "title": doc.title,
                "uploader_id": doc.uploader_id,
                "created_at": doc.created_at,
                "current_version_id": doc.current_version_id,
                "is_public": "not used anymore",
            }
            for doc in Document.query.all()
        ],
        "document_versions": [
            {
                "id": v.id,
                "document_id": v.document_id,
                "version_number": v.version_number,
                "filepath": v.filepath,
                "filename": v.filename,
                "uploaded_at": v.uploaded_at,
                "uploader_id": v.uploader_id,
            }
            for v in DocumentVersion.query.all()
        ],
        "tags": [{"id": t.id, "name": t.name} for t in Tag.query.all()],
        "document_tags": [
            {"document_id": dt.document_id, "tag_id": dt.tag_id}
            for dt in DocumentTag.query.all()
        ],
        "document_permissions": [
            {"document_id": dp.document_id, "department_id": dp.department_id}
            for dp in DocumentPermission.query.all()
        ],
    }
    return jsonify(data)

#%% end main routes ------------------------------

#%% helpers routes ------------------------------

@helpers_bp.route("/download", methods=["GET"])
def download_document():
    # Get parameters from query string
    title = request.args.get("title")
    version_number = request.args.get("version_number", type=float)
    
    # Validate required parameter
    if not title:
        return jsonify({"error": "Title parameter is required"}), 400
    
    # Get current user (you may need to adjust this based on your session handling)
    username = session.get("username")  # Fallback for testing
    
    # Verify user has access to the document
    if not verify_user_document_access(username, title):
        return jsonify({"error": "Access denied. You don't have permission to access this document."}), 403
    
    # Get document file
    metadata, filepath = get_document_file(title, version_number)
    if not filepath:
        return jsonify(metadata), 404

    # Return file for download
    return send_file(filepath, as_attachment=True, download_name=metadata["filename"])

@helpers_bp.route("/view", methods=["GET"])
def view_document():
    # Get parameters from query string
    title = request.args.get("title")
    version_number = request.args.get("version_number", type=float)
    
    # Validate required parameter
    if not title:
        return jsonify({"error": "Title parameter is required"}), 400
    
    # Get current user (you may need to adjust this based on your session handling)
    username = session.get("username")  # Fallback for testing
    
    # Verify user has access to the document
    if not verify_user_document_access(username, title):
        return jsonify({"error": "Access denied. You don't have permission to access this document."}), 403
    
    # Get document file
    metadata, filepath = get_document_file(title, version_number)
    if not filepath:
        return jsonify(metadata), 404
    
    # Return file for viewing (not download)
    return send_file(filepath, as_attachment=False)


