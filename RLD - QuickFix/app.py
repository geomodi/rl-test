"""
RepairLift Attribution Dashboard - Production Server
Standalone version with embedded configuration for Railway deployment
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
# EMBEDDED CONFIGURATION
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

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️ python-dotenv not available, skipping .env file loading")
except Exception as e:
    print(f"⚠️ Error loading .env file: {e}")

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
        'config_loaded': True,
        'api_keys_present': bool(CLAUDE_API_KEY and AIRTABLE_API_KEY)
    })

@app.route('/api/test')
def api_test():
    """Test API endpoint"""
    return jsonify({
        'message': 'RepairLift Attribution Dashboard API is working!',
        'timestamp': datetime.now().isoformat(),
        'config_loaded': True,
        'tables_available': len(AppConfig.FRESH_TABLES),
        'server_info': {
            'host': AppConfig.HOST,
            'port': AppConfig.PORT,
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
        'configuration': {
            'tables_configured': len(AppConfig.FRESH_TABLES),
            'cors_enabled': True,
            'environment_variables': {
                'CLAUDE_API_KEY': 'present' if CLAUDE_API_KEY else 'missing',
                'AIRTABLE_API_KEY': 'present' if AIRTABLE_API_KEY else 'missing',
                'PORT': os.getenv('PORT', '8000'),
                'FLASK_ENV': os.getenv('FLASK_ENV', 'production')
            }
        }
    })

# ============================================================================
# ERROR HANDLERS
# ============================================================================

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Not found', 'message': 'The requested resource was not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error', 'message': 'An unexpected error occurred'}), 500

# ============================================================================
# MAIN EXECUTION
# ============================================================================

if __name__ == '__main__':
    print("🚀 Starting RepairLift Attribution Dashboard...")
    print(f"📊 Server running on {AppConfig.HOST}:{AppConfig.PORT}")
    print(f"🔧 Environment: {os.getenv('FLASK_ENV', 'production')}")
    print(f"✅ Configuration loaded successfully")
    print(f"🔑 API Keys: {'✅ Present' if CLAUDE_API_KEY and AIRTABLE_API_KEY else '❌ Missing'}")
    
    app.run(
        host=AppConfig.HOST,
        port=AppConfig.PORT,
        debug=False
    )
