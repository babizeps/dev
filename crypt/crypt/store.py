"""
Vault-Datei lesen und schreiben.
"""
import os
import tempfile
from pathlib import Path
from crypt.crypto import encrypt, decrypt

VAULT_PATH = Path.home() / ".crypt" / "vault.enc"


def vault_exists() -> bool:
    return VAULT_PATH.exists()


def load(password: str) -> dict:
    """Lädt und entschlüsselt den Vault. Wirft RuntimeError wenn kein Vault existiert."""
    if not vault_exists():
        raise RuntimeError("Kein Vault gefunden. Bitte zuerst 'crypt init' ausführen.")
    payload = VAULT_PATH.read_bytes()
    return decrypt(payload, password)


def save(data: dict, password: str) -> None:
    """Verschlüsselt und speichert den Vault atomar (tempfile + os.replace)."""
    VAULT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = encrypt(data, password)

    # Atomar schreiben: erst in Temp-Datei im selben Verzeichnis, dann ersetzen.
    # So bleibt der Vault bei Absturz während des Schreibens intakt.
    fd, tmp_path = tempfile.mkstemp(dir=VAULT_PATH.parent, prefix=".vault_tmp_")
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(payload)
        os.replace(tmp_path, VAULT_PATH)
    except Exception:
        os.unlink(tmp_path)
        raise
