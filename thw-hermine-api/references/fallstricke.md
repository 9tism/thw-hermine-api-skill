# Fallstricke und Erfahrungen

## Anmeldung und Sitzung

- **„Neue Anmeldung“-Benachrichtigung bei jedem Login.** Wer bei jedem Skriptlauf neu
  anmeldet, flutet den Nutzer mit Hinweisen (und wirkt wie ein Angriff). Lösung:
  `client_key` nach dem Login speichern (Schlüsselbund) und wiederverwenden, dazu eine
  **feste** `device_id` – eine neue ID je Lauf sieht für Hermine wie ein neues Gerät aus.
- **Abgelaufene Sitzung** meldet sich als `short_message` `app_auth_not_ok`, falsche
  Zugangsdaten als `auth_failed`. In beiden Fällen: gespeicherten `client_key` verwerfen,
  **einmal** neu anmelden, Aufruf wiederholen. Schlägt auch das fehl, Fehler melden –
  keine Schleife.
- Fehler kommen oft mit HTTP 200; immer `status.value == "OK"` prüfen.
- In Webanwendungen das `Hermine`-Objekt prozessweit cachen und nach einem Fehler
  verwerfen, statt pro Anfrage neu anzumelden.

## Daten

- **Nachname mit Dienststelle:** `last_name` ist z. B. `"Muster (OV Musterstadt)"`.
  Für Namensabgleiche den Klammerzusatz am Ende abschneiden
  (`re.sub(r"\s*\([^)]*\)\s*$", "", last_name)`).
- **Keine E-Mail-Adressen** der Mitglieder. Abgleich mit eigenen Listen nur über
  Vor- + Nachname (Groß-/Kleinschreibung ignorieren); Mehrdeutigkeiten melden statt raten.
- **Abgleich in beide Richtungen:** Wer ein „ist im Channel“-Häkchen pflegt, sollte es
  auch wieder entfernen, wenn jemand den Channel verlassen hat.
- **Mitgliederzahl** steht mal in `user_count`, mal in `member_count`.
- `channels/info` liefert unter `channels` ein einzelnes Objekt, keine Liste.
- `channels/members` ist seitenweise; ohne Weiterblättern fehlen bei großen Channels Leute.
- **Channel-Namen ändern sich.** Immer die ID speichern; einen gespeicherten Namen beim
  nächsten Lesen aktualisieren.

## Senden

- Ohne `metainfo` `{"v":1,"style":"md"}` wird Markdown nicht gerendert.
- Verschlüsselung siehe `verschluesselung.md`; ohne korrekten Channel-Schlüssel gar
  nicht senden.
- Leere Nachrichten vorher abfangen.
- Nachrichten lassen sich über die API nicht zurückholen – deshalb Probelauf bzw.
  zweistufige Bestätigung, und Tests nur in einem ausdrücklich dafür benannten Channel.

## Grenzen

- Channels nur von Hand in der Hermine-App oder im Web-Interface anlegen;
  `channels/create` → `no_permission` für Skript-Logins.
- Unterhaltungen dagegen lassen sich per API anlegen
  (`message/createEncryptedConversation`, siehe `unterhaltungen.md`).

## Identität und Fairness

- Eigener `app_name` und User-Agent. Bekannte Clients geben sich teils als offizieller
  Web-Client aus (`app_name` wie „hermine@thw-Chrome…“) – das nicht übernehmen; es bringt
  auch keine zusätzlichen Rechte (`channels/create` bleibt verboten).
- Keine Web-Oberfläche scrapen, nur die API benutzen.
- Sparsam abfragen (z. B. Channel-Liste cachen), Hermine ist Einsatzinfrastruktur.
