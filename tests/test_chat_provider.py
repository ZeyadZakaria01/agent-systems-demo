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


def test_a_provider_whose_per_minute_token_limit_is_below_one_request_is_refused_before_any_take():
    from scripts.chat_series import fits_per_minute

    assert not fits_per_minute(prompt_tokens=6500, tokens_per_minute=8000)  # Groq free tier: one request is ~8.5k
    assert fits_per_minute(prompt_tokens=6500, tokens_per_minute=250_000)  # Gemini free tier
    assert fits_per_minute(prompt_tokens=6500, tokens_per_minute=None)  # no header: the first take finds out


def test_memstates_static_prompt_is_measured_from_its_source():
    from scripts.chat_series import static_prompt_tokens

    tokens = static_prompt_tokens()
    assert 4000 < tokens < 20000  # the largest route's system prompt and tool list, measured, not assumed
