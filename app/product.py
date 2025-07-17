from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session, flash, current_app, Response
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
from werkzeug.utils import secure_filename

product_bp = Blueprint('product', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
product_bp = Blueprint('product', __name__)
mysql = MySQL()

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@product_bp.route('/add_product', methods=['GET', 'POST'])
def add_product():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    message = ''
    if request.method == 'POST':
        product_name = request.form['product_name']
        product_price = request.form['product_price']
        product_stock = request.form['product_stock']
        product_description = request.form['product_description']
        product_type = request.form['product_type']
        product_gender = request.form['product_gender']
        product_brand = request.form['product_brand']
        product_size = request.form['product_size']
        files = request.files.getlist('images')

        if not all([product_name, product_price, product_stock, product_description]):
            message = 'Please fill out all required fields!'
            return render_template('add_product.html', message=message)

        if not files or len(files) > 5:
            message = 'Please upload between 1 and 5 image files.'
            return render_template('add_product.html', message=message)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            INSERT INTO Product (product_name, product_price, product_stock, product_description, 
                                 product_type, product_gender, product_brand, product_size, 
                                 creation_date, last_update_date, user_id)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, NOW(), NOW(), %s)
        ''', (product_name, product_price, product_stock, product_description, 
              product_type, product_gender, product_brand, product_size, session['userid']))
        product_id = cursor.lastrowid

        for file in files:
            if file and allowed_file(file.filename):
                image_data = file.read()
                cursor.execute('INSERT INTO Image (product_id, image_data) VALUES (%s, %s)', (product_id, image_data))

        mysql.connection.commit()
     
        cursor.close()
        return redirect(url_for('product.view_products'))

  
    return render_template('add_product.html', message=message, balance=balance)



@product_bp.route('/view_products')
def view_products():
    if 'loggedin' not in session or session.get('role') == 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT pd.*, i.image_data
        FROM ProductDetails pd
        LEFT JOIN (
            SELECT product_id, image_data
            FROM Image
            WHERE (product_id, image_id) IN (
                SELECT product_id, MIN(image_id)
                FROM Image
                GROUP BY product_id
            )
        ) i ON pd.product_id = i.product_id
        WHERE pd.user_id = %s
    ''', (session['userid'],))
    products = cursor.fetchall()
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('view_products.html', products=products, balance=balance)


@product_bp.route('/edit_product/<int:product_id>', methods=['GET', 'POST'])
def edit_product(product_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Product WHERE product_id = %s AND user_id = %s', (product_id, session['userid']))
    product = cursor.fetchone()
    cursor.execute('SELECT * FROM Image WHERE product_id = %s', (product_id,))
    images = cursor.fetchall()
    cursor.close()

    if not product:
        return redirect(url_for('product.view_products'))

    message = ''
    if request.method == 'POST':
        product_name = request.form['product_name']
        product_price = request.form['product_price']
        product_stock = request.form['product_stock']
        product_description = request.form['product_description']
        product_type = request.form['product_type']
        product_gender = request.form['product_gender']
        product_brand = request.form['product_brand']
        product_size = request.form['product_size']
        files = request.files.getlist('images')

        if not all([product_name, product_price, product_stock, product_description]):
            message = 'Please fill out all required fields!'
            return render_template('edit_product.html', message=message, product=product, images=images)

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            UPDATE Product
            SET product_name = %s, product_price = %s, product_stock = %s, product_description = %s, 
                product_type = %s, product_gender = %s, product_brand = %s, product_size = %s, 
                last_update_date = NOW()
            WHERE product_id = %s AND user_id = %s
        ''', (product_name, product_price, product_stock, product_description, 
              product_type, product_gender, product_brand, product_size, product_id, session['userid']))

        if files and len(files) <= 5:
            # Delete all existing images associated with the product
            cursor.execute('DELETE FROM Image WHERE product_id = %s', (product_id,))

            # Insert new images
            for file in files:
                if file and allowed_file(file.filename):
                    image_data = file.read()
                    cursor.execute('INSERT INTO Image (product_id, image_data) VALUES (%s, %s)', (product_id, image_data))
        
        mysql.connection.commit()
        cursor.close()
        return redirect(url_for('product.view_products'))

    return render_template('edit_product.html', message=message, product=product, images=images)


@product_bp.route('/delete_product/<int:product_id>')
def delete_product(product_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Check if the product is in any order with status other than FINALIZED or RETURN_FINALIZED
    cursor.execute('''
        SELECT COUNT(*) AS order_count
        FROM `Order`
        WHERE product_id = %s AND order_status NOT IN ('FINALIZED', 'RETURN_FINALIZED', 'REJECTED', 'RETURN_REJECTED')
    ''', (product_id,))
    order_count = cursor.fetchone()['order_count']

    if order_count > 0:
        cursor.close()
        flash('You cannot delete this product as it is associated with pending orders.', 'danger')
        return redirect(url_for('product.view_products'))

    # Set the product's is_deleted field to TRUE instead of deleting it
    cursor.execute('''
        UPDATE Product
        SET is_deleted = TRUE
        WHERE product_id = %s AND user_id = %s
    ''', (product_id, session['userid']))
    
    cursor.execute('DELETE FROM Image WHERE product_id = %s', (product_id,))
    mysql.connection.commit()
    cursor.close()
    flash('Product marked as deleted.', 'success')
    return redirect(url_for('product.view_products'))



@product_bp.route('/view_all_products', methods=['GET', 'POST'])
def view_all_products():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    filters = {}
    order_by = 'p.product_name'  # default order by product name
    order_direction = 'ASC'  # default order direction

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
        SELECT p.*, i.image_data, s.business_name
        FROM Product p
        LEFT JOIN Image i ON p.product_id = i.product_id
        LEFT JOIN Seller s ON p.user_id = s.user_id
        WHERE p.is_deleted = FALSE
    '''

    if filters:
        conditions = ['p.is_deleted = FALSE']
        values = []
        for key, value in filters.items():
            if '>=' in key or '<=' in key:
                conditions.append(f"{key} %s")
            else:
                conditions.append(f"{key} = %s")
            values.append(value)
        query += ' WHERE ' + ' AND '.join(conditions)
    else:
        values = []

    query += f' ORDER BY {order_by} {order_direction}'

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute(query, values)
    products = cursor.fetchall()
    
    # Fetch distinct values for product types, genders, brands, sizes, and sellers for the filter form
    cursor.execute('SELECT DISTINCT product_type FROM Product WHERE is_deleted = FALSE')
    product_types = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT product_gender FROM Product WHERE is_deleted = FALSE')
    product_genders = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT product_brand FROM Product WHERE is_deleted = FALSE')
    product_brands = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT product_size FROM Product WHERE is_deleted = FALSE')
    product_sizes = cursor.fetchall()
    
    cursor.execute('SELECT DISTINCT business_name FROM Seller WHERE user_id IN (SELECT DISTINCT user_id FROM Product WHERE is_deleted = FALSE)')
    sellers = cursor.fetchall()
    
    cursor.close()

    return render_template('view_all_products.html', 
                           products=products, 
                           product_types=product_types, 
                           product_genders=product_genders, 
                           product_brands=product_brands,
                           product_sizes=product_sizes,
                           sellers=sellers,
                           selected_type=product_type,
                           selected_gender=product_gender,
                           selected_brand=product_brand,
                           selected_size=product_size,
                           selected_seller=seller,
                           selected_price_min=price_min,
                           selected_price_max=price_max,
                           selected_order=order_by,
                           selected_direction=order_direction)


@product_bp.route('/product/<int:product_id>')
def view_product(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch product details along with average rating, review count, and seller details
    cursor.execute('''
        SELECT p.*, i.image_data, 
               COALESCE(ROUND(r.avg_rating, 1), 0) AS average_rating, 
               COALESCE(r.review_count, 0) AS total_reviews,
               s.user_id AS seller_id, s.business_name
        FROM Product p
        LEFT JOIN Image i ON p.product_id = i.product_id
        LEFT JOIN (
            SELECT product_id, 
                   AVG(star_count) AS avg_rating, 
                   COUNT(review_id) AS review_count
            FROM Review
            WHERE product_id = %s
        ) r ON p.product_id = r.product_id
        LEFT JOIN Seller s ON p.user_id = s.user_id
        WHERE p.product_id = %s
    ''', (product_id, product_id))
    product = cursor.fetchone()

    # Fetch reviews for the product
    cursor.execute('''
        SELECT r.*, u.username 
        FROM Review r
        JOIN User u ON r.user_id = u.user_id
        WHERE r.product_id = %s
        ORDER BY r.post_date DESC
    ''', (product_id,))
    reviews = cursor.fetchall()

    balance = None
    favorite_status = False
    if 'role' in session and session['role'] != 'admin':
        user_id = session['userid']
        cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
        balance = cursor.fetchone()['balance']
        favorite_status = is_favorite(user_id, product_id)

    cursor.close()

    if not product:
        return redirect(url_for('product.view_all_products'))

    return render_template('view_product.html', product=product, reviews=reviews, balance=balance, is_favorite=favorite_status)




@product_bp.route('/leave_review/<int:product_id>', methods=['POST'])
def leave_review(product_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    review_content = request.form['review_content']
    star_count = request.form['star_count']
    user_id = session['userid']

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        INSERT INTO Review (user_id, product_id, review_content, star_count, post_date)
        VALUES (%s, %s, %s, %s, NOW())
    ''', (user_id, product_id, review_content, star_count))
    mysql.connection.commit()
    cursor.close()

    return redirect(url_for('product.view_product', product_id=product_id))

@product_bp.route('/edit_review/<int:review_id>', methods=['GET', 'POST'])
def edit_review(review_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT * FROM Review WHERE review_id = %s AND user_id = %s', (review_id, session['userid']))
    review = cursor.fetchone()
    cursor.close()

    if not review:
        return redirect(url_for('product.view_all_products'))

    if request.method == 'POST':
        review_content = request.form['review_content']
        star_count = request.form['star_count']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('''
            UPDATE Review
            SET review_content = %s, star_count = %s, post_date = NOW()
            WHERE review_id = %s AND user_id = %s
        ''', (review_content, star_count, review_id, session['userid']))
        mysql.connection.commit()
        cursor.close()
        
        return redirect(url_for('product.view_product', product_id=review['product_id']))

    return render_template('edit_review.html', review=review)

@product_bp.route('/delete_review/<int:review_id>/<int:product_id>', methods=['GET'])
def delete_review(review_id, product_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM Review WHERE review_id = %s AND user_id = %s', (review_id, session['userid']))
    mysql.connection.commit()
    cursor.close()
    
    return redirect(url_for('product.view_product', product_id=product_id))

@product_bp.route('/product/serve_image/<int:product_id>')
def serve_image(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT image_data FROM Image WHERE product_id = %s', (product_id,))
    image = cursor.fetchone()
    cursor.close()

    if image and image['image_data']:
        return Response(image['image_data'], mimetype='image/jpeg')
    return 'Image not found', 404

@product_bp.route('/product/serve_images/<int:product_id>')
def serve_images(product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT image_data FROM Image WHERE product_id = %s', (product_id,))
    images = cursor.fetchall()
    cursor.close()

    if images:
        return jsonify(images=[image['image_data'].hex() for image in images])
    return jsonify(error='Images not found'), 404

from datetime import datetime

# Route to add a product to favorites
@product_bp.route('/add_to_favorites/<int:product_id>', methods=['POST'])
def add_to_favorites(product_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        INSERT INTO Favorites (user_id, product_id, favorite_date)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE favorite_date = %s
    ''', (user_id, product_id, datetime.now(), datetime.now()))
    mysql.connection.commit()
    cursor.close()

    flash('Product added to favorites.', 'success')
    return redirect(url_for('product.view_product', product_id=product_id))

# Route to remove a product from favorites
@product_bp.route('/remove_from_favorites/<int:product_id>', methods=['POST'])
def remove_from_favorites(product_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        DELETE FROM Favorites WHERE user_id = %s AND product_id = %s
    ''', (user_id, product_id))
    mysql.connection.commit()
    cursor.close()

    flash('Product removed from favorites.', 'success')
    return redirect(url_for('product.view_product', product_id=product_id))

# Route to view favorite products
@product_bp.route('/view_favorites')
def view_favorites():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT p.*, i.image_data, s.business_name
        FROM Favorites f
        JOIN Product p ON f.product_id = p.product_id
        LEFT JOIN Image i ON p.product_id = i.product_id
        JOIN Seller s ON p.user_id = s.user_id
        WHERE f.user_id = %s
    ''', (user_id,))
    favorite_products = cursor.fetchall()
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()

    return render_template('view_favorites.html', products=favorite_products, balance = balance)

def is_favorite(user_id, product_id):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('SELECT 1 FROM Favorites WHERE user_id = %s AND product_id = %s', (user_id, product_id))
    favorite = cursor.fetchone()
    cursor.close()
    return favorite is not None