"""Tests for the interactive identity builder and LLM enhancer."""

from __future__ import annotations

import json
import os
from unittest.mock import MagicMock, patch

import pytest
import yaml

from personanexus.builder import BuiltIdentity, IdentityBuilder, LLMEnhancer

# ---------------------------------------------------------------------------
# BuiltIdentity
# ---------------------------------------------------------------------------


class TestBuiltIdentity:
    def test_initial_structure(self):
        data = {
            "schema_version": "1.0",
            "metadata": {"id": "agt_test_123", "name": "Test"},
        }
        bi = BuiltIdentity(data)
        assert bi.data["schema_version"] == "1.0"
        assert bi.data["metadata"]["name"] == "Test"

    def test_to_dict(self):
        data = {"schema_version": "1.0", "metadata": {"name": "Test"}}
        bi = BuiltIdentity(data)
        assert bi.to_dict() == data

    def test_to_yaml_string_produces_valid_yaml(self):
        data = {
            "schema_version": "1.0",
            "metadata": {"id": "agt_test_123", "name": "Test"},
            "personality": {"traits": {"warmth": 0.7, "rigor": 0.5}},
        }
        bi = BuiltIdentity(data)
        yaml_str = bi.to_yaml_string()
        parsed = yaml.safe_load(yaml_str)
        assert parsed["metadata"]["name"] == "Test"
        assert parsed["personality"]["traits"]["warmth"] == 0.7


# ---------------------------------------------------------------------------
# IdentityBuilder phases (with mocked prompts)
# ---------------------------------------------------------------------------


class TestIdentityBuilderPhases:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_basics_generates_valid_id(self, mock_ask):
        mock_ask.side_effect = [
            "TestBot",  # name
            "Test Assistant",  # title
            "Help users test things",  # purpose
            "A test bot",  # description
            "testing, QA",  # scope
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_basics(data)

        assert data["metadata"]["id"].startswith("agt_testbot_")
        assert data["metadata"]["name"] == "TestBot"
        assert data["metadata"]["version"] == "0.1.0"
        assert data["metadata"]["status"] == "draft"
        assert data["role"]["title"] == "Test Assistant"
        assert data["role"]["scope"]["primary"] == ["testing", "QA"]

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_validates_range(self, mock_ask):
        # Provide values for all 10 traits: some valid, some skipped
        mock_ask.side_effect = [
            "0.8",  # warmth
            "",  # verbosity (skip)
            "0.6",  # assertiveness
            "",  # humor (skip)
            "",  # empathy (skip)
            "0.7",  # directness
            "",  # rigor (skip)
            "",  # creativity (skip)
            "",  # epistemic_humility (skip)
            "",  # patience (skip)
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_personality(data)

        traits = data["personality"]["traits"]
        assert traits["warmth"] == 0.8
        assert traits["assertiveness"] == 0.6
        assert traits["directness"] == 0.7
        assert "rigor" not in traits  # skipped

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_enforces_minimum_2_traits(self, mock_ask):
        # Skip all traits (provide empty for all 10)
        mock_ask.side_effect = [""] * 10
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_personality(data)

        traits = data["personality"]["traits"]
        assert len(traits) >= 2

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_principles_auto_assigns_priorities(self, mock_ask):
        mock_ask.side_effect = [
            "Be helpful",
            "Be safe",
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_principles(data)

        assert len(data["principles"]) == 2
        assert data["principles"][0]["priority"] == 1
        assert data["principles"][1]["priority"] == 2
        assert data["principles"][0]["statement"] == "Be helpful"

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_principles_adds_default_if_empty(self, mock_ask):
        mock_ask.side_effect = [""]  # immediately end
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_principles(data)

        assert len(data["principles"]) == 1
        assert data["principles"][0]["id"] == "safety_first"

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_guardrails_adds_default_if_empty(self, mock_ask):
        mock_ask.side_effect = [""]  # immediately end
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_guardrails(data)

        assert len(data["guardrails"]["hard"]) == 1
        assert data["guardrails"]["hard"][0]["id"] == "no_harmful_content"

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_guardrails_with_input(self, mock_ask):
        mock_ask.side_effect = [
            "Never share passwords",
            "Never impersonate humans",
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_guardrails(data)

        assert len(data["guardrails"]["hard"]) == 2
        assert data["guardrails"]["hard"][0]["severity"] == "critical"

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_communication(self, mock_ask):
        mock_ask.side_effect = [
            "warm and professional",  # tone
            "consultative",  # register
            "sparingly",  # emoji
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_communication(data)

        assert data["communication"]["tone"]["default"] == "warm and professional"
        assert data["communication"]["tone"]["register"] == "consultative"

    @patch("personanexus.builder.Confirm.ask")
    def test_phase_expertise_skipped_if_declined(self, mock_confirm):
        mock_confirm.return_value = False
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert "expertise" not in data

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_phase_expertise_with_domains(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "Python",  # domain name
            "0.9",  # level
            "primary",  # category
            "",  # end loop (domain name empty)
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert len(data["expertise"]["domains"]) == 1
        assert data["expertise"]["domains"][0]["name"] == "Python"
        assert data["expertise"]["domains"][0]["level"] == 0.9


# ---------------------------------------------------------------------------
# Re-prompt validation tests
# ---------------------------------------------------------------------------


class TestRepromptOnInvalidInput:
    """Tests that invalid input triggers a re-prompt.

    Instead of being silently skipped or defaulted.
    """

    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Prompt.ask")
    def test_personality_reprompts_on_out_of_range(self, mock_ask):
        # First trait: enter 1.5 (rejected), then 0.8 (accepted), then skip the rest
        mock_ask.side_effect = [
            "1.5",  # warmth — out of range, re-prompt
            "0.8",  # warmth — accepted
            "",  # verbosity (skip)
            "0.6",  # assertiveness
            "",  # humor (skip)
            "",  # empathy (skip)
            "0.7",  # directness
            "",  # rigor (skip)
            "",  # creativity (skip)
            "",  # epistemic_humility (skip)
            "",  # patience (skip)
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_personality(data)

        traits = data["personality"]["traits"]
        assert traits["warmth"] == 0.8  # got the corrected value
        assert traits["assertiveness"] == 0.6
        assert traits["directness"] == 0.7

    @patch("personanexus.builder.Prompt.ask")
    def test_personality_reprompts_on_non_numeric(self, mock_ask):
        # First trait: enter "abc" (rejected), then "0.7" (accepted), skip rest
        mock_ask.side_effect = [
            "abc",  # warmth — not a number, re-prompt
            "0.7",  # warmth — accepted
            "",  # verbosity (skip)
            "0.5",  # assertiveness
            "",  # humor (skip)
            "",  # empathy (skip)
            "",  # directness (skip)
            "",  # rigor (skip)
            "",  # creativity (skip)
            "",  # epistemic_humility (skip)
            "",  # patience (skip)
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_personality(data)

        traits = data["personality"]["traits"]
        assert traits["warmth"] == 0.7
        assert traits["assertiveness"] == 0.5

    @patch("personanexus.builder.Prompt.ask")
    def test_personality_reprompts_on_negative(self, mock_ask):
        # Enter -0.5 (rejected), then 0.3 (accepted), then skip rest
        mock_ask.side_effect = [
            "-0.5",  # warmth — negative, re-prompt
            "0.3",  # warmth — accepted
            "0.6",  # verbosity
            "",  # assertiveness (skip)
            "",  # humor (skip)
            "",  # empathy (skip)
            "",  # directness (skip)
            "",  # rigor (skip)
            "",  # creativity (skip)
            "",  # epistemic_humility (skip)
            "",  # patience (skip)
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_personality(data)

        traits = data["personality"]["traits"]
        assert traits["warmth"] == 0.3

    @patch("personanexus.builder.Prompt.ask")
    def test_communication_reprompts_bad_register(self, mock_ask):
        mock_ask.side_effect = [
            "warm and professional",  # tone — free text, accepted
            "pirate",  # register — invalid, re-prompt
            "casual",  # register — accepted
            "sparingly",  # emoji — accepted
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_communication(data)

        assert data["communication"]["tone"]["register"] == "casual"

    @patch("personanexus.builder.Prompt.ask")
    def test_communication_reprompts_bad_emoji(self, mock_ask):
        mock_ask.side_effect = [
            "friendly",  # tone
            "consultative",  # register — accepted
            "lots",  # emoji — invalid, re-prompt
            "frequent",  # emoji — accepted
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_communication(data)

        assert data["communication"]["style"]["use_emoji"] == "frequent"

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_expertise_reprompts_bad_level(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "Python",  # domain name
            "abc",  # level — not a number, re-prompt
            "0.9",  # level — accepted
            "primary",  # category — accepted
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert data["expertise"]["domains"][0]["level"] == 0.9

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_expertise_reprompts_out_of_range_level(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "ML",  # domain name
            "1.5",  # level — out of range, re-prompt
            "0.7",  # level — accepted
            "secondary",  # category — accepted
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert data["expertise"]["domains"][0]["level"] == 0.7

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_expertise_reprompts_bad_category(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "Python",  # domain name
            "0.9",  # level — accepted
            "main",  # category — invalid, re-prompt
            "primary",  # category — accepted
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert data["expertise"]["domains"][0]["category"] == "primary"

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_expertise_level_required_not_skippable(self, mock_confirm, mock_ask):
        """Level is required (allow_skip=False) when adding a domain — empty input re-prompts."""
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "Python",  # domain name
            "",  # level — empty, re-prompt (required)
            "0.8",  # level — accepted
            "primary",  # category — accepted
            "",  # end loop
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_expertise(data)

        assert data["expertise"]["domains"][0]["level"] == 0.8


# ---------------------------------------------------------------------------
# LLMEnhancer
# ---------------------------------------------------------------------------


class TestLLMEnhancer:
    def test_template_fallback_returns_expected_keys(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "TestBot"},
                "role": {"title": "Helper", "purpose": "Help users"},
                "personality": {"traits": {"warmth": 0.8, "rigor": 0.7}},
            }
        )
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "personality_notes" in result
        assert "greeting" in result
        assert "vocabulary" in result
        assert "strategies" in result

    def test_personality_notes_reference_agent_role(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "DataBot"},
                "role": {"title": "Data Analyst", "purpose": "Analyze data"},
                "personality": {"traits": {"warmth": 0.5, "rigor": 0.9}},
            }
        )
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "DataBot" in result["personality_notes"]
        assert "Data Analyst" in result["personality_notes"]

    def test_greeting_includes_agent_name(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "Ada"},
                "role": {"title": "Analyst", "purpose": "Analyze things"},
                "personality": {"traits": {"warmth": 0.7, "rigor": 0.8}},
            }
        )
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "Ada" in result["greeting"]

    def test_template_high_warmth_notes(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "WarmBot"},
                "role": {"title": "Helper", "purpose": "Help"},
                "personality": {"traits": {"warmth": 0.9, "rigor": 0.5}},
            }
        )
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "warmth" in result["personality_notes"].lower()

    def test_apply_enhancements_non_interactive(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "TestBot"},
                "role": {"title": "Helper", "purpose": "Help"},
                "personality": {"traits": {"warmth": 0.7, "rigor": 0.5}},
                "communication": {"tone": {"default": "friendly"}},
            }
        )
        enhancements = {
            "personality_notes": "A helpful bot.",
            "greeting": "Hello!",
            "vocabulary": {
                "preferred": ["Great question"],
                "avoided": ["As an AI"],
                "signature_phrases": ["Let's go"],
            },
            "strategies": {
                "uncertainty": {"approach": "transparent"},
            },
        }
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.apply_enhancements(identity, enhancements, interactive=False)

        assert result.data["personality"]["notes"] == "A helpful bot."
        assert result.data["metadata"]["greeting"] == "Hello!"
        assert result.data["communication"]["vocabulary"]["preferred"] == ["Great question"]
        assert result.data["behavior"]["strategies"]["uncertainty"]["approach"] == "transparent"

    def test_no_api_key_falls_back_to_templates(self):
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "Bot"},
                "role": {"title": "Helper", "purpose": "Help"},
                "personality": {"traits": {"warmth": 0.5, "rigor": 0.5}},
            }
        )
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.enhance(identity)

        # Should still produce valid output via templates
        assert isinstance(result["personality_notes"], str)
        assert isinstance(result["greeting"], str)


# ---------------------------------------------------------------------------
# IdentityBuilder.run() orchestration (covers lines 118-139)
# ---------------------------------------------------------------------------


class TestIdentityBuilderRun:
    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_run_returns_built_identity(self, mock_confirm, mock_ask):
        """Full wizard run with custom personality mode (default)."""
        mock_ask.side_effect = [
            # Phase 1: Basics
            "TestBot",
            "Test Assistant",
            "Help users",
            "A test bot",
            "testing",
            # Phase 2a: Mode — default "custom" accepted
            "custom",
            # Phase 2b: Custom personality — 10 traits (skip most)
            "0.8",
            "",
            "0.6",
            "",
            "",
            "0.7",
            "",
            "",
            "",
            "",
            # Phase 3: Communication
            "professional",
            "consultative",
            "sparingly",
            # Phase 4: Principles
            "Be safe",
            "",
            # Phase 5: Guardrails
            "Never harm",
            "",
        ]
        mock_confirm.return_value = False  # skip expertise

        builder = IdentityBuilder(console=MagicMock())
        result = builder.run()

        assert isinstance(result, BuiltIdentity)
        assert result.data["schema_version"] == "1.0"
        assert result.data["metadata"]["name"] == "TestBot"
        assert "personality" in result.data
        assert "principles" in result.data
        assert "guardrails" in result.data


# ---------------------------------------------------------------------------
# Personality mode phases (covers lines 192-207, 218-223, 261-296, 300-362,
# 365-426, 430-449)
# ---------------------------------------------------------------------------


class TestPersonalityModes:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @pytest.mark.parametrize("mode", ["ocean", "disc", "hybrid", "custom"])
    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_mode_sets_mode(self, mock_ask, mode):
        mock_ask.return_value = mode
        builder = self._make_builder()
        data: dict = {}
        builder._phase_personality_mode(data)
        assert data["_personality_mode"] == mode

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_dispatches_ocean(self, mock_ask):
        """When mode is ocean, _phase_personality calls _phase_personality_ocean."""
        # 5 OCEAN dimensions (all required, no skip)
        mock_ask.side_effect = ["0.7", "0.8", "0.6", "0.5", "0.3"]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "ocean"}
        builder._phase_personality(data)

        assert "profile" in data["personality"]
        assert data["personality"]["profile"]["mode"] == "ocean"
        assert data["personality"]["profile"]["ocean"]["openness"] == 0.7

    @patch("personanexus.builder.Confirm.ask")
    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_dispatches_disc_preset(self, mock_ask, mock_confirm):
        """When mode is disc with preset, uses a preset."""
        mock_confirm.return_value = True  # use preset
        mock_ask.return_value = "the_analyst"
        builder = self._make_builder()
        data: dict = {"_personality_mode": "disc"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "disc"
        assert data["personality"]["profile"]["disc_preset"] == "the_analyst"
        assert "traits" in data["personality"]

    @patch("personanexus.builder.Confirm.ask")
    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_disc_manual(self, mock_ask, mock_confirm):
        """When mode is disc without preset, collects 4 manual scores."""
        mock_confirm.return_value = False  # don't use preset
        # 4 DISC dimensions
        mock_ask.side_effect = ["0.7", "0.6", "0.5", "0.8"]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "disc"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "disc"
        assert data["personality"]["profile"]["disc"]["dominance"] == 0.7
        assert "traits" in data["personality"]

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_hybrid_ocean_base(self, mock_ask):
        """Hybrid mode with OCEAN base and no overrides."""
        mock_ask.side_effect = [
            "ocean",  # framework choice
            # 5 OCEAN dimensions
            "0.7",
            "0.8",
            "0.6",
            "0.5",
            "0.3",
            # 10 trait overrides (all skipped)
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "hybrid"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "hybrid"
        assert "ocean" in data["personality"]["profile"]
        assert data["personality"]["profile"]["override_priority"] == "explicit_wins"

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_hybrid_disc_base(self, mock_ask):
        """Hybrid mode with DISC base and no overrides."""
        mock_ask.side_effect = [
            "disc",  # framework choice
            # 4 DISC dimensions
            "0.7",
            "0.6",
            "0.5",
            "0.8",
            # 10 trait overrides (all skipped)
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "hybrid"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "hybrid"
        assert "disc" in data["personality"]["profile"]

    @patch("personanexus.builder.Prompt.ask")
    def test_phase_personality_hybrid_with_overrides(self, mock_ask):
        """Hybrid mode with OCEAN base and some trait overrides."""
        mock_ask.side_effect = [
            "ocean",  # framework choice
            # 5 OCEAN dimensions
            "0.7",
            "0.8",
            "0.6",
            "0.5",
            "0.3",
            # 10 trait overrides: override warmth=0.9, skip rest
            "0.9",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
            "",
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "hybrid"}
        builder._phase_personality(data)

        # With an override, traits dict should contain the override
        assert data["personality"]["traits"]["warmth"] == 0.9

    def test_show_computed_traits_preview(self):
        """Verify _show_computed_traits_preview runs without errors."""
        builder = self._make_builder()
        traits = {"warmth": 0.85, "rigor": 0.55, "humor": 0.15, "patience": 0.4}
        # Should not raise
        builder._show_computed_traits_preview(traits)
        # Verify console.print was called (for the table)
        assert builder.console.print.call_count >= 2


# ---------------------------------------------------------------------------
# LLMEnhancer - client & LLM paths (covers lines 630-639, 654, 661, 669-718)
# ---------------------------------------------------------------------------


class TestLLMEnhancerClient:
    def test_get_client_cached(self):
        enhancer = LLMEnhancer(api_key="test_key")
        mock_client = MagicMock()
        enhancer._client = mock_client
        result = enhancer._get_client()
        assert result is mock_client

    def test_get_client_no_api_key(self):
        enhancer = LLMEnhancer(api_key=None)
        # Ensure env var is not set
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": ""}, clear=False):
            enhancer.api_key = None
            result = enhancer._get_client()
            assert result is None

    def test_get_client_success_with_mock_anthropic(self):
        """When anthropic is importable, _get_client returns a client."""
        import sys

        mock_anthropic = MagicMock()
        mock_client = MagicMock()
        mock_anthropic.Anthropic.return_value = mock_client
        sys.modules["anthropic"] = mock_anthropic
        try:
            enhancer = LLMEnhancer(api_key="test_key")
            result = enhancer._get_client()
            assert result is mock_client
        finally:
            del sys.modules["anthropic"]

    def test_enhance_with_api_key_but_no_sdk(self):
        """When API key set but anthropic not installed, falls back to templates."""
        enhancer = LLMEnhancer(api_key="fake_key", console=MagicMock())
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "Bot"},
                "role": {"title": "Helper", "purpose": "Help"},
                "personality": {"traits": {"warmth": 0.5}},
            }
        )
        # _get_client will return None (no anthropic installed)
        result = enhancer.enhance(identity)
        assert isinstance(result, dict)
        assert "personality_notes" in result


class TestLLMEnhancerLLMPath:
    def test_enhance_with_llm_success(self):
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [
            MagicMock(
                text=json.dumps(
                    {
                        "personality_notes": "Test bot is great.",
                        "greeting": "Hi there!",
                        "vocabulary": {
                            "preferred": ["great"],
                            "avoided": ["bad"],
                            "signature_phrases": ["you bet"],
                        },
                        "strategies": {
                            "uncertainty": {"approach": "transparent"},
                            "disagreement": {"approach": "respectful"},
                        },
                    }
                )
            )
        ]
        mock_client.messages.create.return_value = mock_response

        enhancer = LLMEnhancer(api_key="test_key", console=MagicMock())
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "TestBot"},
                "role": {"title": "Helper", "purpose": "Help users"},
                "personality": {"traits": {"warmth": 0.8}},
            }
        )

        result = enhancer._enhance_with_llm(mock_client, identity)
        assert result["personality_notes"] == "Test bot is great."
        assert result["greeting"] == "Hi there!"
        mock_client.messages.create.assert_called_once()

    def test_enhance_with_llm_error_falls_back(self):
        mock_client = MagicMock()
        mock_client.messages.create.side_effect = Exception("API error")

        enhancer = LLMEnhancer(api_key="test_key", console=MagicMock())
        identity = BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "Bot"},
                "role": {"title": "Helper", "purpose": "Help"},
                "personality": {"traits": {"warmth": 0.5}},
            }
        )

        result = enhancer._enhance_with_llm(mock_client, identity)
        # Falls back to templates
        assert isinstance(result, dict)
        assert "personality_notes" in result


# ---------------------------------------------------------------------------
# LLMEnhancer templates - trait-based conditionals (covers lines 733, 737)
# ---------------------------------------------------------------------------


class TestLLMEnhancerTemplates:
    def _make_identity(self, **traits):
        return BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "TestBot"},
                "role": {"title": "Helper", "purpose": "Help users"},
                "personality": {"traits": traits},
            }
        )

    def test_template_low_warmth(self):
        identity = self._make_identity(warmth=0.2, rigor=0.5)
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer._enhance_with_templates(identity)
        assert "reserved" in result["personality_notes"].lower()

    def test_template_high_rigor(self):
        identity = self._make_identity(warmth=0.5, rigor=0.9)
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer._enhance_with_templates(identity)
        notes = result["personality_notes"]
        assert "precision" in notes.lower() or "thoroughness" in notes.lower()

    def test_template_high_humor(self):
        identity = self._make_identity(warmth=0.5, humor=0.7)
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer._enhance_with_templates(identity)
        assert "humor" in result["personality_notes"].lower()

    def test_template_vocabulary_structure(self):
        identity = self._make_identity(warmth=0.5, rigor=0.5)
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer._enhance_with_templates(identity)
        vocab = result["vocabulary"]
        assert "preferred" in vocab
        assert "avoided" in vocab
        assert "signature_phrases" in vocab

    def test_template_strategies_structure(self):
        identity = self._make_identity(warmth=0.5, rigor=0.5)
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer._enhance_with_templates(identity)
        strategies = result["strategies"]
        assert "uncertainty" in strategies
        assert "disagreement" in strategies


# ---------------------------------------------------------------------------
# apply_enhancements interactive path (covers lines 792-830)
# ---------------------------------------------------------------------------


class TestApplyEnhancementsInteractive:
    def _make_identity(self):
        return BuiltIdentity(
            {
                "schema_version": "1.0",
                "metadata": {"name": "TestBot"},
                "personality": {"traits": {"warmth": 0.5}},
            }
        )

    @patch("personanexus.builder.Confirm.ask")
    def test_accept_personality_notes(self, mock_confirm):
        mock_confirm.return_value = True
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.apply_enhancements(
            self._make_identity(),
            {"personality_notes": "Bot is great."},
            interactive=True,
        )
        assert result.data["personality"]["notes"] == "Bot is great."

    @patch("personanexus.builder.Confirm.ask")
    def test_reject_personality_notes(self, mock_confirm):
        mock_confirm.return_value = False
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.apply_enhancements(
            self._make_identity(),
            {"personality_notes": "Bot is great."},
            interactive=True,
        )
        assert "notes" not in result.data["personality"]

    @patch("personanexus.builder.Confirm.ask")
    def test_accept_greeting(self, mock_confirm):
        mock_confirm.return_value = True
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.apply_enhancements(
            self._make_identity(),
            {"greeting": "Hello!"},
            interactive=True,
        )
        assert result.data["metadata"]["greeting"] == "Hello!"

    @patch("personanexus.builder.Confirm.ask")
    def test_accept_vocabulary(self, mock_confirm):
        mock_confirm.return_value = True
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.apply_enhancements(
            self._make_identity(),
            {"vocabulary": {"preferred": ["great"], "avoided": ["bad"], "signature_phrases": []}},
            interactive=True,
        )
        assert result.data["communication"]["vocabulary"]["preferred"] == ["great"]

    @patch("personanexus.builder.Confirm.ask")
    def test_accept_strategies(self, mock_confirm):
        mock_confirm.return_value = True
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.apply_enhancements(
            self._make_identity(),
            {"strategies": {"uncertainty": {"approach": "transparent"}}},
            interactive=True,
        )
        assert result.data["behavior"]["strategies"]["uncertainty"]["approach"] == "transparent"
