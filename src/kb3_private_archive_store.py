"""Opt-in, content-addressed private GitHub store for verified source receipts.

Not enabled by any live collector. No provider calls, no legacy migration,
no changes to forecast/settlement ledgers. Public code never stores raw data.
"""
from __future__ import annotations

import base64
import gzip
import hashlib
import io
import json
import re
import urllib.error
import urllib.request

from src.kb3_pitch_uefa_evidence import SCHEMA, MAX_RAW, verify_receipts
from src.kb3_pit_ledger import canonical

REPOSITORY = "karolbarankiewicz1984-ui/kb-score-3-data"
API_ROOT = "https://api.github.com/repos/" + REPOSITORY
MAX_BLOB = MAX_RAW + 65536
HEX = re.compile(r"[0-9a-f]{64}")


class PrivateStoreError(RuntimeError):
    """Safe error code; never include provider payload or credentials."""


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def encode_receipts(receipts, *, allow_synthetic=False):
    verify_receipts(receipts, allow_synthetic=allow_synthetic)
    raw = canonical({"schema": SCHEMA, "receipts": receipts})
    if len(raw) > MAX_RAW:
        raise PrivateStoreError("PRIVATE_ARCHIVE_RAW_SIZE_LIMIT")
    return digest(raw), gzip.compress(raw, mtime=0)


def decode_receipts(key, blob, *, allow_synthetic=False):
    if not isinstance(key, str) or not HEX.fullmatch(key):
        raise PrivateStoreError("PRIVATE_ARCHIVE_BAD_ID")
    if len(blob) > MAX_BLOB:
        raise PrivateStoreError("PRIVATE_ARCHIVE_COMPRESSED_SIZE_LIMIT")
    try:
        with gzip.GzipFile(fileobj=io.BytesIO(blob)) as stream:
            raw = stream.read(MAX_RAW + 1)
        if len(raw) > MAX_RAW or digest(raw) != key:
            raise PrivateStoreError("PRIVATE_ARCHIVE_CHECKSUM_MISMATCH")
        obj = json.loads(raw)
        if obj.get("schema") != SCHEMA or canonical(obj) != raw:
            raise PrivateStoreError("PRIVATE_ARCHIVE_SCHEMA_MISMATCH")
        if set(obj) != {"schema", "receipts"}:
            raise PrivateStoreError("PRIVATE_ARCHIVE_SCHEMA_MISMATCH")
        proof = verify_receipts(obj["receipts"], allow_synthetic=allow_synthetic)
    except PrivateStoreError:
        raise
    except (ValueError, TypeError, KeyError, AttributeError, EOFError, OSError) as exc:
        raise PrivateStoreError("PRIVATE_ARCHIVE_INVALID_RECEIPTS") from None
    return obj["receipts"], proof


class PrivateArchiveStore:
    def __init__(self, token):
        if not isinstance(token, str) or not token.strip():
            raise PrivateStoreError("PRIVATE_ARCHIVE_AUTH_REQUIRED")
        self._token = token
        self._opener = urllib.request.build_opener(NoRedirect())

    def _request(self, path="", *, method="GET", body=None, raw=False, missing_ok=False):
        # Only the fixed GitHub API origin and fixed dedicated repository.
        headers = {"Authorization": "Bearer " + self._token,
                   "Accept": "application/vnd.github.raw+json" if raw else "application/vnd.github+json",
                   "X-GitHub-Api-Version": "2022-11-28",
                   "Content-Type": "application/json"}
        request = urllib.request.Request(API_ROOT + path, headers=headers,
                   method=method, data=None if body is None else json.dumps(body).encode("utf-8"))
        try:
            with self._opener.open(request, timeout=45) as response:
                result = response.read(MAX_BLOB + 1)
            if len(result) > MAX_BLOB:
                raise PrivateStoreError("PRIVATE_ARCHIVE_RESPONSE_TOO_LARGE")
            return result if raw else json.loads(result)
        except urllib.error.HTTPError as exc:
            if exc.code == 404 and missing_ok:
                return None
            raise PrivateStoreError("PRIVATE_ARCHIVE_HTTP_" + str(exc.code)) from None
        except (OSError, ValueError) as exc:
            raise PrivateStoreError("PRIVATE_ARCHIVE_REQUEST_FAILED") from None

    def _verify_destination(self):
        meta = self._request()
        if not isinstance(meta, dict) or (
            meta.get("full_name") != REPOSITORY
            or meta.get("private") is not True
            or meta.get("visibility") != "private"
            or meta.get("default_branch") != "main"
        ):
            raise PrivateStoreError("PRIVATE_ARCHIVE_DESTINATION_NOT_VERIFIED")

    @staticmethod
    def _path(key):
        if not isinstance(key, str) or not HEX.fullmatch(key):
            raise PrivateStoreError("PRIVATE_ARCHIVE_BAD_ID")
        return "/contents/receipts/v1/" + key[:2] + "/" + key + ".json.gz"

    def read(self, key):
        self._verify_destination()
        blob = self._request(self._path(key) + "?ref=main", raw=True)
        return decode_receipts(key, blob)

    def write(self, receipts, *, storage_authorized=False):
        # Legal/data-retention decision is external; absence means no upload.
        if storage_authorized is not True:
            raise PrivateStoreError("PRIVATE_ARCHIVE_STORAGE_NOT_AUTHORIZED")
        self._verify_destination()
        key, blob = encode_receipts(receipts)
        path = self._path(key)
        current = self._request(path + "?ref=main", raw=True, missing_ok=True)
        if current is not None:
            decode_receipts(key, current)
            return {"raw_sha256": key, "created": False, "readback_verified": True}
        # Recheck immediately before writing. Never supply a SHA for replacement.
        self._verify_destination()
        self._request(path, method="PUT", body={
            "message": "archive verified source " + key,
            "content": base64.b64encode(blob).decode("ascii"),
            "branch": "main",
        })
        self.read(key)
        return {"raw_sha256": key, "created": True, "readback_verified": True}
