"""
BEEASY2025 Flask Application Entry Point
Run with: python run.py
"""

import os
from app import create_app

# Create Flask app instance
app = create_app(os.getenv('FLASK_ENV', 'development'))

if __name__ == '__main__':
    # Development server settings
    app.run(
        host='0.0.0.0',
        port=5000,
        debug=app.config.get('DEBUG', True)
    )
