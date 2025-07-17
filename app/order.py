from flask import Blueprint, render_template, jsonify, request, redirect, url_for, session, flash, current_app, Response
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os
from werkzeug.utils import secure_filename
from datetime import date

order_bp = Blueprint('order', __name__)
mysql = MySQL()


@order_bp.route('/create_order/<int:product_id>', methods=['POST'])
def create_order(product_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    # Fetch product details
    cursor.execute('SELECT * FROM Product WHERE product_id = %s', (product_id,))
    product = cursor.fetchone()

    if not product:
        flash('Product not found', 'danger')
        return redirect(url_for('buyer_dashboard'))

    # Get order amount from form
    order_amount = int(request.form['order_amount'])
    if order_amount < 1:
        flash('Invalid order amount', 'danger')
        return redirect(url_for('buyer_dashboard'))

    # Create a new order
    order_date = date.today()
    order_status = 'SELECTED'

    cursor.execute('''
        INSERT INTO `Order` (order_status, order_amount, order_date, order_address, payment_method, user_id, product_id)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
    ''', (order_status, order_amount, order_date, 'Default Address', 'BALANCE', user_id, product_id))
    
    mysql.connection.commit()
    cursor.close()

    flash('Order created successfully.', 'success')
    return redirect(url_for('order.view_cart'))
    #return redirect(url_for('product.view_product', product_id=product_id))

@order_bp.route('/cart')
def view_cart():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT o.order_id, o.order_amount AS quantity, o.payment_method, o.card_number, o.order_address AS address,
               p.product_name, p.product_price AS unit_cost, p.product_id, p.product_stock
        FROM `Order` o
        JOIN Product p ON o.product_id = p.product_id
        WHERE o.user_id = %s AND o.order_status = 'SELECTED'
    ''', (user_id,))
    orders = cursor.fetchall()

    for order in orders:
        order['total_cost'] = order['unit_cost'] * order['quantity']
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('shopping_cart.html', orders=orders, balance = balance)

@order_bp.route('/update_cart', methods=['POST'])
def update_cart():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    form_data = request.form

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    order_ids = {key.split('[')[1][:-1] for key in form_data.keys() if key.startswith('quantities[')}

    for order_id in order_ids:
        quantity = form_data.get(f'quantities[{order_id}]')
        payment_method = form_data.get(f'payment_methods[{order_id}]')
        card_number = form_data.get(f'payment_cards[{order_id}]') if payment_method == 'CARD' else None
        address = form_data.get(f'addresses[{order_id}]')

        cursor.callproc('check_and_update_order', (order_id, user_id, quantity, payment_method, card_number, address))

        while True:
            result = cursor.fetchone()
            if result:
                if result['status'] == 'error':
                    flash(result['message'], 'danger')
                    cursor.close()
                    return redirect(url_for('order.view_cart'))
            else:
                break
        cursor.nextset()
        user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    mysql.connection.commit()
    cursor.close()

    flash('Cart updated successfully', 'success')
    return redirect(url_for('order.view_cart'))

@order_bp.route('/commit_orders', methods=['GET', 'POST'])
def commit_orders():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.callproc('commit_all_orders', (user_id,))

    while True:
        result = cursor.fetchone()
        if result:
            if result['status'] == 'error':
                flash(result['message'], 'danger')
                cursor.close()
                return redirect(url_for('order.view_cart'))
        else:
            break
        cursor.nextset()

    mysql.connection.commit()
    cursor.close()

    flash('Orders committed successfully', 'success')
    return redirect(url_for('order.view_cart'))

@order_bp.route('/delete_order/<int:order_id>')
def delete_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('DELETE FROM `Order` WHERE order_id = %s AND user_id = %s', (order_id, user_id))
    mysql.connection.commit()
    cursor.close()

    flash('Order deleted successfully', 'success')
    return redirect(url_for('order.view_cart'))

@order_bp.route('/view_orders_seller')
def view_orders_seller():
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT o.order_id, o.order_amount, o.order_date, o.order_status, o.order_address,
               p.product_name, p.product_price, u.username, s.business_name
        FROM `Order` o
        JOIN `Product` p ON o.product_id = p.product_id
        JOIN `User` u ON o.user_id = u.user_id
        JOIN `Seller` s ON p.user_id = s.user_id
        WHERE s.user_id = %s AND o.order_status != 'SELECTED'
    ''', (user_id,))
    orders = cursor.fetchall()
    
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()
    return render_template('view_orders_seller.html', orders=orders, balance = balance)

@order_bp.route('/ship_order/<int:order_id>', methods=['POST'])
def ship_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        flash('You must be logged in as a seller to perform this action.', 'danger')
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_id, p.product_stock
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            WHERE o.order_id = %s AND o.order_status = 'ORDERED'
        ''', (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('Order not found or not in ORDERED stage.', 'danger')
            return redirect(url_for('order.view_orders_seller'))

        order_amount = order['order_amount']
        product_id = order['product_id']
        product_stock = order['product_stock']

        if order_amount > product_stock:
            flash('Not enough stock to ship the order.', 'danger')
            return redirect(url_for('order.view_orders_seller'))

        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'SHIPPED'
            WHERE order_id = %s
        ''', (order_id,))

        cursor.execute('''
            UPDATE `Product`
            SET product_stock = product_stock - %s
            WHERE product_id = %s
        ''', (order_amount, product_id))

        mysql.connection.commit()
        flash('Order shipped successfully.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_seller'))

@order_bp.route('/reject_order/<int:order_id>', methods=['POST'])
def reject_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_id, p.product_price, u.user_id, u.balance
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            JOIN `User` u ON o.user_id = u.user_id
            WHERE o.order_id = %s AND o.order_status = 'ORDERED'
        ''', (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('Order not found or not in ORDERED stage.', 'danger')
            return redirect(url_for('order.view_orders_seller'))

        order_amount = order['order_amount']
        product_price = order['product_price']
        buyer_id = order['user_id']
        total_refund = order_amount * product_price

        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'REJECTED'
            WHERE order_id = %s
        ''', (order_id,))

        cursor.execute('''
            UPDATE `User`
            SET balance = balance + %s
            WHERE user_id = %s
        ''', (total_refund, buyer_id))

        mysql.connection.commit()
        flash('Order rejected and buyer refunded successfully.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_seller'))

@order_bp.route('/view_orders_buyer')
def view_orders_buyer():
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    user_id = session['userid']
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT o.order_id, o.order_amount, o.order_date, o.order_status, 
               p.product_name, p.product_price, s.business_name
        FROM `Order` o
        JOIN `Product` p ON o.product_id = p.product_id
        JOIN `Seller` s ON p.user_id = s.user_id
        WHERE o.user_id = %s
    ''', (user_id,))
    orders = cursor.fetchall()
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    cursor.close()

    return render_template('view_orders_buyer.html', orders=orders, balance = balance)

@order_bp.route('/cancel_order/<int:order_id>', methods=['POST'])
def cancel_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_id, p.product_price, u.user_id, u.balance, o.order_amount * p.product_price AS total_refund
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            JOIN `User` u ON o.user_id = u.user_id
            WHERE o.order_id = %s AND o.user_id = %s
        ''', (order_id, session['userid']))
        order = cursor.fetchone()

        if not order:
            flash('Order not found or you do not have permission to cancel this order.', 'danger')
            return redirect(url_for('order.view_orders_buyer'))

        buyer_id = order['user_id']
        total_refund = order["total_refund"]
        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'REJECTED'
            WHERE order_id = %s
        ''', (order_id,))

        cursor.execute('''
            UPDATE `User`
            SET balance = balance + %s
            WHERE user_id = %s
        ''', (total_refund, buyer_id))

        mysql.connection.commit()
        flash('Order cancelled and buyer refunded successfully.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_buyer'))

@order_bp.route('/finalize_order/<int:order_id>', methods=['POST'])
def finalize_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_id, p.product_price, p.user_id AS seller_id
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            WHERE o.order_id = %s AND o.user_id = %s
        ''', (order_id, session['userid']))
        order = cursor.fetchone()

        if not order:
            flash('Order not found or you do not have permission to finalize this order.', 'danger')
            return redirect(url_for('order.view_orders_buyer'))

        order_amount = order['order_amount']
        product_price = order['product_price']
        seller_id = order['seller_id']
        total_payment = order_amount * product_price

        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'FINALIZED'
            WHERE order_id = %s AND user_id = %s
        ''', (order_id, session['userid']))

        cursor.execute('''
            UPDATE `User`
            SET balance = balance + %s
            WHERE user_id = %s
        ''', (total_payment, seller_id))

        mysql.connection.commit()
        flash('Order finalized successfully', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_buyer'))

@order_bp.route('/return_order/<int:order_id>', methods=['POST'])
def return_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'buyer':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'RETURNED'
            WHERE order_id = %s AND user_id = %s
        ''', (order_id, session['userid']))
        mysql.connection.commit()
        flash('Order marked as returned.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_buyer'))

@order_bp.route('/return_finalize_order/<int:order_id>', methods=['POST'])
def return_finalize_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_price, u.user_id AS buyer_id
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            JOIN `User` u ON o.user_id = u.user_id
            WHERE o.order_id = %s
        ''', (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('Order not found.', 'danger')
            return redirect(url_for('order.view_orders_seller'))

        order_amount = order['order_amount']
        product_price = order['product_price']
        buyer_id = order['buyer_id']
        total_refund = order_amount * product_price

        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'RETURN_FINALIZED'
            WHERE order_id = %s
        ''', (order_id,))

        cursor.execute('''
            UPDATE `User`
            SET balance = balance + %s
            WHERE user_id = %s
        ''', (total_refund, buyer_id))

        mysql.connection.commit()
        flash('Return finalized and buyer refunded successfully.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_seller'))

@order_bp.route('/return_reject_order/<int:order_id>', methods=['POST'])
def return_reject_order(order_id):
    if 'loggedin' not in session or session.get('role') != 'seller':
        return redirect(url_for('login'))

    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    try:
        cursor.execute('''
            SELECT o.order_amount, p.product_price, p.user_id AS seller_id
            FROM `Order` o
            JOIN `Product` p ON o.product_id = p.product_id
            WHERE o.order_id = %s AND o.order_status = 'RETURNED'
        ''', (order_id,))
        order = cursor.fetchone()

        if not order:
            flash('Order not found or not in RETURNED stage.', 'danger')
            return redirect(url_for('order.view_orders_seller'))

        order_amount = order['order_amount']
        product_price = order['product_price']
        seller_id = order['seller_id']
        total_payment = order_amount * product_price

        cursor.execute('''
            UPDATE `Order`
            SET order_status = 'RETURN_REJECTED'
            WHERE order_id = %s
        ''', (order_id,))

        cursor.execute('''
            UPDATE `User`
            SET balance = balance + %s
            WHERE user_id = %s
        ''', (total_payment, seller_id))

        mysql.connection.commit()
        flash('Return rejected and payment processed to seller.', 'success')
    except MySQLdb.Error as e:
        mysql.connection.rollback()
        flash(f'Database error: {str(e)}', 'danger')
    except Exception as e:
        mysql.connection.rollback()
        flash(f'An error occurred: {str(e)}', 'danger')
    finally:
        cursor.close()

    return redirect(url_for('order.view_orders_seller'))
