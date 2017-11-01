######################################
# author ben lawson <balawson@bu.edu> 
# Edited by: Baichuan Zhou (baichuan@bu.edu) and Craig Einstein <einstein@bu.edu>
######################################
# Some code adapted from 
# CodeHandBook at http://codehandbook.org/python-web-application-development-using-flask-and-mysql/
# and MaxCountryMan at https://github.com/maxcountryman/flask-login/
# and Flask Offical Tutorial at  http://flask.pocoo.org/docs/0.10/patterns/fileuploads/
# see links for further understanding
###################################################

import flask
from flask import Flask, Response, request, render_template, redirect, url_for
from flaskext.mysql import MySQL
import flask.ext.login as flask_login
import time

# for image uploading
#from werkzeug import secure_filename
import os, base64

mysql = MySQL()
app = Flask(__name__)
app.secret_key = 'super secret string'  # Change this!

# These will need to be changed according to your creditionals
app.config['MYSQL_DATABASE_USER'] = 'root'
app.config['MYSQL_DATABASE_PASSWORD'] = 'hello'
app.config['MYSQL_DATABASE_DB'] = 'photoshare'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

# begin code used for login
login_manager = flask_login.LoginManager()
login_manager.init_app(app)

conn = mysql.connect()
cursor = conn.cursor()
cursor.execute("SELECT email FROM Users")
users = cursor.fetchall()


def getUserList():
    cursor = conn.cursor()
    cursor.execute("SELECT email FROM Users")
    return cursor.fetchall()


class User(flask_login.UserMixin):
    pass


@login_manager.user_loader
def user_loader(email):
    users = getUserList()
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    return user


@login_manager.request_loader
def request_loader(request):
    users = getUserList()
    email = request.form.get('email')
    if not (email) or email not in str(users):
        return
    user = User()
    user.id = email
    cursor = mysql.connect().cursor()
    cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email))
    data = cursor.fetchall()
    pwd = str(data[0][0])
    user.is_authenticated = request.form['password'] == pwd
    return user


'''
A new page looks like this:
@app.route('new_page_name')
def new_page_function():
    return new_page_html
'''


@app.route('/login', methods=['GET', 'POST'])
def login():
    if flask.request.method == 'GET':
        return '''
               <form action='login' method='POST'>
                <input type='text' name='email' id='email' placeholder='email'></input>
                <input type='password' name='password' id='password' placeholder='password'></input>
                <input type='submit' name='submit'></input>
               </form></br>
           <a href='/'>Home</a>
               '''
    # The request method is POST (page is recieving data)
    email = flask.request.form['email']
    cursor = conn.cursor()
    # check if email is registered
    if cursor.execute("SELECT password FROM Users WHERE email = '{0}'".format(email)):
        data = cursor.fetchall()
        pwd = str(data[0][0])
        if flask.request.form['password'] == pwd:
            user = User()
            user.id = email
            flask_login.login_user(user)  # okay login in user
            return flask.redirect(flask.url_for('protected'))  # protected is a function defined in this file

    # information did not match
    return "<a href='/login'>Try again</a>\
            </br><a href='/register'>or make an account</a>"


@app.route('/logout')
def logout():
    flask_login.logout_user()
    return render_template('hello.html', message='Logged out')


@login_manager.unauthorized_handler
def unauthorized_handler():
    return render_template('unauth.html')


# you can specify specific methods (GET/POST) in function header instead of inside the functions as seen earlier
@app.route("/register", methods=['GET'])
def register():
    return render_template('register.html', supress='True')


@app.route("/register", methods=['POST'])
def register_user():
    try:
        email = request.form.get('email')
        password = request.form.get('password')
    except:
        print(
            "couldn't find all tokens")  # this prints to shell, end users will not see this (all print statements go to shell)
        return flask.redirect(flask.url_for('register'))
    cursor = conn.cursor()
    test = isEmailUnique(email)
    if test:
        print(cursor.execute("INSERT INTO Users (email, password) VALUES ('{0}', '{1}')".format(email, password)))
        conn.commit()
        # log user in
        user = User()
        user.id = email
        flask_login.login_user(user)
        return render_template('hello.html', name=email, message='Account Created!')
    else:
        print("couldn't find all tokens")
        return flask.redirect(flask.url_for('register'))


def getUsersPhotos(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT imgdata, pid, caption FROM Photos WHERE uid = '{0}'".format(uid))
    return cursor.fetchall()  # NOTE list of tuples, [(imgdata, pid), ...]


def getUserIdFromEmail(email):
    cursor = conn.cursor()
    cursor.execute("SELECT uid  FROM Users WHERE email = '{0}'".format(email))
    return cursor.fetchone()[0]


def isEmailUnique(email):
    # use this to check if a email has already been registered
    cursor = conn.cursor()
    if cursor.execute("SELECT email  FROM Users WHERE email = '{0}'".format(email)):
        # this means there are greater than zero entries with that email
        return False
    else:
        return True


# end login code

@app.route('/profile')
@flask_login.login_required
def protected():
    return render_template('hello.html', name=flask_login.current_user.id, message="Here's your profile")










# begin photo uploading code
# photos uploaded using base64 encoding so they can be directly embeded in HTML 
ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg', 'gif'])


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS

@app.route('/create_album', methods=['GET', 'POST'])
@flask_login.login_required
def create_album():
    if request.method == 'POST':
        uid = getUserIdFromEmail(flask_login.current_user.id)
        album_title = request.form.get('album_title')

        if isAlbumTitleUnique(album_title):
            cursor = conn.cursor()
            date = time.strftime("%Y-%m-%d")
            cursor.execute('INSERT INTO Albums (Name, uid, Adate) VALUES (%s,%s,%s)', (album_title,uid,date))
            conn.commit()

            return render_template('hello.html', name=flask_login.current_user.id, message='Album Created Successfully', albums=getUsersAlbums(uid))
        else:
            return render_template('create_album.html', message="Pick a new title!")
    else:
        return render_template('create_album.html')


@app.route('/upload', methods=['GET', 'POST'])
@flask_login.login_required
def upload_file():
    user = getUserIdFromEmail(flask_login.current_user.id)
    if (getUsersAlbums(user)):
        if request.method == 'POST':
            photo = request.files['photo']
            photo_data = base64.standard_b64encode(photo.read())
            atit = request.form.get('album_title')
            aid = getAlbumIdFromTitle(atit)
            caption2 = request.form.get('caption')
            cursor = conn.cursor()

            if isAlbumTitleUnique(atit) == False and userOwnsAlbum(user, atit) == True:
                cursor.execute('INSERT INTO Photos(imgdata, caption, uid, aid) VALUES (%s,%s,%s,%s)', (photo_data, caption2, user, aid))
                conn.commit()
                return render_template('hello.html', name=flask_login.current_user.id, message='Photo Uploaded Successfully', photos=getUsersPhotos(user))
            else:
                return render_template('upload.html', name=flask_login.current_user.id, message='Not a valid Album', photos=getUsersPhotos(user))
        else:
            return render_template('upload.html')
    else:
        return render_template('create_album.html', message="Please create an album first!")

def isAlbumTitleUnique(album_title):
    cursor = conn.cursor()
    if cursor.execute("SELECT Name FROM Albums WHERE Name = '{0}'".format(album_title)):
        return False
    else:
        return True

def getUsersAlbums(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT Name, Adate FROM Albums WHERE uid='{0}'".format(uid))
    return cursor.fetchall()

def userOwnsAlbum(uid, album_title):
    cursor = conn.cursor()
    if cursor.execute("SELECT * FROM Albums WHERE Name = '{0}' AND uid = '{1}'".format(album_title, uid)):
        return True
    else:
        return False

def getAlbumIdFromTitle(album_title):
    cursor = conn.cursor()
    cursor.execute("SELECT aid FROM Albums WHERE Name = '{0}'".format(album_title))
    return cursor.fetchone()[0]

# end photo uploading code










@app.route('/albums', methods=['GET', 'POST'])
def albums():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    pix_with_tags_and_comments = []
    if request.method == 'POST':
        album_id = request.form.get('album_id')
        album_title = request.form["album_search"]

        for i in getAlbumPhotos(album_id, uid):
            pix_with_tags_and_comments += [getTagsAndComments(i)]
        return render_template("show_all_photos.html", photos=pix_with_tags_and_comments, album_title=album_title)
    else:
        return render_template("albums.html", albums=showAlbums(uid))

def showAlbums(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT Name, aid, aDate FROM Albums WHERE uid = '{0}'".format(uid))
    return cursor.fetchall()

def getAlbumPhotos(album_id, uid):
    cursor = conn.cursor()
    query = "SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A WHERE A.aid = P.aid AND A.aid = '{0}' AND A.uid = '{1}'"
    cursor.execute(query.format(album_id, uid))
    return cursor.fetchall()

def getTagsAndComments(photo):
	return [photo] + [getTags(photo[1])] + [getComments(photo[1])] + [getLikes(photo[1])]

def getLikes(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT COUNT(pid) FROM Likes WHERE pid ='{0}'".format(picture_id))
	return cursor.fetchall()

def getComments(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT C.content, U.uid from Comments C, Users U WHERE C.uid = U.uid AND C.pid = '{0}'".format(picture_id))
	return cursor.fetchall()

def getTags(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT word FROM photoTags WHERE pid = '{0}'".format(picture_id))
	return cursor.fetchall()











# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
