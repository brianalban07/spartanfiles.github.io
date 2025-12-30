from flask import Flask, render_template, request, redirect, url_for, session, abort, flash
from werkzeug.middleware.proxy_fix import ProxyFix
from werkzeug.utils import secure_filename
import os

# Initialize the Flask app
app = Flask(__name__)

# ProxyFix: Handle subpath "/spartanfiles" in NGINX
app.wsgi_app = ProxyFix(app.wsgi_app, x_prefix=1)

# Secret key for session and flash messages (ensure to use environment-secured key in production)
app.secret_key = os.urandom(24)

# Base directory where all files are stored
BASE_DIR = "/home/te-dl/Spartan_Files"
ALLOWED_EXTENSIONS = {
    'txt', 'pdf', 'docx', 'xlsx', 'pptx', 'png', 'jpg', 'jpeg',
    'mp4', 'avi', 'mov', 'mkv', 'log', 'zip', 'tar', 'gz', 'rar', '7z'
}

# Ensure the base directory exists
if not os.path.exists(BASE_DIR):
    os.makedirs(BASE_DIR)

# Hardcoded login credentials (Replace with a proper authentication system in production)
VALID_USERNAME = "wistron-dl"
VALID_PASSWORD = "Wistron@123"

# Helper: Check if a filename has a valid extension
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Authentication decorator
def login_required(f):
    def wrapper(*args, **kwargs):
        if 'username' not in session:
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrapper.__name__ = f.__name__  # Keep wrapper function's original name
    return wrapper

# Login route
@app.route("/spartanfiles/login", methods=["GET", "POST"])
def login():
    """
    Login page for user authentication.
    """
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        # Authenticate
        if username == VALID_USERNAME and password == VALID_PASSWORD:
            session['username'] = username  # Store user in the session
            flash("Login successful!", "success")  # Flash login success message
            return redirect(url_for("clear_flash_redirect"))  # Redirect to clear the flash
        else:
            flash("Invalid username or password.", "danger")

    return render_template("login.html")

# Intermediate route to clear flash messages before showing the index
@app.route("/spartanfiles/clear-flash-redirect")
def clear_flash_redirect():
    """
    Redirect route to consume any lingering flash messages after login.
    """
    messages = flash("")  # Consume flash messages from the session
    return redirect(url_for("index"))  # Redirect to the index page cleanly

# Logout route
@app.route("/spartanfiles/logout")
def logout():
    """
    Logout the user and clear session & flashed messages.
    """
    session.clear()  # Completely clear the session, including any flashed messages
    flash("You have been logged out.", "success")
    return redirect(url_for("login"))

# Protect the index route and all subsequent routes
@app.route("/spartanfiles/")
@login_required
def index():
    departments_data = {}
    departments = ["TE", "PE", "FAE", "ATE", "AFTE"]

    for department in departments:
        department_path = os.path.join(BASE_DIR, department)
        if os.path.exists(department_path) and os.path.isdir(department_path):
            categories = [
                d for d in os.listdir(department_path)
                if os.path.isdir(os.path.join(department_path, d))
            ]
            departments_data[department] = categories
        else:
            departments_data[department] = []  # No categories, empty list

    return render_template("index.html", departments_data=departments_data)

@app.route("/spartanfiles/<department>/<category>", methods=["GET", "POST"])
@login_required
def category_page(department, category):
    category_path = os.path.join(BASE_DIR, department, category)

    if not os.path.exists(category_path) or not os.path.isdir(category_path):
        abort(404)

    if request.method == "POST":
        if "file" in request.files:
            file = request.files["file"]
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                os.makedirs(category_path, exist_ok=True)
                file.save(os.path.join(category_path, filename))
                flash(f"File '{filename}' uploaded successfully!", "success")
            else:
                flash("Invalid file type or no file uploaded.", "danger")

        if "delete_file" in request.form:
            file_to_delete = request.form["delete_file"]
            file_path = os.path.join(category_path, file_to_delete)
            if os.path.exists(file_path):
                os.remove(file_path)
                flash(f"File '{file_to_delete}' deleted successfully!", "success")
            else:
                flash("File not found.", "danger")

        return redirect(url_for("category_page", department=department, category=category))

    files = [
        f for f in os.listdir(category_path) if os.path.isfile(os.path.join(category_path, f))
    ]
    return render_template("category.html", department=department, category=category, files=files)

@app.route("/spartanfiles/<department>/<category>/<filename>")
@login_required
def download_file(department, category, filename):
    category_path = os.path.join(BASE_DIR, department, category)

    if not os.path.exists(category_path):
        abort(404)
    file_path = os.path.join(category_path, filename)
    if not os.path.exists(file_path):
        abort(404)

    return send_from_directory(category_path, filename, as_attachment=True)

@app.errorhandler(404)
def not_found_error(error):
    return render_template("404.html"), 404

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
