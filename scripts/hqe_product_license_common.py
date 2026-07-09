from __future__ import annotations

import base64
import getpass
import hashlib
import json
import math
import os
import platform
import random
import secrets
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple


PRODUCT_CODE = "HQE_PRODUCT_APP"
LICENSE_VERSION = "HQE_LICENSE_V1"
DEFAULT_OWNER_KEY_DIR = Path(r"D:\HQE_PRODUCT_LICENSE_OWNER")
DEFAULT_PUBLIC_KEY_NAME = "hqe_license_public_key.json"
DEFAULT_PRIVATE_KEY_NAME = "hqe_owner_private_key.json"


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def b64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("ascii").rstrip("=")


def b64url_decode(text: str) -> bytes:
    pad = "=" * ((4 - len(text) % 4) % 4)
    return base64.urlsafe_b64decode((text + pad).encode("ascii"))


def canonical_json(payload: Dict[str, Any]) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def machine_id() -> str:
    raw = "|".join([
        platform.node() or "",
        getpass.getuser() or "",
        str(uuid.getnode()),
        platform.platform() or "",
    ])
    return "HQE-" + hashlib.sha256(raw.encode("utf-8")).hexdigest().upper()[:32]


def app_config_dir(workspace: str | Path | None = None) -> Path:
    if workspace:
        path = Path(workspace) / "HQE_PRODUCT_APP_CONFIG"
    else:
        base = os.environ.get("APPDATA") or str(Path.home())
        path = Path(base) / "HQE_PRODUCT_APP"
    path.mkdir(parents=True, exist_ok=True)
    return path


def license_file_path(workspace: str | Path | None = None) -> Path:
    return app_config_dir(workspace) / "license.key"


def public_key_path(workspace: str | Path | None = None) -> Path:
    return app_config_dir(workspace) / DEFAULT_PUBLIC_KEY_NAME


def _is_probable_prime(n: int, rounds: int = 12) -> bool:
    if n < 2:
        return False
    small_primes = [2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37]
    for p in small_primes:
        if n == p:
            return True
        if n % p == 0:
            return False
    d = n - 1
    s = 0
    while d % 2 == 0:
        s += 1
        d //= 2
    for _ in range(rounds):
        a = secrets.randbelow(n - 3) + 2
        x = pow(a, d, n)
        if x in (1, n - 1):
            continue
        for __ in range(s - 1):
            x = pow(x, 2, n)
            if x == n - 1:
                break
        else:
            return False
    return True


def _generate_prime(bits: int) -> int:
    while True:
        value = secrets.randbits(bits) | (1 << (bits - 1)) | 1
        if _is_probable_prime(value):
            return value


def _egcd(a: int, b: int) -> Tuple[int, int, int]:
    if a == 0:
        return b, 0, 1
    g, y, x = _egcd(b % a, a)
    return g, x - (b // a) * y, y


def _modinv(a: int, m: int) -> int:
    g, x, _ = _egcd(a, m)
    if g != 1:
        raise ValueError("modular inverse does not exist")
    return x % m


def generate_rsa_keypair(bits: int = 1024) -> Tuple[Dict[str, str], Dict[str, str]]:
    if bits < 512:
        raise ValueError("bits must be >= 512")
    e = 65537
    half = bits // 2
    while True:
        p = _generate_prime(half)
        q = _generate_prime(bits - half)
        if p == q:
            continue
        n = p * q
        phi = (p - 1) * (q - 1)
        if math.gcd(e, phi) == 1:
            d = _modinv(e, phi)
            break
    public_key = {
        "license_version": LICENSE_VERSION,
        "algorithm": "RSA-SHA256",
        "n": str(n),
        "e": str(e),
        "created_at_utc": utc_now(),
    }
    private_key = {
        "license_version": LICENSE_VERSION,
        "algorithm": "RSA-SHA256",
        "n": str(n),
        "e": str(e),
        "d": str(d),
        "p": str(p),
        "q": str(q),
        "created_at_utc": utc_now(),
    }
    return public_key, private_key


def init_owner_keys(owner_dir: str | Path = DEFAULT_OWNER_KEY_DIR, bits: int = 1024, force: bool = False) -> Dict[str, str]:
    owner = Path(owner_dir)
    owner.mkdir(parents=True, exist_ok=True)
    private_path = owner / DEFAULT_PRIVATE_KEY_NAME
    public_path = owner / DEFAULT_PUBLIC_KEY_NAME
    if private_path.exists() and public_path.exists() and not force:
        return {"private_key_path": str(private_path), "public_key_path": str(public_path), "created": "false"}
    public_key, private_key = generate_rsa_keypair(bits=bits)
    private_path.write_text(json.dumps(private_key, indent=2, sort_keys=True), encoding="utf-8")
    public_path.write_text(json.dumps(public_key, indent=2, sort_keys=True), encoding="utf-8")
    return {"private_key_path": str(private_path), "public_key_path": str(public_path), "created": "true"}


def load_private_key(path: str | Path) -> Dict[str, str]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def load_public_key(path: str | Path) -> Dict[str, str]:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def sign_payload(payload: Dict[str, Any], private_key: Dict[str, str]) -> str:
    body = canonical_json(payload)
    digest = hashlib.sha256(body).digest()
    h = int.from_bytes(digest, "big")
    n = int(private_key["n"])
    d = int(private_key["d"])
    sig_int = pow(h, d, n)
    sig_len = (n.bit_length() + 7) // 8
    return b64url_encode(sig_int.to_bytes(sig_len, "big"))


def make_license_key(payload: Dict[str, Any], private_key: Dict[str, str]) -> str:
    payload = dict(payload)
    payload["product"] = PRODUCT_CODE
    payload["license_version"] = LICENSE_VERSION
    body = b64url_encode(canonical_json(payload))
    signature = sign_payload(payload, private_key)
    return body + "." + signature


def parse_license_key(license_key: str) -> Tuple[Dict[str, Any], bytes]:
    parts = license_key.strip().split(".")
    if len(parts) != 2:
        raise ValueError("license key must contain one dot separator")
    payload = json.loads(b64url_decode(parts[0]).decode("utf-8"))
    signature = b64url_decode(parts[1])
    return payload, signature


def verify_license_key(license_key: str, public_key: Dict[str, str], expected_machine_id: str | None = None) -> Dict[str, Any]:
    try:
        payload, signature = parse_license_key(license_key)
        if payload.get("product") != PRODUCT_CODE:
            return {"valid": False, "reason": "wrong_product", "payload": payload}
        if payload.get("license_version") != LICENSE_VERSION:
            return {"valid": False, "reason": "wrong_license_version", "payload": payload}

        body = canonical_json(payload)
        digest = hashlib.sha256(body).digest()
        expected_hash = int.from_bytes(digest, "big")
        n = int(public_key["n"])
        e = int(public_key["e"])
        sig_int = int.from_bytes(signature, "big")
        actual_hash = pow(sig_int, e, n)
        if actual_hash != expected_hash:
            return {"valid": False, "reason": "bad_signature", "payload": payload}

        if expected_machine_id and payload.get("machine_id") != expected_machine_id:
            return {"valid": False, "reason": "machine_id_mismatch", "payload": payload, "expected_machine_id": expected_machine_id}

        expires_on = str(payload.get("expires_on", "")).strip()
        if expires_on:
            try:
                expires_date = datetime.strptime(expires_on, "%Y-%m-%d").date()
                if datetime.now().date() > expires_date:
                    return {"valid": False, "reason": "expired", "payload": payload}
            except ValueError:
                return {"valid": False, "reason": "bad_expiry_format", "payload": payload}

        return {"valid": True, "reason": "ok", "payload": payload}
    except Exception as exc:
        return {"valid": False, "reason": f"exception:{exc.__class__.__name__}", "error": str(exc)}


def create_license_payload(customer_name: str, customer_email: str, machine_id_value: str, expires_on: str, features: list[str] | None = None) -> Dict[str, Any]:
    return {
        "customer_name": customer_name,
        "customer_email": customer_email,
        "machine_id": machine_id_value,
        "expires_on": expires_on,
        "features": features or ["paper_validation", "dashboard", "reports"],
        "issued_at_utc": utc_now(),
    }
