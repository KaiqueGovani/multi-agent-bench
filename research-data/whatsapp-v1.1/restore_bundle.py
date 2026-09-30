"""Authenticate and restore the local research ZIP; never extract its contents."""
import argparse
import hashlib
import json
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

MAGIC = b"TCCREPO1\x00"
ROOT = Path(__file__).resolve().parent


def restore(artifact, keyfile, manifest, output=None):
    encrypted = artifact.read_bytes()
    if (len(encrypted) != manifest["encrypted_bytes"] or
            hashlib.sha256(encrypted).hexdigest() != manifest["encrypted_sha256"]):
        raise ValueError("Arquivo divergente ou ponteiro Git LFS. Execute git lfs pull.")
    if not encrypted.startswith(MAGIC):
        raise ValueError("Formato de arquivo desconhecido.")
    keydata = json.loads(keyfile.read_text(encoding="utf-8"))
    if keydata.get("format") != "TCCREPO1":
        raise ValueError("Use a chave do repositorio, nao a chave interna do pacote.")
    key = bytes.fromhex(keydata["key_hex"])
    if len(key) != 32:
        raise ValueError("Chave invalida.")
    offset = len(MAGIC)
    plain = AESGCM(key).decrypt(
        encrypted[offset:offset + 12], encrypted[offset + 12:], MAGIC
    )
    if (len(plain) != manifest["original_bytes"] or
            hashlib.sha256(plain).hexdigest() != manifest["original_sha256"]):
        raise ValueError("O ZIP recuperado nao corresponde ao manifesto.")
    if output is not None:
        output.parent.mkdir(parents=True, exist_ok=True)
        with output.open("xb") as stream:
            stream.write(plain)
    return {"authenticated": True, "zip_sha256": manifest["original_sha256"]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--key", type=Path, required=True)
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--verify", action="store_true")
    action.add_argument("--output", type=Path)
    args = parser.parse_args()
    manifest = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
    result = restore(ROOT / manifest["encrypted_file"], args.key, manifest, args.output)
    print(json.dumps(result))


if __name__ == "__main__":
    main()
