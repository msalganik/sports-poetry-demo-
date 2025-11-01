"""Unit tests for config_builder module."""

import pytest
import json
from pathlib import Path
from config_builder import ConfigBuilder, ConfigValidationError


class TestConfigBuilder:
    """Tests for ConfigBuilder class."""

    def test_default_config(self):
        """Test that default config has expected values."""
        builder = ConfigBuilder()
        assert builder.config["sports"] == []
        assert builder.config["retry_enabled"] is True
        assert builder.config["generation_mode"] == "template"
        assert builder.config["llm_provider"] == "together"

    def test_with_sports_valid(self):
        """Test adding valid sports list."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        assert builder.config["sports"] == ["basketball", "soccer", "tennis"]

    def test_with_sports_normalizes_case(self):
        """Test that sports names are normalized to lowercase."""
        builder = ConfigBuilder()
        builder.with_sports(["BASKETBALL", "Soccer", "TenNis"])
        assert builder.config["sports"] == ["basketball", "soccer", "tennis"]

    def test_with_sports_strips_whitespace(self):
        """Test that whitespace is stripped from sport names."""
        builder = ConfigBuilder()
        builder.with_sports([" basketball ", "  soccer", "tennis  "])
        assert builder.config["sports"] == ["basketball", "soccer", "tennis"]

    def test_with_sports_too_few(self):
        """Test that fewer than 3 sports raises error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="at least 3 sports"):
            builder.with_sports(["basketball", "soccer"])

    def test_with_sports_too_many(self):
        """Test that more than 5 sports raises error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="more than 5 sports"):
            builder.with_sports(["a", "b", "c", "d", "e", "f"])

    def test_with_sports_duplicates(self):
        """Test that duplicate sports raise error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="duplicates"):
            builder.with_sports(["basketball", "soccer", "basketball"])

    def test_with_sports_empty_string(self):
        """Test that empty sport names raise error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="empty values"):
            builder.with_sports(["basketball", "", "tennis"])

    def test_with_sports_not_list(self):
        """Test that non-list input raises error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="must be a list"):
            builder.with_sports("basketball,soccer,tennis")

    def test_with_session_id_custom(self):
        """Test setting custom session ID."""
        builder = ConfigBuilder()
        builder.with_session_id("test_session_123")
        assert builder.config["session_id"] == "test_session_123"

    def test_with_session_id_auto_generate(self):
        """Test auto-generating session ID."""
        builder = ConfigBuilder()
        builder.with_session_id()
        assert builder.config["session_id"] is not None
        assert builder.config["session_id"].startswith("session_")

    def test_with_timestamp_custom(self):
        """Test setting custom timestamp."""
        builder = ConfigBuilder()
        timestamp = "2025-01-01T12:00:00Z"
        builder.with_timestamp(timestamp)
        assert builder.config["timestamp"] == timestamp

    def test_with_timestamp_auto_generate(self):
        """Test auto-generating timestamp."""
        builder = ConfigBuilder()
        builder.with_timestamp()
        assert builder.config["timestamp"] is not None
        assert "Z" in builder.config["timestamp"]

    def test_with_retry_enabled(self):
        """Test enabling retry."""
        builder = ConfigBuilder()
        builder.with_retry(True)
        assert builder.config["retry_enabled"] is True

    def test_with_retry_disabled(self):
        """Test disabling retry."""
        builder = ConfigBuilder()
        builder.with_retry(False)
        assert builder.config["retry_enabled"] is False

    def test_with_generation_mode_template(self):
        """Test setting template generation mode."""
        builder = ConfigBuilder()
        builder.with_generation_mode("template")
        assert builder.config["generation_mode"] == "template"

    def test_with_generation_mode_llm(self):
        """Test setting LLM generation mode."""
        builder = ConfigBuilder()
        builder.with_generation_mode("llm")
        assert builder.config["generation_mode"] == "llm"

    def test_with_generation_mode_invalid(self):
        """Test that invalid generation mode raises error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="Invalid generation mode"):
            builder.with_generation_mode("invalid")

    def test_with_llm_provider_together(self):
        """Test setting Together.ai provider."""
        builder = ConfigBuilder()
        builder.with_llm_provider("together")
        assert builder.config["llm_provider"] == "together"

    def test_with_llm_provider_huggingface(self):
        """Test setting HuggingFace provider."""
        builder = ConfigBuilder()
        builder.with_llm_provider("huggingface")
        assert builder.config["llm_provider"] == "huggingface"

    def test_with_llm_provider_invalid(self):
        """Test that invalid LLM provider raises error."""
        builder = ConfigBuilder()
        with pytest.raises(ConfigValidationError, match="Invalid LLM provider"):
            builder.with_llm_provider("openai")

    def test_with_llm_model(self):
        """Test setting LLM model."""
        builder = ConfigBuilder()
        builder.with_llm_model("custom-model-name")
        assert builder.config["llm_model"] == "custom-model-name"

    def test_method_chaining(self):
        """Test that methods support chaining."""
        builder = ConfigBuilder()
        result = (builder
                  .with_sports(["basketball", "soccer", "tennis"])
                  .with_generation_mode("llm")
                  .with_retry(False))
        assert result is builder
        assert builder.config["sports"] == ["basketball", "soccer", "tennis"]
        assert builder.config["generation_mode"] == "llm"
        assert builder.config["retry_enabled"] is False

    def test_validate_success(self):
        """Test that valid config passes validation."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_session_id("test")
        builder.with_timestamp("2025-01-01T12:00:00Z")
        config = builder.validate()
        assert config["sports"] == ["basketball", "soccer", "tennis"]

    def test_validate_missing_sports(self):
        """Test that validation fails without sports."""
        builder = ConfigBuilder()
        builder.with_session_id("test")
        builder.with_timestamp("2025-01-01T12:00:00Z")
        with pytest.raises(ConfigValidationError, match="Sports list is required"):
            builder.validate()

    def test_validate_missing_session_id(self):
        """Test that validation fails without session ID."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_timestamp("2025-01-01T12:00:00Z")
        with pytest.raises(ConfigValidationError, match="Session ID is required"):
            builder.validate()

    def test_validate_missing_timestamp(self):
        """Test that validation fails without timestamp."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_session_id("test")
        with pytest.raises(ConfigValidationError, match="Timestamp is required"):
            builder.validate()

    def test_validate_llm_mode_requires_provider(self):
        """Test that LLM mode requires provider."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_session_id("test")
        builder.with_timestamp("2025-01-01T12:00:00Z")
        builder.with_generation_mode("llm")
        builder.config["llm_provider"] = None  # Manually break it
        with pytest.raises(ConfigValidationError, match="LLM provider is required"):
            builder.validate()

    def test_validate_llm_mode_requires_model(self):
        """Test that LLM mode requires model."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_session_id("test")
        builder.with_timestamp("2025-01-01T12:00:00Z")
        builder.with_generation_mode("llm")
        builder.config["llm_model"] = None  # Manually break it
        with pytest.raises(ConfigValidationError, match="LLM model is required"):
            builder.validate()

    def test_build_auto_generates_fields(self):
        """Test that build auto-generates missing fields."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        config = builder.build()
        assert config["session_id"] is not None
        assert config["timestamp"] is not None
        assert config["sports"] == ["basketball", "soccer", "tennis"]

    def test_build_preserves_explicit_fields(self):
        """Test that build preserves explicitly set fields."""
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_session_id("custom_session")
        builder.with_timestamp("2025-01-01T12:00:00Z")
        config = builder.build()
        assert config["session_id"] == "custom_session"
        assert config["timestamp"] == "2025-01-01T12:00:00Z"

    def test_save_creates_file(self, tmp_path):
        """Test that save creates a config file."""
        config_path = tmp_path / "test_config.json"
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        path = builder.save(str(config_path))

        assert path.exists()
        with open(path, "r") as f:
            data = json.load(f)
        assert data["sports"] == ["basketball", "soccer", "tennis"]

    def test_save_default_path(self, tmp_path, monkeypatch):
        """Test that save uses default path."""
        monkeypatch.chdir(tmp_path)
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        path = builder.save()

        assert path.name == "config.json"
        assert path.exists()

    def test_from_dict(self):
        """Test creating builder from dictionary."""
        data = {
            "sports": ["basketball", "soccer", "tennis"],
            "session_id": "test_session",
            "timestamp": "2025-01-01T12:00:00Z",
            "retry_enabled": False,
            "generation_mode": "llm",
            "llm_provider": "together",
            "llm_model": "test-model"
        }
        builder = ConfigBuilder.from_dict(data)
        assert builder.config["sports"] == ["basketball", "soccer", "tennis"]
        assert builder.config["retry_enabled"] is False
        assert builder.config["generation_mode"] == "llm"

    def test_load_existing_config(self, tmp_path):
        """Test loading existing config file."""
        config_path = tmp_path / "test_config.json"
        data = {
            "sports": ["hockey", "volleyball", "swimming"],
            "session_id": "loaded_session",
            "timestamp": "2025-01-01T12:00:00Z",
            "retry_enabled": True,
            "generation_mode": "template",
            "llm_provider": "together",
            "llm_model": "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"
        }
        with open(config_path, "w") as f:
            json.dump(data, f)

        builder = ConfigBuilder.load(str(config_path))
        assert builder.config["sports"] == ["hockey", "volleyball", "swimming"]
        assert builder.config["session_id"] == "loaded_session"


class TestConfigBuilderIntegration:
    """Integration tests for typical usage patterns."""

    def test_template_mode_workflow(self, tmp_path):
        """Test complete workflow for template mode config."""
        config_path = tmp_path / "config.json"
        builder = ConfigBuilder()
        builder.with_sports(["basketball", "soccer", "tennis"])
        builder.with_generation_mode("template")
        path = builder.save(str(config_path))

        # Verify file contents
        with open(path, "r") as f:
            config = json.load(f)

        assert config["sports"] == ["basketball", "soccer", "tennis"]
        assert config["generation_mode"] == "template"
        assert config["session_id"].startswith("session_")
        assert "Z" in config["timestamp"]

    def test_llm_mode_workflow(self, tmp_path):
        """Test complete workflow for LLM mode config."""
        config_path = tmp_path / "config.json"
        builder = ConfigBuilder()
        builder.with_sports(["hockey", "volleyball", "swimming", "baseball"])
        builder.with_generation_mode("llm")
        builder.with_llm_provider("together")
        builder.with_llm_model("meta-llama/Llama-3.3-70B-Instruct-Turbo-Free")
        path = builder.save(str(config_path))

        # Verify file contents
        with open(path, "r") as f:
            config = json.load(f)

        assert config["sports"] == ["hockey", "volleyball", "swimming", "baseball"]
        assert config["generation_mode"] == "llm"
        assert config["llm_provider"] == "together"
        assert config["llm_model"] == "meta-llama/Llama-3.3-70B-Instruct-Turbo-Free"

    def test_modify_and_resave(self, tmp_path):
        """Test loading, modifying, and resaving config."""
        config_path = tmp_path / "config.json"

        # Create initial config
        builder1 = ConfigBuilder()
        builder1.with_sports(["basketball", "soccer", "tennis"])
        builder1.save(str(config_path))

        # Load and modify
        builder2 = ConfigBuilder.load(str(config_path))
        builder2.with_generation_mode("llm")
        builder2.with_llm_provider("together")
        builder2.save(str(config_path))

        # Verify modifications
        with open(config_path, "r") as f:
            config = json.load(f)

        assert config["sports"] == ["basketball", "soccer", "tennis"]
        assert config["generation_mode"] == "llm"
