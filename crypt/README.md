# crypt

Verschlüsselter CLI-Passwort-Manager. Passwörter werden lokal mit AES-256-GCM gespeichert, der Schlüssel per scrypt aus dem Master-Passwort abgeleitet.

## Installation

```bash
cd crypt
pip install -r requirements.txt
pip install -e .
```

## Verwendung

```bash
# Vault initialisieren (einmalig)
crypt init

# Passwort hinzufügen
crypt add github -u meinuser

# Passwort automatisch generieren
crypt add github -u meinuser --generate

# Passwort abrufen (kopiert in Zwischenablage)
crypt get github

# Passwort im Terminal anzeigen
crypt get github --show

# Alle Einträge auflisten
crypt list

# Eintrag löschen
crypt delete github
```

## Sicherheit

- **AES-256-GCM** — authentifizierte Verschlüsselung (verhindert Manipulation)
- **scrypt** — memory-hard Key Derivation (Brute-Force-resistent)
- Vault liegt verschlüsselt unter `~/.crypt/vault.enc`
- Kein Netzwerkzugriff, alles lokal

## Dateistruktur

```
crypt/
├── crypt/
│   ├── cli.py      # CLI-Commands (click)
│   ├── crypto.py   # Verschlüsselung (AES-256-GCM + scrypt)
│   └── store.py    # Vault-Datei lesen/schreiben
├── main.py
├── requirements.txt
└── setup.py
```
