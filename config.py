"""Environment configuration for Canvas plugin."""
import os
from pathlib import Path


def load_env():
    """Load environment variables from .env file."""
    env_file = Path(__file__).parent / '.env'
    if env_file.exists():
        with open(env_file) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#'):
                    key, value = line.split('=', 1)
                    os.environ[key] = value

# Load environment variables
load_env()

# Canvas API Configuration
CANVAS_CLIENT_ID = os.getenv('CANVAS_CLIENT_ID')
CANVAS_CLIENT_SECRET = os.getenv('CANVAS_CLIENT_SECRET')
CANVAS_BASE_URL = os.getenv('CANVAS_BASE_URL', 'https://fumage-gh.canvasmedical.com')

# OneRoom Backend Configuration
ONEROOM_WEBHOOK_URL = os.getenv('ONEROOM_WEBHOOK_URL')
