# Quellen und verwandte Projekte

Stand der Prüfung: 25.10.2026 (Seiten live aufgerufen).

| Projekt | Sprache / Lizenz | Nutzen |
|---|---|---|
| HermineBot – https://github.com/sebiw/HermineBot | PHP 8.1, keine Lizenzangabe | Senden an Channels, Unterhaltungen anlegen (`src/Stashcat/ApiClient.php`, Schlüssel/Signatur in `src/Stashcat/CryptoBox.php`, Endpunkte in `src/Stashcat/Config.php`); THW-Erinnerungen |
| stashconnect – https://pypi.org/project/stashconnect/ (Code: https://github.com/BuStudios/StashConnect) | Python, MIT, v0.9.7.6 (05.12.2024) | Python-Client für stashcat inkl. Verschlüsselung |
| imap-to-stashcat – https://gitlab.com/C0FFEEC0FFEE/imap-to-stashcat | GPLv3 | E-Mails aus einem IMAP-Postfach in einen stashcat-Channel |
| THW Projekte – https://gitlab.com/tast-it/thw-projekte | Sammlung | Übersicht frei nutzbarer THW-Projekte, u. a. mit Hermine-Bezug |

Der Referenzclient in `scripts/hermine_client.py` ist eine eigene Umsetzung (MIT-Lizenz); die
Projekte oben dienten zum Abgleich von Endpunkten und Verschlüsselung.
