#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Shared Tencent Cloud API v3 signer used by plugin implementations.
"""

import hashlib
import hmac
import time
from datetime import datetime
from typing import Dict


class TencentSigner:
    """Tencent Cloud API v3 Signature Generator."""

    @staticmethod
    def sha256_hex(s: str) -> str:
        return hashlib.sha256(s.encode("utf-8")).hexdigest()

    @staticmethod
    def hmac_sha256(key: bytes, msg: str) -> bytes:
        return hmac.new(key, msg.encode("utf-8"), hashlib.sha256).digest()

    @classmethod
    def sign(
        cls,
        secret_id: str,
        secret_key: str,
        service: str,
        host: str,
        action: str,
        version: str,
        region: str,
        payload: str,
    ) -> Dict[str, str]:
        algorithm = "TC3-HMAC-SHA256"
        timestamp = int(time.time())
        date = datetime.utcfromtimestamp(timestamp).strftime("%Y-%m-%d")

        ct = "application/json; charset=utf-8"
        canonical_headers = f"content-type:{ct}\nhost:{host}\nx-tc-action:{action.lower()}\n"
        signed_headers = "content-type;host;x-tc-action"
        hashed_request_payload = cls.sha256_hex(payload)

        canonical_request = (
            "POST\n"
            "/\n"
            "\n"
            f"{canonical_headers}\n"
            f"{signed_headers}\n"
            f"{hashed_request_payload}"
        )

        credential_scope = f"{date}/{service}/tc3_request"
        hashed_canonical_request = cls.sha256_hex(canonical_request)
        string_to_sign = (
            f"{algorithm}\n"
            f"{timestamp}\n"
            f"{credential_scope}\n"
            f"{hashed_canonical_request}"
        )

        secret_date = cls.hmac_sha256(("TC3" + secret_key).encode("utf-8"), date)
        secret_service = cls.hmac_sha256(secret_date, service)
        secret_signing = cls.hmac_sha256(secret_service, "tc3_request")
        signature = hmac.new(secret_signing, string_to_sign.encode("utf-8"), hashlib.sha256).hexdigest()

        authorization = (
            f"{algorithm} "
            f"Credential={secret_id}/{credential_scope}, "
            f"SignedHeaders={signed_headers}, "
            f"Signature={signature}"
        )

        return {
            "Authorization": authorization,
            "Content-Type": ct,
            "Host": host,
            "X-TC-Action": action,
            "X-TC-Timestamp": str(timestamp),
            "X-TC-Version": version,
            "X-TC-Region": region,
        }
