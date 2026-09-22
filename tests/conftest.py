"""pytest configuration: add workspace root to Python path for imports."""

import sys
from pathlib import Path

# Add workspace root to Python path so tests can import app, auth, etc.
workspace_root = Path(__file__).parent.parent
sys.path.insert(0, str(workspace_root))
