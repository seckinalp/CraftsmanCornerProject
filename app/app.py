import re
import os
from flask import Flask, render_template, request, redirect, url_for, session, flash
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature
import MySQLdb.cursors
from werkzeug.utils import secure_filename
from admin.route import admin_bp
from product import product_bp
from profile import profile_bp
from report import report_bp
from order import order_bp
from flask_mysqldb import MySQL
from flask_mail import Mail, Message

app = Flask(__name__)

app.secret_key = 'abcdefgh'

app.config['MYSQL_HOST'] = 'db'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'password'
app.config['MYSQL_DB'] = 'craftsmancornerdb'
app.config['MYSQL_CHARSET'] = 'utf8mb4'
app.config['UPLOAD_FOLDER'] = 'uploads/'  
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024

app.config['MAIL_SERVER'] = 'smtp.fastmail.com'
app.config['MAIL_PORT'] = 465
app.config['MAIL_USE_SSL'] = True
app.config['MAIL_USE_TSL'] = False
app.config['MAIL_USERNAME'] = 'craftsmancornerhelp@fastmail.com'
app.config['MAIL_PASSWORD'] = 'ww898b9zxsckj7hl'
app.config['MAIL_DEFAULT_SENDER'] = 'craftsmancornerhelp@gmail.com '

mail = Mail(app)


mysql = MySQL(app)
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(product_bp, url_prefix='/product')
app.register_blueprint(profile_bp)
app.register_blueprint(report_bp, url_prefix='/report')
app.register_blueprint(order_bp, url_prefix='/order')
@app.route('/')

@app.route('/login', methods=['GET', 'POST'])
def login():
    message = ''
    if request.method == 'POST':
        login = request.form.get('login')  # 'login' can be either username or email
        password = request.form.get('password')

        if not login or not password:
            message = 'Please fill out all fields!'
            return render_template('login.html', message=message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT * FROM User WHERE (username = %s OR email = %s) AND password = %s", (login, login, password))
        account = cursor.fetchone()

        if account:
            if account['is_blocked']:
                return redirect(url_for('banned'))

            session['loggedin'] = True
            session['logged_in'] = True # This is for seeing the reports dont remove
            session['userid'] = account['user_id']
            session['username'] = account['username']
            session['balance'] = account.get('balance', 0.0)  # Add balance to session, default to 0.0 if not set
            session['role'] = 'buyer'  # default role

            cursor.execute('SELECT * FROM Buyer WHERE user_id = %s', (account['user_id'],))
            buyer = cursor.fetchone()
            if buyer:
                session['role'] = 'buyer'
                message = 'Login successful!'
                return redirect(url_for('buyer_dashboard'))

            cursor.execute('SELECT * FROM Seller WHERE user_id = %s', (account['user_id'],))
            seller = cursor.fetchone()
            if seller:
                session['role'] = 'seller'
                message = 'Login successful!'
                return redirect(url_for('seller_dashboard'))

            message = 'This account does not have buyer or seller privileges.'
        else:
            message = 'Invalid login or password'

    return render_template('login.html', message=message)


@app.route('/banned_user')
def banned():
    return render_template('banned.html')


@app.route('/seller_dashboard')
def seller_dashboard():
    if 'loggedin' in session and session.get('role') == 'seller':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        
        # Fetch user information
        cursor.execute("SELECT * FROM User WHERE user_id = %s", (session['userid'],))
        user = cursor.fetchone()
        
        # Fetch seller information
        cursor.execute('''
            SELECT u.username, u.name, u.surname, u.email, u.contact_info_address, u.contact_info_phone_no,
                   s.tax_number, s.business_address, s.business_name, s.is_verified, s.bio,
                   COALESCE(ROUND(AVG(r.star_count), 1), 0) AS average_rating, COUNT(r.review_id) AS total_reviews
            FROM User u
            JOIN Seller s ON u.user_id = s.user_id
            LEFT JOIN Product p ON s.user_id = p.user_id
            LEFT JOIN Review r ON p.product_id = r.product_id
            WHERE u.user_id = %s
        ''', (session['userid'],))
        seller = cursor.fetchone()
        
        # Fetch seller's products
        cursor.execute('''
            SELECT p.*, i.image_data,
                   COALESCE(ROUND(r.avg_rating, 1), 0) AS average_rating, 
                   COALESCE(r.review_count, 0) AS total_reviews
            FROM Product p
           LEFT JOIN (
        SELECT product_id, image_data
        FROM Image
        WHERE (product_id, image_id) IN (
            SELECT product_id, MIN(image_id)
            FROM Image
            GROUP BY product_id
        )
    ) i ON p.product_id = i.product_id
            LEFT JOIN (
                SELECT product_id, 
                       AVG(star_count) AS avg_rating, 
                       COUNT(review_id) AS review_count
                FROM Review
                GROUP BY product_id
            ) r ON p.product_id = r.product_id
            WHERE p.user_id = %s
        ''', (session['userid'],))
        products = cursor.fetchall()
        
        balance = user['balance']
        cursor.close()
        
        return render_template('seller_dashboard.html', user=user, seller=seller, products=products, balance=balance)
    else:
        return redirect(url_for('login'))


@app.route('/buyer_dashboard', methods=['GET', 'POST'])
def buyer_dashboard():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    filters = {'p.is_deleted': False}  # Default filter to exclude deleted products
    order_by = 'p.product_name'  # default order by product name
    order_direction = 'ASC'  # default order direction

    search_query = request.form.get('search_query', '')
    product_type = request.form.get('product_type', '')
    product_gender = request.form.get('product_gender', '')
    product_brand = request.form.get('product_brand', '')
    product_size = request.form.get('product_size', '')
    seller = request.form.get('seller', '')
    price_min = request.form.get('price_min', '')
    price_max = request.form.get('price_max', '')
    order_by = request.form.get('order_by', 'p.product_name')
    order_direction = request.form.get('order_direction', 'ASC')

    if product_type:
        filters['p.product_type'] = product_type
    if product_gender:
        filters['p.product_gender'] = product_gender
    if product_brand:
        filters['p.product_brand'] = product_brand
    if product_size:
        filters['p.product_size'] = product_size
    if seller:
        filters['s.business_name'] = seller
    if price_min:
        filters['p.product_price >='] = price_min
    if price_max:
        filters['p.product_price <='] = price_max

    query = '''
        SELECT p.*, i.image_data, s.business_name,
               COALESCE(ROUND(r.avg_rating, 1), 0) AS average_rating, 
               COALESCE(r.review_count, 0) AS total_reviews
        FROM Product p
        LEFT JOIN (
            SELECT product_id, image_data
            FROM Image
            WHERE (product_id, image_id) IN (
                SELECT product_id, MIN(image_id)
                FROM Image
                GROUP BY product_id
            )
        ) i ON p.product_id = i.product_id
        LEFT JOIN Seller s ON p.user_id = s.user_id
        LEFT JOIN (
            SELECT product_id, 
                   AVG(star_count) AS avg_rating, 
                   COUNT(review_id) AS review_count
            FROM Review
            GROUP BY product_id
        ) r ON p.product_id = r.product_id
    '''

    conditions = ['p.is_deleted = FALSE']
    values = []

    if search_query:
        conditions.append('p.product_name LIKE %s')
        values.append(f'%{search_query}%')

    if filters:
        for key, value in filters.items():
            if '>=' in key or '<=' in key:
                conditions.append(f"{key} %s")
            else:
                conditions.append(f"{key} = %s")
            values.append(value)
        query += ' WHERE ' + ' AND '.join(conditions)

    query += f' ORDER BY {order_by} {order_direction}'

    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = 9
    offset = (page - 1) * per_page

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, values)
    all_products = cursor.fetchall()

    total_products = len(all_products)
    total_pages = (total_products + per_page - 1) // per_page  # Calculate total pages

    products = all_products[offset:offset + per_page]

    # Fetch distinct values for product types, genders, brands, sizes, and sellers for the filter form
    cursor.execute('SELECT DISTINCT product_type FROM Product WHERE is_deleted = FALSE')
    product_types = cursor.fetchall()

    cursor.execute('SELECT DISTINCT product_gender FROM Product WHERE is_deleted = FALSE')
    product_genders = cursor.fetchall()

    cursor.execute('SELECT DISTINCT product_brand FROM Product WHERE is_deleted = FALSE')
    product_brands = cursor.fetchall()

    cursor.execute('SELECT DISTINCT product_size FROM Product WHERE is_deleted = FALSE')
    product_sizes = cursor.fetchall()

    cursor.execute(
        'SELECT DISTINCT business_name FROM Seller WHERE user_id IN (SELECT DISTINCT user_id FROM Product WHERE is_deleted = FALSE)')
    sellers = cursor.fetchall()

    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()

    return render_template('buyer_dashboard.html',
                           products=products,
                           product_types=product_types,
                           product_genders=product_genders,
                           product_brands=product_brands,
                           product_sizes=product_sizes,
                           sellers=sellers,
                           search_query=search_query,
                           selected_type=product_type,
                           selected_gender=product_gender,
                           selected_brand=product_brand,
                           selected_size=product_size,
                           selected_seller=seller,
                           selected_price_min=price_min,
                           selected_price_max=price_max,
                           selected_order=order_by,
                           selected_direction=order_direction,
                           current_page=page,
                           total_pages=total_pages,
                           balance=balance)


def user_exists(username):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM User WHERE username = %s', (username,))
    account = cursor.fetchone()
    cursor.close()
    return account

def insert_user(username, password, email, name, surname):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('INSERT INTO User (username, password, email, name, surname) VALUES (%s, %s, %s, %s, %s)',
                   (username, password, email, name, surname))
    mysql.connection.commit()
    cursor.execute('SELECT user_id FROM User WHERE username = %s', (username,))
    user_id = cursor.fetchone()['user_id']
    cursor.close()
    return user_id

@app.route('/register_buyer', methods=['GET', 'POST'])
def register_buyer():
    message = ''
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')

        if not username or not password or not email or not surname or not name:
            message = 'Please fill out all fields!'
            return render_template('register_buyer.html', message=message)

        if user_exists(username):
            message = 'Username already exists. Choose a different username!'
            return render_template('register_buyer.html', message=message)

        user_id = insert_user(username, password, email, name, surname)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO Buyer (user_id) VALUES (%s)', (user_id,))
        mysql.connection.commit()
        cursor.close()
        
        # Automatically log in the user after registration
        session['loggedin'] = True
        session['userid'] = user_id
        session['balance'] = 0.0  # Set initial balance to 0.0
        session['role'] = 'buyer'
        return redirect(url_for('buyer_dashboard'))

    return render_template('register_buyer.html', message=message)

@app.route('/register_seller', methods=['GET', 'POST'])
def register_seller():
    message = ''
    if request.method == 'POST':
        name = request.form.get('name')
        surname = request.form.get('surname')
        username = request.form.get('username')
        password = request.form.get('password')
        email = request.form.get('email')
        business_name = request.form.get('business_name')
        tax_number = request.form.get('tax_number')

        if not name or not surname or not username or not password or not email or not business_name or not tax_number:
            message = 'Please fill out all fields!'
            return render_template('register_seller.html', message=message)

        if user_exists(username):
            message = 'Username already exists. Choose a different username!'
            return render_template('register_seller.html', message=message)

        user_id = insert_user(username, password, email, name, surname)
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('INSERT INTO Seller (user_id, business_name, tax_number) VALUES (%s, %s, %s)', (user_id, business_name, tax_number))
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('login'))

    return render_template('register_seller.html', message=message)


@app.route('/add_balance', methods=['GET', 'POST'])
def add_balance():
    if 'loggedin' not in session:
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        amount = request.form['amount']
        if amount:
            amount = float(amount)  # Convert the amount to float
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('UPDATE User SET balance = balance + %s WHERE user_id = %s', (amount, session['userid']))
            mysql.connection.commit()
            cursor.close()
           #session['balance'] += amount  # Update the balance in the session
            return redirect(url_for('buyer_dashboard'))
    
    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('add_balance.html', balance = balance)

@app.route('/withdraw_balance', methods=['GET', 'POST'])
def withdraw_balance():
    if 'loggedin' not in session:
        return redirect(url_for('login'))

    if request.method == 'POST':
        iban = request.form['iban']
        amount = request.form['amount']
        
        if iban and amount:
            amount = float(amount)
            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            cursor.execute('SELECT balance FROM User WHERE user_id = %s', (session['userid'],))
            balance = cursor.fetchone()['balance']
            
            if amount <= balance:
                cursor.execute('UPDATE User SET balance = balance - %s WHERE user_id = %s', (amount, session['userid']))
                mysql.connection.commit()
                flash('Withdrawal successful!', 'success')
            else:
                flash('Insufficient balance!', 'danger')
            
            cursor.close()
            if session['role'] == 'seller':
                return redirect(url_for('seller_dashboard'))
            else:
                return redirect(url_for('buyer_dashboard'))
    
    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    
    return render_template('withdraw_balance.html', balance=balance)



@app.route('/main')
def main_page():

    if 'loggedin' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM owns JOIN account ON owns.aid = account.aid WHERE owns.cid = %s', (session['userid'],))
        accounts = cursor.fetchall()
        return render_template('main.html', accounts=accounts)
    else:
        return redirect(url_for('login'))
    

@app.route('/sold_items')
def sold_items():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    user_id = session['userid']
    
    # Adjusted SQL query with backticks for the Order table
    query = '''
        SELECT p.product_name, p.product_price, o.finalized_date 
        FROM `Order` o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.user_id = %s AND o.order_status = "FINALIZED" AND p.user_id = %s
    '''
    cursor.execute(query, (user_id, user_id))
    sold_items = cursor.fetchall()
    cursor.close()

    return render_template('sold_items.html', sold_items=sold_items)


""" @app.route('/sold_items')
def sold_items():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    #seller_id = session['seller_id']
    cursor.execute('SELECT * FROM Order WHERE user_id = %s AND order_status = "FINALIZED"',  (session['userid'],))
    sold_items = cursor.fetchall()
    cursor.close()

    return render_template('sold_items.html', sold_items=sold_items) """


@app.route('/logout')
def logout():
    session.clear() 
    return redirect(url_for('login'))  
# Initialize URLSafeTimedSerializer
s = URLSafeTimedSerializer(app.secret_key)

@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form['email']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM User WHERE email = %s', (email,))
        user = cursor.fetchone()
        cursor.close()

        if user:
            token = s.dumps(email, salt='email-confirm')
            reset_link = url_for('reset_password', token=token, _external=True)
            msg = Message(subject="Password Reset Request",
                          sender=app.config['MAIL_USERNAME'],
                          recipients=[email],
                          body=f"To reset your password, click the following link: {reset_link}")
            try:
                mail.send(msg)
                flash('Password reset link sent! Check your email.', 'success')
            except Exception as e:
                flash(f'An error occurred while sending the email: {str(e)}', 'danger')
        else:
            flash('Email not found', 'danger')
        return redirect(url_for('login'))
    return render_template('forgot_password.html')

@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    try:
        email = s.loads(token, salt='email-confirm', max_age=3600)
    except Exception as e:
        flash('The password reset link is invalid or has expired.', 'danger')
        return redirect(url_for('login'))

    if request.method == 'POST':
        new_password = request.form['password']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('UPDATE User SET password = %s WHERE email = %s', (new_password, email))
        mysql.connection.commit()
        cursor.close()
        flash('Your password has been updated!', 'success')
        return redirect(url_for('login'))

    return render_template('reset_password.html', token=token)
    
if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(debug=True, host='0.0.0.0', port=port)
