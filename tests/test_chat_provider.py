"""Chat runs on a hosted model: `--provider groq` sends every turn to Groq, starts no Ollama, and the recording says
which provider and model answered; the series runner starts a take only when the free-tier quota can finish it."""

import pytest

from demo import chat_run
from demo.chat_recording import chat_provider


def test_the_provider_defaults_to_ollama_and_refuses_an_unknown_one(monkeypatch):
    monkeypatch.delenv("GEM_CHAT_PROVIDER", raising=False)
    assert chat_provider() == "ollama"
    monkeypatch.setenv("GEM_CHAT_PROVIDER", "groq")
    assert chat_provider() == "groq"
    monkeypatch.setenv("GEM_CHAT_PROVIDER", "grok")
    with pytest.raises(ValueError, match="grok"):
        chat_provider()


def test_a_groq_run_starts_no_ollama_and_records_the_groq_model(monkeypatch, tmp_path):
    monkeypatch.setenv("GEM_CHAT_PROVIDER", "groq")
    monkeypatch.setenv("MEMSTATE_GROQ_MODEL", "openai/gpt-oss-20b")
    monkeypatch.setattr(chat_run, "ollama_running", lambda: pytest.fail("Ollama must not start for Groq"))
    seen = {}

    def record_case(case, run, recordings, link_root, flags, environment, command, base_url):
        seen.update(environment=environment, base_url=base_url)
        return tmp_path / "rec.json"

    monkeypatch.setattr(chat_run, "_record_case", record_case)
    result = chat_run.record_chats(object(), tmp_path, tmp_path, "cmd", ("bad-merge",), log=lambda *_: None)
    assert result.errors == [] and seen["environment"] == {"provider": "groq", "groq_model_setting": "openai/gpt-oss-20b"}
    assert "groq" in seen["base_url"]


def test_the_series_starts_a_take_only_when_the_daily_quota_can_finish_it():
    from scripts.chat_series import take_fits

    assert take_fits(remaining_requests=40, per_take=12)
    assert not take_fits(remaining_requests=13, per_take=12)  # a 20% margin: a take that cannot finish wastes its start
    assert take_fits(remaining_requests=40, per_take=None)  # unknown cost before the first take: one take is allowed
