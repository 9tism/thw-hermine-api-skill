# Unterhaltungen per API anlegen

Anders als Channels lassen sich **Unterhaltungen** (Ende-zu-Ende-verschlüsselte Chats mit
ausgewählten Personen) per API anlegen und beschreiben. Grundlage ist die Umsetzung in
HermineBot (https://github.com/sebiw/HermineBot, `src/Stashcat/ApiClient.php`,
`src/Stashcat/CryptoBox.php`, `src/Stashcat/Config.php`; Stand 25.10.2026). Im
Referenzclient ist das **nicht** enthalten – vor dem Einbau mit Testpersonen prüfen und
die Endpunkte bewusst in die Allow-List aufnehmen.

## Ablauf

1. **Personen bestimmen** – IDs z. B. aus `channels/members` oder `users/listing`.
2. **Öffentliche Schlüssel holen** – je Person `users/info` mit `user_id` und
   `withkey: "true"`; die Antwort enthält den öffentlichen RSA-Schlüssel (PEM).
3. **Unterhaltungsschlüssel erzeugen** – 32 zufällige Bytes (AES-256).
4. **Je Mitglied (auch für sich selbst) einen Eintrag bauen:**
   - `id`: Benutzer-ID (int)
   - `key`: Unterhaltungsschlüssel, mit dem öffentlichen Schlüssel der Person per
     **RSA-OAEP** verschlüsselt, **Base64**
   - `signature`: **RSASSA-PKCS1-v1_5/SHA-256**-Signatur (Hex, Kleinbuchstaben) mit dem
     eigenen **Signaturschlüssel** über
     `key + "$" + unique_identifier [+ "$" + expiry] [+ "$" + IDs]` – IDs als Ganzzahlen,
     ohne Doppelte, aufsteigend sortiert, mit `$` verbunden
   - `expiry`: Unix-Zeit des Ablaufs, beim eigenen Eintrag `null`
   - `userVerified`: bool (ob der Schlüssel der Person geprüft ist; nicht signiert)
5. **Anlegen** – `message/createEncryptedConversation` mit `members` (JSON-Liste der
   Einträge) und `unique_identifier` (32 Zeichen, Teil der Signatur), plus `client_key`,
   `device_id`. Die Antwort liefert die Unterhaltung samt ID.
6. **Senden** – `message/send` mit `target: "conversation"`, `conversation_id`, Text
   AES-256-CBC mit zufälligem IV, `text`/`iv` hex, `encrypted: "true"` – wie bei
   Channels (siehe `verschluesselung.md`), nur mit dem Unterhaltungsschlüssel.

## Signaturschlüssel

Neben dem privaten Hauptschlüssel gibt es einen eigenen Signaturschlüssel:
`security/get_private_key` mit `type: "signing"` und `format: "jwk"`. Er ist mit einem
AES-256-CBC-Schlüssel verschlüsselt, der seinerseits RSA-OAEP-verschlüsselt mit dem
privaten Hauptschlüssel vorliegt (Schlüssel entschlüsseln → Signaturschlüssel
entschlüsseln). Die genauen Feldnamen in HermineBot (`CryptoBox.php`) nachsehen.

## Hinweise

- Die einzelnen Schritte sind aus HermineBot übernommen und nicht in diesem Projekt
  getestet. Rohdaten der Antworten ansehen, bevor man sich auf Feldnamen verlässt.
- Personen bekommen eine neue Unterhaltung sofort angezeigt – erst mit sich selbst und
  einer ausdrücklich zustimmenden Testperson ausprobieren.
- Bestehende Unterhaltungen: `message/conversations` (Liste), `message/conversation`
  (eine, mit `conversation_id`); den Unterhaltungsschlüssel holt man dort wie beim
  Channel aus dem eigenen, RSA-verschlüsselten `key`.
