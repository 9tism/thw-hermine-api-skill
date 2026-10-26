#!/usr/bin/env python3
"""Hermine (THW-Messenger auf stashcat-Basis) – Referenzclient: lesen plus Nachricht senden.

Lizenz: MIT (siehe LICENSE im Skill-Ordner).

Liest die eigenen Channels und deren Mitglieder. Einziger schreibender Zugriff: eine
Textnachricht in einen Channel senden (send_message). _post() lässt nur die Endpunkte in
READ_ONLY und SEND zu – neue Endpunkte bewusst einzeln freigeben.
Der Client meldet sich ehrlich mit eigenem app_name und User-Agent an, nicht als
offizieller Hermine-Client oder Browser. APP_NAME bitte auf den eigenen Projektnamen ändern.

Verschlüsselte Channels: Der Channel-Schlüssel (AES-256) liegt RSA-verschlüsselt beim Channel;
den privaten RSA-Schlüssel liefert Hermine mit dem Verschlüsselungskennwort geschützt aus.
Die Nachricht wird lokal mit AES-256-CBC verschlüsselt, Hermine sieht nur Chiffretext.

Abhängigkeiten: requests, pycryptodome, optional keyring (für Sitzung und Kennwörter).

Zugangsdaten (Umgebungsvariable oder Schlüsselbund, Dienst HERMINE_KEYRING_SERVICE):
    HERMINE_EMAIL
    HERMINE_PASSWORD                 python hermine_client.py set-secret HERMINE_PASSWORD
    HERMINE_ENCRYPTION_PASSWORD      nur zum Senden
Im Schlüsselbund legt der Client außerdem HERMINE_DEVICE_ID und HERMINE_CLIENT_KEY ab.

Beispiele:
    python hermine_client.py channels
    python hermine_client.py members 123456
    python hermine_client.py dump members 123456      # Rohdaten (JSON)
    python hermine_client.py send 123456 "Text"       # Probelauf; --execute sendet wirklich
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import secrets
import sys
from typing import Callable, Dict, List, Optional

import requests
from Crypto.Cipher import AES, PKCS1_OAEP
from Crypto.PublicKey import RSA
from Crypto.Random import get_random_bytes
from Crypto.Util.Padding import pad

__version__ = "0.2.2-alpha"

BASE_URL = "https://api.thw-messenger.de/"
APP_NAME = "Mein-THW-Tool"  # eigenen Projektnamen eintragen – keine offiziellen Clients nachahmen
KEYRING_SERVICE = os.environ.get("HERMINE_KEYRING_SERVICE", "hermine-client")

# Erlaubte lesende Endpunkte (Login erzeugt lediglich eine Sitzung).
READ_ONLY = frozenset({"auth/login", "company/member", "channels/subscripted", "channels/members",
                       "channels/info", "security/get_private_key"})
# Einziger schreibender Endpunkt; nur send_message() benutzt ihn.
SEND = frozenset({"message/send"})

PAGE = 100

# Antworten (short_message), nach denen eine neue Sitzung nötig ist.
AUTH_ERRORS = frozenset({"auth_failed", "app_auth_not_ok"})


class UsageError(Exception):
    """Fehlende oder falsche Eingabe/Konfiguration."""


class AuthFailed(RuntimeError):
    """Sitzung (client_key) ungültig oder abgelaufen."""


class Hermine:
    def __init__(self, email: str, password: str, device_id: str, base_url: str = BASE_URL,
                 client_key: Optional[str] = None, on_login: Optional[Callable[[str], None]] = None,
                 encryption_password: Optional[Callable[[], str]] = None, app_name: str = APP_NAME):
        self.base = base_url.rstrip("/") + "/"
        self.email = email
        self.password = password
        self.device_id = device_id
        self.app_name = app_name
        self.session = requests.Session()
        self.session.headers["User-Agent"] = f"{app_name} (python-requests)"
        # Gespeicherte Sitzung wiederverwenden: jeder Login löst bei Hermine eine
        # "Neue Anmeldung"-Benachrichtigung aus.
        self.client_key = client_key
        self.on_login = on_login
        self.user: dict = {}
        # Erst beim Senden abgefragt – zum Lesen wird das Kennwort nicht gebraucht.
        self.encryption_password = encryption_password
        self._private_key = None

    def _post(self, endpoint: str, data: Dict[str, object]) -> dict:
        if endpoint not in READ_ONLY | SEND:
            raise RuntimeError(f"Hermine-Endpunkt {endpoint} ist nicht freigegeben.")
        if endpoint == "auth/login":
            return self._send(endpoint, data)
        reused = self.client_key is not None
        try:
            return self._send(endpoint, {**data, "client_key": self.login()})
        except AuthFailed:
            if not reused:
                raise
            self.client_key = None  # Sitzung abgelaufen – einmal neu anmelden
            return self._send(endpoint, {**data, "client_key": self.login()})

    def _send(self, endpoint: str, data: Dict[str, object]) -> dict:
        data = {**data, "device_id": self.device_id}
        r = self.session.post(self.base + endpoint, data=data, timeout=30)
        if not r.ok:
            # Kein Antworttext: beim Login könnte er Eingaben spiegeln.
            raise RuntimeError(f"Hermine {endpoint}: HTTP {r.status_code}")
        body = r.json()
        status = body.get("status") or {}
        if status.get("value") != "OK":
            error = AuthFailed if status.get("short_message") in AUTH_ERRORS else RuntimeError
            raise error(f"Hermine {endpoint}: {status.get('message') or status.get('value') or 'Fehler'}")
        return body.get("payload") or {}

    def login(self) -> str:
        if self.client_key is None:
            payload = self._post("auth/login", {"email": self.email, "password": self.password,
                                                "app_name": self.app_name, "encrypted": "true",
                                                "callable": "true"})
            self.client_key = payload["client_key"]
            self.user = payload.get("userinfo") or {}
            if self.on_login:
                self.on_login(self.client_key)
        return self.client_key

    def companies(self) -> List[dict]:
        return self._post("company/member", {"no_cache": "true"}).get("companies") or []

    def channels(self, company_id: int) -> List[dict]:
        return self._post("channels/subscripted", {"company": company_id}).get("channels") or []

    def channel_info(self, channel_id: int) -> dict:
        return self._post("channels/info", {"channel_id": channel_id, "without_members": "true"}).get("channels") or {}

    def members(self, channel_id: int) -> List[dict]:
        result: List[dict] = []
        while True:
            page = self._post("channels/members", {"channel_id": channel_id, "limit": PAGE,
                                                   "offset": len(result), "filter": "members"})
            members = page.get("members") or []
            result.extend(members)
            if len(members) < PAGE:
                return result

    def private_key(self):
        """Eigener privater RSA-Schlüssel, entsperrt mit dem Verschlüsselungskennwort (nur im Speicher)."""
        if self._private_key is None:
            if self.encryption_password is None:
                raise UsageError("Kein Hermine-Verschlüsselungskennwort angegeben.")
            password = self.encryption_password()
            keys = self._post("security/get_private_key", {}).get("keys") or {}
            try:
                encrypted = json.loads(keys["private_key"])["private"]
            except (KeyError, TypeError, ValueError):
                raise RuntimeError("Hermine: privater Schlüssel nicht lesbar.")
            try:
                self._private_key = RSA.import_key(encrypted, passphrase=password)
            except (ValueError, IndexError, TypeError):
                raise UsageError("Hermine-Verschlüsselungskennwort falsch.")
        return self._private_key

    def channel_key(self, info: dict) -> bytes:
        try:
            return PKCS1_OAEP.new(self.private_key()).decrypt(base64.b64decode(info["key"]))
        except (KeyError, TypeError, ValueError):
            raise RuntimeError("Hermine: Channel-Schlüssel nicht lesbar.")

    def send_message(self, channel_id: int, text: str) -> dict:
        """Textnachricht (Markdown) in einen Channel senden; verschlüsselt, wenn der Channel es ist."""
        text = text.strip()
        if not text:
            raise UsageError("Die Nachricht ist leer.")
        info = self.channel_info(channel_id)
        data = {"target": "channel", "channel_id": channel_id, "text": text, "encrypted": "false",
                "files": "[]", "url": "[]", "type": "text", "verification": "", "is_forwarded": "false",
                "metainfo": json.dumps({"v": 1, "style": "md"})}
        if info.get("company"):
            data["company"] = info["company"]
        if info.get("encrypted"):
            key = self.channel_key(info)  # vor dem Senden: ohne Schlüssel wird nichts verschickt
            iv = get_random_bytes(16)
            cipher = AES.new(key, AES.MODE_CBC, iv=iv).encrypt(pad(text.encode("utf-8"), AES.block_size))
            data.update(encrypted="true", iv=iv.hex(), text=cipher.hex())
        return self._post("message/send", data).get("message") or {}


# --------------------------------------------------------------------------- Hilfsfunktionen

def keyring_get(name: str) -> Optional[str]:
    try:
        import keyring
        return keyring.get_password(KEYRING_SERVICE, name)
    except Exception:  # kein keyring installiert, kein Backend oder Zugriff verweigert
        return None


def keyring_set(name: str, value: str) -> None:
    import keyring
    keyring.set_password(KEYRING_SERVICE, name, value)


def secret(name: str) -> str:
    value = os.environ.get(name) or keyring_get(name)
    if not value:
        raise UsageError(f"{name} fehlt – als Umgebungsvariable setzen oder mit "
                         f"`python hermine_client.py set-secret {name}` speichern.")
    return value


def device_id() -> str:
    """Feste Geräte-ID dieses Rechners, damit Hermine nicht bei jedem Lauf ein neues Gerät sieht."""
    value = os.environ.get("HERMINE_DEVICE_ID") or keyring_get("HERMINE_DEVICE_ID")
    if not value:
        value = secrets.token_hex(16)
        try:
            keyring_set("HERMINE_DEVICE_ID", value)
        except Exception:
            print("Hinweis: Geräte-ID nicht gespeichert (kein Schlüsselbund) – "
                  "HERMINE_DEVICE_ID fest setzen.", file=sys.stderr)
    return value


def save_client_key(key: str) -> None:
    try:
        keyring_set("HERMINE_CLIENT_KEY", key)
    except Exception:  # dann eben beim nächsten Start neu anmelden
        pass


def connect() -> Hermine:
    return Hermine(secret("HERMINE_EMAIL"), secret("HERMINE_PASSWORD"), device_id(),
                   os.environ.get("HERMINE_BASE_URL", BASE_URL),
                   client_key=keyring_get("HERMINE_CLIENT_KEY"), on_login=save_client_key,
                   encryption_password=lambda: secret("HERMINE_ENCRYPTION_PASSWORD"))


def member_name(m: dict) -> str:
    return f"{m.get('first_name', '')} {m.get('last_name', '')}".strip() or f"ID {m.get('id')}"


def member_person(m: dict) -> dict:
    """Vor- und Nachname eines Mitglieds; Hermine hängt die Dienststelle an den Nachnamen an
    ("Muster (OV Musterstadt)"), die wird abgeschnitten."""
    name = re.sub(r"\s*\([^)]*\)\s*$", "", str(m.get("last_name") or ""))
    return {"vorname": str(m.get("first_name") or "").strip(), "name": name.strip(),
            "label": member_name(m)}


def all_channels(h: Hermine) -> List[dict]:
    """Eigene Channels aller Firmen, nach Name sortiert."""
    result = [{"id": int(c["id"]), "name": str(c.get("name", "")).strip(),
               "members": c.get("user_count", c.get("member_count"))}
              for company in h.companies() for c in h.channels(company["id"])]
    return sorted(result, key=lambda c: c["name"].lower())


# --------------------------------------------------------------------------- CLI

def cmd_channels(h: Hermine, args) -> None:
    for company in h.companies():
        print(f"{company.get('name')} (Firma {company.get('id')})")
        for c in sorted(h.channels(company["id"]), key=lambda c: str(c.get("name", "")).lower()):
            count = c.get("user_count", c.get("member_count", "?"))
            print(f"  {c.get('id'):>8}  {c.get('name')}  ({count} Mitglieder)")


def cmd_members(h: Hermine, args) -> None:
    members = sorted(h.members(args.channel_id),
                     key=lambda m: (str(m.get("last_name", "")).lower(), str(m.get("first_name", "")).lower()))
    for m in members:
        print(f"  {member_name(m)}")
    print(f"{len(members)} Mitglieder")


def cmd_send(h: Hermine, args) -> None:
    info = h.channel_info(args.channel_id)
    name = info.get("name") or f"Channel {args.channel_id}"
    if not args.execute:
        if info.get("encrypted"):
            h.channel_key(info)  # prüft Kennwort und Schlüssel, ohne zu senden
        print(f"Probelauf – an „{name}“ ({info.get('user_count', '?')} Mitglieder"
              f"{', verschlüsselt' if info.get('encrypted') else ''}):\n{args.text}\n"
              "Mit --execute wirklich senden.")
        return
    message = h.send_message(args.channel_id, args.text)
    print(f"An „{name}“ gesendet (Nachricht {message.get('id', '?')}).")


def cmd_dump(h: Hermine, args) -> None:
    if args.what == "channels":
        data = {c["id"]: h.channels(c["id"]) for c in h.companies()}
    else:
        if args.id is None:
            raise UsageError("Channel-ID fehlt.")
        data = h.members(args.id)
    print(json.dumps(data, indent=2, ensure_ascii=False))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("channels", help="Eigene Channels je Firma auflisten")
    p = sub.add_parser("members", help="Mitglieder eines Channels auflisten")
    p.add_argument("channel_id", type=int)
    p = sub.add_parser("dump", help="Rohdaten (JSON) ausgeben")
    p.add_argument("what", choices=["channels", "members"])
    p.add_argument("id", type=int, nargs="?", help="Channel-ID (bei members)")
    p = sub.add_parser("send", help="Nachricht in einen Channel senden (ohne --execute nur Probelauf)")
    p.add_argument("channel_id", type=int)
    p.add_argument("text")
    p.add_argument("--execute", action="store_true", help="wirklich senden")
    p = sub.add_parser("set-secret", help="Zugangsdaten im Schlüsselbund speichern")
    p.add_argument("name", choices=["HERMINE_EMAIL", "HERMINE_PASSWORD", "HERMINE_ENCRYPTION_PASSWORD"])
    args = parser.parse_args()
    try:
        if args.cmd == "set-secret":
            import getpass
            keyring_set(args.name, getpass.getpass(f"{args.name}: "))
            print(f"{args.name} gespeichert (Dienst {KEYRING_SERVICE}).")
            return
        h = connect()
        {"channels": cmd_channels, "members": cmd_members, "dump": cmd_dump, "send": cmd_send}[args.cmd](h, args)
    except (UsageError, RuntimeError) as e:
        sys.exit(f"Fehler: {e}")


if __name__ == "__main__":
    main()
