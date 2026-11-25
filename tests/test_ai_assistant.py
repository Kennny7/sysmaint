# tests/test_ai_assistant.py

from __future__ import annotations

from unittest.mock import MagicMock, patch

from sysmaint.modules.ai_assistant import (
    RECOMMENDED_MODEL,
    analyze_problem,
    check_ollama_environment,
    is_command_safe,
)


def test_is_command_safe():
    assert is_command_safe("sfc /scannow") is True
    assert is_command_safe("Dism.exe /Online /Cleanup-Image /RestoreHealth") is True
    assert is_command_safe("rm -rf /") is False
    assert is_command_safe("format C:") is False


@patch("sysmaint.modules.ai_assistant.httpx.get")
@patch("sysmaint.modules.ai_assistant.shutil.which", return_value=None)
def test_check_ollama_environment_offline(mock_which, mock_get):
    mock_get.side_effect = ConnectionError("Connection refused")
    res = check_ollama_environment()
    assert res["ready"] is False
    assert res["recommended_model"] == RECOMMENDED_MODEL
    assert len(res["setup_guide"]) >= 2


@patch("sysmaint.modules.ai_assistant.httpx.post")
@patch("sysmaint.modules.ai_assistant.check_ollama_environment")
def test_analyze_problem_returns_structured_plan(mock_env, mock_post):
    mock_env.return_value = {"ready": True, "model": RECOMMENDED_MODEL}
    fake_resp = MagicMock()
    fake_resp.status_code = 200
    fake_resp.json.return_value = {
        "response": (
            '{"diagnosis": "Corrupted DNS cache", "risk_level": "low", '
            '"sysmaint_action": "network flush-dns", '
            '"commands": [{"cmd": "ipconfig /flushdns", "purpose": "Clear DNS", "requires_admin": false}], '
            '"warning": "None"}'
        )
    }
    mock_post.return_value = fake_resp

    res = analyze_problem("Websites fail to resolve after VPN disconnect", execute=False)
    assert res["model"] == RECOMMENDED_MODEL
    assert res["plan"]["diagnosis"] == "Corrupted DNS cache"
    assert res["executed"] is False
