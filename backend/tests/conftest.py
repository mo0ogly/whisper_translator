import sys
from pathlib import Path

# Allow imports like "from backend.main import ..."
sys.path.insert(0, str(Path(__file__).resolve().parent.parent.parent))
