"""Keep the local API, web app, and extension on one generated API key.

The resolve command writes its result only for Make's captured variable expansion.
The sync command reads API_KEY from its environment and never prints the key.
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import re
import secrets
import tempfile


LEGACY_DEMO_KEY = "poc-dev-key-2026"


def read_env_value(path: Path, name: str) -> str | None:
    """Read ordinary single-line dotenv values without a runtime dependency."""
    if not path.exists():
        return None
    value = None
    assignment = re.compile(rf"^\s*(?:export\s+)?{re.escape(name)}\s*=\s*(.*)$")
    for line in path.read_text().splitlines():
        match = assignment.match(line)
        if match:
            raw = match.group(1).strip()
            if raw.startswith(("'", '"')):
                quote = raw[0]
                quoted = re.match(rf"{quote}((?:\\.|[^{quote}])*){quote}\s*(?:#.*)?$", raw)
                if quoted is None:
                    raise ValueError("Invalid API key assignment")
                value = quoted.group(1)
                if quote == "'":
                    value = re.sub(r"\\([\\'])", r"\1", value)
                else:
                    escapes = {"n": "\n", "r": "\r", "t": "\t", "b": "\b", "f": "\f", "v": "\v", "a": "\a"}
                    value = re.sub(r'\\([\\\'"abfnrtv])', lambda item: escapes.get(item[1], item[1]), value)
            else:
                value = re.sub(r"\s+#.*$", "", raw).rstrip()
    return value


def resolve_api_key(root: Path, override: str | None = None) -> str:
    if override is not None:
        return override
    existing = read_env_value(root / "apps/api/.env", "API_KEY")
    if existing and existing != LEGACY_DEMO_KEY:
        return existing
    return secrets.token_urlsafe(32)


def configured_api_key(root: Path, override: str | None = None) -> str:
    """Read a client's existing key; clients must never generate their own key."""
    if override is not None:
        return override
    existing = read_env_value(root / "apps/api/.env", "API_KEY")
    if existing:
        return existing
    raise ValueError("No local API key is configured. Run make sync-env or set API_KEY.")


def _write_env_value(path: Path, name: str, value: str) -> None:
    if "\n" in value or "\r" in value or "\x00" in value:
        raise ValueError("The API key must be a single-line value")
    # Single quotes preserve dollar signs and comments in custom keys. Escape
    # backslashes/quotes as supported by python-dotenv, used by the services.
    quoted = "'" + value.replace("\\", "\\\\").replace("'", "\\'") + "'"
    assignment = re.compile(rf"^\s*(?:export\s+)?{re.escape(name)}\s*=")
    original = path.read_text() if path.exists() else ""
    lines, replaced = [], False
    for line in original.splitlines():
        if assignment.match(line):
            if not replaced:
                lines.append(f"{name}={quoted}")
                replaced = True
        else:
            lines.append(line)
    if not replaced:
        lines.append(f"{name}={quoted}")
    updated = "\n".join(lines) + "\n"
    path.parent.mkdir(parents=True, exist_ok=True)
    if original == updated:
        path.chmod(0o600)
        return
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(updated)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def sync_api_key(root: Path, key: str) -> None:
    _write_env_value(root / "apps/api/.env", "API_KEY", key)
    _write_env_value(root / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY", key)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("resolve", "sync"))
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    arguments = parser.parse_args()
    key = resolve_api_key(arguments.root, os.environ.get("API_KEY"))
    if arguments.mode == "resolve":
        print(key)
    else:
        sync_api_key(arguments.root, key)


if __name__ == "__main__":
    main()
