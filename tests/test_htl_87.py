"""Regression tests for HTL-87: Whitespace and control character stripping from secret-sourced config values."""

import os
from unittest.mock import patch
from src.config import AppConfig


def test_htl_87_env_secrets_stripped_with_trailing_crlf():
    """HTL-87 / HTL-66: Confirm trailing \\r\\n, \\n, tabs, and spaces in secret env vars are stripped at config load time."""
    env_overrides = {
        "ANTHROPIC_API_KEY": "sk-ant-test-key-with-newline\r\n",
        "OPENAI_API_KEY": "\tsk-proj-openai-key-with-whitespace \n",
        "ADMIN_PASSPHRASE": "  admin-secret-passphrase\r\n",
        "GENERATION_PASSPHRASE": "gen-secret-passphrase\r\n",
    }
    with patch.dict(os.environ, env_overrides, clear=False):
        cfg = AppConfig(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            admin_passphrase=os.getenv("ADMIN_PASSPHRASE", ""),
            generation_passphrase=os.getenv("GENERATION_PASSPHRASE", ""),
        )

        assert cfg.anthropic_api_key == "sk-ant-test-key-with-newline"
        assert cfg.openai_api_key == "sk-proj-openai-key-with-whitespace"
        assert cfg.admin_passphrase == "admin-secret-passphrase"
        assert cfg.generation_passphrase == "gen-secret-passphrase"


def test_htl_87_app_config_direct_constructor_kwargs_stripped():
    """HTL-87: Confirm AppConfig constructor strips whitespace and control characters from explicit kwargs via __post_init__."""
    cfg = AppConfig(
        anthropic_api_key="sk-ant-explicit-key\r\n",
        openai_api_key="  sk-proj-explicit-openai\n",
        admin_passphrase="admin-pass\r\n",
        generation_passphrase="\tgen-pass\r\n",
        default_provider="  ANTHROPIC \r\n",
        openai_model="  gpt-6.1-sol\n",
        default_governance_tier="  Elevated \r\n",
        default_contract_type=" Fixed Bid \n",
        llm_cache_mode=" REPLAY \r\n",
        review_storage_backend=" GCP \n",
    )

    assert cfg.anthropic_api_key == "sk-ant-explicit-key"
    assert cfg.openai_api_key == "sk-proj-explicit-openai"
    assert cfg.admin_passphrase == "admin-pass"
    assert cfg.generation_passphrase == "gen-pass"
    assert cfg.default_provider == "anthropic"
    assert cfg.openai_model == "gpt-6.1-sol"
    assert cfg.default_governance_tier == "Elevated"
    assert cfg.default_contract_type == "Fixed Bid"
    assert cfg.llm_cache_mode == "replay"
    assert cfg.review_storage_backend == "gcp"


def test_htl_87_clean_values_remain_unchanged():
    """HTL-87: Confirm that already-clean secret values are unchanged and retain their exact content."""
    clean_anthropic = "sk-ant-api03-clean-key-12345"
    clean_openai = "sk-proj-clean-openai-key-67890"
    clean_admin = "dev-only-change-me"
    clean_gen = "dev-generation-only-change-me"

    cfg = AppConfig(
        anthropic_api_key=clean_anthropic,
        openai_api_key=clean_openai,
        admin_passphrase=clean_admin,
        generation_passphrase=clean_gen,
    )

    assert cfg.anthropic_api_key == clean_anthropic
    assert cfg.openai_api_key == clean_openai
    assert cfg.admin_passphrase == clean_admin
    assert cfg.generation_passphrase == clean_gen


def test_htl_87_default_values_when_unset_are_clean():
    """HTL-87: Confirm default fallbacks when env vars are unset are properly populated and clean."""
    cfg = AppConfig()
    assert isinstance(cfg.admin_passphrase, str)
    assert cfg.admin_passphrase == cfg.admin_passphrase.strip()
    assert isinstance(cfg.generation_passphrase, str)
    assert cfg.generation_passphrase == cfg.generation_passphrase.strip()
