import pytest
from pathlib import Path
from backend.app.core.safety import check_disk_safety, DiskSafetyError

def test_disk_safety_normal(tmp_path: Path):
    # Small test size (10 MB) should pass on any modern disk
    is_safe, free_bytes, required_bytes = check_disk_safety(tmp_path, estimated_output_bytes=10 * 1024 * 1024)
    assert is_safe is True
    assert free_bytes > required_bytes

def test_disk_safety_overflow(tmp_path: Path):
    # Absurdly large size (10,000 Terabytes) should trigger DiskSafetyError
    with pytest.raises(DiskSafetyError):
        check_disk_safety(tmp_path, estimated_output_bytes=10_000 * 1024 * 1024 * 1024 * 1024)
