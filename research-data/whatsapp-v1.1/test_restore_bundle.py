"""Synthetic fixtures only: no research data or real keys."""
import hashlib
import json
from pathlib import Path
import secrets
import tempfile
import unittest

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from restore_bundle import MAGIC, restore


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.artifact = self.root / "sample.tccenc"
        self.keyfile = self.root / "key.json"
        self.output = self.root / "restored.zip"
        self.plain = b"synthetic archive fixture"
        self.key = AESGCM.generate_key(bit_length=256)
        self.write_key(self.key)
        nonce = secrets.token_bytes(12)
        sealed = MAGIC + nonce + AESGCM(self.key).encrypt(nonce, self.plain, MAGIC)
        self.artifact.write_bytes(sealed)
        self.manifest = {
            "encrypted_bytes": len(sealed),
            "encrypted_sha256": hashlib.sha256(sealed).hexdigest(),
            "original_bytes": len(self.plain),
            "original_sha256": hashlib.sha256(self.plain).hexdigest(),
        }

    def write_key(self, key):
        self.keyfile.write_text(json.dumps({"format": "TCCREPO1", "key_hex": key.hex()}))

    def test_roundtrip_and_no_overwrite(self):
        restore(self.artifact, self.keyfile, self.manifest, self.output)
        self.assertEqual(self.output.read_bytes(), self.plain)
        with self.assertRaises(FileExistsError):
            restore(self.artifact, self.keyfile, self.manifest, self.output)
        self.assertEqual(self.output.read_bytes(), self.plain)

    def test_verify_does_not_write(self):
        self.assertTrue(restore(self.artifact, self.keyfile, self.manifest)["authenticated"])
        self.assertFalse(self.output.exists())

    def test_wrong_key_writes_nothing(self):
        self.write_key(AESGCM.generate_key(bit_length=256))
        with self.assertRaises(InvalidTag):
            restore(self.artifact, self.keyfile, self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_tampering_rejected_even_with_updated_hash(self):
        sealed = bytearray(self.artifact.read_bytes())
        sealed[-1] ^= 1
        self.artifact.write_bytes(sealed)
        self.manifest["encrypted_sha256"] = hashlib.sha256(sealed).hexdigest()
        with self.assertRaises(InvalidTag):
            restore(self.artifact, self.keyfile, self.manifest, self.output)
        self.assertFalse(self.output.exists())

    def test_lfs_pointer_rejected(self):
        self.artifact.write_bytes(b"version https://git-lfs.github.com/spec/v1\n")
        with self.assertRaises(ValueError):
            restore(self.artifact, self.keyfile, self.manifest, self.output)
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
