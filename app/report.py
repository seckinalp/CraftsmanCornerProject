from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from datetime import datetime
from flask_mysqldb import MySQL
import MySQLdb.cursors
import os


report_bp = Blueprint('report', __name__)
mysql = MySQL()
@report_bp.route('/report', methods=['GET', 'POST'])
def report():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    
    cursor.execute('SELECT user_id, username FROM User')
    users = cursor.fetchall()
    
    cursor.execute('SELECT product_id, product_name FROM Product')
    products = cursor.fetchall()
    
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    
    
    if request.method == 'POST':
        report_type = request.form['report_type']
        description = request.form['description']
        
        cursor = mysql.connection.cursor()
        
        if report_type == 'user':
            reported_user_id = request.form['reported_user_id']
            cursor.execute('INSERT INTO Report (reporting_user_id, report_date, description) VALUES (%s, NOW(), %s)', (session['userid'], description))
            report_id = cursor.lastrowid
            cursor.execute('INSERT INTO User_Report (report_id, reported_user_id) VALUES (%s, %s)', (report_id, reported_user_id))
        
        elif report_type == 'product':
            reported_product_id = request.form['reported_product_id']
            report_reason = request.form['report_reason']
            cursor.execute('INSERT INTO Report (reporting_user_id, report_date, description) VALUES (%s, NOW(), %s)', (session['userid'], description))
            report_id = cursor.lastrowid
            cursor.execute('INSERT INTO Product_Report (report_id, reported_product_id, report_reason) VALUES (%s, %s, %s)', (report_id, reported_product_id, report_reason))
        
        else:
            cursor.execute('INSERT INTO Report (reporting_user_id, report_date, description) VALUES (%s, NOW(), %s)', (session['userid'], description))
        
        mysql.connection.commit()
        user_id = session['userid']
        cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
        cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
        balance = cursor.fetchone()['balance']
        cursor.close()
        #return redirect(url_for('report.view_reports'))
        flash('Report submitted successfully!', 'success')
    
    return render_template('report.html', users=users, products=products, balance = balance)

@report_bp.route('/view_reports')
def view_reports():
    cursor = mysql.connection.cursor(MySQLdb.cursors.DictCursor)
    cursor.execute('''
        SELECT r.*, ur.reported_user_id, pr.reported_product_id, pr.report_reason 
        FROM Report r 
        LEFT JOIN User_Report ur ON r.report_id = ur.report_id 
        LEFT JOIN Product_Report pr ON r.report_id = pr.report_id 
        WHERE r.reporting_user_id = %s
    ''', (session['userid'],))
    reports = cursor.fetchall()
    user_id = session['userid']
    cursor.execute('SELECT balance FROM User WHERE user_id = %s', (user_id,))
    balance = cursor.fetchone()['balance']
    return render_template('view_reports.html', reports=reports, balance = balance)