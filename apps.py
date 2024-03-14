
import secrets
import string
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from flask_mysqldb import MySQL
from flask_mail import Mail, Message


#----------------------------------------SQL Server configuration --------------------------------




app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Secret key for session management

app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'forum'

mysql = MySQL(app)



# --------------------------------Configure Flask-Mail---------------------------------------



app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_TLS'] = False
app.config['MAIL_USE_SSL'] = True  # Use SSL for secure connection
app.config['MAIL_USERNAME'] = 'daneryesjon@gmail.com'
app.config['MAIL_PASSWORD'] = 'vtew piey kmog aqre'
app.config['MAIL_DEFAULT_SENDER'] = 'daneryesjon@gmail.com'
mail = Mail(app)



# -----------------------------------REGISTRATION ----------------------------------------------------




@app.route('/', methods=['GET', 'POST'])
def registration():
    if 'logged_in' in session:
        return redirect(url_for('profile'))
    
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['passwords']  # Changed variable name to 'password'
        repeat_password = request.form['repeat_password']

        if len(name) < 4 or len(name) > 25:
            flash('Name must be between 4 and 25 characters', 'error_name')
        if len(email) < 6 or len(email) > 35:
            flash('Email must be between 6 and 35 characters', 'error_email')
        if len(password) < 6:  # Adjusted password validation check
            flash('Password must be at least 6 characters long', 'error_password')
        if password != repeat_password:
            flash('Passwords do not match', 'error_password')  # Corrected error category
        elif len(name) >= 4 and len(name) <= 25 and len(email) >= 6 and len(email) <= 35 and password == repeat_password:
            cur = mysql.connection.cursor()
            cur.execute("INSERT INTO details (user_name, user_email, password) VALUES (%s, %s, %s)", (name, email, password))
            mysql.connection.commit()
            cur.close()

            flash('Registration successful', 'success')
            return redirect(url_for('signin'))

    return render_template("registration.html")




# ----------------------SIGNIN----------------------------------------





@app.route('/signin', methods=['GET', 'POST'])
def signin():
    if 'logged_in' in session:
        return redirect(url_for('profile'))  # Redirect to profile if already logged in

    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

        if not email or not password:
            flash('Email and password are required', 'error')
            return redirect(url_for('signin'))  # Redirect back to the sign-in page

        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM details WHERE user_email = %s", (email,))
        user = cur.fetchone()
        cur.close()

        if user and user[3] == password:  # Assuming password is stored in the fourth column
            session['logged_in'] = True
            session['user_id'] = user[0]  # Assuming the first column in the 'details' table is the user ID
            session['user_name'] = user[1]  # Assuming the second column is the user name
            return redirect(url_for('profile'))  # Redirect to user profile page after successful sign-in
        else:
            flash('Invalid email or password', 'error')

    return render_template("signin.html")





# ------------------------------FORGET PAGE ----------------------------------





@app.route('/forgot', methods=['GET', 'POST'])
def forgot():
    if request.method == 'POST':
        email = request.form['email']
        if email_exists_in_database(email):
            token = generate_token()  # Generate a token
            store_token_in_database(email, token)  # Store the token in the database
            send_reset_password_email(email, token)  # Send the password reset email with the token
            flash('Password reset email sent. Check your inbox.')
            return redirect(url_for('signin'))
        else:
            flash('Email not found in the database.', 'error')

    return render_template('forgot.html')





#------------------------------check if the user email is there or not-----------------------------





def email_exists_in_database(email):
    cur = mysql.connection.cursor()
    cur.execute("SELECT * FROM details WHERE user_email = %s", (email,))
    user = cur.fetchone()
    cur.close()
    return user is not None





#-------------------------------------it will send the reset password email-----------------------------




def send_reset_password_email(email, token):
    reset_link = url_for('reset_password', token=token, _external=True)
    msg = Message('Password Reset Request', recipients=[email])
    msg.body = f'Click the following link to reset your password: {reset_link}'
    mail.send(msg)



#-------------------- Function to generate token----------------------------




def generate_token(length=32):
    """Generate a random token."""
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))




#------------------- function to store the token in the database-------------------------




def store_token_in_database(email, token):
    try:
        cur = mysql.connection.cursor()
        # Retrieve the user ID associated with the email
        cur.execute("SELECT id FROM details WHERE user_email = %s", (email,))
        user_id = cur.fetchone()[0]
        # Insert the token and user ID into the password_reset table
        cur.execute("INSERT INTO password_reset (user_id, token) VALUES (%s, %s)", (user_id, token))
        mysql.connection.commit()
        cur.close()
        return True
    except Exception as e:
        print("Error storing token in database:", e)
        return False





# --------------------------------RESET PASSWORD PAGE ----------------------------------




@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if request.method == 'POST':
        new_password = request.form['new_password']
        confirm_password = request.form['confirm_password']
        if new_password == confirm_password:
            update_password_in_database(token, new_password)
            return redirect(url_for('signin'))
        else:
            flash('Passwords do not match.', 'error')
    return render_template('reset_password.html', token=token)




# -----------------function to update the password in database and remove the exisiting password -------------------------





def update_password_in_database(token, new_password):
    try:
        cur = mysql.connection.cursor()
        # Retrieve the user ID associated with the token
        cur.execute("SELECT user_id FROM password_reset WHERE token = %s", (token,))
        user_id = cur.fetchone()[0]
        
        # Update the user's password in the 'details' table
        cur.execute("UPDATE details SET password = %s WHERE id = %s", (new_password, user_id))
        mysql.connection.commit()
        
        # Delete the password reset entry from the password_reset table
        cur.execute("DELETE FROM password_reset WHERE token = %s", (token,))
        mysql.connection.commit()
        
        cur.close()
        
        return True  # Password update successful
    except Exception as e:
        print("Error updating password:", e)
        return False  # Error occurred during password update




# --------------------------------PROFILE PAGE --------------------------------    





@app.route('/profile', methods=['GET', 'POST'])  # Updated to handle POST requests for updating user details
def profile():
    if 'logged_in' in session:
        if request.method == 'POST':
            user_id = request.json['userId']
            name = request.json['name']
            email = request.json['email']

            cur = mysql.connection.cursor()
            cur.execute("UPDATE details SET user_name = %s, user_email = %s WHERE id = %s", (name, email, user_id))
            mysql.connection.commit()
            cur.close()

            return jsonify({'message': 'User details updated successfully'})
        else:
            cur = mysql.connection.cursor()
            cur.execute("SELECT * FROM details")
            user = cur.fetchall()
            cur.close()
            return render_template('profile.html', user=user)
    else:
        return redirect(url_for('signin'))
    
    
    
    
    
# --------------------------------DELETE BUTTON --------------------------------




@app.route('/delete_user/<int:user_id>', methods=['DELETE'])
def delete_user(user_id):
    try:
        cur = mysql.connection.cursor()
        cur.execute("DELETE FROM details WHERE id = %s", (user_id,))
        mysql.connection.commit()
        cur.close()
        return jsonify({'message': 'User deleted successfully'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    
    
    
    
# ---------------------------------LOGOUT BUTTONS --------------------------------




@app.route('/logout', methods=['POST'])
def logout():
    session.clear()  # Clear the session data, effectively logging the user out
    return redirect(url_for('signin'))  # Redirect the user to the registration page after logout





# --------------------------------MAIN --------------------------------




if __name__ == '__main__':
    app.run(debug=True, port=6969)
