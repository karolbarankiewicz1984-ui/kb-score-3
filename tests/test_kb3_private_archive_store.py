"""Offline synthetic checks; never contact GitHub or PitchAPI."""
from datetime import datetime, timezone
import base64
import unittest
from unittest.mock import patch

from src.kb3_pitch_uefa_evidence import add_observation
from src.kb3_private_archive_store import (
    PrivateArchiveStore, PrivateStoreError, REPOSITORY,
    encode_receipts, decode_receipts,
)


def fixture():
    rows = []
    # Synthetic payload, using the normal capture shape only for unit tests.
    now = datetime.now(timezone.utc).isoformat()
    add_observation(rows, resource="pitchapi:synthetic:private-store-test",
                    payload={"test_only": True}, started=now, completed=now)
    return rows


class FakeStore(PrivateArchiveStore):
    def __init__(self, private=True):
        self.private = private
        self.files = {}
        self.requests = []
        self.fail_readback = False

    def _request(self, path="", *, method="GET", body=None, raw=False, missing_ok=False):
        self.requests.append((method, path))
        if not path:
            return {"full_name": REPOSITORY, "private": self.private,
                    "visibility": "private" if self.private else "public",
                    "default_branch": "main"}
        path = path.split("?")[0]
        if method == "PUT":
            assert "sha" not in body
            assert path not in self.files
            self.files[path] = base64.b64decode(body["content"])
            return {}
        if path in self.files:
            return b"corrupt" if self.fail_readback else self.files[path]
        if missing_ok:
            return None
        raise PrivateStoreError("PRIVATE_ARCHIVE_HTTP_404")


class PrivateStoreTests(unittest.TestCase):
    def test_roundtrip_and_integrity(self):
        rows = fixture()
        key, blob = encode_receipts(rows)
        recovered, proof = decode_receipts(key, blob)
        self.assertEqual(recovered, rows)
        self.assertEqual(proof["sessions"], 1)
        with self.assertRaises(PrivateStoreError):
            decode_receipts("0" * 64, blob)
        with self.assertRaises(PrivateStoreError):
            decode_receipts(key, b"not gzip")

    def test_public_destination_no_upload(self):
        store = FakeStore(private=False)
        with self.assertRaisesRegex(PrivateStoreError, "DESTINATION_NOT_VERIFIED"):
            store.write(fixture(), storage_authorized=True)
        self.assertFalse(store.files)
        self.assertEqual(store.requests, [("GET", "")])

    def test_unapproved_no_network(self):
        store = FakeStore()
        with self.assertRaisesRegex(PrivateStoreError, "STORAGE_NOT_AUTHORIZED"):
            store.write(fixture())
        self.assertEqual(store.requests, [])

    def test_immutable_idempotent_write_and_readback(self):
        store = FakeStore()
        rows = fixture()
        first = store.write(rows, storage_authorized=True)
        second = store.write(rows, storage_authorized=True)
        self.assertTrue(first["created"])
        self.assertTrue(first["readback_verified"])
        self.assertFalse(second["created"])
        self.assertEqual(first["raw_sha256"], second["raw_sha256"])
        self.assertEqual(sum(method == "PUT" for method, _ in store.requests), 1)
        self.assertEqual(store.read(first["raw_sha256"])[0], rows)

    def test_corrupt_readback_not_success(self):
        store = FakeStore()
        store.fail_readback = True
        with self.assertRaises(PrivateStoreError):
            store.write(fixture(), storage_authorized=True)

    def test_path_traversal_rejected(self):
        with self.assertRaisesRegex(PrivateStoreError, "BAD_ID"):
            FakeStore().read("../public-data")

    def test_missing_token(self):
        with self.assertRaisesRegex(PrivateStoreError, "AUTH_REQUIRED"):
            PrivateArchiveStore("")

    def test_wrong_repository_rejected(self):
        store = FakeStore()
        with patch.object(store, "_request", return_value={
            "full_name": "different/repo", "private": True,
            "visibility": "private", "default_branch": "main"}):
            with self.assertRaisesRegex(PrivateStoreError, "DESTINATION_NOT_VERIFIED"):
                store.write(fixture(), storage_authorized=True)


if __name__ == "__main__":
    unittest.main()
