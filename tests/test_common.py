# tests/test_common.py

from __future__ import annotations

from sysmaint.utils.common import extract_progress_percent


def test_extract_progress_percent_dism_sfc_chkdsk():
    assert extract_progress_percent("[========================== 42.5% ==========================]") == 42.5
    assert extract_progress_percent("Verification 35% complete.") == 35.0
    assert extract_progress_percent("18 percent completed.") == 18.0
    assert extract_progress_percent("Deployment Image Servicing and Management tool") is None
