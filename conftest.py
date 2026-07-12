"""pytest configuration — add project src to Python path and skip rate limits."""
import os
import sys
from pathlib import Path

# Bypass license rate limiting during tests
os.environ.setdefault("REVENUEHOLDINGS_SKIP_LIMIT", "1")

# Add user site-packages for dependencies installed outside venv
import site

user_site = site.getusersitepackages()
if user_site and user_site not in sys.path:
    sys.path.insert(0, user_site)

# Add src directory to Python path
src_dir = Path(__file__).parent / "src"
if str(src_dir) not in sys.path:
    sys.path.insert(0, str(src_dir))
