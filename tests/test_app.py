import os
import json
import pandas as pd
import requests
from datetime import datetime
from flask import Flask, request, render_template, jsonify, redirect, url_for, flash
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.secret_key = 'sms_bridge_test_secret_key'

# Configuration
SMS_BRIDGE_URL = os.getenv('SMS_BRIDGE_URL', 'http://localhost:8080')
UPLOAD_FOLDER = '/app/uploads'
ALLOWED_EXTENSIONS = {'xlsx', 'xls', 'csv'}

# Ensure upload directory exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def send_sms_to_bridge(sender_number, sms_message, received_timestamp):
    """Send SMS to the SMS Bridge server"""
    try:
        payload = {
            "sender_number": sender_number,
            "sms_message": sms_message,
            "received_timestamp": received_timestamp
        }
        
        response = requests.post(
            f"{SMS_BRIDGE_URL}/sms/receive",
            json=payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        return {
            'success': response.status_code == 200,
            'status_code': response.status_code,
            'response': response.json() if response.headers.get('content-type') == 'application/json' else response.text
        }
    except Exception as e:
        return {
            'success': False,
            'error': str(e)
        }

@app.route('/')
def index():
    """Main page with single SMS form and file upload"""
    return render_template('index.html')

@app.route('/send_single', methods=['POST'])
def send_single_sms():
    """Send a single SMS message"""
    sender_number = request.form.get('sender_number')
    sms_message = request.form.get('sms_message')
    received_timestamp = request.form.get('received_timestamp')
    
    # Validate input
    if not all([sender_number, sms_message, received_timestamp]):
        flash('All fields are required', 'error')
        return redirect(url_for('index'))
    
    # Send to SMS Bridge
    result = send_sms_to_bridge(sender_number, sms_message, received_timestamp)
    
    if result['success']:
        flash(f'SMS sent successfully! Response: {result["response"]}', 'success')
    else:
        error_msg = result.get('error', f'Failed with status code: {result.get("status_code")}')
        flash(f'Failed to send SMS: {error_msg}', 'error')
    
    return redirect(url_for('index'))

@app.route('/upload_file', methods=['POST'])
def upload_file():
    """Upload and process Excel/CSV file with SMS data"""
    if 'file' not in request.files:
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    file = request.files['file']
    if file.filename == '':
        flash('No file selected', 'error')
        return redirect(url_for('index'))
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        
        try:
            # Read the file based on extension
            if filename.endswith(('.xlsx', '.xls')):
                df = pd.read_excel(filepath)
            elif filename.endswith('.csv'):
                df = pd.read_csv(filepath)
            
            # Validate required columns
            required_columns = ['sender_number', 'sms_message', 'received_timestamp']
            if not all(col in df.columns for col in required_columns):
                flash(f'File must contain columns: {", ".join(required_columns)}', 'error')
                return redirect(url_for('index'))
            
            # Process each row
            results = []
            success_count = 0
            error_count = 0
            
            for index, row in df.iterrows():
                result = send_sms_to_bridge(
                    str(row['sender_number']),
                    str(row['sms_message']),
                    str(row['received_timestamp'])
                )
                
                results.append({
                    'row': index + 1,
                    'sender_number': row['sender_number'],
                    'success': result['success'],
                    'response': result.get('response', result.get('error'))
                })
                
                if result['success']:
                    success_count += 1
                else:
                    error_count += 1
            
            # Store results in session for display
            session_results = {
                'filename': filename,
                'total_rows': len(df),
                'success_count': success_count,
                'error_count': error_count,
                'results': results
            }
            
            flash(f'File processed: {success_count} successful, {error_count} failed out of {len(df)} total', 'info')
            return render_template('results.html', results=session_results)
            
        except Exception as e:
            flash(f'Error processing file: {str(e)}', 'error')
            return redirect(url_for('index'))
    else:
        flash('Invalid file type. Please upload Excel (.xlsx, .xls) or CSV files only.', 'error')
        return redirect(url_for('index'))

@app.route('/health')
def health_check():
    """Health check endpoint"""
    return jsonify({"status": "healthy", "service": "SMS Bridge Test Application"})

@app.route('/api/send_sms', methods=['POST'])
def api_send_sms():
    """API endpoint for sending SMS (for automation/scripts)"""
    try:
        data = request.get_json()
        
        if not data or not all(key in data for key in ['sender_number', 'sms_message', 'received_timestamp']):
            return jsonify({
                'success': False,
                'error': 'Missing required fields: sender_number, sms_message, received_timestamp'
            }), 400
        
        result = send_sms_to_bridge(
            data['sender_number'],
            data['sms_message'],
            data['received_timestamp']
        )
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000, debug=True)
