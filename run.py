#!/usr/bin/env python3
"""
Bitespeed Identity Reconciliation System Runner
Optimized startup script with environment configuration
"""

import os
import sys
import uvicorn
from pathlib import Path

def setup_environment():
    """Setup environment and create necessary directories"""
    
    # Create static directory if it doesn't exist
    static_dir = Path("static")
    static_dir.mkdir(exist_ok=True)
    
    # Set environment variables if not already set
    os.environ.setdefault("ENVIRONMENT", "development")
    
    print("🔮 Bitespeed Identity Reconciliation System")
    print("=" * 50)
    print(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    print(f"Static directory: {static_dir.absolute()}")
    print(f"Python version: {sys.version}")
    print("=" * 50)

def main():
    """Main application runner"""
    setup_environment()
    
    # Configuration based on environment
    config = {
        "app": "main:app",
        "host": "0.0.0.0",
        "port": int(os.environ.get("PORT", 8000)),
        "reload": os.environ.get("ENVIRONMENT") == "development",
        "workers": 1 if os.environ.get("ENVIRONMENT") == "development" else 4,
        "log_level": "info"
    }
    
    print(f"🚀 Starting server on http://{config['host']}:{config['port']}")
    print(f"📊 Dashboard available at http://localhost:{config['port']}")
    print(f"🔧 API docs at http://localhost:{config['port']}/docs")
    
    try:
        uvicorn.run(**config)
    except KeyboardInterrupt:
        print("\n👋 Shutting down gracefully...")
    except Exception as e:
        print(f"❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()