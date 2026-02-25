"""Extended tests for the identity builder — covering untested phases."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml

from personanexus.builder import BuiltIdentity, IdentityBuilder

# ---------------------------------------------------------------------------
# BuiltIdentity.from_yaml
# ---------------------------------------------------------------------------


class TestBuiltIdentityFromYaml:
    def test_from_yaml_loads_valid_file(self, tmp_path: Path):
        p = tmp_path / "test.yaml"
        p.write_text(
            yaml.dump({"schema_version": "1.0", "metadata": {"name": "Test"}})
        )
        bi = BuiltIdentity.from_yaml(p)
        assert bi.data["metadata"]["name"] == "Test"

    def test_from_yaml_raises_on_nonexistent(self, tmp_path: Path):
        with pytest.raises(FileNotFoundError):
            BuiltIdentity.from_yaml(tmp_path / "missing.yaml")

    def test_from_yaml_raises_on_non_mapping(self, tmp_path: Path):
        p = tmp_path / "list.yaml"
        p.write_text("- one\n- two\n")
        with pytest.raises(ValueError, match="Expected a YAML mapping"):
            BuiltIdentity.from_yaml(p)


# ---------------------------------------------------------------------------
# Phase 6: Narrative
# ---------------------------------------------------------------------------


class TestPhaseNarrative:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Confirm.ask")
    def test_narrative_skipped_if_declined(self, mock_confirm):
        mock_confirm.return_value = False
        builder = self._make_builder()
        data: dict = {}
        builder._phase_narrative(data)
        assert "narrative" not in data

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_narrative_with_backstory_and_focus(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "A wise old bot.",       # backstory
            "Helping users",         # focus 1
            "Learning new things",   # focus 2
            "",                      # end focus
            "Rudeness",              # pet peeve 1
            "",                      # end peeves
        ]
        builder = self._make_builder()
        data: dict = {}
        builder._phase_narrative(data)

        assert data["narrative"]["backstory"] == "A wise old bot."
        assert data["narrative"]["current_focus"] == ["Helping users", "Learning new things"]
        assert data["narrative"]["pet_peeves"] == ["Rudeness"]

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_narrative_empty_fields_omitted(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "",   # backstory (skip)
            "",   # focus (none)
            "",   # peeves (none)
        ]
        builder = self._make_builder()
        data: dict = {}
        builder._phase_narrative(data)
        # No data entered -> no narrative key
        assert "narrative" not in data


# ---------------------------------------------------------------------------
# Phase 7: Behavioral Modes
# ---------------------------------------------------------------------------


class TestPhaseBehavioralModes:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Confirm.ask")
    def test_behavioral_modes_skipped_if_declined(self, mock_confirm):
        mock_confirm.return_value = False
        builder = self._make_builder()
        data: dict = {}
        builder._phase_behavioral_modes(data)
        assert "behavioral_modes" not in data

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_behavioral_modes_with_entries(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [
            "crisis",           # mode 1 name
            "Emergency mode",   # mode 1 description
            "formal",           # mode 1 register override
            "urgent and clear", # mode 1 tone override
            "casual",           # mode 2 name
            "Relaxed mode",     # mode 2 description
            "",                 # mode 2 register (skip)
            "",                 # mode 2 tone (skip)
            "",                 # end modes
            "crisis",           # default mode choice
        ]
        builder = self._make_builder()
        data: dict = {}
        builder._phase_behavioral_modes(data)

        assert len(data["behavioral_modes"]["modes"]) == 2
        assert data["behavioral_modes"]["default"] == "crisis"
        assert data["behavioral_modes"]["modes"][0]["tone_register"] == "formal"

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_behavioral_modes_empty_list(self, mock_confirm, mock_ask):
        mock_confirm.return_value = True
        mock_ask.side_effect = [""]  # immediately end
        builder = self._make_builder()
        data: dict = {}
        builder._phase_behavioral_modes(data)
        assert "behavioral_modes" not in data


# ---------------------------------------------------------------------------
# Phase 8: Interaction Protocols
# ---------------------------------------------------------------------------


class TestPhaseInteraction:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Confirm.ask")
    def test_interaction_skipped_if_declined(self, mock_confirm):
        mock_confirm.return_value = False
        builder = self._make_builder()
        data: dict = {}
        builder._phase_interaction(data)
        assert "interaction" not in data

    @patch("personanexus.builder.Prompt.ask")
    @patch("personanexus.builder.Confirm.ask")
    def test_interaction_full_setup(self, mock_confirm, mock_ask):
        # Confirm calls: add interaction = True, tone_matching = True
        mock_confirm.side_effect = [True, True]
        mock_ask.side_effect = [
            "Hello there!",     # greeting style
            "Goodbye!",         # farewell style
            "structured",       # handoff style
            "concise",          # status reporting
            "escalate",         # conflict resolution
        ]
        builder = self._make_builder()
        data: dict = {}
        builder._phase_interaction(data)

        assert data["interaction"]["human"]["greeting_style"] == "Hello there!"
        assert data["interaction"]["human"]["farewell_style"] == "Goodbye!"
        assert data["interaction"]["human"]["tone_matching"] is True
        assert data["interaction"]["agent"]["handoff_style"] == "structured"


# ---------------------------------------------------------------------------
# Jungian Personality Mode
# ---------------------------------------------------------------------------


class TestJungianPersonalityMode:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Prompt.ask")
    def test_jungian_by_type_code(self, mock_ask):
        """Path 1: enter a 4-letter type code."""
        mock_ask.side_effect = [
            "1",     # path choice
            "intj",  # type code
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "jungian"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "jungian"
        assert data["personality"]["profile"]["jungian_preset"] == "intj"
        assert "traits" in data["personality"]

    @patch("personanexus.builder.Prompt.ask")
    def test_jungian_manual_dimensions(self, mock_ask):
        """Path 3: enter dimensions manually."""
        mock_ask.side_effect = [
            "3",    # path choice
            "0.7",  # ei
            "0.6",  # sn
            "0.4",  # tf
            "0.3",  # jp
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "jungian"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "jungian"
        assert data["personality"]["profile"]["jungian"]["ei"] == 0.7

    @patch("personanexus.builder.Prompt.ask")
    def test_jungian_role_recommendation(self, mock_ask):
        """Path 2: role-based recommendation."""
        mock_ask.side_effect = [
            "2",    # path choice
            "1",    # category number (first in sorted list)
            "1",    # pick first recommended type
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "jungian"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "jungian"
        assert "jungian_preset" in data["personality"]["profile"]


# ---------------------------------------------------------------------------
# Hybrid personality with Jungian base
# ---------------------------------------------------------------------------


class TestHybridJungian:
    def _make_builder(self):
        return IdentityBuilder(console=MagicMock())

    @patch("personanexus.builder.Prompt.ask")
    def test_hybrid_jungian_base(self, mock_ask):
        """Hybrid mode with jungian base via type code path."""
        mock_ask.side_effect = [
            "jungian",  # base framework choice
            "1",        # jungian input path (type code)
            "enfp",     # type code
            # 10 trait overrides (all skipped)
            "", "", "", "", "", "", "", "", "", "",
        ]
        builder = self._make_builder()
        data: dict = {"_personality_mode": "hybrid"}
        builder._phase_personality(data)

        assert data["personality"]["profile"]["mode"] == "hybrid"
        assert "jungian_preset" in data["personality"]["profile"]
