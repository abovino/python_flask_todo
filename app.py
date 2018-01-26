from flask import Flask, render_template, flash, request, redirect, url_for, session, logging
from flask_mysqldb import MySQL
from wtforms import Form, StringField, TextAreaField, DateTimeField, PasswordField, validators
from wtforms.fields.html5 import DateField
from passlib.hash import sha256_crypt
from functools import wraps
import time, datetime, calendar
import config

app = Flask(__name__)
app.secret_key='secret123'

# Config MySQL
app.config['MYSQL_HOST'] = config.MYSQL_HOST
app.config['MYSQL_USER'] = config.MYSQL_USER
app.config['MYSQL_PASSWORD'] = config.MYSQL_PASSWORD
app.config['MYSQL_DB'] = config.MYSQL_DB
app.config['MYSQL_CURSORCLASS'] = config.MYSQL_CURSORCLASS

# init MYSQL
mysql = MySQL(app)

# if __name__ == '__main__':
# 	app.run() # Runs the app ... no env var needed

@app.route('/')
def index():
	return render_template('index.html')

@app.route('/articles')
def articles():
	return render_template('articles.html', articles = Articles)

@app.route('/article/<string:id>/')
def article(id):
	return render_template('article.html', id = id)

class RegisterForm(Form):
	name = StringField('Name', [validators.Length(min=1, max=50)])
	username = StringField('Username', [validators.Length(min=1, max=25)])
	email = StringField('Email', [validators.Length(min=6, max=50)])
	password = PasswordField('Password', [
		validators.DataRequired(),
		validators.EqualTo('confirm', message='Passwords do not match')
	])
	confirm = PasswordField('Confirm Password')

@app.route('/register', methods=['GET', 'POST'])
def register():
		form = RegisterForm(request.form)
		if request.method == 'POST' and form.validate():
			name = form.name.data
			email = form.email.data
			username = form.username.data
			password = sha256_crypt.encrypt(str(form.password.data))

			# Create cursor for MySQL
			cur = mysql.connection.cursor()
			
			# Execute query
			cur.execute("INSERT INTO users(name, email, username, password) VALUES(%s, %s, %s, %s)", (name, email, username, password))

			# Commit to DB
			mysql.connection.commit()

			# Close connection to DB
			cur.close()

			flash('You are now registered and can log in', 'success')

			return redirect(url_for('login'))
		return render_template('register.html', form=form)

# User login
@app.route('/login', methods=['GET', 'POST'])
def login():
	if request.method == 'POST':
		# Get Form Fields
		username = request.form['username']
		password_candidate = request.form['password']

		# Create cursor
		cur = mysql.connection.cursor()

		# Get user by username
		result = cur.execute("SELECT * FROM users WHERE username = %s", [username])

		if result > 0:
			# Get stored hash
			data = cur.fetchone()
			password = data['password']
			userId = data['id']

			# Compare passwords
			if sha256_crypt.verify(password_candidate, password):
				# Passed
				session['logged_in'] = True
				session['username'] = username
				session['userId'] = userId

				flash('You are now logged in', 'success')
				return redirect(url_for('dashboard'))
			else:
				error = 'Invalid login attempt'
				return render_template('login.html', error=error)
			# Close connection
			cur.close()
		else:
			error = 'Username not found'
			return render_template('login.html', error=error)

	return render_template('login.html')

# Check if user is logged in
def is_logged_in(f):
	@wraps(f)
	def wrap(*args, **kwargs):
		if 'logged_in' in session:
			return f(*args, **kwargs)
		else:
			flash('Unauthorized, Please login', 'danger')
			return redirect(url_for('login'))
	return wrap

# Logout
@app.route('/logout')
@is_logged_in
def logout():
	session.clear()
	flash('You are now logged out', 'success')
	return redirect(url_for('login'))

# Dashboard
@app.route('/dashboard')
@is_logged_in
def dashboard():
	# Render all users tasks ...
	# Create cursor
	cur = mysql.connection.cursor()

	# Get tasks by userId
	userId = str(session['userId'])
	data = cur.execute("SELECT * FROM todos WHERE created_by_id = %s ORDER BY -due_date DESC", userId)

	# Fetch all tasks in dictionary form to make tasks iterable
	tasks = cur.fetchall()
	for i in range(len(tasks)):
		due_date = str(tasks[i]['due_date'])
		create_date = str(tasks[i]['create_date'])
		update_date = str(tasks[i]['update_date'])
		
		# print(due_date, create_date, update_date)
		if due_date != 'None':
			a = time.strptime(due_date, '%Y-%m-%d %H:%M:%S')
			tasks[i]['due_date'] = time.strftime('%m/%d/%Y @ %I:%M %p', a)
			tasks[i]['defaultDateHtml'] = time.strftime('%Y-%m-%d')
			tasks[i]['defaultTimeHtml'] = time.strftime('%H:%M', a)
			tasks[i]['prettyDueDate'] = time.strftime('%b %d, %Y %I:%M %p', a)
			tasks[i]['prettyDueTime'] = time.strftime('%b %d, %Y', a)
			# print(tasks[i]['prettyDueDate'])

		a = time.strptime(create_date, '%Y-%m-%d %H:%M:%S')
		tasks[i]['create_date'] = time.strftime('%m/%d/%Y', a)

		a = time.strptime(update_date, '%Y-%m-%d %H:%M:%S')
		tasks[i]['update_date'] = time.strftime('%m/%d/%Y', a)

		tasks[i]['sequence'] = str(i + 1)

	# Close connection
	cur.close()
	return render_template('dashboard.html', tasks = tasks)

class TaskForm(Form):
	task = StringField('Task', [validators.Length(min=1, max=125)])
	details = StringField('Details', [validators.Length(min=1, max=500)])
	# date = DateField('Date', format='%Y-%m-%d')
	# time = DateTimeField('Time', format='%H:%M:%S')
	
@app.route('/add_task', methods=['GET', 'POST'])
@is_logged_in
def add_task():
	# form = TaskForm(request.form)
	if request.method == 'POST':
		task = request.form['task']
		details = request.form['details']
		due_date = None # Initially assign NULL so if due date was not provided by user NULL is inserted in DB
		for inputs in request.form:
			if 'date' in inputs:
				# If user does not enter date/time then insert NULL in 'due_date' DB column
				if len(request.form['date']) < 1:
					due_date = None
				else:
					due_date = request.form['date'] + ' ' + request.form['time']
					mySqlDateTimeFormat = time.strptime(due_date, "%Y-%m-%d %H:%M")
					due_date = time.strftime('%Y-%m-%d %H:%M:%S', mySqlDateTimeFormat)
		
		# Create Cursor
		cur = mysql.connection.cursor()
		
		# Execute query
		cur.execute('INSERT INTO todos(task, details, created_by_id, due_date) VALUES(%s, %s, %s, %s)', (task, details, session['userId'], due_date))

		# Commit to DB
		mysql.connection.commit()

		# Close connection to DB
		cur.close()
		return redirect(url_for('dashboard'))

	return render_template('add_task.html', form=form)

@app.route('/edit_task/<string:id>', methods=['GET', 'POST'])
@is_logged_in
def edit_task(id):
	# form = TaskForm(request.form)
	if request.method == 'POST':
		task = request.form['task']
		details = request.form['details']
		due_date = None # Initially assign NULL so if due date was not provided by user NULL is inserted in DB
		for inputs in request.form:
			if 'date' in inputs:
				# If user does not enter date/time then insert NULL in 'due_date' DB column
				if len(request.form['date']) < 1:
					due_date = None
				else:
					due_date = request.form['date'] + ' ' + request.form['time']
					mySqlDateTimeFormat = time.strptime(due_date, "%Y-%m-%d %H:%M")
					due_date = time.strftime('%Y-%m-%d %H:%M:%S', mySqlDateTimeFormat)
		
		update_date = datetime.datetime.now()
		# mySqlDateTimeFormat = time.strptime(due_date, "%Y-%m-%d %H:%M")
		# due_date = time.strftime('%Y-%m-%d %H:%M:%S', mySqlDateTimeFormat)
		
		# Create Cursor
		cur = mysql.connection.cursor()
		
		# Execute query
		cur.execute('UPDATE todos SET task=%s, details=%s, due_date=%s, update_date=%s WHERE id=%s AND created_by_id=%s', (task, details, due_date, update_date, id, session['userId']))

		# Commit to DB
		mysql.connection.commit()

		# Close connection to DB
		cur.close()
		return redirect(url_for('dashboard'))

	return render_template('add_task.html', form=form)