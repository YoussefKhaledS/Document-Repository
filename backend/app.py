import pandas as pd
from flask import Flask, jsonify, render_template
from models import *
from flask_migrate import Migrate
from seed_data import seed_data
from helpers.services import *
from werkzeug.datastructures import FileStorage
from routes.routes import *
from database import db
from dotenv import load_dotenv
import os
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

load_dotenv()


def rate_limit_key():
    return session.get("username") or get_remote_address()


def create_app():
    app = Flask(__name__, template_folder="../frontend/templates")
    app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///siemens.db"
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.permanent_session_lifetime = timedelta(days=7)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
    limiter = Limiter(
        key_func=rate_limit_key,
        # <- one global limit for all routes
        default_limits=["100 per minute"],
    )
    # limiter.init_app(app)
    db.init_app(app)

    with app.app_context():
        db.create_all()
        # seed_data()

    app.register_blueprint(auth_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(helpers_bp)

    @app.route("/")
    def notIndex():
        return redirect(url_for("main.index"))

    # %% for testing only ------------------------------
    @app.route("/viewer")
    def viewer():
        return render_template("test_all.html")

    @app.route("/sql_playground", methods=["GET", "POST"])
    def sql_playground():
        
        from flask import render_template
        from sqlalchemy import text
        if "role" not in session or session.get("role").lower() != "admin":
            flash("You must be an admin to access signup.", "error")
            return redirect(url_for("auth.login"))
        result_html = ""
        query = ""

        if request.method == "POST":
            query = request.form["query"]
            try:
                result = db.session.execute(text(query))
                rows = result.fetchall()

                if rows:
                    df = pd.DataFrame(rows, columns=result.keys())
                    result_html = df.to_html(
                        classes="table table-bordered", index=False)
                else:
                    result_html = "<p>No rows returned.</p>"
            except Exception as e:
                result_html = f"<p style='color:red;'>Error: {e}</p>"
        return render_template("sql_playground.html", query=query, result_html=result_html)

    # @app.route("/create_employee")
    # def create_employee_route():
    #     create_employee("youssef_cf", "dc2@gmai.com", "abc2",
    #                     "Developer", "Engineering")
    #     return jsonify({"message": "Employee created!"})

    # @app.route("/upload_document")
    # def upload_document_route():

    #     with open("../../Technical Assessment.pdf", "rb") as f:
    #         file_storage = FileStorage(
    #             stream=f,
    #             filename="Technical Assessment.pdf"
    #         )
    #         document = handle_document_upload(
    #             title="sample doc",
    #             uploader_name="youssef",
    #             file=file_storage,
    #             version_number=1,
    #             departments=["IT", "HR"],
    #             tags=["tag1", "tag2"],
    #         )
    #     return jsonify({"message": f"Document '{document.title}' uploaded!", "id": document.id})

    # @app.route("/search")
    # def get_documents():
    #     return search_documents(None, None, None, "Bob HR")

    # @app.route("/versions")
    # def get_versions():

    #     return get_document_version_history("sample doc")

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True)
