"""Tests for LangChain, CrewAI, and AutoGen compile targets."""

from __future__ import annotations

import json

import pytest
import yaml

from personanexus.compiler import (
    AutoGenCompiler,
    CrewAICompiler,
    LangChainCompiler,
    SystemPromptCompiler,
    compile_identity,
)
from personanexus.resolver import IdentityResolver


@pytest.fixture
def resolver(examples_dir):
    return IdentityResolver(search_paths=[examples_dir])


@pytest.fixture
def mira_identity(resolver, mira_path):
    return resolver.resolve_file(mira_path)


@pytest.fixture
def minimal_identity(resolver, minimal_path):
    return resolver.resolve_file(minimal_path)


@pytest.fixture
def prompt_compiler():
    return SystemPromptCompiler()


# ---------------------------------------------------------------------------
# LangChain target
# ---------------------------------------------------------------------------


class TestLangChainCompiler:
    def test_compile_returns_dict(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result, dict)

    def test_required_keys_present(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert "agent_type" in result
        assert "system_message" in result
        assert "name" in result
        assert "description" in result
        assert "tools" in result
        assert "verbose" in result
        assert "metadata" in result

    def test_agent_type_is_conversational(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert result["agent_type"] == "conversational"

    def test_name_matches_identity(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert result["name"] == mira_identity.metadata.name

    def test_description_matches_identity(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert result["description"] == mira_identity.metadata.description

    def test_tools_is_empty_list(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert result["tools"] == []

    def test_verbose_is_true(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert result["verbose"] is True

    def test_system_message_is_nonempty_string(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result["system_message"], str)
        assert len(result["system_message"]) > 0

    def test_metadata_contains_required_fields(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        meta = result["metadata"]
        assert meta["personanexus_id"] == mira_identity.metadata.id
        assert meta["personanexus_version"] == mira_identity.metadata.version
        assert meta["personality_mode"] == mira_identity.personality.profile.mode.value

    def test_result_is_json_serializable(self, mira_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(mira_identity)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_compile_identity_langchain_target(self, mira_identity):
        result = compile_identity(mira_identity, target="langchain")
        assert isinstance(result, dict)
        assert result["agent_type"] == "conversational"

    def test_minimal_identity(self, minimal_identity):
        compiler = LangChainCompiler()
        result = compiler.compile(minimal_identity)
        assert result["name"] == minimal_identity.metadata.name
        assert result["agent_type"] == "conversational"


# ---------------------------------------------------------------------------
# CrewAI target
# ---------------------------------------------------------------------------


class TestCrewAICompiler:
    def test_compile_returns_string(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result, str)

    def test_output_is_valid_yaml(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed, dict)

    def test_agent_key_present(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert "agent" in parsed

    def test_role_matches_identity(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["role"] == mira_identity.role.title

    def test_goal_matches_purpose(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["goal"] == mira_identity.role.purpose

    def test_backstory_is_nonempty(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed["agent"]["backstory"], str)
        assert len(parsed["agent"]["backstory"]) > 0

    def test_verbose_is_true(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["verbose"] is True

    def test_tools_is_empty_list(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["tools"] == []

    def test_allow_delegation_is_boolean(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert isinstance(parsed["agent"]["allow_delegation"], bool)

    def test_metadata_contains_personanexus_id(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["metadata"]["personanexus_id"] == mira_identity.metadata.id

    def test_compile_identity_crewai_target(self, mira_identity):
        result = compile_identity(mira_identity, target="crewai")
        assert isinstance(result, str)
        parsed = yaml.safe_load(result)
        assert "agent" in parsed

    def test_minimal_identity(self, minimal_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(minimal_identity)
        parsed = yaml.safe_load(result)
        assert parsed["agent"]["role"] == minimal_identity.role.title

    def test_backstory_includes_personality_traits(self, mira_identity):
        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        parsed = yaml.safe_load(result)
        backstory = parsed["agent"]["backstory"].lower()
        # Mira has high rigor (0.9), so backstory should mention rigorous
        assert "rigorous" in backstory or "you are" in backstory


# ---------------------------------------------------------------------------
# AutoGen target
# ---------------------------------------------------------------------------


class TestAutoGenCompiler:
    def test_compile_returns_dict(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result, dict)

    def test_required_keys_present(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert "name" in result
        assert "system_message" in result
        assert "human_input_mode" in result
        assert "description" in result
        assert "metadata" in result

    def test_name_matches_identity(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert result["name"] == mira_identity.metadata.name

    def test_human_input_mode_is_never(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert result["human_input_mode"] == "NEVER"

    def test_description_matches_identity(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert result["description"] == mira_identity.metadata.description

    def test_system_message_is_nonempty_string(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result["system_message"], str)
        assert len(result["system_message"]) > 0

    def test_metadata_contains_required_fields(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        meta = result["metadata"]
        assert meta["personanexus_id"] == mira_identity.metadata.id
        assert meta["personanexus_version"] == mira_identity.metadata.version

    def test_result_is_json_serializable(self, mira_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        serialized = json.dumps(result)
        assert isinstance(serialized, str)

    def test_compile_identity_autogen_target(self, mira_identity):
        result = compile_identity(mira_identity, target="autogen")
        assert isinstance(result, dict)
        assert result["human_input_mode"] == "NEVER"

    def test_minimal_identity(self, minimal_identity):
        compiler = AutoGenCompiler()
        result = compiler.compile(minimal_identity)
        assert result["name"] == minimal_identity.metadata.name
        assert result["human_input_mode"] == "NEVER"


# ---------------------------------------------------------------------------
# Cross-target tests
# ---------------------------------------------------------------------------


class TestCompileTargetConsistency:
    """Verify consistency across all three new targets for the same identity."""

    def test_all_targets_use_same_agent_name(self, mira_identity):
        lc = LangChainCompiler().compile(mira_identity)
        ag = AutoGenCompiler().compile(mira_identity)
        cr_parsed = yaml.safe_load(CrewAICompiler().compile(mira_identity))

        expected_name = mira_identity.metadata.name
        assert lc["name"] == expected_name
        assert ag["name"] == expected_name
        # CrewAI uses role title, not name, so we check role
        assert cr_parsed["agent"]["role"] == mira_identity.role.title

    def test_all_targets_include_personanexus_id(self, mira_identity):
        lc = LangChainCompiler().compile(mira_identity)
        ag = AutoGenCompiler().compile(mira_identity)
        cr_parsed = yaml.safe_load(CrewAICompiler().compile(mira_identity))

        expected_id = mira_identity.metadata.id
        assert lc["metadata"]["personanexus_id"] == expected_id
        assert ag["metadata"]["personanexus_id"] == expected_id
        assert cr_parsed["agent"]["metadata"]["personanexus_id"] == expected_id

    def test_compile_identity_routes_all_targets(self, mira_identity):
        """All three targets should be routable via compile_identity."""
        lc_result = compile_identity(mira_identity, target="langchain")
        cr_result = compile_identity(mira_identity, target="crewai")
        ag_result = compile_identity(mira_identity, target="autogen")

        assert isinstance(lc_result, dict)
        assert isinstance(cr_result, str)
        assert isinstance(ag_result, dict)

    def test_unknown_target_raises_error(self, mira_identity):
        from personanexus.compiler import CompilerError

        with pytest.raises(CompilerError, match="Unknown target format"):
            compile_identity(mira_identity, target="nonexistent")
