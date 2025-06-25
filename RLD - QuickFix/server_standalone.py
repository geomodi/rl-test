"""
Analytics Dashboard Server - Standalone Version
All configuration embedded to avoid import issues
"""
import os
import sys
import logging
from datetime import datetime, timedelta
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ============================================================================
# EMBEDDED CONFIGURATION (to avoid import issues)
# ============================================================================

class AppConfig:
    """Embedded configuration class"""
    
    # API Configuration
    CLAUDE_API_URL = 'https://api.anthropic.com/v1/messages'
    AIRTABLE_BASE_URL = 'https://api.airtable.com/v0'
    
    # Server Configuration
    HOST = '0.0.0.0'  # Railway requires 0.0.0.0
    PORT = int(os.getenv('PORT', 8000))
    
    # Request Timeouts (in seconds)
    CLAUDE_API_TIMEOUT = 30
    AIRTABLE_API_TIMEOUT = 15
    
    # Pagination Settings
    MAX_RECORDS_PER_REQUEST = 100
    MAX_TOTAL_RECORDS = 10000
    MAX_PAGINATION_PAGES = 50
    
    # Security Settings
    CORS_ORIGINS = ['*']  # Allow all origins for now
    
    # Fresh Tables (Primary)
    FRESH_TABLES = {
        'ghl': {
            'id': 'tblcdFVUC3zJrbmNf',
            'name': 'Fresh GHL',
            'date_field': 'Date Created',
            'sort_direction': 'desc'
        },
        'pos': {
            'id': 'tblHyyZHUsTdEb3BL',
            'name': 'Fresh POS',
            'date_field': 'Created',
            'sort_direction': 'desc'
        },
        'meta_ads': {
            'id': 'tbl7mWcQBNA2TQAjc',
            'name': 'Fresh Meta Ads',
            'date_field': 'Reporting ends',
            'sort_direction': 'desc'
        },
        'meta_ads_summary': {
            'id': 'tblIQXVSwtwq1P4W7',
            'name': 'Meta Ads Summary',
            'date_field': 'Reporting ends',
            'sort_direction': 'desc'
        },
        'meta_ads_simplified': {
            'id': 'tblA6ABFBTURfyZx9',
            'name': 'Meta Ads Simplified',
            'date_field': 'period',
            'sort_direction': 'desc'
        },
        'google_ads': {
            'id': 'tblRBXdh6L6zm9CZn',
            'name': 'Fresh Google Ads',
            'date_field': 'Date',
            'sort_direction': 'desc'
        }
    }

# ============================================================================
# FLASK APPLICATION SETUP
# ============================================================================

# Initialize Flask app
app = Flask(__name__, static_folder='.', static_url_path='')

# Configure CORS
CORS(app, origins=AppConfig.CORS_ORIGINS)

# API Configuration - Using environment variables for security
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')

# Validate that required environment variables are set
if not CLAUDE_API_KEY:
    print("❌ CLAUDE_API_KEY environment variable is required")
    sys.exit(1)
if not AIRTABLE_API_KEY:
    print("❌ AIRTABLE_API_KEY environment variable is required")
    sys.exit(1)

print("✅ Environment variables loaded successfully")

# ============================================================================
# ROUTES
# ============================================================================

@app.route('/')
def index():
    """Serve the main dashboard page"""
    return send_from_directory('.', 'index.html')

@app.route('/health')
def health_check():
    """Health check endpoint for Railway"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'version': '1.0.0',
        'environment': os.getenv('FLASK_ENV', 'production')
    })

@app.route('/api/test')
def api_test():
    """Test API endpoint"""
    return jsonify({
        'message': 'RepairLift Attribution Dashboard API is working!',
        'timestamp': datetime.now().isoformat(),
        'config_loaded': True,
        'tables_available': len(AppConfig.FRESH_TABLES)
    })

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting RepairLift Attribution Dashboard...")
    print(f"📊 Server running on {AppConfig.HOST}:{AppConfig.PORT}")
    print(f"🔧 Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"✅ Configuration loaded successfully")
    
    app.run(
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        debug=False
    )
