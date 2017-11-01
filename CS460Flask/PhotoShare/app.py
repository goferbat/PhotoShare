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
            tags = str(request.form.get('tags')).split(' ')
            cursor = conn.cursor()

            if isAlbumTitleUnique(atit) == False and userOwnsAlbum(user, atit) == True:
                cursor.execute('INSERT INTO Photos(imgdata, caption, uid, aid) VALUES (%s,%s,%s,%s)', (photo_data, caption2, user, aid))
                conn.commit()
                pid = cursor.lastrowid
                addPhotoTags(tags, pid)
                return render_template('hello.html', name=flask_login.current_user.id, message='Photo Uploaded Successfully', photos=getUsersPhotos(user))
            else:
                return render_template('upload.html', name=flask_login.current_user.id, message='Not a valid Album', photos=getUsersPhotos(user))
        else:
            return render_template('upload.html')
    else:
        return render_template('create_album.html', message="Please create an album first!")

def addPhotoTags(tags, picture_id):
    cursor = conn.cursor()
    for i in tags:
        cursor.execute("INSERT INTO photoTags (word, pid) VALUES ('{0}', '{1}')".format(i, picture_id))
    conn.commit()

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







@app.route("/show_my_photos", methods=["POST", "GET"])
@flask_login.login_required
def myPix():
	user = getUserIdFromEmail(flask_login.current_user.id)
	pix = []
	for i in getUsersPhotos(user):
		pix += [getTagsAndComments(i)]
	return render_template("show_all_photos.html", photos=pix)

def getUsersPhotos(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A WHERE P.aid = A.aid "
                   "AND P.uid = '{0}'".format(uid))
	return cursor.fetchall()

@app.route("/albums_delete", methods=['GET', "POST"])
@flask_login.login_required
def geridofAlbum():
	user = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == 'POST':
		album_id = request.form.get('album_id')
		deleteAlbum(album_id, user)
		return render_template("hello.html", message="Album Deleted Successfully")
	else:
		return render_template("albums.html", albums=showAlbums(uid), message="You have no albums or the name was incorrect")

@app.route('/albums', methods=['GET', 'POST'])
def albums():
    uid = getUserIdFromEmail(flask_login.current_user.id)
    pix_with_tags_and_comments = []
    if request.method == 'POST':
        album_id = request.form.get('album_id')
        album_title = request.form["album_search"]

        for i in getAlbumPhotos(album_id, uid):
            pix_with_tags_and_comments += [getTagsAndComments(i)]
        return render_template("show_all_photos.html",photos=pix_with_tags_and_comments, album_title=album_title)
    else:
        return render_template("albums.html", albums=showAlbums(uid))

def deleteAlbum(album_id, uid):
	cursor = conn.cursor()
	pictures = getAlbumPhotos(album_id, uid)
	for pic in pictures:
		deletePhoto(pic[1])
	cursor.execute("DELETE FROM Albums WHERE aid='{0}'".format(album_id))
	conn.commit()

def deletePhoto(photo_id):
	cursor = conn.cursor()
	cursor.execute("DELETE FROM Likes where pid = '{0}'".format(photo_id))
	conn.commit()
	cursor.execute("DELETE FROM photoComments WHERE pid='{0}'".format(photo_id))
	conn.commit()
	cursor.execute("DELETE FROM photoTags WHERE pid='{0}'".format(photo_id))
	conn.commit()
	cursor.execute("DELETE FROM Photos WHERE pid='{0}'".format(photo_id))
	conn.commit()


def showAlbums(uid):
    cursor = conn.cursor()
    cursor.execute("SELECT Name, aid, aDate FROM Albums WHERE uid = '{0}'".format(uid))
    return cursor.fetchall()

def getAlbumPhotos(album_id, uid):
    cursor = conn.cursor()
    query = "SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A WHERE " \
            "A.aid = P.aid AND A.aid = '{0}' AND A.uid = '{1}'"
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
	cursor.execute("SELECT C.content, U.uid from Comments C, Users U, photoComments PC WHERE C.uid = U.uid AND PC.pid = '{0}'".format(picture_id))
	return cursor.fetchall()

def getTags(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT word FROM photoTags WHERE pid = '{0}'".format(picture_id))
	return cursor.fetchall()


@app.route("/show_all_photos", methods=['POST', 'GET'])
def showPix():
    if flask_login.current_user.is_authenticated:
        user = getUserIdFromEmail(flask_login.current_user.id)
    if request.method == 'POST':
        if request.form.get("comment"):
            comment = request.form.get("comment")
            photo_id = request.form.get("picture_id")
            if flask_login.current_user.is_authenticated:
                if (isCommentValid(photo_id, user)):
                    comment_id = addComment(comment, user)
                else:
                    return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                           message="All photos. You cannot comment on your own photo.")
            else:
                comment_id = addComment(comment, -1)
            addCommentToPhoto(comment_id, photo_id)

            return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                   message="All photos. Comment added!")
        elif request.form["photo_delete"]:
            photo_id = request.form.get("picture_id")
            if flask_login.current_user.is_authenticated:
                if currentUserOwnsPhoto(user, photo_id):
                    deletePhoto(photo_id)
                    return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                           message="Photo Deleted!")
                else:
                    return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                           message="You do not have permission to delete this photo.")
            else:
                return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                       message="You do not have permission to delete this photo.")
        else:
            return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                                   message="All photos")
    else:
        return render_template("show_all_photos.html", photos=displayAllPicturesWithCommentsAndTags(),
                               message="All photos")

@app.route("/like_pic", methods=["POST", "GET"])
@flask_login.login_required
def pics_liked():
    user = getUserIdFromEmail(flask_login.current_user.id)
    pix = displayAllPicturesWithCommentsAndTags()
    if request.method == 'POST':
        picture_id = request.form.get("picture_id")
        if likeValid(user, picture_id) == False:
            return render_template("show_all_photos.html", photos=pix,
                                       message="You've already liked this picture. Try again")
        else:
            likePic(user, picture_id)
            pix = displayAllPicturesWithCommentsAndTags()
            return render_template("show_all_photos.html", photos=pix,
                                       message="Photo liked!! Here are all pictures")
    else:
        return render_template("show_all_photos.html", photos=pix, message="Error liking picture. Try again")

def likePic(uid, picture_id):
	cursor= conn.cursor()
	cursor.execute("INSERT INTO Likes(uid, pid) VALUES('{0}', '{1}')".format(uid, picture_id))
	conn.commit()

def likeValid(uid, picture_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT uid FROM Likes WHERE uid ='{0}' AND pid='{1}'".format(uid, picture_id)):
		return False
	else:
		return True


def displayAllPicturesWithCommentsAndTags():
    pix_with_tags_and_comments = []
    for i in getAllPhotos():
        pix_with_tags_and_comments += [getTagsAndComments(i)]
    return pix_with_tags_and_comments

def addCommentToPhoto(comment_id, picture_id):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO photoComments(cid, pid) VALUES('{0}', '{1}')".format(comment_id, picture_id))
    conn.commit()

def currentUserOwnsPhoto(uid, picture_id):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Photos WHERE uid = '{0}' AND pid = '{1}'".format(uid, picture_id)):
		return True
	else:
		return False


def addComment(comment, uid):
    cursor = conn.cursor()
    cursor.execute("INSERT INTO Comments(content, uid) VALUES ('{0}', '{1}')".format(comment, uid))
    conn.commit()
    comment_id = cursor.lastrowid
    return comment_id

def isCommentValid(picture_id, uid):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM Photos WHERE pid = '{0}' AND uid='{1}'".format(picture_id, uid)):
		return False
	else:
		return True

def getAllPhotos():
    cursor = conn.cursor()
    cursor.execute(
        "SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A WHERE P.aid = A.aid")
    return cursor.fetchall()

#Tag Section

def getTags(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT word FROM photoTags WHERE pid = '{0}'".format(picture_id))
	return cursor.fetchall()

@app.route('/my_tag_search', methods=["POST", "GET"])
@flask_login.login_required
def searchMyTags():
	user = getUserIdFromEmail(flask_login.current_user.id)
	pix_with_tags_and_comments = []
	pix = []
	for i in getUsersPhotos(user):
		pix += [getTagsAndComments(i)]
	if request.method == "POST":
		tag = request.form.get('tag_name')
		for i in getUserTaggedPhotos(tag, user):
			pix_with_tags_and_comments += [getTagsAndComments(i)]
		if pix_with_tags_and_comments:
			return render_template("show_all_photos.html", photos=pix_with_tags_and_comments)
		else:
			return render_template("show_all_photos.html", message="Sorry, none, try again!")
	else:
		return render_template("show_all_photos.html", photos=pix)


def getUserTaggedPhotos(tag, uid):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A, photoTags T WHERE T.pid "
                   "= P.pid AND P.aid = A.aid AND T.word = '{0}' AND P.uid ='{1}'".format(tag, uid))
	return cursor.fetchall()

@app.route('/tag_search', methods=["POST", "GET"])
def searchTags():
	pix_with_tags_and_comments = []
	if request.method == "POST":
		if(request.form.get('tag_search')):
			tags = request.form.get('tag_search').split(" ")
			for i in getAllTaggedPhotos(tags):
				pix_with_tags_and_comments += [getTagsAndComments(i)]
		else:
			tag = request.form['common_tag']
			for i in getTaggedPhotos(tag):
				pix_with_tags_and_comments += [getTagsAndComments(i)]
		if pix_with_tags_and_comments:
			return render_template("show_all_photos.html", photos=pix_with_tags_and_comments)
		else:
			return render_template("tag_search.html", common=getMostCommonTags(), message="Sorry, none, try again!")
	else:
		return render_template("tag_search.html", common=getMostCommonTags())

def getTaggedPhotos(tag):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A, photoTags T "
                   "WHERE T.pid = P.pid AND P.aid = A.aid AND T.word = '{0}'".format(tag))
	return cursor.fetchall()


def tagValid(tag):
	cursor = conn.cursor()
	if cursor.execute("SELECT * FROM photoTags WHERE word = '{0}'".format(tag)):
		return True
	else:
		return False

def getTagQuery(tags):
	query = "SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A, photoTags T " \
            "WHERE T.pid = P.pid AND P.aid = A.aid AND T.word = '{0}'".format(tags[0])
	for i in range(1, len(tags)):
		query += " AND P.picture_id IN (SELECT P.picture_id  FROM Pictures P, Album A, Tagged_photos T " \
                 "WHERE T.picture_id = P.picture_id AND P.album_id = A.album_id AND T.word = '{0}')".format(tags[i])
	print(query)
	return query


def getAllTaggedPhotos(tags):
	cursor = conn.cursor()
	if len(tags) == 1:
		return getTaggedPhotos(tags[0])
	else:
		pics = getTaggedPhotos(tags[0])
		for i in pics:
			cursor.execute(getTagQuery(tags))
		return cursor.fetchall()


def getMostCommonTags():
	cursor = conn.cursor()
	cursor.execute("SELECT word, COUNT(word) FROM photoTags GROUP BY word ORDER BY COUNT(word) DESC LIMIT 5")
	return cursor.fetchall()

def getCommonTags(uid):
	cursor = conn.cursor()
	cursor.execute("SELECT T.word, Count(T.pid) FROM photoTags T, Photos P WHERE "
                   "P.pid = T.pid AND P.uid = '{0}' GROUP BY word ORDER BY Count(T.pid) DESC LIMIT 5".format(uid))
	return cursor.fetchall()

def commonTagsPhotoSearch(tag, uid):
	cursor = conn.cursor()
	query = "SELECT Tag.pid, Count(Tag.pid) as Pcount FROM ("
	for i in tag:
		query += "SELECT P.pid, T.word, P.uid FROM Photos P, photoTags T WHERE " \
                 "T.pid = P.pid AND T.word = '{0}'".format(i)
		query += " UNION "
	query = query[:-7] +  ") as Tag WHERE Tag.uid <> '{0}' GROUP BY Tag.pid ORDER BY Pcount DESC".format(uid)
	cursor.execute(query)
	suggested_photos_id = cursor.fetchall()
	suggested_photos = []
	for i in suggested_photos_id:
		suggested_photos += getPhotoFromPhotoId(i[0])
	return suggested_photos


def getPhotoFromPhotoId(picture_id):
	cursor = conn.cursor()
	cursor.execute("SELECT P.imgdata, P.pid, P.caption, A.Name FROM Photos P, Albums A WHERE P.aid = A.aid and "
                   "P.pid = '{0}'".format(picture_id))
	return cursor.fetchall()

@app.route("/recommend_tags", methods=["GET", "POST"])
@flask_login.login_required
def recommend():
	user = getUserIdFromEmail(flask_login.current_user.id)
	if request.method == "POST":
		tags = request.form.get("recommend_tags").split(" ")
		recommended_tags = getRecommendedTags(tags, user)
		return render_template("hello.html", tags=recommended_tags)
	else:
		return render_template("hello.html", message="Sorry, try again")


def getRecommendedTags(tags, uid):
	cursor = conn.cursor()
	query = "SELECT T.word, Count(T.word) as tcount FROM photoTags T, ("
	for i in tags:
		query += "SELECT P.pid, T.word FROM Photos P, Albums A, photoTags T " \
                 "WHERE T.pid = P.pid AND P.aid = A.aid AND T.word = '{0}'".format(i)
		query += " UNION "
	query = query[:-7] +  ") as Tags WHERE T.pid = T.pid"
	for i in tags:
		query += " AND T.word != '{0}'".format(i)
	query += "GROUP BY T.word ORDER BY tcount DESC"
	cursor.execute(query)
	return cursor.fetchall()


#MayLike

@app.route("/you_may_also_like")
@flask_login.login_required
def youMayLike():
	user = getUserIdFromEmail(flask_login.current_user.id)
	pix_with_tags_and_comments = []
	pics = getYouMayAlsoLike(user)
	for i in pics:
		pix_with_tags_and_comments += [getTagsAndComments(i)]
	return render_template("show_all_photos.html", message="You may also like", photos=pix_with_tags_and_comments)


def getYouMayAlsoLike(uid):
	cursor = conn.cursor()
	common_tags = getCommonTags(uid)
	lst = []
	for i in common_tags:
		lst += [i[0]]
	pics = commonTagsPhotoSearch(lst, uid)
	return pics

# default page
@app.route("/", methods=['GET'])
def hello():
    return render_template('hello.html', message='Welecome to Photoshare')


if __name__ == "__main__":
    # this is invoked when in the shell  you run
    # $ python app.py
    app.run(port=5000, debug=True)
