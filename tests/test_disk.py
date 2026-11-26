# sysmaint/tests/test_disk.py

from __future__ import annotations

from unittest.mock import patch

from sysmaint.modules.disk import check_disk


@patch("sysmaint.modules.disk.run_command")
def test_check_disk_windows(mock_run):
    """Test Windows disk check command construction."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""

    with patch("platform.system", return_value="Windows"):
        result = check_disk(repair=False, volume="C:")

    assert result["tool"] == "chkdsk"
    assert result["volume"] == "C:"
    assert "/scan" in result["output"] or mock_run.called
    mock_run.assert_called_once()


@patch("sysmaint.modules.disk.run_command")
def test_check_disk_linux(mock_run):
    """Test Linux disk check command construction."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = ""
    mock_run.return_value.stderr = ""

    with patch("platform.system", return_value="Linux"):
        result = check_disk(repair=True)

    assert result["tool"] == "fsck"
    assert "-y" in mock_run.call_args[0][0]
    mock_run.assert_called_once()