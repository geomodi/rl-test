from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import requests
import os
import json
from datetime import datetime, timedelta
import subprocess
from collections import defaultdict
import time
import logging
from logging.handlers import RotatingFileHandler
from config import AppConfig
import hashlib
import pickle

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()  # This loads variables from .env file
    print("✅ Environment variables loaded from .env file")
except ImportError:
    print("⚠️  python-dotenv not installed. Using system environment variables only.")
    print("   Install with: pip install python-dotenv")

app = Flask(__name__)
CORS(app)  # Enable CORS for all routes

# Simple in-memory cache for Airtable data
class SimpleCache:
    """
    Simple in-memory cache with TTL (Time To Live) support.
    Perfect for caching Airtable responses to reduce API calls.
    """

    def __init__(self):
        self._cache = {}
        self._timestamps = {}

    def _generate_key(self, base_id, table_id, filter_formula, max_records):
        """Generate a unique cache key for the request parameters"""
        key_data = f"{base_id}:{table_id}:{filter_formula or ''}:{max_records}"
        return hashlib.md5(key_data.encode()).hexdigest()

    def get(self, base_id, table_id, filter_formula=None, max_records=1000, ttl_seconds=300):
        """
        Get cached data if it exists and is not expired.

        Args:
            base_id: Airtable base ID
            table_id: Airtable table ID
            filter_formula: Optional filter formula
            max_records: Maximum records requested
            ttl_seconds: Time to live in seconds (default: 5 minutes)

        Returns:
            Cached data or None if not found/expired
        """
        cache_key = self._generate_key(base_id, table_id, filter_formula, max_records)

        if cache_key not in self._cache:
            return None

        # Check if cache entry has expired
        cache_time = self._timestamps.get(cache_key, 0)
        if time.time() - cache_time > ttl_seconds:
            # Remove expired entry
            del self._cache[cache_key]
            del self._timestamps[cache_key]
            return None

        logger.debug(f"🎯 Cache HIT for key: {cache_key[:8]}...")
        return self._cache[cache_key]

    def set(self, base_id, table_id, data, filter_formula=None, max_records=1000):
        """
        Store data in cache with current timestamp.

        Args:
            base_id: Airtable base ID
            table_id: Airtable table ID
            data: Data to cache
            filter_formula: Optional filter formula
            max_records: Maximum records requested
        """
        cache_key = self._generate_key(base_id, table_id, filter_formula, max_records)
        self._cache[cache_key] = data
        self._timestamps[cache_key] = time.time()

        logger.debug(f"💾 Cache SET for key: {cache_key[:8]}... (size: {len(data.get('records', []))} records)")

    def clear(self):
        """Clear all cached data"""
        self._cache.clear()
        self._timestamps.clear()
        logger.info("🗑️ Cache cleared")

    def get_stats(self):
        """Get cache statistics"""
        total_entries = len(self._cache)
        total_size = sum(len(str(data)) for data in self._cache.values())

        return {
            'total_entries': total_entries,
            'total_size_bytes': total_size,
            'cache_keys': list(self._cache.keys())
        }

# Initialize cache
cache = SimpleCache()

# Configure structured logging
def setup_logging():
    """Configure structured logging with different levels and file rotation"""

    # Create logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Configure logging format
    log_format = logging.Formatter(
        AppConfig.LOG_FORMAT,
        datefmt=AppConfig.LOG_DATE_FORMAT
    )

    # Configure root logger
    logger = logging.getLogger()
    logger.setLevel(getattr(logging, AppConfig.LOG_LEVEL))

    # Console handler (for development)
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    # File handler with rotation (for production)
    file_handler = RotatingFileHandler(
        'logs/server.log',
        maxBytes=AppConfig.LOG_FILE_MAX_BYTES,
        backupCount=AppConfig.LOG_BACKUP_COUNT
    )
    file_handler.setLevel(getattr(logging, AppConfig.LOG_LEVEL))
    file_handler.setFormatter(log_format)

    # Error file handler (separate file for errors)
    error_handler = RotatingFileHandler(
        'logs/errors.log',
        maxBytes=AppConfig.LOG_FILE_MAX_BYTES,
        backupCount=AppConfig.LOG_BACKUP_COUNT
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(log_format)

    # Add handlers to logger
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    logger.addHandler(error_handler)

    # Configure Flask's logger
    app.logger.setLevel(logging.INFO)

    return logger

# Initialize logging
logger = setup_logging()
logger.info("[STARTUP] Analytics Dashboard Server starting up...")
logger.info(f"[INFO] Working directory: {os.getcwd()}")
logger.info(f"[INFO] Python version: {os.sys.version}")

# API Configuration - Using environment variables for security
CLAUDE_API_KEY = os.getenv('CLAUDE_API_KEY')
CLAUDE_API_URL = AppConfig.CLAUDE_API_URL

AIRTABLE_API_KEY = os.getenv('AIRTABLE_API_KEY')
AIRTABLE_BASE_URL = AppConfig.AIRTABLE_BASE_URL

# Validate that required environment variables are set
if not CLAUDE_API_KEY:
    raise ValueError("CLAUDE_API_KEY environment variable is required")
if not AIRTABLE_API_KEY:
    raise ValueError("AIRTABLE_API_KEY environment variable is required")

@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

@app.route('/health', methods=['GET'])
def health_check():
    """
    Health check endpoint that verifies all critical components are working.
    Returns detailed status information for monitoring and debugging.
    """
    try:
        health_status = {
            'status': 'healthy',
            'timestamp': datetime.now().isoformat(),
            'version': '1.0.0',
            'components': {}
        }

        # Check environment variables
        try:
            if CLAUDE_API_KEY and AIRTABLE_API_KEY:
                health_status['components']['environment'] = {
                    'status': 'healthy',
                    'message': 'All required environment variables are set'
                }
            else:
                health_status['components']['environment'] = {
                    'status': 'unhealthy',
                    'message': 'Missing required environment variables'
                }
                health_status['status'] = 'unhealthy'
        except Exception as e:
            health_status['components']['environment'] = {
                'status': 'error',
                'message': f'Environment check failed: {str(e)}'
            }
            health_status['status'] = 'unhealthy'

        # Check file system (logs directory)
        try:
            if os.path.exists('logs') and os.access('logs', os.W_OK):
                health_status['components']['filesystem'] = {
                    'status': 'healthy',
                    'message': 'Logs directory is accessible'
                }
            else:
                health_status['components']['filesystem'] = {
                    'status': 'warning',
                    'message': 'Logs directory not accessible (will use console only)'
                }
        except Exception as e:
            health_status['components']['filesystem'] = {
                'status': 'error',
                'message': f'Filesystem check failed: {str(e)}'
            }

        # Test Airtable connectivity (optional quick test)
        try:
            # Just test if we can make a basic request (don't actually fetch data)
            test_url = f"{AIRTABLE_BASE_URL}/meta"  # Airtable meta endpoint
            test_headers = {'Authorization': f'Bearer {AIRTABLE_API_KEY}'}

            # Quick connectivity test with short timeout
            test_response = requests.get(test_url, headers=test_headers, timeout=5)

            if test_response.status_code in [200, 401, 403]:  # Any response means connectivity works
                health_status['components']['airtable'] = {
                    'status': 'healthy',
                    'message': 'Airtable API is reachable'
                }
            else:
                health_status['components']['airtable'] = {
                    'status': 'warning',
                    'message': f'Airtable API returned status {test_response.status_code}'
                }
        except requests.exceptions.Timeout:
            health_status['components']['airtable'] = {
                'status': 'warning',
                'message': 'Airtable API timeout (may be slow)'
            }
        except Exception as e:
            health_status['components']['airtable'] = {
                'status': 'warning',
                'message': f'Airtable connectivity test failed: {str(e)}'
            }

        # Determine overall status
        component_statuses = [comp['status'] for comp in health_status['components'].values()]
        if 'error' in component_statuses or health_status['status'] == 'unhealthy':
            health_status['status'] = 'unhealthy'
            status_code = 503
        elif 'warning' in component_statuses:
            health_status['status'] = 'degraded'
            status_code = 200
        else:
            health_status['status'] = 'healthy'
            status_code = 200

        logger.info(f"🏥 Health check completed: {health_status['status']}")
        return jsonify(health_status), status_code

    except Exception as e:
        logger.error(f"💥 Health check failed: {str(e)}", exc_info=True)
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'message': f'Health check failed: {str(e)}'
        }), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        # Get the request data from the frontend
        data = request.json

        logger.info(f"💬 Chat request received with {len(data.get('messages', []))} messages")
        logger.debug(f"📝 Full request: {json.dumps(data, indent=2)}")

        # Extract system message and user messages
        messages = data.get('messages', [])
        system_message = None
        filtered_messages = []

        for message in messages:
            if message.get('role') == 'system':
                system_message = message.get('content')
            else:
                filtered_messages.append(message)

        # Prepare the request to Claude API with correct format
        claude_request = {
            'model': data.get('model', 'claude-3-opus-20240229'),
            'max_tokens': data.get('max_tokens', 4000),
            'temperature': data.get('temperature', 0.7),
            'messages': filtered_messages
        }

        # Add system message if present
        if system_message:
            claude_request['system'] = system_message

        logger.info(f"🤖 Sending request to Claude API (model: {claude_request['model']})")
        logger.debug(f"📤 Claude request: {json.dumps(claude_request, indent=2)}")

        # Prepare headers
        headers = {
            'Content-Type': 'application/json',
            'x-api-key': CLAUDE_API_KEY,
            'anthropic-version': '2023-01-01'
        }

        # Forward the request to Claude API with timeout
        try:
            response = requests.post(
                CLAUDE_API_URL,
                json=claude_request,
                headers=headers,
                timeout=AppConfig.CLAUDE_API_TIMEOUT
            )
        except requests.exceptions.Timeout:
            logger.error("⏱️ Claude API request timed out after 30 seconds")
            return jsonify({"error": "Request timed out. Please try again."}), 504
        except requests.exceptions.ConnectionError:
            logger.error("🔌 Failed to connect to Claude API")
            return jsonify({"error": "Unable to connect to AI service. Please try again."}), 503
        except requests.exceptions.RequestException as e:
            logger.error(f"🚫 Claude API request failed: {str(e)}")
            return jsonify({"error": "AI service request failed. Please try again."}), 502

        # Check if the request was successful
        if response.status_code != 200:
            logger.error(f"❌ Claude API error: {response.status_code} - {response.text}")
            return jsonify({"error": f"Claude API returned status code {response.status_code}"}), response.status_code

        # Return the response from Claude API
        logger.info("✅ Claude API request successful")
        return jsonify(response.json())

    except Exception as e:
        logger.error(f"💥 Unexpected error in /api/chat: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

def validate_airtable_params(base_id, table_id, max_records_str, filter_formula):
    """
    Validate and sanitize input parameters for Airtable API requests.
    Returns (validated_params, error_message) tuple.
    """
    errors = []

    # Validate base_id format (should start with 'app' and be 17 chars)
    if not base_id:
        errors.append("baseId is required")
    elif not base_id.startswith('app') or len(base_id) != 17:
        errors.append("baseId must start with 'app' and be 17 characters long")

    # Validate table_id format (should start with 'tbl' and be 17 chars)
    if not table_id:
        errors.append("tableId is required")
    elif not table_id.startswith('tbl') or len(table_id) != 17:
        errors.append("tableId must start with 'tbl' and be 17 characters long")

    # Validate max_records (optional - if not specified, fetch ALL records)
    max_records = None  # No limit by default - fetch ALL records
    if max_records_str:
        try:
            max_records = int(max_records_str)
            if max_records <= 0:
                errors.append("maxRecords must be a positive integer")
            elif max_records > AppConfig.MAX_TOTAL_RECORDS:
                errors.append(f"maxRecords cannot exceed {AppConfig.MAX_TOTAL_RECORDS:,} (configured limit)")
        except ValueError:
            errors.append("maxRecords must be a valid integer")

    # Validate filter formula (basic sanitization)
    if filter_formula:
        # Check for potentially dangerous patterns
        dangerous_patterns = ['javascript:', 'eval(', 'script>', 'DROP TABLE', 'DELETE FROM']
        filter_lower = filter_formula.lower()
        for pattern in dangerous_patterns:
            if pattern in filter_lower:
                errors.append(f"Filter formula contains potentially dangerous pattern: {pattern}")

        # Check length (Airtable has limits)
        if len(filter_formula) > 1000:
            errors.append("Filter formula is too long (max 1000 characters)")

    if errors:
        return None, "; ".join(errors)

    return {
        'base_id': base_id,
        'table_id': table_id,
        'max_records': max_records,
        'filter_formula': filter_formula
    }, None

@app.route('/api/airtable/records', methods=['GET'])
def get_airtable_records():
    try:
        # Get and validate query parameters
        base_id = request.args.get('baseId')
        table_id = request.args.get('tableId')
        max_records_str = request.args.get('maxRecords')  # No default limit - fetch ALL records
        filter_formula = request.args.get('filterByFormula')

        # Validate input parameters
        validated_params, error_msg = validate_airtable_params(
            base_id, table_id, max_records_str, filter_formula
        )

        if error_msg:
            logger.warning(f"🚫 Validation error: {error_msg}")
            return jsonify({"error": f"Validation error: {error_msg}"}), 400

        # Extract validated parameters
        base_id = validated_params['base_id']
        table_id = validated_params['table_id']
        max_records = validated_params['max_records']
        filter_formula = validated_params['filter_formula']

        logger.info(f"📊 Airtable request: baseId={base_id}, tableId={table_id}, maxRecords={max_records}")
        if filter_formula:
            logger.debug(f"🔍 Filter formula: {filter_formula}")

        # Check cache first (5 minute TTL for most requests, 1 minute for filtered requests)
        cache_ttl = 60 if filter_formula else 300  # Shorter TTL for filtered data
        cached_data = cache.get(base_id, table_id, filter_formula, max_records, cache_ttl)

        if cached_data:
            logger.info(f"🎯 Returning cached data: {len(cached_data.get('records', []))} records")
            return jsonify(cached_data)

        # Prepare Airtable API request
        url = f"{AIRTABLE_BASE_URL}/{base_id}/{table_id}"
        headers = {
            'Authorization': f'Bearer {AIRTABLE_API_KEY}',
            'Content-Type': 'application/json'
        }

        params = {
            'maxRecords': max_records
        }

        # Add optional filters
        if request.args.get('filterByFormula'):
            params['filterByFormula'] = request.args.get('filterByFormula')

        if request.args.get('sort'):
            params['sort'] = request.args.get('sort')

        # Add pagination support
        if request.args.get('offset'):
            params['offset'] = request.args.get('offset')

        logger.info(f"🌐 Fetching Airtable data from: {url}")
        logger.debug(f"📋 Initial params: {params}")

        # 🚨 SIMPLIFIED PAGINATION - Remove all complex logic
        all_records = []
        offset = None
        page_count = 0
        max_pages = 100  # Increased safety limit

        if max_records is None:
            logger.info(f"🚨 SIMPLIFIED PAGINATION v3.0 - Fetching ALL available records (no limits)")
        else:
            logger.info(f"🚨 SIMPLIFIED PAGINATION v3.0 - Fetching up to {max_records} records")

        while page_count < max_pages:
            page_count += 1

            # Simple page parameters - let Airtable handle pagination naturally
            page_params = {}

            # Only add offset if we have one from previous page
            if offset:
                page_params['offset'] = offset
                logger.info(f"📄 Page {page_count}: Using offset from previous page")
            else:
                logger.info(f"📄 Page {page_count}: Starting fresh (no offset)")

            # ✅ FIX: Don't add maxRecords parameter when we want ALL records
            # This allows Airtable to return its default page size (100 records per page)
            # and we'll paginate through all pages to get all records
            if max_records is not None:
                # Only add maxRecords if a specific limit was requested
                remaining_records = max_records - len(all_records)
                if remaining_records <= 0:
                    logger.info(f"📄 Page {page_count}: Reached maxRecords limit of {max_records}")
                    break
                # Request up to 100 records per page (Airtable's max per page)
                page_params['maxRecords'] = min(100, remaining_records)
                logger.info(f"📄 Page {page_count}: Requesting {page_params['maxRecords']} records (remaining: {remaining_records})")

            # Add any filters that were requested
            if 'filterByFormula' in params and params['filterByFormula']:
                page_params['filterByFormula'] = params['filterByFormula']

            # Add sorting for consistent results
            table_config = AppConfig.get_table_config(table_id)
            if table_config:
                page_params['sort[0][field]'] = table_config['date_field']
                page_params['sort[0][direction]'] = table_config['sort_direction']

            # Make request to Airtable
            try:
                response = requests.get(
                    url,
                    headers=headers,
                    params=page_params,
                    timeout=AppConfig.AIRTABLE_API_TIMEOUT
                )
                response.raise_for_status()
            except requests.exceptions.RequestException as e:
                logger.error(f"❌ Airtable API error on page {page_count}: {str(e)}")
                return jsonify({"error": f"Data service error: {str(e)}"}), 502

            data = response.json()
            page_records = data.get('records', [])

            # Add records from this page
            for record in page_records:
                flattened_record = {
                    'id': record['id'],
                    'createdTime': record['createdTime'],
                    **record['fields']
                }
                all_records.append(flattened_record)

            logger.info(f"📄 Page {page_count}: {len(page_records)} records (Total: {len(all_records)})")

            # Check for next page
            offset = data.get('offset')
            if offset:
                logger.info(f"✅ More pages available - continuing...")
                continue
            else:
                logger.info(f"🔚 No more pages - pagination complete")
                break

        # 🔧 FINAL DEDUPLICATION: Remove any duplicate records by ID
        seen_ids = set()
        unique_records = []
        original_count = len(all_records)

        for record in all_records:
            record_id = record.get('id')
            if record_id not in seen_ids:
                seen_ids.add(record_id)
                unique_records.append(record)
            else:
                logger.debug(f"🔧 DEDUPLICATION: Removed duplicate record {record_id}")

        if len(unique_records) != original_count:
            logger.info(f"🔧 DEDUPLICATION: Removed {original_count - len(unique_records)} duplicate records")
            all_records = unique_records

        # Prepare final response
        response_data = {
            'records': all_records,
            'offset': None,  # No offset since we fetched all available records
            'pagination_info': {
                'total_records': len(all_records),
                'pages_fetched': page_count,
                'server_side_pagination': True,
                'duplicates_removed': original_count - len(all_records)
            }
        }

        logger.info(f"Server-side pagination complete: {len(all_records)} total records from {page_count} pages")

        # Cache the successful response
        cache.set(base_id, table_id, response_data, filter_formula, max_records)

        return jsonify(response_data)

    except Exception as e:
        logger.error(f"💥 Unexpected error in /api/airtable/records: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

@app.route('/api/cache', methods=['GET', 'DELETE'])
def manage_cache():
    """
    Cache management endpoint for monitoring and clearing cache.
    GET: Returns cache statistics
    DELETE: Clears all cached data
    """
    try:
        if request.method == 'GET':
            # Return cache statistics
            stats = cache.get_stats()
            stats['cache_enabled'] = True
            stats['timestamp'] = datetime.now().isoformat()

            logger.info(f"📊 Cache stats requested: {stats['total_entries']} entries")
            return jsonify(stats)

        elif request.method == 'DELETE':
            # Clear cache
            cache.clear()
            logger.info("🗑️ Cache cleared via API request")
            return jsonify({
                'status': 'success',
                'message': 'Cache cleared successfully',
                'timestamp': datetime.now().isoformat()
            })

    except Exception as e:
        logger.error(f"💥 Error in cache management: {str(e)}", exc_info=True)
        return jsonify({"error": str(e)}), 500

# Debug test page for Airtable pagination
@app.route('/debug-airtable')
def debug_airtable():
    """Serve the Airtable debug test page"""
    return send_from_directory('.', 'debug_airtable_test.html')

# Serve static files
@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('.', path)

if __name__ == '__main__':
    # Check if we're in development or production
    is_development = os.getenv('FLASK_ENV') == 'development' or os.getenv('DEBUG') == 'true'

    if is_development:
        print("🔧 Starting in DEVELOPMENT mode...")
        print("⚠️  Do NOT use this in production!")
        print("🌐 Server will be available at http://localhost:8000")
        app.run(debug=True, port=8000, host='127.0.0.1')
    else:
        print("[PRODUCTION] Starting in PRODUCTION mode...")
        print("[TIP] For best results, use the startup script: python start_server_dev.py")
        print("[SECURITY] This will automatically choose the right production server")
        print("🌐 Server will be available at http://localhost:8000")

        # Fallback to development server with production settings
        print("⚠️  Using Flask development server with production settings...")
        app.run(debug=False, port=8000, host='127.0.0.1', threaded=True)
