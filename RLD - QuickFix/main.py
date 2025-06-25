#!/usr/bin/env python3
"""
RepairLift Attribution Dashboard - Main Entry Point
Simple, reliable Flask application for Railway deployment
"""
import os
import sys
from datetime import datetime
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS

# Environment variable validation
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')

if not CLAUDE_API_KEY:
    print("❌ CLAUDE_API_KEY environment variable is required")
    sys.exit(1)
if not AIRTABLE_API_KEY:
    print("❌ AIRTABLE_API_KEY environment variable is required")
    sys.exit(1)

print("✅ Environment variables loaded successfully")

# Create Flask application
app = Flask(__name__, static_folder='.', static_url_path='')
CORS(app, origins=['*'])

@app.route('/')
def index():
    """Serve the main dashboard page"""
    try:
        return send_from_directory('.', 'index.html')
    except Exception as e:
        return jsonify({'error': 'Dashboard not found', 'message': str(e)}), 404

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'environment': os.getenv('FLASK_ENV', 'production'),
        'api_keys_present': bool(CLAUDE_API_KEY and AIRTABLE_API_KEY)
    })

@app.route('/api/test')
def api_test():
    """Test API endpoint"""
    return jsonify({
        'message': 'RepairLift Attribution Dashboard API is working!',
        'timestamp': datetime.now().isoformat(),
        'server_info': {
            'host': '0.0.0.0',
            'port': int(os.getenv('PORT', 8000)),
            'environment': os.getenv('FLASK_ENV', 'production')
        }
    })

@app.route('/api/status')
def api_status():
    """Detailed status endpoint"""
    return jsonify({
        'application': 'RepairLift Attribution Dashboard',
        'status': 'running',
        'timestamp': datetime.now().isoformat(),
        'environment_variables': {
            'CLAUDE_API_KEY': 'present' if CLAUDE_API_KEY else 'missing',
            'AIRTABLE_API_KEY': 'present' if AIRTABLE_API_KEY else 'missing',
            'PORT': os.getenv('PORT', '8000'),
            'FLASK_ENV': os.getenv('FLASK_ENV', 'production')
        }
    })

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

if __name__ == '__main__':
    print("🚀 Starting RepairLift Attribution Dashboard...")
    print(f"📊 Server running on 0.0.0.0:{os.getenv('PORT', 8000)}")
    print(f"🔧 Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"🔑 API Keys: {'✅ Present' if CLAUDE_API_KEY and AIRTABLE_API_KEY else '❌ Missing'}")
    
    app.run(
        host='0.0.0.0',
        port=int(os.getenv('PORT', 8000)),
        debug=False
    )
