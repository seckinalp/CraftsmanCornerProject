import os
from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_mysqldb import MySQL
import logging
import MySQLdb.cursors
import json
import base64
from datetime import datetime, timedelta
from decimal import Decimal
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)

admin_bp = Blueprint('admin_bp', __name__, template_folder='../templates/admin')
mysql = MySQL()

@admin_bp.route('/list_reports', methods=['GET'])
def list_reports():
    if 'logged_in' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if session.get('role') == 'admin':
            # Admin sees all reports, ordered by report date
            cursor.execute("SELECT system_report_id, report_name, report_date, report_file FROM SystemReport ORDER BY report_date DESC")
            reports = cursor.fetchall()
        else:
            # Non-admin users (e.g., sellers) see reports related to their account, ordered by report date
            username = session.get('username')
            cursor.execute("""
                SELECT system_report_id, report_name, report_date, CONVERT(report_file USING utf8) as report_file
                FROM SystemReport
                WHERE (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) = %s)
                OR (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) IS NULL)
                OR (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) = '')
                ORDER BY report_date DESC
            """, (username,))
            reports = cursor.fetchall()

        cursor.close()
        return render_template('list_reports.html', reports=reports)
    else:
        return redirect(url_for('admin_bp.login_admin'))


@admin_bp.route('/view_report/<int:report_id>', methods=['GET'])
def view_report(report_id):
    if 'logged_in' in session:
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
            return redirect(url_for('admin_bp.list_reports'))
    else:
        return redirect(url_for('admin_bp.login_admin'))


@admin_bp.route('/admin_dashboard', methods=['GET', 'POST'])
def admin_dashboard():
    if 'logged_in' in session and session.get('role') == 'admin':
        if request.method == 'POST':
            selected_year = request.form.get('selectedYear')
            selected_month = request.form.get('selectedMonth')
            limit_value = request.form.get('limitValue', '5')
            product_filter = request.form.get('productFilter', 'most_sold_general')
            min_value = request.form.get('minValue', '0')
            max_value = request.form.get('maxValue', '999999')
            period = request.form.get('period')
            category = request.form.get('category')
        else:
            selected_year = request.args.get('selectedYear')
            selected_month = request.args.get('selectedMonth')
            limit_value = request.args.get('limitValue', '5')
            product_filter = request.args.get('productFilter', 'most_sold_general')
            min_value = request.args.get('minValue', '0')
            max_value = request.args.get('maxValue', '999999')
            period = request.args.get('period')
            category = request.args.get('category')


        try:
            limit_value = int(limit_value) if limit_value else 5
        except ValueError:
            limit_value = 5  # Default value if conversion fails
        try:
            min_value = int(min_value) if min_value else 0
        except ValueError:
            min_value = 0  # Default value if conversion fails
        try:
            max_value = int(max_value) if max_value else 999999
        except ValueError:
            max_value = 999999  # Default value if conversion fails

        # Calculate start_date based on the period
        if period:
            if 'week' in period:
                number_of_weeks = int(period.split(' ')[0])
                start_date = datetime.now() - timedelta(weeks=number_of_weeks)
            elif 'month' in period:
                number_of_months = int(period.split(' ')[0])
                start_date = datetime.now() - timedelta(days=30 * number_of_months)
            elif 'year' in period:
                number_of_years = int(period.split(' ')[0])
                start_date = datetime.now() - timedelta(days=365 * number_of_years)
        else:
            start_date = None

        end_date = datetime.now()

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        labels, total_sales = sales_sum(selected_year, selected_month)
        top_sellers = get_top_sellers()
        cursor.execute("SELECT DISTINCT product_type FROM Product")
        product_types = cursor.fetchall()
        # Fetch top products based on the selected filter
        if product_filter == 'most_sold_general':
            top_products = get_top_products(limit_value, min_value, max_value)
        elif product_filter == 'most_sold_category':
            top_products = get_top_products_by_category(limit_value, min_value, max_value)
        elif product_filter == 'most_faved_general':
            top_products = get_most_faved_products(limit_value, min_value, max_value)
        elif product_filter == 'most_faved_category':
            top_products = get_most_faved_products_by_category(limit_value, min_value, max_value)
        elif product_filter == 'most_reviewed_general':
            top_products = get_most_reviewed_products(limit_value, min_value, max_value)
        elif product_filter == 'most_reviewed_category':
            top_products = get_most_reviewed_products_by_category(limit_value, min_value, max_value)

        # New calculations
        seller_most_quantity = get_seller_with_most_quantity(cursor, start_date, end_date, category)
        seller_most_revenue = get_seller_with_most_revenue(cursor, start_date, end_date, category)
        seller_most_products_in_category = get_seller_with_most_products_in_category(cursor, category, start_date, end_date)

        cursor.close()

        return render_template('admin_dashboard.html',
                               months=labels, total_sales=total_sales,
                               selected_year=selected_year, selected_month=selected_month,
                               top_sellers=top_sellers, top_products=top_products,
                               limit_value=limit_value, product_filter=product_filter,
                               min_value=min_value, max_value=max_value,
                               seller_most_quantity=seller_most_quantity,
                               seller_most_revenue=seller_most_revenue,
                               seller_most_products_in_category=seller_most_products_in_category,
                               product_types=product_types)

    else:
        return redirect(url_for('admin_bp.login_admin'))

def get_top_products(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT p.product_id, p.product_name, SUM(o.order_amount) AS total_orders
        FROM Product p
        JOIN `Order` o ON p.product_id = o.product_id
        WHERE p.product_price BETWEEN %s AND %s AND o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
        GROUP BY p.product_id, p.product_name
        ORDER BY total_orders DESC
        LIMIT %s;
    '''
    cursor.execute(query, (min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])

    return top_products


def get_top_products_by_category(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    subquery = '''
        SELECT p.product_id, p.product_name, p.product_type, SUM(o.order_amount) AS total_orders
        FROM Product p
        JOIN `Order` o ON p.product_id = o.product_id
        WHERE p.product_price BETWEEN %s AND %s AND o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
        GROUP BY p.product_id, p.product_name, p.product_type
    '''

    max_sales_query = '''
        SELECT product_type, MAX(total_orders) AS max_sold
        FROM ({}) AS subquery
        GROUP BY product_type
    '''.format(subquery)

    final_query = '''
        SELECT subquery.product_id, subquery.product_name, subquery.product_type, subquery.total_orders
        FROM ({}) AS subquery
        JOIN ({}) AS max_sales
        ON subquery.product_type = max_sales.product_type AND subquery.total_orders = max_sales.max_sold
        ORDER BY subquery.total_orders DESC
        LIMIT %s
    '''.format(subquery, max_sales_query)

    cursor.execute(final_query, (min_value, max_value, min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])

    return top_products


def get_most_faved_products(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT p.product_id, p.product_name, COUNT(f.user_id) AS faves_count
        FROM Product p
        JOIN Favorites f ON p.product_id = f.product_id
        WHERE p.product_price BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name
        ORDER BY faves_count DESC
        LIMIT %s;
    '''
    cursor.execute(query, (min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])
        product['total_sold'] = product['faves_count']  # Assigning faves_count to total_sold key

    return top_products

def get_most_faved_products_by_category(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT p.product_id, p.product_name, p.product_type, COUNT(f.user_id) AS faves_count
        FROM Product p
        JOIN Favorites f ON p.product_id = f.product_id
        WHERE p.product_price BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name, p.product_type
        ORDER BY p.product_type, faves_count DESC
        LIMIT %s;
    '''
    cursor.execute(query, (min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])
        product['total_sold'] = product['faves_count']

    return top_products

def get_most_reviewed_products(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT p.product_id, p.product_name, COUNT(r.review_id) AS reviews_count
        FROM Product p
        JOIN Review r ON p.product_id = r.product_id
        WHERE p.product_price BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name
        ORDER BY reviews_count DESC
        LIMIT %s;
    '''
    cursor.execute(query, (min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])
        product['total_sold'] = product['reviews_count']

    return top_products

def get_most_reviewed_products_by_category(limit_value, min_value, max_value):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT p.product_id, p.product_name, p.product_type, COUNT(r.review_id) AS reviews_count
        FROM Product p
        JOIN Review r ON p.product_id = r.product_id
        WHERE p.product_price BETWEEN %s AND %s
        GROUP BY p.product_id, p.product_name, p.product_type
        ORDER BY p.product_type, reviews_count DESC
        LIMIT %s;
    '''
    cursor.execute(query, (min_value, max_value, limit_value))
    top_products = cursor.fetchall()
    cursor.close()

    for product in top_products:
        product['product_url'] = url_for('product.view_product', product_id=product['product_id'])
        product['total_sold'] = product['reviews_count']

    return top_products


@admin_bp.route('/report', methods=['GET'])
def report():
    if 'logged_in' in session:
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if session.get('role') == 'admin':
            # Admin sees all reports, ordered by report date
            cursor.execute(
                "SELECT system_report_id, report_name, report_date, report_file FROM SystemReport ORDER BY report_date DESC")
            reports = cursor.fetchall()
        else:
            # Non-admin users (e.g., sellers) see reports related to their account, ordered by report date
            username = session.get('username')
            cursor.execute("""
                SELECT system_report_id, report_name, report_date, CONVERT(report_file USING utf8) as report_file
                FROM SystemReport
                WHERE (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) = %s)
                OR (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) IS NULL)
                OR (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.username')) = '')
                ORDER BY report_date DESC
            """, (username,))
            reports = cursor.fetchall()

        cursor.close()
        return render_template('list_reports.html', reports=reports)
    else:
        return redirect(url_for('admin_bp.login_admin'))



@admin_bp.route('/create_system_report', methods=['GET', 'POST'])
def create_system_report():
    if 'logged_in' in session and session.get('role') == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute("SELECT u.username FROM Seller s, User u WHERE s.user_id = u.user_id")
        sellers = cursor.fetchall()

        cursor.execute("SELECT DISTINCT product_type FROM Product")
        product_types = cursor.fetchall()
        cursor.close()

        if request.method == 'POST':
            report_type = request.form.get('reportType')
            start_date = request.form.get('startDate')
            end_date = request.form.get('endDate')
            min_price = request.form.get('minPrice') or '0'
            max_price = request.form.get('maxPrice') or '999999'
            product_type = request.form.get('productType') or 'all'
            reporting_user_name = request.form.get('reportingUserName')
            limit_numbers = request.form.get('limitNumbers', '10')

            cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
            report_data = []

            try:
                user_condition = ""
                user_params = []
                reporting_user_id = None
                if reporting_user_name and reporting_user_name != 'all' and not report_type in ['top_customers', 'top_customers_by_orders', 'top_customers_by_reviews']:
                    cursor.execute("SELECT user_id FROM User WHERE username = %s", (reporting_user_name,))
                    user = cursor.fetchone()
                    if user:
                        reporting_user_id = user['user_id']
                        user_condition = " AND p.user_id = %s"
                        user_params.append(reporting_user_id)

                product_type_condition = ""
                if product_type and product_type != "all" and not report_type in ['popular_categories', 'top_customers_by_reviews']:
                    product_type_condition = " AND p.product_type = %s"
                    user_params.append(product_type)

                date_condition = ""
                if not report_type in ['top_customers_by_reviews', 'popular_categories', 'popular_products_by_review', 'popular_products_by_favorited']:
                    if start_date and end_date:
                        date_condition = " AND o.order_date BETWEEN %s AND %s"
                        user_params.extend([start_date, end_date])
                    elif start_date:
                        date_condition = " AND o.order_date >= %s"
                        user_params.append(start_date)
                    elif end_date:
                        date_condition = " AND o.order_date <= %s"
                        user_params.append(end_date)

                if report_type == 'popular_categories':
                    query = f"""
                        SELECT p.product_type, SUM(filtered_orders.order_amount * p.product_price) AS total_revenue
                        FROM Product p
                        JOIN (
                            SELECT o.product_id, o.order_amount
                            FROM `Order` o
                            WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
                        ) AS filtered_orders
                        ON p.product_id = filtered_orders.product_id
                        WHERE p.product_price BETWEEN %s AND %s {user_condition}
                        GROUP BY p.product_type
                        ORDER BY total_revenue DESC
                        LIMIT %s
                        """
                    cursor.execute(query, (min_price, max_price) + tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'most_popular_products':
                    query = f"""
                    SELECT p.product_name, p.product_id, SUM(filtered_orders.order_amount) AS sales_count
                    FROM Product p
                    JOIN (
                        SELECT o.product_id, o.order_amount
                        FROM `Order` o
                        WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {date_condition}
                    ) AS filtered_orders
                    ON p.product_id = filtered_orders.product_id
                    WHERE 1=1 {user_condition} {product_type_condition}
                    GROUP BY p.product_id
                    ORDER BY sales_count DESC
                    LIMIT %s
                    """
                    cursor.execute(query, tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'top_customers':
                    query = f"""
                    SELECT u.username, SUM(o.order_amount * p.product_price) AS total_spent
                    FROM User u
                    JOIN `Order` o ON u.user_id = o.user_id
                    JOIN Product p ON o.product_id = p.product_id
                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {product_type_condition} {date_condition}
                    GROUP BY u.user_id
                    ORDER BY total_spent DESC
                    LIMIT %s
                    """
                    cursor.execute(query, tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'popular_products_by_review':
                    query = f"""
                    SELECT p.product_name, p.product_id, COUNT(r.review_id) AS review_count
                    FROM Product p
                    JOIN Review r ON p.product_id = r.product_id
                    WHERE p.product_price BETWEEN %s AND %s {user_condition} {product_type_condition}
                    GROUP BY p.product_id
                    ORDER BY review_count DESC
                    LIMIT %s
                    """
                    cursor.execute(query, (min_price, max_price) + tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'popular_products_by_favorited':
                    query = f"""
                    SELECT p.product_name, p.product_id, COUNT(f.user_id) AS favorites_count
                    FROM Product p
                    JOIN Favorites f ON p.product_id = f.product_id
                    WHERE p.product_price BETWEEN %s AND %s {user_condition} {product_type_condition}
                    GROUP BY p.product_id
                    ORDER BY favorites_count DESC
                    LIMIT %s
                    """
                    cursor.execute(query, (min_price, max_price) + tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'top_customers_by_orders':
                    query = f"""
                    SELECT u.username, COUNT(o.order_amount) AS orders_count
                    FROM User u
                    JOIN `Order` o ON u.user_id = o.user_id
                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {product_type_condition} {date_condition}
                    GROUP BY u.user_id
                    ORDER BY orders_count DESC
                    LIMIT %s
                    """
                    cursor.execute(query, tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'top_customers_by_reviews':
                    query = f"""
                    SELECT u.username, COUNT(r.review_id) AS reviews_count
                    FROM User u
                    JOIN Review r ON u.user_id = r.user_id
                    GROUP BY u.user_id
                    ORDER BY reviews_count DESC
                    LIMIT %s
                    """
                    cursor.execute(query, (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'sales_over_time_by_revenue':
                    query = f"""
                    SELECT DATE(o.order_date) AS date, SUM(o.order_amount * p.product_price) AS total_revenue
                    FROM `Order` o
                    JOIN Product p ON o.product_id = p.product_id
                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {user_condition} {product_type_condition} {date_condition}
                    GROUP BY DATE(o.order_date)
                    ORDER BY date
                    LIMIT %s
                    """
                    cursor.execute(query, tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                elif report_type == 'most_exp_most_chp_product':
                    if product_type != 'all':
                        query = """
                           SELECT
                               MAX(p.product_price) AS max_price,
                               MIN(p.product_price) AS min_price
                           FROM Product p
                           WHERE p.product_type = %s
                           """
                        cursor.execute(query, (product_type,))
                    else:
                        query = """
                           SELECT
                               MAX(p.product_price) AS max_price,
                               MIN(p.product_price) AS min_price
                           FROM Product p
                           """
                        cursor.execute(query)
                        report_data = cursor.fetchall()

                elif report_type == 'products_with_highest_lowest_orders':
                    query_highest = f"""
                                    SELECT p.product_name, SUM(o.order_amount) AS total_orders
                                    FROM Product p
                                    JOIN `Order` o ON p.product_id = o.product_id
                                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED')  {product_type_condition} {date_condition}
                                    GROUP BY p.product_id
                                    ORDER BY total_orders DESC
                                    LIMIT 1
                                    """
                    cursor.execute(query_highest, tuple(user_params))
                    highest_ordered_product = cursor.fetchone()

                    query_lowest = f"""
                                    SELECT p.product_name, SUM(o.order_amount) AS total_orders
                                    FROM Product p
                                    JOIN `Order` o ON p.product_id = o.product_id
                                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {product_type_condition} {date_condition}
                                    GROUP BY p.product_id
                                    ORDER BY total_orders ASC
                                    LIMIT 1
                                    """
                    cursor.execute(query_lowest, tuple(user_params))
                    lowest_ordered_product = cursor.fetchone()

                    report_data = {
                        'highest_ordered_product': highest_ordered_product,
                        'lowest_ordered_product': lowest_ordered_product
                    }

                elif report_type == 'sales_over_time_by_amount':
                    query = f"""
                    SELECT DATE(o.order_date) AS date, SUM(o.order_amount) AS total_sales
                    FROM `Order` o
                    JOIN Product p ON o.product_id = p.product_id
                    WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED') {user_condition} {product_type_condition} {date_condition}
                    GROUP BY DATE(o.order_date)
                    ORDER BY date
                    LIMIT %s
                    """
                    cursor.execute(query, tuple(user_params) + (int(limit_numbers),))
                    report_data = cursor.fetchall()

                cursor.execute("SELECT admin_id FROM Admin WHERE admin_id = %s", (session['admin_id'],))
                admin = cursor.fetchone()
                if not admin:
                    flash("Admin ID not found.", "danger")
                    return redirect(url_for('admin_bp.create_system_report'))

                if reporting_user_id:
                    for item in report_data:
                        item['user_id'] = reporting_user_id

                report_details_json = json.dumps(report_data, ensure_ascii=False, default=str)
                report_file_blob = report_details_json.encode('utf-8')
                report_description = f"Report Type: {report_type}\n"
                if start_date:
                    report_description += f"Start Date: {start_date}\n"
                if end_date:
                    report_description += f"End Date: {end_date}\n"
                if product_type:
                    report_description += f"Product Type: {product_type}\n"
                if reporting_user_name:
                    report_description += f"Reporting User: {reporting_user_name}\n"

                cursor.execute("""
                    INSERT INTO SystemReport (admin_id, report_name, report_date, report_details, report_file)
                    VALUES (%s, %s, NOW(), %s, %s)
                """, (session['admin_id'], report_type, report_description, report_file_blob))
                mysql.connection.commit()

                flash("System report created successfully!", "success")
                return redirect(url_for('admin_bp.admin_dashboard'))

            except MySQLdb.Error as e:
                flash(f"An error occurred: {str(e)}", "danger")
                return redirect(url_for('admin_bp.create_system_report'))
            finally:
                cursor.close()

        return render_template('create_system_report.html', sellers=sellers, product_types=product_types)
    else:
        return redirect(url_for('admin_bp.login_admin'))



def get_top_sellers():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    query = '''
        SELECT s.user_id, s.business_name, SUM(o.order_amount) AS total_sold_amount
        FROM Seller s
        JOIN Product p ON s.user_id = p.user_id
        JOIN `Order` o ON p.product_id = o.product_id
        WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
        GROUP BY s.user_id, s.business_name
        ORDER BY total_sold_amount DESC
        LIMIT 5;
    '''
    cursor.execute(query)
    top_sellers = cursor.fetchall()
    cursor.close()
    return top_sellers


def sales_sum(selected_year, selected_month):
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

    if selected_year and selected_month:
        query = '''
                    SELECT 
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d') AS day,
                        SUM(o.order_amount) AS total_sales
                    FROM 
                        `Order` o
                    WHERE 
                        YEAR(o.order_date) = %s AND MONTH(o.order_date) = %s AND o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
                    GROUP BY 
                        DATE_FORMAT(o.order_date, '%%Y-%%m-%%d')
                    ORDER BY 
                        day
                '''
        cursor.execute(query, (selected_year, selected_month))
    elif selected_year:
        query = '''
                    SELECT 
                        DATE_FORMAT(o.order_date, '%%Y-%%m') AS month,
                        SUM(o.order_amount) AS total_sales
                    FROM 
                        `Order` o
                    WHERE 
                        YEAR(o.order_date) = %s AND o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
                    GROUP BY 
                        DATE_FORMAT(o.order_date, '%%Y-%%m')
                    ORDER BY 
                        month
                '''
        cursor.execute(query, (selected_year,))
    else:
        query = '''
                    SELECT 
                        DATE_FORMAT(o.order_date, '%%Y-%%m') AS month,
                        SUM(o.order_amount) AS total_sales
                    FROM 
                        `Order` o
                    WHERE 
                        o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
                    GROUP BY 
                        DATE_FORMAT(o.order_date, '%%Y-%%m')
                    ORDER BY 
                        month
                '''
        cursor.execute(query)

    sales_data = cursor.fetchall()
    cursor.close()

    if selected_year and selected_month:
        labels = [row['day'] for row in sales_data]
    else:
        labels = [row['month'] for row in sales_data]
    total_sales = [row['total_sales'] for row in sales_data]
    return labels, total_sales


@admin_bp.route('/handle_user_report', methods=['POST'])
def handle_user_report():
    if 'logged_in' in session and session.get('role') == 'admin':
        report_id = request.form.get('report_id')
        reported_user_id = request.form.get('reported_user_id')
        action = request.form.get('action')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        success_message = ""

        try:
            if action == 'block':
                # Block the user
                cursor.execute("UPDATE User SET is_blocked = TRUE WHERE user_id = %s", (reported_user_id,))
                mysql.connection.commit()  
                success_message = "User blocked successfully!"

            elif action == 'warn':
                # Check if the reported user is a seller
                cursor.execute("SELECT * FROM Seller WHERE user_id = %s", (reported_user_id,))
                seller = cursor.fetchone()
                if seller:
                    # Set is_verified to False for the seller
                    cursor.execute("UPDATE Seller SET is_verified = FALSE WHERE user_id = %s", (reported_user_id,))
                    mysql.connection.commit()
                    success_message = "Seller warned and verification status set to false!"

                # Create a system report for the warning
                cursor.execute("SELECT username, email FROM User WHERE user_id = %s", (reported_user_id,))
                user_result = cursor.fetchone()
                if user_result:
                    # Get the description from the user report
                    cursor.execute("SELECT description FROM Report WHERE report_id = %s", (report_id,))
                    report_description = cursor.fetchone()['description']

                    report_details = f"""
                        Warning: Your account has been reported. 
                        Description: {report_description}
                        For further assistance, please contact our support at craftsmancornerhelp@gmail.com.
                    """

                    json_data = {
                        'action': 'warn',
                        'user_id': reported_user_id,
                        'username': user_result['username'],
                        'description': report_description
                    }

                    cursor.execute("""
                        INSERT INTO SystemReport (admin_id, report_name, report_date, report_details, report_file)
                        VALUES (%s, %s, NOW(), %s, %s)
                    """, (
                        session['admin_id'],
                        "Warning Report",
                        report_details,
                        json.dumps(json_data).encode('utf-8')
                    ))
                    mysql.connection.commit()

                    # Count the number of warning reports for this user
                    cursor.execute("""
                        SELECT COUNT(*) AS warning_count 
                        FROM SystemReport 
                        WHERE report_name = %s AND  (JSON_UNQUOTE(JSON_EXTRACT(CONVERT(report_file USING utf8), '$.user_id')) = %s)
                    """, ("Warning Report", reported_user_id))
                    warning_count = cursor.fetchone()['warning_count']

                    if warning_count >= 3:
                        # Block the seller after 3 warnings
                        cursor.execute("UPDATE User SET is_blocked = TRUE WHERE user_id = %s", (reported_user_id,))
                        mysql.connection.commit()
                        success_message = "Seller blocked after 3 warnings!"

            cursor.execute("DELETE FROM User_Report WHERE report_id = %s", (report_id,))
            cursor.execute("DELETE FROM Report WHERE report_id = %s", (report_id,))
            mysql.connection.commit()

            flash(success_message, 'success')

        except MySQLdb.Error as e:
            print(f"Error: {e}")
            flash(f"An error occurred: {str(e)}", 'danger')
        finally:
            cursor.close()

        return redirect(url_for('admin_bp.user_reports'))
    else:
        return redirect(url_for('admin_bp.login_admin'))



@admin_bp.route('/product_reports', methods=['GET', 'POST'])
def product_reports():
    if 'logged_in' in session and session.get('role') == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        reporter_filter = ""
        product_id_filter = ""
        reason_filter = ""
        limit_value = ""

        if request.method == 'POST':
            reporter_filter = request.form.get('reporterFilter', '')
            product_id_filter = request.form.get('productIdFilter', '')
            reason_filter = request.form.get('reasonFilter', '')
            limit_value = request.form.get('limitValue', '')

        base_query = """
        SELECT pr.report_id, pr.reported_product_id, u.username AS reporter_username, 
               p.product_name, pr.report_reason, r.description
        FROM Product_Report pr
        JOIN Report r ON pr.report_id = r.report_id
        JOIN User u ON r.reporting_user_id = u.user_id
        JOIN Product p ON pr.reported_product_id = p.product_id
        """

        count_query = """
        SELECT pr.reported_product_id
        FROM Product_Report pr
        GROUP BY pr.reported_product_id
        HAVING COUNT(pr.report_id) >= %s
        """

        count_params = []
        if limit_value:
            try:
                count_params.append(int(limit_value))
            except ValueError:
                count_params.append(0)  # Default to 0 if limit value is invalid
        else:
            count_params.append(0)  # Default to 0 if no limit value is provided

        cursor.execute(count_query, count_params)
        product_ids = [row['reported_product_id'] for row in cursor.fetchall()]

        if product_ids:
            query_conditions = []
            query_params = []

            if reporter_filter:
                query_conditions.append("u.username = %s")
                query_params.append(reporter_filter)
            if product_id_filter:
                query_conditions.append("p.product_id = %s")
                query_params.append(product_id_filter)
            if reason_filter:
                query_conditions.append("pr.report_reason = %s")
                query_params.append(reason_filter)
            if product_ids:
                query_conditions.append("pr.reported_product_id IN (%s)" % ','.join(['%s'] * len(product_ids)))
                query_params.extend(product_ids)

            if query_conditions:
                base_query += " WHERE " + " AND ".join(query_conditions)

            cursor.execute(base_query, query_params)
            reports = cursor.fetchall()
        else:
            reports = []

        cursor.execute("SELECT username FROM User")
        reporters = cursor.fetchall()

        cursor.execute("SELECT product_id, product_name FROM Product")
        products = cursor.fetchall()

        cursor.close()

        return render_template('product_reports.html',
                               reports=reports,
                               reporters=reporters,
                               products=products,
                               reporterFilter=reporter_filter,
                               productIdFilter=product_id_filter,
                               reasonFilter=reason_filter,
                               limitValue=limit_value)
    else:
        return redirect(url_for('admin_bp.login_admin'))

@admin_bp.route('/login_admin', methods=['GET', 'POST'])
def login_admin():
    if request.method == 'POST':
        username_or_email = request.form['username_or_email']
        password = request.form['password']

        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT * FROM Admin WHERE (username = %s OR email = %s) AND password = %s', (username_or_email, username_or_email, password))
        admin = cursor.fetchone()
        cursor.close()
        if admin:
            session['logged_in'] = True
            session['username'] = admin['username']
            session['role'] = 'admin'
            session['admin_id'] = admin['admin_id']
            return redirect(url_for('admin_bp.admin_dashboard'))
        else:
            flash('Invalid username/email or password', 'danger')

    return render_template('login_admin.html')


@admin_bp.route('/handle_product_report', methods=['POST'])
def handle_product_report():
    if 'logged_in' in session and session.get('role') == 'admin':
        action = request.form.get('action')
        report_id = request.form.get('report_id')
        product_id = request.form.get('product_id')
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        success_message = ""

        try:
            if action == 'delete':
                # Delete related entries in Order
                cursor.execute("DELETE FROM `Order` WHERE product_id = %s", (product_id,))
                # Delete related entries in Product_Report
                cursor.execute("DELETE FROM Product_Report WHERE reported_product_id = %s", (product_id,))
                # Delete the product from Product
                cursor.execute("DELETE FROM Product WHERE product_id = %s", (product_id,))
                # Commit the changes
                mysql.connection.commit()
                success_message = "Product deleted successfully!"
            elif action == 'warn':
                # Create a system report for the warning
                cursor.execute(
                    "SELECT p.user_id, u.username FROM Product p JOIN User u ON p.user_id = u.user_id WHERE p.product_id = %s",
                    (product_id,))
                user_result = cursor.fetchone()
                if user_result:
                    # Get the description from the product report
                    cursor.execute("SELECT description FROM Report WHERE report_id = %s", (report_id,))
                    report_description = cursor.fetchone()['description']

                    report_details = {
                        'action': 'warn',
                        'product_id': product_id,
                        'user_id': user_result['user_id'],
                        'username': user_result['username'],
                        'description': report_description
                    }

                    # Report details as email message
                    report_email_message = f"""
                        Dear {user_result['username']},

                        We have received a report regarding your product (ID: {product_id}).
                        Description of the report:
                        {report_description}

                        Please ensure compliance with our community guidelines to avoid further action.

                        For further assistance, please contact our support at craftsmancornerhelp@fastmail.com.
                    """

                    cursor.execute("""
                        INSERT INTO SystemReport (admin_id, report_name, report_date, report_details, report_file)
                        VALUES (%s, %s, NOW(), %s, %s)
                    """, (
                        session['admin_id'], "Warning Report", report_email_message, json.dumps(report_details)
                    ))
                    mysql.connection.commit()
                    success_message = "Warning issued and system report created!"

            # Delete the report after handling it
            cursor.execute("DELETE FROM Product_Report WHERE report_id = %s", (report_id,))
            cursor.execute("DELETE FROM Report WHERE report_id = %s", (report_id,))
            mysql.connection.commit()

            flash(success_message, 'success')

        except MySQLdb.Error as e:
            print(f"Error: {e}")
            flash(f"An error occurred: {str(e)}", 'danger')
        finally:
            cursor.close()

        return redirect(url_for('admin_bp.product_reports'))
    else:
        return redirect(url_for('admin_bp.login_admin'))


def get_seller_with_most_quantity(cursor, start_date=None, end_date=None, category=None):
    query = """
        SELECT s.user_id, s.business_name, SUM(o.order_amount) AS total_quantity
        FROM Seller s
        JOIN Product p ON s.user_id = p.user_id
        JOIN `Order` o ON p.product_id = o.product_id
        WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
    """
    filters = []
    if start_date:
        filters.append(f"o.order_date >= '{start_date}'")
    if end_date:
        filters.append(f"o.order_date <= '{end_date}'")
    if category:
        filters.append(f"p.product_type = '{category}'")
    if filters:
        query += " AND " + " AND ".join(filters)
    query += """
        GROUP BY s.user_id
        ORDER BY total_quantity DESC
        LIMIT 3;
    """
    cursor.execute(query)
    result = cursor.fetchall()
    return result if result else []


def get_seller_with_most_revenue(cursor, start_date=None, end_date=None, category=None):
    query = """
        SELECT s.user_id, s.business_name, SUM(o.order_amount * p.product_price) AS total_revenue
        FROM Seller s
        JOIN Product p ON s.user_id = p.user_id
        JOIN `Order` o ON p.product_id = o.product_id
        WHERE o.order_status IN ('FINALIZED', 'RETURN_REJECTED')
    """

    filters = []
    if start_date:
        filters.append(f"o.order_date >= '{start_date}'")
    if end_date:
        filters.append(f"o.order_date <= '{end_date}'")
    if category:
        filters.append(f"p.product_type = '{category}'")
    if filters:
        query += " AND " + " AND ".join(filters)

    query += """
        GROUP BY s.user_id, s.business_name
        ORDER BY total_revenue DESC
        LIMIT 3;
    """

    cursor.execute(query)
    result = cursor.fetchall()
    return result if result else []


def get_seller_with_most_products_in_category(cursor, category, start_date=None, end_date=None):
    query = """
        SELECT s.user_id, s.business_name, COUNT(p.product_id) AS total_products
        FROM Seller s
        JOIN Product p ON s.user_id = p.user_id
    """
    filters = []
    if category:
        filters.append(f"p.product_type = '{category}'")
    if start_date:
        filters.append(f"p.creation_date >= '{start_date}'")
    if end_date:
        filters.append(f"p.creation_date <= '{end_date}'")
    if filters:
        query += " WHERE " + " AND ".join(filters)
    query += """
        GROUP BY s.user_id
        ORDER BY total_products DESC
        LIMIT 1;
    """
    cursor.execute(query)
    result = cursor.fetchall()
    return result if result else []

@admin_bp.route('/user_reports', methods=['GET', 'POST'])
def user_reports():
    if 'logged_in' in session and session.get('role') == 'admin':
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        reporter_filter = ""
        reported_user_filter = ""
        limit_value = ""
        filter_sellers = False
        filter_buyers = False

        if request.method == 'POST':
            reporter_filter = request.form.get('reporterFilter', '')
            reported_user_filter = request.form.get('reportedUserFilter', '')
            limit_value = request.form.get('limitValue', '')
            filter_sellers = 'filterSellers' in request.form
            filter_buyers = 'filterBuyers' in request.form

        base_query = """
        SELECT ur.report_id, ur.reported_user_id, ru.username AS reported_username,
               u.username AS reporter_username, r.description
        FROM User_Report ur
        JOIN Report r ON ur.report_id = r.report_id
        JOIN User u ON r.reporting_user_id = u.user_id
        JOIN User ru ON ur.reported_user_id = ru.user_id
        """

        count_query = """
        SELECT ur.reported_user_id
        FROM User_Report ur
        GROUP BY ur.reported_user_id
        HAVING COUNT(ur.report_id) >= %s
        """

        count_params = []
        if limit_value:
            try:
                count_params.append(int(limit_value))
            except ValueError:
                count_params.append(0)  # Default to 0 if limit value is invalid
        else:
            count_params.append(0)  # Default to 0 if no limit value is provided

        cursor.execute(count_query, count_params)
        user_ids = [row['reported_user_id'] for row in cursor.fetchall()]

        if user_ids:
            query_conditions = []
            query_params = []

            if reporter_filter:
                query_conditions.append("u.username = %s")
                query_params.append(reporter_filter)
            if reported_user_filter:
                query_conditions.append("ru.user_id = %s")
                query_params.append(reported_user_filter)
            if filter_sellers:
                query_conditions.append("EXISTS (SELECT 1 FROM Seller s WHERE s.user_id = ur.reported_user_id)")
            if filter_buyers:
                query_conditions.append("EXISTS (SELECT 1 FROM Buyer b WHERE b.user_id = ur.reported_user_id)")
            if user_ids:
                query_conditions.append("ur.reported_user_id IN (%s)" % ','.join(['%s'] * len(user_ids)))
                query_params.extend(user_ids)

            if query_conditions:
                base_query += " WHERE " + " AND ".join(query_conditions)

            cursor.execute(base_query, query_params)
            reports = cursor.fetchall()
        else:
            reports = []

        cursor.execute("SELECT DISTINCT username FROM User WHERE user_id IN (SELECT reporting_user_id FROM Report)")
        reporters = cursor.fetchall()

        cursor.execute("SELECT user_id, username FROM User")
        reported_users = cursor.fetchall()

        cursor.close()

        return render_template('user_reports.html',
                               reports=reports,
                               reporters=reporters,
                               reportedUsers=reported_users,
                               reporterFilter=reporter_filter,
                               reportedUserFilter=reported_user_filter,
                               limitValue=limit_value,
                               filterSellers=filter_sellers,
                               filterBuyers=filter_buyers)
    else:
        return redirect(url_for('admin_bp.login_admin'))

@admin_bp.route('/logout_admin')
def logout_admin():
    # Clear the session data
    session.clear()
    # Redirect to the admin login page
    return redirect(url_for('admin_bp.login_admin'))

@admin_bp.route('/profile', methods=['GET', 'POST'])
def profile():
    if 'logged_in' in session and session.get('role') == 'admin':
        admin_username = session['username']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)

        if request.method == 'POST':
            email = request.form.get('email')
            password = request.form.get('password')

            if password:
                cursor.execute('''
                    UPDATE Admin 
                    SET email = %s, password = %s 
                    WHERE username = %s
                ''', ( email, password, admin_username))
            else:
                cursor.execute('''
                    UPDATE Admin 
                    SET  email = %s 
                    WHERE username = %s
                ''', ( email, admin_username))

            mysql.connection.commit()
            flash('Profile updated successfully!', 'success')

        # Fetch admin details
        cursor.execute('SELECT * FROM Admin WHERE username = %s', (admin_username,))
        admin = cursor.fetchone()
        cursor.close()

        return render_template('profile.html', admin=admin)
    else:
        return redirect(url_for('admin_bp.login_admin'))

