from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from archive_digest import cli as cli_mod
from archive_digest.extract import extract_article
from archive_digest.fetch import is_archive_url, looks_like_captcha, snapshot_url
from archive_digest.summarize import build_prompt, stream_overview

FIXTURE = (Path(__file__).parent / "fixture_snapshot.html").read_text(encoding="utf-8")


def test_snapshot_url():
    assert snapshot_url("https://archive.ph/AbCd1") == "https://archive.ph/AbCd1"
    assert snapshot_url("https://archive.is/AbCd1") == "https://archive.is/AbCd1"
    assert snapshot_url("example.com/a") == "https://archive.ph/newest/https://example.com/a"
    assert not is_archive_url("https://example.com/archive.ph")


def test_captcha_detection():
    assert looks_like_captcha('<div class="g-recaptcha"></div>')
    assert not looks_like_captcha(FIXTURE)


def test_extract_article():
    a = extract_article(FIXTURE)
    assert a.title == "Stadt plant autofreie Innenstadt bis 2030"
    assert a.original_url == "https://www.example-zeitung.de/stadt/autofrei-123.html"
    assert a.archived_at == "2026-10-30T08:15:00Z"
    assert "## Kritik vom Einzelhandel" in a.text
    assert "15 Prozent" in a.text and "Parkhäuser" in a.text
    assert a.text.count("34 zu 21") == 1  # dedupliziert
    for noise in ("alert", "Impressum", "Startseite"):
        assert noise not in a.text


class FakeStream:
    def __init__(self, stop_reason="end_turn"):
        self.text_stream = iter(["# Titel", "\n\nInhalt"])
        self._final = SimpleNamespace(stop_reason=stop_reason, stop_details=None)

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def get_final_message(self):
        return self._final


class FakeClient:
    def __init__(self):
        self.calls = []
        self.beta = SimpleNamespace(messages=SimpleNamespace(stream=self._stream))

    def _stream(self, **kwargs):
        self.calls.append(kwargs)
        return FakeStream()


def test_stream_overview_request():
    client = FakeClient()
    article = extract_article(FIXTURE)
    out = "".join(stream_overview(article, client=client))
    assert out == "# Titel\n\nInhalt"
    call = client.calls[0]
    assert call["model"] == "claude-opus-5-5"
    assert call["fallbacks"] == "default"
    assert "<artikel>" in call["messages"][0]["content"]
    assert "Deutsch" in call["system"]


def test_short_prompt():
    prompt = build_prompt(extract_article(FIXTURE), short=True)
    assert "TL;DR" in prompt and "Einordnung" not in prompt


def test_cli_text_only(tmp_path):
    f = tmp_path / "s.html"
    f.write_text(FIXTURE, encoding="utf-8")
    res = CliRunner().invoke(cli_mod.cli, ["--html", str(f), "--text"])
    assert res.exit_code == 0, res.output
    assert "Parkhäuser" in res.output


def test_cli_summary(tmp_path, monkeypatch):
    f = tmp_path / "s.html"
    f.write_text(FIXTURE, encoding="utf-8")
    client = FakeClient()
    real = cli_mod.stream_overview
    monkeypatch.setattr(cli_mod, "stream_overview", lambda a, **kw: real(a, client=client, **kw))
    res = CliRunner().invoke(cli_mod.cli, ["--html", str(f), "-k"])
    assert res.exit_code == 0, res.output
    assert "# Titel" in res.output
