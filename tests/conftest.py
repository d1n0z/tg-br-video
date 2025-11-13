import os
import sys
from pathlib import Path

os.environ.setdefault("TOKEN", "fake-token-for-tests")
os.environ.setdefault("DATABASE_URL", "sqlite://:memory:")
os.environ.setdefault("APPLICATIONS_CHAT_ID", "1")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))
