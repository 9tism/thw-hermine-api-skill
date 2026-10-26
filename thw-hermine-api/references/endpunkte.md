# Hermine-Endpunkte

Alle Aufrufe: `POST https://api.thw-messenger.de/<endpunkt>`, Body
`application/x-www-form-urlencoded`. Boolesche Werte als Strings `"true"`/`"false"`,
Listen/Objekte als JSON-String. Jeder Aufruf enthält `device_id`; alle außer
`auth/login` zusätzlich `client_key`.

Antwortrahmen:

```json
{"status": {"value": "OK", "short_message": "", "message": ""},
 "payload": { … }}
```

Bei Fehlern ist `status.value` ungleich `"OK"`; `short_message` ist ein stabiler Code
(z. B. `auth_failed`, `app_auth_not_ok`, `no_permission`), `message` ein Klartext.

## auth/login

| Feld | Wert |
|---|---|
| `email` | Login-E-Mail |
| `password` | Login-Passwort |
| `app_name` | eigener Projektname (ehrlich, kein offizieller Client) |
| `encrypted` | `"true"` |
| `callable` | `"true"` |
| `device_id` | feste, zufällige ID je Rechner (z. B. 32 Hex-Zeichen), gespeichert |

Antwort: `payload.client_key` (Sitzung), `payload.userinfo` (eigenes Konto).
Jeder Login → „Neue Anmeldung“-Benachrichtigung beim Nutzer. Sitzung speichern.

## company/member

Firmen (Organisationen), in denen das Konto Mitglied ist. Parameter: `no_cache: "true"`.
Antwort: `payload.companies` – Liste mit u. a. `id`, `name`. Die Firmen-ID braucht man
für die Channel-Liste.

## channels/subscripted

Eigene (abonnierte) Channels einer Firma. Parameter: `company` (Firmen-ID).
Antwort: `payload.channels` – Liste mit u. a. `id`, `name`, Mitgliederzahl in
`user_count` (bei manchen Antworten `member_count` – beide prüfen).

## channels/info

Ein Channel im Detail. Parameter: `channel_id`, `without_members: "true"`.
Antwort: `payload.channels` (**ein Objekt**, trotz Plural) mit u. a. `id`, `name`,
`company`, `encrypted` (bool), `key` (Base64, RSA-verschlüsselter Channel-Schlüssel),
`user_count`. Wird vor jedem Senden gebraucht.

## channels/members

Mitglieder eines Channels, seitenweise. Parameter: `channel_id`, `limit` (z. B. 100),
`offset`, `filter: "members"`. Weiterblättern, bis eine Seite weniger als `limit`
Einträge hat.
Antwort: `payload.members` – Liste mit u. a. `id`, `first_name`, `last_name`.
`last_name` enthält meist die Dienststelle: `"Muster (OV Musterstadt)"`. Keine E-Mail.

## security/get_private_key

Eigener privater RSA-Schlüssel. Keine weiteren Parameter.
Antwort: `payload.keys.private_key` ist ein **JSON-String**; darin steht unter
`"private"` der PEM-Schlüssel, verschlüsselt mit dem Verschlüsselungskennwort.
Siehe `verschluesselung.md`.

## message/send

Nachricht in einen Channel. Felder, wie sie funktionieren:

| Feld | Wert |
|---|---|
| `target` | `"channel"` |
| `channel_id` | Channel-ID |
| `company` | Firmen-ID aus `channels/info` (schickt auch HermineBot mit) |
| `text` | Klartext oder bei verschlüsselten Channels Chiffretext (hex) |
| `encrypted` | `"true"` / `"false"` |
| `iv` | nur verschlüsselt: IV (hex) |
| `files` | `"[]"` |
| `url` | `"[]"` |
| `type` | `"text"` |
| `verification` | `""` |
| `is_forwarded` | `"false"` |
| `metainfo` | `{"v": 1, "style": "md"}` als JSON-String → Markdown wird gerendert |

Antwort: `payload.message` mit u. a. `id`.

## Bekannt, aber nicht im Referenzclient

- `message/createEncryptedConversation` – Unterhaltung anlegen; `message/conversations`,
  `message/conversation` – Unterhaltungen auflisten bzw. lesen; `users/info` (mit
  `withkey: "true"`) – öffentlicher Schlüssel einer Person; `users/listing` – Personen.
  Details: `unterhaltungen.md`.
- `channels/create` – für Skript-Logins `no_permission`; Channels nur von Hand in der
  Hermine-App oder im Web-Interface anlegen.
