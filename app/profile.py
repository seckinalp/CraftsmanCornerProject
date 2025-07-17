from flask import Blueprint, render_template, session, redirect, url_for, request, flash
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os

profile_bp = Blueprint('profile', __name__)
mysql = MySQL()

@profile_bp.route('/seller_profile')
def seller_profile():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
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
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()


    return render_template('seller_profile.html', seller=seller, balance = balance)

@profile_bp.route('/edit_seller_profile', methods=['GET', 'POST'])
def edit_seller_profile():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT u.username, u.name, u.surname, u.email, u.is_blocked, u.balance, u.contact_info_address, u.contact_info_phone_no,
               s.tax_number, s.business_address, s.business_name, s.is_verified, s.bio
        FROM User u
        JOIN Seller s ON u.user_id = s.user_id
        WHERE u.user_id = %s
    ''', (session['userid'],))
    seller = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        address = request.form['contact_info_address']
        phone_no = request.form['contact_info_phone_no']
        tax_number = request.form['tax_number']
        business_address = request.form['business_address']
        business_name = request.form['business_name']
        bio = request.form['bio']

        cursor.execute('''
            UPDATE User
            SET name = %s, surname = %s, email = %s, contact_info_address = %s, contact_info_phone_no = %s
            WHERE user_id = %s
        ''', (name, surname, email, address, phone_no, session['userid']))
        
        cursor.execute('''
            UPDATE Seller
            SET tax_number = %s, business_address = %s, business_name = %s, bio = %s
            WHERE user_id = %s
        ''', (tax_number, business_address, business_name, bio, session['userid']))
        
        mysql.connection.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.seller_profile'))
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    
    cursor.close()
    return render_template('edit_seller_profile.html', seller=seller,balance=balance)

@profile_bp.route('/buyer_profile')
def buyer_profile():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT u.username, u.name, u.surname, u.email, u.is_blocked, u.balance, u.contact_info_address, u.contact_info_phone_no
        FROM User u
        JOIN Buyer b ON u.user_id = b.user_id
        WHERE u.user_id = %s
    ''', (session['userid'],))
    buyer = cursor.fetchone()
    
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('buyer_profile.html', buyer=buyer, balance = balance)

@profile_bp.route('/edit_buyer_profile', methods=['GET', 'POST'])
def edit_buyer_profile():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT u.username, u.name, u.surname, u.email, u.is_blocked, u.balance, u.contact_info_address, u.contact_info_phone_no
        FROM User u
        JOIN Buyer b ON u.user_id = b.user_id
        WHERE u.user_id = %s
    ''', (session['userid'],))
    buyer = cursor.fetchone()

    if request.method == 'POST':
        name = request.form['name']
        surname = request.form['surname']
        email = request.form['email']
        address = request.form['contact_info_address']
        phone_no = request.form['contact_info_phone_no']

        cursor.execute('''
            UPDATE User
            SET name = %s, surname = %s, email = %s, contact_info_address = %s, contact_info_phone_no = %s
            WHERE user_id = %s
        ''', (name, surname, email, address, phone_no, session['userid']))
        
        mysql.connection.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.buyer_profile'))

    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('edit_buyer_profile.html', buyer=buyer,balance = balance)




@profile_bp.route('/view_report/<int:report_id>', methods=['GET'])
def view_report(report_id):
    if 'loggedin' not in session or session.get('role') not in ['admin', 'seller']:
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute("SELECT * FROM SystemReport WHERE system_report_id = %s", (report_id,))
    report = cursor.fetchone()
    cursor.close()

    if report:
        try:
            # Decode the BLOB content
            report_file_blob = report['report_file']
            report_file_content = json.loads(report_file_blob.decode('utf-8'))
            report['report_file'] = report_file_content
        except json.JSONDecodeError:
            flash("Error decoding report file content.", "danger")
            report['report_file'] = None
        except Exception as e:
            flash(f"An error occurred: {str(e)}", "danger")
            report['report_file'] = None

        return render_template('view_report.html', report=report)
    else:
        flash("Report not found.", "danger")
        return redirect(url_for('profile.seller_reports'))


@profile_bp.route('/view_seller_profile/<int:seller_id>')
def view_seller_profile(seller_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

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
    ''', (seller_id,))
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
    ''', (seller_id,))
    products = cursor.fetchall()

    balance = None
    if 'role' in session and session['role'] != 'admin':
        user_id = session['userid']
        cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
        balance = cursor.fetchone()['balance']

    cursor.close()

    return render_template('view_seller_profile.html', seller=seller, products=products, balance=balance)


@profile_bp.route('/all_shops')
def all_shops():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('''
        SELECT u.user_id, u.username, s.business_name, s.is_verified, s.bio,
               COALESCE(ROUND(AVG(r.star_count), 1), 0) AS average_rating, COUNT(r.review_id) AS total_reviews
        FROM User u
        JOIN Seller s ON u.user_id = s.user_id
        LEFT JOIN Product p ON s.user_id = p.user_id
        LEFT JOIN Review r ON p.product_id = r.product_id
        GROUP BY u.user_id, s.business_name, s.is_verified, s.bio
    ''')
    sellers = cursor.fetchall()
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()

    return render_template('all_shops.html', sellers=sellers, balance = balance)

