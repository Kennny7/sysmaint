# tests/test_recovery.py

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from sysmaint.modules.recovery import carve_recoverable_files, list_shadow_copies


def test_carve_recoverable_files_pdf_and_png(tmp_path: Path):
    """Carve synthetic PDF and PNG payloads from a binary blob."""
    img_dir = tmp_path / "source"
    out_dir = tmp_path / "recovered"
    img_dir.mkdir()

    pdf_bytes = b"%PDF-1.4\nhello world\n%%EOF"
    png_bytes = b"\x89PNG\r\n\x1a\nfake_png_dataIEND\xaeB`\x82"
    blob = b"\x00" * 64 + pdf_bytes + b"\x00" * 32 + png_bytes + b"\x00" * 16

    img_file = img_dir / "disk.img"
    img_file.write_bytes(blob)

    dry_res = carve_recoverable_files(img_file, out_dir, file_types=["pdf", "png"], dry_run=True)
    assert dry_res["carved_count"] == 2
    assert not out_dir.exists()

    real_res = carve_recoverable_files(img_file, out_dir, file_types=["pdf", "png"], dry_run=False)
    assert real_res["carved_count"] == 2
    carved_files = list(out_dir.iterdir())
    assert len(carved_files) == 2
    assert any(f.suffix == ".pdf" and f.read_bytes() == pdf_bytes for f in carved_files)
    assert any(f.suffix == ".png" and f.read_bytes() == png_bytes for f in carved_files)


def test_carve_safety_blocks_same_dir_for_disk_image(tmp_path: Path):
    """Refuse to carve into the same directory as a raw disk image."""
    img_file = tmp_path / "backup.img"
    img_file.write_bytes(b"%PDF-1.4\n%%EOF")
    res = carve_recoverable_files(img_file, tmp_path, dry_run=False)
    assert "error" in res


@patch("sysmaint.modules.recovery.run_command")
def test_list_shadow_copies_windows(mock_run):
    """Parse vssadmin list shadows output cleanly."""
    mock_run.return_value.returncode = 0
    mock_run.return_value.stdout = (
        "Contents of shadow copy set ID: {1111}\n"
        "   Shadow Copy ID: {2222}\n"
        "   Original Volume: (C:)\\\\?\\Volume{abc}\\\n"
        "   Shadow Copy Volume: \\\\?\\GLOBALROOT\\Device\\HarddiskVolumeShadowCopy1\n"
    )
    with patch("platform.system", return_value="Windows"):
        res = list_shadow_copies()

    assert res["count"] == 1
    assert res["shadows"][0]["shadow_id"] == "{2222}"
