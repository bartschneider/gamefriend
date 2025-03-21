import os
import shutil
import sys
from pathlib import Path

import pytest

# Add the project root to the Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


@pytest.fixture(autouse=True)
def setup_test_env():
    """Setup test environment variables and paths."""
    # Create a temporary guides directory for testing
    guides_dir = project_root / "guides"
    guides_dir.mkdir(exist_ok=True)

    yield

    # Clean up after tests
    if guides_dir.exists():
        for item in guides_dir.glob("*"):
            if item.is_file():
                item.unlink()
            elif item.is_dir():
                shutil.rmtree(item)
        guides_dir.rmdir()
