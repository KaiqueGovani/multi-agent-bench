"""Local setup uses one durable key without exposing it in command output."""
from importlib.util import module_from_spec, spec_from_file_location
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

import pytest


ROOT = Path(__file__).resolve().parents[1]
SPEC = spec_from_file_location("local_api_key", ROOT / "scripts/local_api_key.py")
keys = module_from_spec(SPEC)
SPEC.loader.exec_module(keys)


def environment():
    return {name: value for name, value in os.environ.items()
            if name not in {
                "API_KEY", "NEXT_PUBLIC_API_KEY", "MAKEFLAGS", "MFLAGS", "MAKELEVEL",
                "AWS_BEARER_TOKEN_BEDROCK", "ANTHROPIC_API_KEY", "AI_SERVICE_SECRET", "DB_PASSWORD",
            }}


def prepare_make(root):
    (root / "scripts").mkdir()
    shutil.copyfile(ROOT / "Makefile", root / "Makefile")
    shutil.copyfile(ROOT / "scripts/local_api_key.py", root / "scripts/local_api_key.py")
    for app in ("api", "web", "agent-runtime"):
        (root / "apps" / app).mkdir(parents=True)


def test_fresh_key_is_random_and_persisted_to_matching_files(tmp_path):
    first = keys.resolve_api_key(tmp_path)
    assert re.fullmatch(r"[A-Za-z0-9_-]{43}", first)
    assert first != keys.resolve_api_key(tmp_path)
    keys.sync_api_key(tmp_path, first)
    assert keys.resolve_api_key(tmp_path) == first
    assert keys.read_env_value(tmp_path / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY") == first
    assert (tmp_path / "apps/api/.env").stat().st_mode & 0o777 == 0o600
    assert (tmp_path / "apps/web/.env.local").stat().st_mode & 0o777 == 0o600


@pytest.mark.parametrize("previous", ["", keys.LEGACY_DEMO_KEY])
def test_empty_and_legacy_keys_are_replaced(tmp_path, previous):
    keys.sync_api_key(tmp_path, previous)
    selected = keys.resolve_api_key(tmp_path)
    assert selected not in {"", keys.LEGACY_DEMO_KEY}
    assert len(selected) == 43


@pytest.mark.parametrize("existing", ["custom-existing-test-key", "custom$test#value", "custom'test\\value"])
def test_custom_keys_survive_sync_and_other_settings_are_preserved(tmp_path, existing):
    api = tmp_path / "apps/api/.env"
    web = tmp_path / "apps/web/.env.local"
    api.parent.mkdir(parents=True)
    web.parent.mkdir(parents=True)
    api.write_text("DATABASE_URL=postgresql://local/test\nOTHER_SETTING=keep\n")
    web.write_text("NEXT_PUBLIC_API_BASE_URL=http://127.0.0.1:8100\n")
    keys.sync_api_key(tmp_path, existing)
    assert keys.resolve_api_key(tmp_path) == existing
    assert keys.read_env_value(web, "NEXT_PUBLIC_API_KEY") == existing
    assert "OTHER_SETTING=keep" in api.read_text()
    assert "DATABASE_URL=postgresql://local/test" in api.read_text()
    assert "http://127.0.0.1:8100" in web.read_text()


def test_explicit_override_wins(tmp_path):
    keys.sync_api_key(tmp_path, "existing-test-key")
    assert keys.resolve_api_key(tmp_path, "override-test-key") == "override-test-key"
    assert keys.resolve_api_key(tmp_path, "") == ""


def test_clients_read_the_configured_key_without_generating_or_writing(tmp_path):
    with pytest.raises(ValueError, match="make sync-env or set API_KEY"):
        keys.configured_api_key(tmp_path)
    assert not (tmp_path / "apps").exists()
    keys.sync_api_key(tmp_path, "configured-client-test-key")
    assert keys.configured_api_key(tmp_path) == "configured-client-test-key"
    assert keys.configured_api_key(tmp_path, "explicit-client-test-key") == "explicit-client-test-key"
    assert keys.configured_api_key(tmp_path, "") == ""


@pytest.mark.parametrize("existing", ["custom$test#value", "custom'test\\value"])
def test_make_preserves_existing_custom_key_literals(tmp_path, existing):
    prepare_make(tmp_path)
    keys.sync_api_key(tmp_path, existing)
    result = subprocess.run(["make", "-s", "sync-api-key"], cwd=tmp_path, env=environment(), capture_output=True, text=True, check=True)
    assert keys.resolve_api_key(tmp_path) == existing
    assert keys.read_env_value(tmp_path / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY") == existing
    assert existing not in result.stdout + result.stderr


def test_make_generates_once_and_preserves_key_on_next_invocation(tmp_path):
    prepare_make(tmp_path)
    first = subprocess.run(["make", "-s", "sync-api-key"], cwd=tmp_path, env=environment(), capture_output=True, text=True, check=True)
    key = keys.resolve_api_key(tmp_path)
    assert first.stdout == ""
    assert key not in first.stderr
    assert key == keys.read_env_value(tmp_path / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY")
    subprocess.run(["make", "-s", "sync-api-key"], cwd=tmp_path, env=environment(), capture_output=True, check=True)
    assert keys.resolve_api_key(tmp_path) == key


def test_make_sync_env_migrates_legacy_and_exports_one_key_to_submakes(tmp_path):
    prepare_make(tmp_path)
    keys.sync_api_key(tmp_path, keys.LEGACY_DEMO_KEY)
    subprocess.run(["make", "-s", "sync-env"], cwd=tmp_path, env=environment(), capture_output=True, check=True)
    key = keys.resolve_api_key(tmp_path)
    assert key != keys.LEGACY_DEMO_KEY
    assert keys.read_env_value(tmp_path / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY") == key
    check = tmp_path / "check.py"
    check.write_text("import os\nassert os.environ['API_KEY'] == os.environ['NEXT_PUBLIC_API_KEY']\n")
    with (tmp_path / "Makefile").open("a") as makefile:
        makefile.write("\n.PHONY: verify-parent verify-child\nverify-parent:\n\t@$(MAKE) -s verify-child\nverify-child:\n\t@python3 check.py\n")
    subprocess.run(["make", "-s", "verify-parent"], cwd=tmp_path, env=environment(), capture_output=True, check=True)
    assert keys.resolve_api_key(tmp_path) == key


@pytest.mark.parametrize("use_environment", [True, False])
def test_make_honors_explicit_override_without_logging_it(tmp_path, use_environment):
    prepare_make(tmp_path)
    env = environment()
    command = ["make", "-s", "sync-api-key"]
    override = "explicit-override-test-only"
    if use_environment:
        env["API_KEY"] = override
    else:
        command.append(f"API_KEY={override}")
    result = subprocess.run(command, cwd=tmp_path, env=env, capture_output=True, text=True, check=True)
    assert keys.resolve_api_key(tmp_path) == override
    assert keys.read_env_value(tmp_path / "apps/web/.env.local", "NEXT_PUBLIC_API_KEY") == override
    assert override not in result.stdout + result.stderr


def test_sync_cli_never_prints_key(tmp_path):
    env = environment()
    env["API_KEY"] = "cli-test-key"
    result = subprocess.run([sys.executable, str(ROOT / "scripts/local_api_key.py"), "sync", "--root", str(tmp_path)], env=env, capture_output=True, text=True, check=True)
    assert result.stdout == ""
    assert "cli-test-key" not in result.stderr
