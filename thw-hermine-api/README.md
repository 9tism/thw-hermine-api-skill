# Skill „thw-hermine-api“

**Version 0.2.1-alpha** (26.10.2026) – früher Stand: Inhalte stammen aus einem Projekt und
sind nur teilweise breit erprobt; Rückmeldungen und Korrekturen sind willkommen.

Bis Version 0.1-alpha hieß der Skill „hermine-api“. Wer ihn schon installiert hat, löscht
den alten Ordner `hermine-api/` (bzw. den alten Skill in claude.ai), sonst ist er doppelt da.

Ein Skill für Claude (Claude Code, claude.ai, Claude-Desktop-App), der Praxiswissen zur
API von **Hermine**, dem THW-Messenger auf stashcat-Basis, mitbringt – plus einen
eigenständigen Python-Referenzclient. Entstanden in einem THW-Praxisprojekt, getestet bis
Oktober 2026.

Das Wissen (Endpunkte, Kryptoparameter, Fallstricke) ist sprachunabhängig; der
Referenzclient ist in Python, `references/verschluesselung.md` enthält Hinweise für PHP,
Node.js/Browser, Java, C# und Go.

Claude lädt den Skill automatisch, sobald es in einer Aufgabe um Hermine/stashcat geht,
z. B. „Bau mir eine Funktion, die eine Erinnerung in unseren Hermine-Channel schickt“.

## Inhalt

| Datei | Inhalt |
|---|---|
| `SKILL.md` | Überblick, Grundregeln, Grenzen (lädt Claude zuerst) |
| `references/endpunkte.md` | Endpunkte mit Parametern und Antwortfeldern |
| `references/verschluesselung.md` | E2E-Verschlüsselung beim Senden (RSA-OAEP + AES-256-CBC) |
| `references/fallstricke.md` | Erfahrungen: Sitzung, Namen, Paging, Identität |
| `references/unterhaltungen.md` | Unterhaltungen per API anlegen (Channels nur von Hand) |
| `references/quellen.md` | Verwandte Open-Source-Projekte |
| `scripts/hermine_client.py` | Referenzclient (lesen + verschlüsselt senden) mit CLI |

## Installation

**Claude Code:** Ordner `thw-hermine-api/` nach `~/.claude/skills/` (für alle Projekte) oder
nach `<projekt>/.claude/skills/` (nur dieses Projekt) kopieren. Neue Sitzung starten.

**claude.ai / Desktop-App:** Einstellungen → Fähigkeiten (Capabilities) → Skills → ZIP
hochladen.

## Referenzclient direkt benutzen

```sh
pip install -r scripts/requirements.txt
export HERMINE_EMAIL=vorname.nachname@example.org
python scripts/hermine_client.py set-secret HERMINE_PASSWORD
python scripts/hermine_client.py set-secret HERMINE_ENCRYPTION_PASSWORD   # nur zum Senden
python scripts/hermine_client.py channels
python scripts/hermine_client.py members 123456
python scripts/hermine_client.py send 123456 "Test"            # Probelauf
python scripts/hermine_client.py send 123456 "Test" --execute  # sendet wirklich
```

Vorher in `hermine_client.py` `APP_NAME` auf den eigenen Projektnamen setzen.

## Hinweise

- Hermine hat keine offiziell dokumentierte API; Verhalten kann sich ändern.
- Bitte fair bleiben: ehrlicher App-Name, keine offiziellen Clients nachahmen, nur in
  eigenen Test-Channels ausprobieren, Zugangsdaten nie weitergeben.
- Lizenz: MIT (siehe `LICENSE`), ohne Gewähr. Fragen zur Nutzung im eigenen Ortsverband vorher mit den Zuständigen
  (z. B. IT/Admin) klären.
