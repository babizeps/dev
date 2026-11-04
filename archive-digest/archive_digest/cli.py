"""Kommandozeile: archive-digest <url>"""

from __future__ import annotations

import sys
from pathlib import Path

import anthropic
import click

from .extract import extract_article
from .fetch import DEFAULT_MIRROR, FetchError, fetch_snapshot
from .summarize import DEFAULT_MODEL, SummaryRefused, stream_overview


@click.command(context_settings={"help_option_names": ["-h", "--help"]})
@click.argument("url", required=False)
@click.option("--html", "html_file", type=click.Path(exists=True, dir_okay=False, path_type=Path),
              help="Lokal gespeicherte archive.ph-Seite statt Download verwenden.")
@click.option("-k", "--kurz", "short", is_flag=True, help="Nur TL;DR und wenige Stichpunkte.")
@click.option("--text", "text_only", is_flag=True, help="Nur den extrahierten Artikeltext ausgeben (ohne Claude).")
@click.option("-l", "--sprache", "language", default="Deutsch", show_default=True, help="Sprache des Überblicks.")
@click.option("--model", default=DEFAULT_MODEL, show_default=True, help="Claude-Modell.")
@click.option("--effort", type=click.Choice(["low", "medium", "high", "xhigh", "max"]),
              default="medium", show_default=True, help="Wie gründlich Claude nachdenkt.")
@click.option("--mirror", default=DEFAULT_MIRROR, show_default=True,
              help="archive.today-Spiegel, z.B. https://archive.is")
def cli(url, html_file, short, text_only, language, model, effort, mirror):
    """Ruft einen Artikel über archive.ph ab und gibt einen Überblick.

    URL kann ein archive.ph-Link (https://archive.ph/AbCd1) oder die Original-URL
    eines Artikels sein – dann wird der neueste Snapshot verwendet.
    """
    if not url and not html_file:
        raise click.UsageError("Bitte eine URL oder --html DATEI angeben.")

    if html_file:
        snapshot, html = None, html_file.read_text(encoding="utf-8", errors="replace")
    else:
        click.secho(f"Lade Snapshot für {url} …", fg="bright_black", err=True)
        try:
            snapshot, html = fetch_snapshot(url, mirror=mirror)
        except FetchError as exc:
            raise click.ClickException(str(exc)) from exc

    article = extract_article(html, snapshot_url=snapshot)
    if article.word_count < 50:
        raise click.ClickException(
            "Im Snapshot wurde kaum Artikeltext gefunden (Paywall, leere Seite oder CAPTCHA?)."
        )

    info = f"„{article.title}“ – {article.word_count} Wörter"
    if snapshot:
        info += f" – {snapshot}"
    click.secho(info, fg="bright_black", err=True)

    if text_only:
        click.echo(article.text)
        return

    try:
        for chunk in stream_overview(article, model=model, language=language, short=short, effort=effort):
            sys.stdout.write(chunk)
            sys.stdout.flush()
        sys.stdout.write("\n")
    except SummaryRefused as exc:
        raise click.ClickException(f"Abgelehnt: {exc}") from exc
    except anthropic.AuthenticationError as exc:
        raise click.ClickException("Kein gültiger API-Key – ANTHROPIC_API_KEY setzen.") from exc
    except anthropic.RateLimitError as exc:
        raise click.ClickException("Rate-Limit erreicht, bitte kurz warten.") from exc
    except anthropic.APIStatusError as exc:
        raise click.ClickException(f"API-Fehler {exc.status_code}: {exc.message}") from exc
    except anthropic.APIConnectionError as exc:
        raise click.ClickException("Keine Verbindung zur Claude-API.") from exc


if __name__ == "__main__":
    cli()
