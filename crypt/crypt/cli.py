"""
CLI-Interface für crypt
Befehle: init, add, update, get, list, delete
"""
import click
import secrets
import string
import pyperclip

from crypt.store import load, save, vault_exists


ALPHABET = string.ascii_letters + string.digits + "!@#$%^&*"


def prompt_master(confirm: bool = False) -> str:
    return click.prompt("Master-Passwort", hide_input=True, confirmation_prompt=confirm)


def _load_vault(password: str):
    """Lädt den Vault und gibt None bei Fehler zurück (mit Ausgabe)."""
    try:
        return load(password)
    except RuntimeError as e:
        click.echo(f"Fehler: {e}", err=True)
        return None
    except ValueError as e:
        click.echo(f"Fehler: {e}", err=True)
        return None


def _generate_password(length: int = 20) -> str:
    return "".join(secrets.choice(ALPHABET) for _ in range(length))


@click.group()
def cli():
    """crypt — verschlüsselter Passwort-Manager"""
    pass


@cli.command()
def init():
    """Neuen Vault erstellen."""
    if vault_exists():
        click.echo("Vault existiert bereits.")
        return
    password = prompt_master(confirm=True)
    save({}, password)
    click.echo("Vault erstellt.")


@cli.command()
@click.argument("name")
@click.option("--username", "-u", default="", help="Benutzername")
@click.option("--url", default="", help="URL / Website")
@click.option("--notes", "-n", default="", help="Notizen")
@click.option("--generate", "-g", is_flag=True, help="Passwort automatisch generieren")
@click.option("--length", "-l", default=20, show_default=True, help="Länge des generierten Passworts")
def add(name, username, url, notes, generate, length):
    """Eintrag hinzufügen. NAME ist der Bezeichner (z.B. 'github')."""
    password = prompt_master()
    vault = _load_vault(password)
    if vault is None:
        return

    if name in vault:
        if not click.confirm(f"'{name}' existiert bereits. Überschreiben?"):
            return

    if generate:
        entry_password = _generate_password(length)
        pyperclip.copy(entry_password)
        click.echo(f"Generiertes Passwort für '{name}' in Zwischenablage kopiert.")
    else:
        entry_password = click.prompt("Passwort", hide_input=True, confirmation_prompt=True)

    vault[name] = {
        "username": username,
        "password": entry_password,
        "url": url,
        "notes": notes,
    }
    save(vault, password)
    click.echo(f"'{name}' gespeichert.")


@cli.command()
@click.argument("name")
@click.option("--username", "-u", default=None, help="Neuer Benutzername")
@click.option("--url", default=None, help="Neue URL")
@click.option("--notes", "-n", default=None, help="Neue Notizen")
@click.option("--password", "-p", is_flag=True, help="Passwort neu eingeben")
@click.option("--generate", "-g", is_flag=True, help="Neues Passwort generieren")
@click.option("--length", "-l", default=20, show_default=True, help="Länge des generierten Passworts")
def update(name, username, url, notes, password, generate, length):
    """Bestehenden Eintrag aktualisieren. Nur angegebene Felder werden geändert."""
    master = prompt_master()
    vault = _load_vault(master)
    if vault is None:
        return

    if name not in vault:
        click.echo(f"'{name}' nicht gefunden.", err=True)
        return

    entry = vault[name]

    if username is not None:
        entry["username"] = username
    if url is not None:
        entry["url"] = url
    if notes is not None:
        entry["notes"] = notes

    if generate:
        new_pw = _generate_password(length)
        pyperclip.copy(new_pw)
        entry["password"] = new_pw
        click.echo(f"Neues Passwort für '{name}' generiert und in Zwischenablage kopiert.")
    elif password:
        entry["password"] = click.prompt("Neues Passwort", hide_input=True, confirmation_prompt=True)

    # Fehlende Felder aus alten Einträgen ergänzen (Rückwärtskompatibilität)
    entry.setdefault("url", "")
    entry.setdefault("notes", "")

    vault[name] = entry
    save(vault, master)
    click.echo(f"'{name}' aktualisiert.")


@cli.command()
@click.argument("name")
@click.option("--show", "-s", is_flag=True, help="Passwort anzeigen statt kopieren")
def get(name, show):
    """Passwort abrufen. Standardmäßig in Zwischenablage kopieren."""
    password = prompt_master()
    vault = _load_vault(password)
    if vault is None:
        return

    if name not in vault:
        click.echo(f"'{name}' nicht gefunden.", err=True)
        return

    entry = vault[name]
    if entry.get("username"):
        click.echo(f"Benutzer: {entry['username']}")
    if entry.get("url"):
        click.echo(f"URL:      {entry['url']}")
    if entry.get("notes"):
        click.echo(f"Notizen:  {entry['notes']}")

    if show:
        click.echo(f"Passwort: {entry['password']}")
    else:
        pyperclip.copy(entry["password"])
        click.echo(f"Passwort für '{name}' in Zwischenablage kopiert.")


@cli.command(name="list")
def list_entries():
    """Alle gespeicherten Einträge anzeigen."""
    password = prompt_master()
    vault = _load_vault(password)
    if vault is None:
        return

    if not vault:
        click.echo("Vault ist leer.")
        return

    for name, entry in sorted(vault.items()):
        user = f"  ({entry['username']})" if entry.get("username") else ""
        url = f"  {entry['url']}" if entry.get("url") else ""
        click.echo(f"  {name}{user}{url}")


@cli.command()
@click.argument("name")
def delete(name):
    """Eintrag löschen."""
    password = prompt_master()
    vault = _load_vault(password)
    if vault is None:
        return

    if name not in vault:
        click.echo(f"'{name}' nicht gefunden.", err=True)
        return

    if click.confirm(f"'{name}' wirklich löschen?"):
        del vault[name]
        save(vault, password)
        click.echo(f"'{name}' gelöscht.")


if __name__ == "__main__":
    cli()
