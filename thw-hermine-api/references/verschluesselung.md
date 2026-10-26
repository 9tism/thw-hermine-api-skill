# Ende-zu-Ende-Verschlüsselung beim Senden

In Hermine sind die Channels in der Praxis alle verschlüsselt (`channels/info` →
`encrypted: true`). Der Server sieht nur Chiffretext; der Client verschlüsselt selbst.
Lesen von Channel-Listen und Mitgliedern braucht **keine** Verschlüsselung.

## Schlüsselkette

1. **Privater RSA-Schlüssel des Kontos** – `security/get_private_key` →
   `payload.keys.private_key` (JSON-String) → Feld `private` = PEM, geschützt mit dem
   **Verschlüsselungskennwort** (das Kennwort, das man in der App zum Entsperren der
   Verschlüsselung eingibt; nicht das Login-Passwort).
2. **Channel-Schlüssel** – `channels/info` → `key` (Base64), mit dem öffentlichen
   RSA-Schlüssel des Kontos per **RSA-OAEP** verschlüsselt. Entschlüsselt: 32 Byte
   AES-256-Schlüssel.
3. **Nachricht** – **AES-256-CBC**, PKCS#7-Padding, zufälliger 16-Byte-IV je Nachricht.
   `text` = Chiffretext **hex**, `iv` = IV **hex**, `encrypted = "true"`.

## Kryptoparameter (sprachunabhängig)

Diese Werte gelten für jede Umsetzung. Belegt durch den Python-Referenzclient, der damit
erfolgreich sendet (pycryptodome), und durch HermineBot (PHP, `src/Core/Crypt.php`,
`src/Stashcat/Config.php`, `src/Stashcat/CryptoBox.php`; Stand 25.10.2026).

| Baustein | Parameter |
|---|---|
| Privater Schlüssel | PEM-Text aus `payload.keys.private_key` (JSON-String) → Feld `private`, mit dem Verschlüsselungskennwort verschlüsselt. **PEM-Variante ungeprüft** (siehe unten) |
| Channel-/Unterhaltungsschlüssel (`key`) | Base64 (Standard-Alphabet) → RSA-Entschlüsselung mit **OAEP, Hash SHA-1, MGF1 mit SHA-1**, leeres Label → 32 Byte |
| Nachricht | **AES-256-CBC**, Schlüssel = die 32 Byte direkt (keine Ableitung), **PKCS#7-Padding** (Blockgröße 16), zufälliger **16-Byte-IV** je Nachricht |
| Text vor dem Verschlüsseln | UTF-8-Bytes |
| `text`, `iv` im Request | **Hex, Kleinbuchstaben** |
| Signatur (nur Unterhaltungen) | **RSASSA-PKCS1-v1_5 mit SHA-256**, Ausgabe **Hex, Kleinbuchstaben** |
| Request-Body | `application/x-www-form-urlencoded`; Bools als `"true"`/`"false"`, Listen/Objekte als JSON-String |

Der häufigste Fehler in anderen Sprachen ist der OAEP-Hash: Manche Schnittstellen
verlangen eine ausdrückliche Wahl (WebCrypto, .NET), und viele Codebeispiele nehmen
SHA-256 – hier muss **SHA-1** stehen.
Schlägt das Entschlüsseln des Channel-Schlüssels fehl, zuerst das prüfen.

### PEM-Variante des privaten Schlüssels (ungeprüft)

Nicht nachgesehen ist, ob das PEM als PKCS#8 (`-----BEGIN ENCRYPTED PRIVATE KEY-----`) oder
im alten OpenSSL-Format (`-----BEGIN RSA PRIVATE KEY-----` mit `Proc-Type: 4,ENCRYPTED`)
kommt. pycryptodome (`RSA.import_key`) und PHP (`openssl_pkey_get_private`) erkennen
beide selbst. In anderen Sprachen beim ersten Lauf die erste Zeile des PEM ansehen (nur
die Kopfzeile ausgeben, nie den Schlüssel) und danach die Ladefunktion wählen.

### Bausteine je Sprache

Diese Hinweise beruhen auf der Doku der Bibliotheken, nicht auf eigenen Tests gegen Hermine.

- **PHP (OpenSSL):** `openssl_pkey_get_private($pem, $kennwort)`,
  `openssl_private_decrypt($key, $out, $pk, OPENSSL_PKCS1_OAEP_PADDING)` (= SHA-1),
  `openssl_encrypt($text, 'aes-256-cbc', $key, OPENSSL_RAW_DATA, $iv)` (PKCS#7),
  `bin2hex`. Komplette Vorlage: HermineBot.
- **Node.js (`crypto`):** `createPrivateKey({key: pem, passphrase})` (beide PEM-Varianten),
  `privateDecrypt({key, padding: constants.RSA_PKCS1_OAEP_PADDING, oaepHash: 'sha1'}, buf)`,
  `createCipheriv('aes-256-cbc', key, iv)` (PKCS#7 standardmäßig), `.toString('hex')`.
- **Browser / WebCrypto:** `RSA-OAEP` mit `hash: 'SHA-1'` angeben; `importKey('pkcs8')`
  nimmt nur **unverschlüsselte** Schlüssel – das verschlüsselte PEM vorher mit einer
  Bibliothek (z. B. node-forge) entschlüsseln. `AES-CBC` padded PKCS#7 automatisch.
  Kennwort und privaten Schlüssel im Browser nur mit gutem Grund verarbeiten.
- **Java:** `Cipher.getInstance("RSA/ECB/OAEPWithSHA-1AndMGF1Padding")`,
  `Cipher.getInstance("AES/CBC/PKCS5Padding")` (bei 16-Byte-Blöcken = PKCS#7);
  verschlüsseltes PEM mit Bouncy Castle (`PEMParser` + passender Decryptor-Provider).
- **C# / .NET:** `RSA.ImportFromEncryptedPem(pem, kennwort)` (nur PKCS#8; das alte
  OpenSSL-Format braucht Bouncy Castle), `rsa.Decrypt(key, RSAEncryptionPadding.OaepSHA1)`,
  `Aes` mit `CipherMode.CBC`/`PaddingMode.PKCS7`; `Convert.ToHexString` liefert
  Großbuchstaben → `.ToLowerInvariant()`.
- **Go:** `rsa.DecryptOAEP(sha1.New(), nil, pk, key, nil)`, `cipher.NewCBCEncrypter` mit
  selbst geschriebenem PKCS#7-Padding, `hex.EncodeToString`; verschlüsseltes PEM: altes
  Format per `x509.DecryptPEMBlock` (veraltet), PKCS#8 über eine Zusatzbibliothek.

## Python (pycryptodome)

```python
import base64, json
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

keys = post("security/get_private_key", {})["keys"]
pem = json.loads(keys["private_key"])["private"]
private_key = RSA.import_key(pem, passphrase=encryption_password)  # ValueError = falsches Kennwort

info = post("channels/info", {"channel_id": cid, "without_members": "true"})["channels"]
channel_key = PKCS1_OAEP.new(private_key).decrypt(base64.b64decode(info["key"]))

iv = get_random_bytes(16)
cipher = AES.new(channel_key, AES.MODE_CBC, iv=iv).encrypt(pad(text.encode("utf-8"), AES.block_size))
data.update(encrypted="true", iv=iv.hex(), text=cipher.hex())
```

## Hinweise

- Den Channel-Schlüssel **vor** dem Senden entschlüsseln; schlägt das fehl, gar nichts
  senden (sonst landet Klartext oder Müll im Channel).
- Ein Probelauf kann `private_key()` und `channel_key()` schon ausführen und so
  Kennwort und Schlüssel prüfen, ohne eine Nachricht zu verschicken.
- Den entsperrten privaten Schlüssel nur im Speicher halten, nie auf Platte schreiben.
  Das Verschlüsselungskennwort erst abfragen, wenn wirklich gesendet wird.
- `RSA.import_key` wirft bei falschem Kennwort `ValueError` (teils `IndexError`/`TypeError`)
  – als „Kennwort falsch“ melden.
- Andere Sprachen: siehe „Bausteine je Sprache“; vollständige PHP-Umsetzung in HermineBot
  (`src/Stashcat/`, `src/Core/Crypt.php`), Python auch in stashconnect.
