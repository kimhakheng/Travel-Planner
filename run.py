from flask import Flask, flash, render_template, request, redirect, session, url_for
from flask_wtf import Form
from wtforms import StringField
from wtforms.widgets import TextArea
from wtforms.validators import DataRequired
import hashlib
import pymysql
import time

app = Flask(__name__)
app.config['SECRET_KEY'] = '8ffe05624dfe0efdf7c7f67288d4f4ce5005e0dfb6a1bc48366ef9906dd0586e'

#####################################################################
#                          WTF FORMS                                #
#####################################################################
class ReviewForm(Form):
    title = StringField('review_title', validators=[DataRequired()])
    body = StringField('review_body', widget=TextArea(), validators=[DataRequired()])

#####################################################################
#                          WEB PAGES                                #
#####################################################################

# Visit site for first time. Pictures.
@app.route('/')
@app.route('/index')
def index():
	return render_template('index.html')

# Login/Registration Page. Redirects to home if already logged in.
@app.route('/login-page')
def login_page():

	# Show login page if not logged in, edirect to home if already logged in.
	if 'username' not in session or session['username'] == '':
		return render_template('login.html')
	else:
		return redirect(url_for('home'))

# Home page. Displays admin interface if user is admin.
@app.route('/home')
def home():

	# Disallow unlogged in users from requesting homepage.
	if 'username' not in session or session['username'] is '':
		return redirect(url_for('index'))

	# Query database when user is admin for admin panel
	rows = []
	if session['is_admin']:
		cursor = db.cursor()
		cursor.execute("select * from user;")
		rows = [dict(is_admin="Yes" if row[3] == 1 else "No", username=row[0], password=row[1], first_name=row[4], last_name=row[5], email=row[2], suspended="Yes" if row[7] == 1 else "No") for row in cursor.fetchall()]

	return render_template("home.html", session=session, items=rows)

# Shows current trip itinerary.
@app.route('/trip')
def trip():
	return render_template('trip.html', session=session)

# Shows all available attractions.
@app.route('/attractions')
def attractions():
	return render_template('attractions.html', session=session)

# Select visisted attraction to review.
@app.route('/review')
def reviews():

	# TODO: Write SQL query that gets all the past activities completed by this user.
	# Also find out which index into row to get the date, name, and description.
	cursor = db.cursor()
	cursor.execute("select * from user;")
	attractions = [dict(date=row[0], name=row[2], description=row[1]) for row in cursor.fetchall()]
	return render_template('review.html', items=attractions, session=session)

#####################################################################
#                            REQUESTS                               #
#####################################################################

# On Login Form Submit. Loads home page or shows error.
@app.route('/login', methods=['POST'])
def verify_credentials():

	# Parse user input fields
	name=request.form['login_username']
	password=hashlib.sha256(request.form['login_password'].encode('utf-8')).hexdigest()

	# Query Database
	cursor = db.cursor()
	cursor.execute("select * from user where username = '" + name + "' and password = '" + password + "';")
	rows = cursor.fetchall()
	error = None

	if rows:
		# User found
		if rows[0][7] != 1:
			# Not suspended
			session['username'] = rows[0][0]
			session['email'] = rows[0][2]
			session['is_admin'] = rows[0][3]
			session['name'] = rows[0][4]	
			return redirect(url_for('home'))
		else:
			# Suspended user
			error='User suspended.'
	else:
		# No such user. Login again.
		error = 'Incorrect username or password. Please try again.'
	return render_template('login.html', error=error)

# On Register Form Submit. Loads home page.
# TODO: Put proper address for each user. Re-fill out correct fields when registration fails.
@app.route('/register', methods=['POST'])
def register():

	# Parse user input fields
	name=request.form['register_username']
	password1=hashlib.sha256(request.form['register_password'].encode('utf-8')).hexdigest()
	password2=hashlib.sha256(request.form['register_password2'].encode('utf-8')).hexdigest()
	firstname=request.form['register_firstname']
	lastname=request.form['register_lastname']
	email=request.form['register_email']
	street=request.form['register_streetaddress']
	city=request.form['register_city']
	state=request.form['register_state']
	zipcode=request.form['register_zip']

	# Check if all user fields filled in
	if name == '' or password1 == '' or password2 == '' or firstname == '' or firstname == '' or lastname == '' or email == '' or street == '' or city == '' or state == '' or zipcode == '':
		error = 'Please fill out all the fields.'
		return render_template('login.html', error2=error, scroll="register")

	# Check that passwords match
	if password1 != password2:
		error = 'Passwords do not match.'
		return render_template('login.html', error2=error, scroll="register")

	# Parse street_no from street
	street_no = -1

	# Check that address is valid format
	if len(street.split(" ")) < 3 or not street.split(" ")[0].isdigit():
		error = 'Street Address format not recognized. Please re-enter.'
		return render_template('login.html', error2=error, scroll="register")

	street_no = str(street.split(" ")[0])
	street = street[street.index(" ") + 1:]

	# Write to Database
	cursor = db.cursor()
	cursor.execute("insert into address (street_no, street_name, city, state, zip) values ("
			+ street_no + ", '" + street + "', '" + city + "', '" + state + "', '" + zipcode + "');")
	cursor.execute("insert into user (username, password, email, is_admin, first_name, last_name, address_id, suspended) values ('"
	+ name + "', '" + password1 + "', '" + email + "', false, '" + firstname + "', '" + lastname + "', 1, 0);") # TODO: Remove 1 and replace with address ID of newly created address
	db.commit()

	# Update current user session
	session['username'] = name
	session['name'] = firstname
	session['is_admin'] = 0
	session['email'] = email
	return redirect(url_for('home'))

# Logs out of system and redirects to pictures.
@app.route('/logout')
def logout():
	# Clear out session variables
	session.clear()
	return redirect(url_for('index'))

# Delete user from admin panel
@app.route('/delete-user/<username>')
def delete_user(username):

	cursor = db.cursor()
	cursor.execute("delete from user where username='" + username + "';")
	db.commit()

	return redirect(url_for('home'))

# Suspend user from admin panel
@app.route('/suspend-user/<username>')
def suspend_user(username):

	cursor = db.cursor()
	cursor.execute("select suspended from user where username='" + username + "';")
	if cursor.fetchall()[0][0] == 1:
		cursor.execute("update user set suspended=0 where username='" + username + "';")
	else:
		cursor.execute("update user set suspended=1 where username='" + username + "';")
	db.commit()

	return redirect(url_for('home'))

# Make user an Admin from admin panel
@app.route('/make-admin/<username>')
def make_admin(username):

	cursor = db.cursor()
	cursor.execute("update user set is_admin=1 where username='" + username + "';")
	db.commit()

	return redirect(url_for('home'))

# Submit review for attraction by its name.
@app.route('/write-review/<attraction_name>')
def write_review(attraction_name):
	cursor = db.cursor()

	# TODO: Write SQL query that gets all the past activities completed by this user.
	# Also find out which index into row to get the date, name, and description.
	cursor.execute("select * from user;")
	attractions = [dict(date=row[0], name=row[2], description=row[1]) for row in cursor.fetchall()]

	valid_review = False

	for attraction in attractions:
		if attraction['name'] == attraction_name:
			valid_review = True
			break

	if valid_review:
		form = ReviewForm()
		return render_template('review.html', items=attractions, attraction_name=attraction_name, review=1, form=form, session=session)
	else:
		error='You must complete a visit to the attraction before you can review it!'
		return render_template('review.html', items=attractions, error=error, session=session)

@app.route('/create-review', methods=['POST'])
def create_review():
	cursor = db.cursor()
	query = "insert into review (title, authored_date, body, username, attraction_name) values ('" + request.form['title'] + "', '" + time.strftime('%Y-%m-%d') + "', '" + request.form['body'] + "', '" + session['username'] + "', '" + request.form['attraction_name'] + "');"
	cursor.execute(query)

	# TODO: Get Reviews
	cursor.execute("select * from user;")
	attractions = [dict(date=row[0], name=row[2], description=row[1]) for row in cursor.fetchall()]

	message = "Created review for " + request.form['attraction_name'] + "!"
	return render_template('review.html', items=attractions, success=message, session=session)

# Run the application
if __name__ == '__main__':

	# Note: If your database uses a different password, enter it here.
	db_pass = 'root'

	# Make sure your database is started before running run.py
	db_name = 'team1'
	db = pymysql.connect(host='localhost', user='root', passwd=db_pass, db=db_name)
	app.run(debug=True)
	db.close()