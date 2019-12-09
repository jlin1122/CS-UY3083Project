from flask import Flask, render_template, request, session, redirect, url_for, send_file
import os
import uuid
import hashlib
import pymysql.cursors
from functools import wraps
import time

app = Flask(__name__)
app.secret_key = "super secret key"
IMAGES_DIR = os.path.join(os.getcwd(), "images")
SALT = "cs3083"


connection = pymysql.connect(host="localhost",
                             user="root",
                             password="",
                             db="finsta",
                             charset="utf8mb4",
                             port=3306,
                             cursorclass=pymysql.cursors.DictCursor,
                             autocommit=True)

def login_required(f):
    @wraps(f)
    def dec(*args, **kwargs):
        if not "username" in session:
            return redirect(url_for("login"))
        return f(*args, **kwargs)
    return dec

@app.route("/")
def index():
    if "username" in session:
        return redirect(url_for("home"))
    return render_template("index.html")

@app.route("/home")
@login_required
def home():
    return render_template("home.html", username=session["username"])

@app.route("/upload", methods=["GET"])
@login_required
def upload():
    return render_template("upload.html")

@app.route("/follow", methods=["GET"])
@login_required
def follow():
    return render_template("follow.html")

@app.route("/request", methods=["GET"])
@login_required
def list_request():
    curr_user = session["username"]
    query = "SELECT * FROM follow WHERE username_followed = %s AND followstatus = 0"
    with connection.cursor() as cursor:
        cursor.execute(query, (curr_user))
    data = cursor.fetchall()
    #print(data)
    #return render_template('followers.html', username=username, flist=data, requests=newreqs, mefollow=mefollow)
    return render_template("request.html", requests = data)

@app.route("/accept", methods = ["GET","POST"])
@login_required
def accept():
    curr_user = session["username"]
    follower = request.form["follower"]
    query = "UPDATE follow SET followstatus = 1 WHERE username_followed = %s AND username_follower = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (curr_user, follower))
    return redirect(url_for("list_request"))


@app.route("/reject", methods = ["GET","POST"])
@login_required
def reject():
    curr_user = session["username"]
    follower = request.form["follower"]
    query = "DELETE FROM follow WHERE username_followed = %s AND username_follower = %s AND followstatus = 0"
    with connection.cursor() as cursor:
        cursor.execute(query, (curr_user, follower))
    return redirect(url_for("list_request"))

@app.route("/images", methods=["GET"])
@login_required
def images():
    query = "SELECT * FROM photo"
    with connection.cursor() as cursor:
        cursor.execute(query)
    data = cursor.fetchall()
    return render_template("images.html", images=data)

@app.route("/images/<image_name>", methods=["GET"])
def image(image_name):
    image_location = os.path.join(IMAGES_DIR, image_name)
    if os.path.isfile(image_location):
        return send_file(image_location, mimetype="image/jpg")

@app.route("/login", methods=["GET"])
def login():
    return render_template("login.html")

@app.route("/register", methods=["GET"])
def register():
    return render_template("register.html")

@app.route("/loginAuth", methods=["GET", "POST"])
def loginAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"] + SALT
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()

        with connection.cursor() as cursor:
            query = "SELECT * FROM person WHERE username = %s AND password = %s"
            cursor.execute(query, (username, hashedPassword))
        data = cursor.fetchone()
        if data:
            session["username"] = username
            return redirect(url_for("home"))

        error = "Incorrect username or password."
        return render_template("login.html", error=error)

    error = "An unknown error has occurred. Please try again."
    return render_template("login.html", error=error)

@app.route("/registerAuth", methods=["POST"])
def registerAuth():
    if request.form:
        requestData = request.form
        username = requestData["username"]
        plaintextPasword = requestData["password"]+SALT
        hashedPassword = hashlib.sha256(plaintextPasword.encode("utf-8")).hexdigest()
        firstName = requestData["fname"]
        lastName = requestData["lname"]
        bio = requestData["bio"]
        
        try:
            with connection.cursor() as cursor:
                query = "INSERT INTO person (username, password, firstName, lastName, bio) VALUES (%s, %s, %s, %s, %s)"
                cursor.execute(query, (username, hashedPassword, firstName, lastName, bio))
                #connection.commit()
        except pymysql.err.IntegrityError:
            error = "%s is already taken." % (username)
            return render_template('register.html', error=error)    

        return redirect(url_for("login"))

    error = "An error has occurred. Please try again."
    return render_template("register.html", error=error)

@app.route("/logout", methods=["GET"])
def logout():
    session.pop("username")
    return redirect("/")

@app.route("/uploadImage", methods=["GET", "POST"])
@login_required
def upload_image():
    if request.form:
        image_file = request.files.get("imageToUpload", "")
        image_name = image_file.filename
        filepath = os.path.join(IMAGES_DIR, image_name)
        image_file.save(filepath)
        allfollowers = request.form["AllFollowers"]
        caption = request.form["caption"]
        posting_time = time.strftime("%Y-%m-%d %H:%M:%S")
        username = session["username"]

        
        query = "INSERT INTO photo (postingdate, filepath, allFollowers, caption, photoPoster) VALUES (%s, %s, %s, %s, %s)"
        #print(posting_time, filepath, allfollowers, caption)
        #q2 = INSERT INTO sharedWith
        with connection.cursor() as cursor:
            cursor.execute(query, (posting_time, filepath, allfollowers, caption, username))
        message = "Image has been successfully uploaded."
        
        return render_template("upload.html", message=message)
    else:
        message = "Failed to upload image."
        return render_template("upload.html", message=message)

@app.route("/followUser", methods=["GET", "POST"])
@login_required
def follow_user():
    userToFollow = request.form["username"]
    curr_user = session["username"]
    #print(userToFollow)
    #print(curr_user)
    #check if there is already a follow request
    query = "SELECT COUNT(*) FROM follow WHERE username_followed = %s AND username_follower = %s"
    with connection.cursor() as cursor:
        cursor.execute(query, (userToFollow, curr_user))
    data = cursor.fetchone()
    #print(data)
    
    if data['COUNT(*)'] > 0:
        message = "You already sent a follow request or you already follow this user."
        return render_template("follow.html", message=message)
    else:
        q2 = "INSERT INTO follow (username_followed, username_follower, followStatus) VALUES (%s, %s, 0)"
        with connection.cursor() as cursor:
            cursor.execute(q2, (userToFollow, curr_user))
        message = "Follow request sent to " + str(userToFollow)
        return render_template("follow.html", message=message)

    #error = "An unknown error has occurred. Please try again."
    #return render_template("follow.html", error=error)


if __name__ == "__main__":
    if not os.path.isdir("images"):
        os.mkdir(IMAGES_DIR)
    app.run()