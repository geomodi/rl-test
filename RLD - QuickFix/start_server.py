#!/usr/bin/env python3
"""
Production-ready server startup script
"""
import os
import sys
import subprocess

def check_requirements():
    """Check if all required packages are installed"""
    try:
        import flask
        import flask_cors
        import requests
        import dotenv
        print("[OK] All required packages are installed")
        return True
    except ImportError as e:
        print(f"❌ Missing required package: {e}")
        print("📦 Install requirements with: pip install -r requirements.txt")
        return False

def check_environment():
    """Check if environment variables are set"""
    from dotenv import load_dotenv
    load_dotenv()
    
    missing_vars = []
    if not os.getenv('CLAUDE_API_KEY'):
        missing_vars.append('CLAUDE_API_KEY')
    if not os.getenv('AIRTABLE_API_KEY'):
        missing_vars.append('AIRTABLE_API_KEY')
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("📝 Create a .env file with your API keys")
        return False
    
    print("[OK] All environment variables are set")
    return True

def start_production_server():
    """Start the production server with the best available WSGI server"""
    import platform

    # Detect platform and choose appropriate server
    is_windows = platform.system().lower() == 'windows'

    if is_windows:
        # Use Waitress on Windows (cross-platform WSGI server)
        try:
            from waitress import serve
            print("[STARTUP] Starting production server with Waitress (Windows-compatible)...")
            print("[SERVER] Server will be available at http://localhost:8000")
            print("[SECURITY] Production-ready with proper security and performance")

            # Clear module cache to ensure fresh import
            import sys
            if 'server' in sys.modules:
                del sys.modules['server']

            # Import the Flask app (fresh import)
            from server import app

            # Start Waitress server
            serve(
                app,
                host='127.0.0.1',
                port=8000,
                threads=4,                      # 4 threads for handling requests
                connection_limit=100,           # Max 100 concurrent connections
                cleanup_interval=30,            # Clean up connections every 30s
                channel_timeout=120,            # 2 minute timeout for channels
                log_untrusted_proxy_headers=True,
                clear_untrusted_proxy_headers=True
            )

        except ImportError:
            print("❌ Waitress not installed")
            print("📦 Install with: pip install waitress")
            print("🔧 Falling back to development server...")
            start_development_server()

    else:
        # Use Gunicorn on Unix/Linux systems
        try:
            import gunicorn
            print("[STARTUP] Starting production server with Gunicorn (Unix/Linux)...")
            print("[SERVER] Server will be available at http://localhost:8000")
            print("[SECURITY] Production-ready with proper security and performance")

            # Gunicorn configuration
            cmd = [
                "gunicorn",
                "--workers", "2",                    # 2 worker processes
                "--bind", "127.0.0.1:8000",         # Bind to localhost:8000
                "--timeout", "60",                  # 60 second timeout
                "--keep-alive", "5",                # Keep connections alive
                "--max-requests", "1000",           # Restart workers after 1000 requests
                "--max-requests-jitter", "100",     # Add jitter to prevent thundering herd
                "--preload",                        # Preload the application
                "--access-logfile", "-",            # Log to stdout
                "--error-logfile", "-",             # Log errors to stdout
                "server:app"                        # Module:application
            ]

            subprocess.run(cmd)

        except ImportError:
            print("❌ Gunicorn not installed")
            print("📦 Install with: pip install gunicorn")
            print("🔧 Falling back to development server...")
            start_development_server()

def start_development_server():
    """Start the development server"""
    print("[DEV] Starting development server...")
    print("[WARNING] This is for development only - do not use in production!")
    print("[SERVER] Server will be available at http://localhost:8000")
    
    os.environ['FLASK_ENV'] = 'development'
    os.environ['DEBUG'] = 'true'
    
    import server
    # This will trigger the development mode in server.py

def main():
    """Main startup function"""
    print("[STARTUP] Starting Analytics Dashboard Server...")
    print("=" * 50)
    
    # Check requirements
    if not check_requirements():
        sys.exit(1)
    
    # Check environment
    if not check_environment():
        sys.exit(1)
    
    # Determine mode
    mode = os.getenv('SERVER_MODE', 'production').lower()
    
    if mode == 'development' or '--dev' in sys.argv:
        start_development_server()
    else:
        start_production_server()

if __name__ == '__main__':
    main()
