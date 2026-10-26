---
name: thw-hermine-api
license: MIT (siehe LICENSE)
metadata:
  version: "0.2.2-alpha"
description: Praxiswissen und Referenzclient für die API von Hermine, dem THW-Messenger auf stashcat-Basis (api.thw-messenger.de). Verwenden, wenn ein Projekt Hermine/stashcat anbinden soll – anmelden, Sitzung wiederverwenden, Firmen und Channels auflisten, Channel-Mitglieder lesen, mit Personenlisten abgleichen oder Nachrichten Ende-zu-Ende-verschlüsselt in einen Channel senden. Auch wenn ein Skript Channels, Gruppen oder Unterhaltungen in Hermine automatisch anlegen soll (Channels gehen nur von Hand, Unterhaltungen per API). Auch bei Fehlern wie auth_failed, app_auth_not_ok oder no_permission, bei Fragen zu Channel-Schlüssel, Verschlüsselungskennwort, RSA/AES in Hermine oder zu „Neue Anmeldung“-Benachrichtigungen.
---

# Hermine-API (THW-Messenger / stashcat)

Hermine hat keine offiziell dokumentierte API. Alles hier stammt aus einem laufenden
Projekt (getestet bis Oktober 2026) und aus dem Abgleich mit anderen Open-Source-Clients
(siehe `references/quellen.md`). Das Wissen kann veralten – im Zweifel mit einem
lesenden Aufruf nachprüfen und Rohdaten ansehen (`hermine_client.py dump …`).

## Schnellüberblick

- Basis-URL `https://api.thw-messenger.de/`; jeder Aufruf ist `POST`, **form-encoded**
  (kein JSON-Body). Jeder Aufruf schickt `device_id`, alle außer dem Login auch `client_key`.
- Antwort immer `{"status": {"value", "short_message", "message"}, "payload": {…}}`.
  Erfolg **nur** bei `status.value == "OK"` – auch Fehler kommen oft mit HTTP 200.
- Login `auth/login` → `payload.client_key` (Sitzung). **Jeder Login erzeugt beim Nutzer
  eine „Neue Anmeldung“-Benachrichtigung** → `client_key` und eine feste `device_id`
  dauerhaft speichern (Schlüsselbund) und wiederverwenden.
- Bei `short_message` `auth_failed` oder `app_auth_not_ok` (abgelaufene Sitzung) genau
  einmal neu anmelden und den Aufruf wiederholen.
- Lesen: `company/member` → `channels/subscripted` (je Firma) → `channels/members`
  (Paging) bzw. `channels/info`.
- Senden: `message/send`. Channels sind in der Praxis **alle Ende-zu-Ende-verschlüsselt**;
  dafür braucht es zusätzlich das **Verschlüsselungskennwort** des Kontos (nicht das
  Login-Passwort).

Details zu jedem Endpunkt: `references/endpunkte.md`.
Verschlüsselung Schritt für Schritt, Kryptoparameter und Bausteine je Sprache: `references/verschluesselung.md`.
Fallstricke und Grenzen: `references/fallstricke.md`.
Unterhaltungen per API anlegen: `references/unterhaltungen.md`.

## Referenzclient

`scripts/hermine_client.py` ist ein eigenständiger Python-Client (nur `requests`,
`pycryptodome`, optional `keyring`) mit genau diesen Fähigkeiten: Login mit
Sitzungswiederverwendung, Firmen, Channels, Channel-Info, Mitglieder (mit Paging),
privaten Schlüssel entsperren, Channel-Schlüssel entschlüsseln, verschlüsselt senden.
Dazu eine kleine CLI (`channels`, `members`, `dump`, `send` als Probelauf mit
`--execute`, `set-secret`).

**Andere Sprachen:** Der Client ist eine Python-Vorlage; das Wissen selbst ist
sprachunabhängig. Für PHP, JavaScript, Java, C#, Go usw. nach `references/endpunkte.md`
und der Tabelle „Kryptoparameter“ in `references/verschluesselung.md` umsetzen (dort auch
Bausteine je Sprache; Stolperstein Nr. 1: RSA-OAEP mit **SHA-1**). Den Python-Client als
lesbare Referenz für Ablauf, Fehlerbehandlung und Allow-List nehmen. Fertige PHP-Umsetzung:
HermineBot (`references/quellen.md`).

Beim Einbau in ein Python-Projekt:
1. Datei kopieren oder als Vorlage nehmen; **`APP_NAME` auf den eigenen Projektnamen setzen**.
2. Zugangsdaten nicht in den Code: `HERMINE_EMAIL`, `HERMINE_PASSWORD`,
   `HERMINE_ENCRYPTION_PASSWORD` als Umgebungsvariable oder im Schlüsselbund
   (`HERMINE_KEYRING_SERVICE` legt den Dienstnamen fest).
3. Die Allow-List (`READ_ONLY`, `SEND`) beibehalten und neue Endpunkte einzeln und
   bewusst freigeben.

## Grundregeln für Hermine-Anbindungen

Diese Regeln haben sich bewährt; beim Bauen einer Anbindung standardmäßig befolgen und
Abweichungen nur auf ausdrücklichen Wunsch des Nutzers:

- **Ehrlich identifizieren:** eigener `app_name` und User-Agent. Nicht als offizieller
  Hermine-Client oder Browser ausgeben (einige bekannte Projekte tun das – nicht übernehmen).
- **So wenig Schreibrechte wie möglich:** Endpunkt-Allow-List im Client; jede neue
  schreibende Funktion ist eine bewusste Entscheidung.
- **Senden nie ohne Bestätigung:** CLI mit Probelauf (ohne `--execute`), in Oberflächen
  zwei Klicks. Der Probelauf kann Kennwort und Channel-Schlüssel schon prüfen, ohne zu senden.
- **Testen nur in einem Channel, den der Nutzer ausdrücklich nennt** – nie „mal eben“ in
  einen echten Einheits-Channel.
- **Geheimnisse schützen:** Passwort, Verschlüsselungskennwort und `client_key` gehören in
  den Schlüsselbund; den entsperrten privaten Schlüssel nur im Speicher halten. In
  Fehlermeldungen keine Antworttexte des Servers bei HTTP-Fehlern ausgeben (können
  Eingaben spiegeln) und keine Zugangsdaten.
- **Nicht unnötig anmelden:** gespeicherte Sitzung wiederverwenden, sonst bekommt der
  Nutzer bei jedem Lauf eine Benachrichtigung.
- **Channels nach ID zuordnen, nicht nach Name** – Namen werden in Hermine umbenannt.
  Einen gespeicherten Anzeigenamen beim nächsten Lesen still aktualisieren.

## Channels und Unterhaltungen anlegen

Bei jeder Frage nach „automatisch anlegen“ beides ansprechen – egal wofür (Lehrgang,
Einsatz, Gruppe, Projekt):

- **Channels lassen sich nur von Hand anlegen** – in der Hermine-App oder im
  Web-Interface. Per API geht es nicht: `channels/create` antwortet für Skript-Logins mit
  `no_permission`, und daran ändert auch ein vorgetäuschter offizieller Client nichts.
  Muster: Channel von Hand anlegen, Channel-ID im Tool hinterlegen, den Rest (Abgleich,
  Nachrichten) automatisieren.
- **Unterhaltungen (verschlüsselte Gruppen- oder 1:1-Chats) lassen sich per API anlegen**
  – über `message/createEncryptedConversation`, danach Nachrichten über `message/send`
  mit `target: "conversation"`. Das ist oft die passende Alternative, wenn ein Skript
  selbst einen Gesprächsraum für eine Personengruppe aufmachen soll. Ablauf, Schlüssel
  und Signatur: `references/unterhaltungen.md`. Nicht im Referenzclient enthalten; jede
  neue schreibende Funktion bewusst freigeben und erst mit Testpersonen ausprobieren.

## Was sonst nicht geht

- **E-Mail-Adressen von Mitgliedern:** liefert die API nicht. Abgleich mit Personenlisten
  nur über Vor- und Nachname (Dienststellen-Zusatz am Nachnamen vorher abschneiden, siehe
  `member_person()`).
