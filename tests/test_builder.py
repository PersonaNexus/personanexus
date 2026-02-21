"""Tests for the interactive identity builder and LLM enhancer."""

from __future__ import annotations

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
            "TestBot",       # name
            "Test Assistant", # title
            "Help users test things",  # purpose
            "A test bot",    # description
            "testing, QA",   # scope
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
            "0.8",   # warmth
            "",      # verbosity (skip)
            "0.6",   # assertiveness
            "",      # humor (skip)
            "",      # empathy (skip)
            "0.7",   # directness
            "",      # rigor (skip)
            "",      # creativity (skip)
            "",      # epistemic_humility (skip)
            "",      # patience (skip)
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
            "consultative",            # register
            "sparingly",               # emoji
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
            "Python",   # domain name
            "0.9",      # level
            "primary",  # category
            "",         # end loop (domain name empty)
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
    """Tests that invalid input triggers a re-prompt instead of being silently skipped or defaulted."""

    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Prompt.ask")
    def test_personality_reprompts_on_out_of_range(self, mock_ask):
        # First trait: enter 1.5 (rejected), then 0.8 (accepted), then skip the rest
        mock_ask.side_effect = [
            "1.5",   # warmth — out of range, re-prompt
            "0.8",   # warmth — accepted
            "",      # verbosity (skip)
            "0.6",   # assertiveness
            "",      # humor (skip)
            "",      # empathy (skip)
            "0.7",   # directness
            "",      # rigor (skip)
            "",      # creativity (skip)
            "",      # epistemic_humility (skip)
            "",      # patience (skip)
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
            "abc",   # warmth — not a number, re-prompt
            "0.7",   # warmth — accepted
            "",      # verbosity (skip)
            "0.5",   # assertiveness
            "",      # humor (skip)
            "",      # empathy (skip)
            "",      # directness (skip)
            "",      # rigor (skip)
            "",      # creativity (skip)
            "",      # epistemic_humility (skip)
            "",      # patience (skip)
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
            "0.3",   # warmth — accepted
            "0.6",   # verbosity
            "",      # assertiveness (skip)
            "",      # humor (skip)
            "",      # empathy (skip)
            "",      # directness (skip)
            "",      # rigor (skip)
            "",      # creativity (skip)
            "",      # epistemic_humility (skip)
            "",      # patience (skip)
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
            "pirate",                  # register — invalid, re-prompt
            "casual",                  # register — accepted
            "sparingly",               # emoji — accepted
        ]
        builder = self._make_builder()
        data: dict = {"schema_version": "1.0"}
        builder._phase_communication(data)

        assert data["communication"]["tone"]["register"] == "casual"

    @patch("personanexus.builder.Prompt.ask")
    def test_communication_reprompts_bad_emoji(self, mock_ask):
        mock_ask.side_effect = [
            "friendly",    # tone
            "consultative", # register — accepted
            "lots",        # emoji — invalid, re-prompt
            "frequent",    # emoji — accepted
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
            "Python",   # domain name
            "abc",      # level — not a number, re-prompt
            "0.9",      # level — accepted
            "primary",  # category — accepted
            "",         # end loop
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
            "ML",       # domain name
            "1.5",      # level — out of range, re-prompt
            "0.7",      # level — accepted
            "secondary", # category — accepted
            "",          # end loop
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
            "Python",   # domain name
            "0.9",      # level — accepted
            "main",     # category — invalid, re-prompt
            "primary",  # category — accepted
            "",         # end loop
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
            "Python",   # domain name
            "",         # level — empty, re-prompt (required)
            "0.8",      # level — accepted
            "primary",  # category — accepted
            "",         # end loop
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
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "TestBot"},
            "role": {"title": "Helper", "purpose": "Help users"},
            "personality": {"traits": {"warmth": 0.8, "rigor": 0.7}},
        })
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "personality_notes" in result
        assert "greeting" in result
        assert "vocabulary" in result
        assert "strategies" in result

    def test_personality_notes_reference_agent_role(self):
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "DataBot"},
            "role": {"title": "Data Analyst", "purpose": "Analyze data"},
            "personality": {"traits": {"warmth": 0.5, "rigor": 0.9}},
        })
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "DataBot" in result["personality_notes"]
        assert "Data Analyst" in result["personality_notes"]

    def test_greeting_includes_agent_name(self):
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "Ada"},
            "role": {"title": "Analyst", "purpose": "Analyze things"},
            "personality": {"traits": {"warmth": 0.7, "rigor": 0.8}},
        })
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "Ada" in result["greeting"]

    def test_template_high_warmth_notes(self):
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "WarmBot"},
            "role": {"title": "Helper", "purpose": "Help"},
            "personality": {"traits": {"warmth": 0.9, "rigor": 0.5}},
        })
        enhancer = LLMEnhancer(api_key=None)
        result = enhancer.enhance(identity)

        assert "warmth" in result["personality_notes"].lower()

    def test_apply_enhancements_non_interactive(self):
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "TestBot"},
            "role": {"title": "Helper", "purpose": "Help"},
            "personality": {"traits": {"warmth": 0.7, "rigor": 0.5}},
            "communication": {"tone": {"default": "friendly"}},
        })
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
        identity = BuiltIdentity({
            "schema_version": "1.0",
            "metadata": {"name": "Bot"},
            "role": {"title": "Helper", "purpose": "Help"},
            "personality": {"traits": {"warmth": 0.5, "rigor": 0.5}},
        })
        enhancer = LLMEnhancer(api_key=None, console=MagicMock())
        result = enhancer.enhance(identity)

        # Should still produce valid output via templates
        assert isinstance(result["personality_notes"], str)
        assert isinstance(result["greeting"], str)
