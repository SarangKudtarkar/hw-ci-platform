import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

# The flow modules import each other by bare name, as they do when run as scripts.
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "flow"))
