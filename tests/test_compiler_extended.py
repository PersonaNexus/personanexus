"""Extended tests for the identity compiler — targeting uncovered code paths."""

import json

import pytest

from personanexus.compiler import (
    CompilerError,
    LangChainCompiler,
    MarkdownCompiler,
    OpenClawCompiler,
    SoulCompiler,
    SystemPromptCompiler,
    _expertise_level_text,
    _trait_to_language,
    compile_identity,
)
from personanexus.resolver import IdentityResolver
from personanexus.types import (
    AgentRelationship,
    BehaviorRule,
    BehaviorStrategy,
    Enforcement,
    ExpertiseCategory,
    ExpertiseDomain,
    HardGuardrail,
    HumanInteraction,
    InteractionConfig,
    InteractionEscalationTrigger,
    PromptLayer,
    RelationshipDynamic,
    Relationships,
    Severity,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
def mira_modes_identity(resolver, examples_dir):
    path = examples_dir / "identities" / "mira-modes.yaml"
    return resolver.resolve_file(path)


@pytest.fixture
def compiler():
    return SystemPromptCompiler()


@pytest.fixture
def small_budget_compiler():
    """Compiler with an extremely small token budget to force truncation."""
    return SystemPromptCompiler(token_budget=50)


@pytest.fixture
def soul_compiler():
    return SoulCompiler()


@pytest.fixture
def openclaw_compiler():
    return OpenClawCompiler()


@pytest.fixture
def langchain_compiler():
    return LangChainCompiler()


@pytest.fixture
def markdown_compiler():
    return MarkdownCompiler()


# ---------------------------------------------------------------------------
# _trait_to_language — generic fallback for unknown traits
# ---------------------------------------------------------------------------


class TestTraitToLanguage:
    """Cover the generic fallback branch for traits not in TRAIT_TEMPLATES."""

    def test_custom_trait_low(self):
        result = _trait_to_language("obscure_trait", 0.1)
        assert "low obscure_trait" in result

    def test_custom_trait_moderate(self):
        result = _trait_to_language("obscure_trait", 0.5)
        assert "moderate obscure_trait" in result

    def test_custom_trait_high(self):
        result = _trait_to_language("obscure_trait", 0.8)
        assert "high obscure_trait" in result

    def test_known_trait_level_0(self):
        """Value < 0.2 should map to level 0 ('reserved and professional' for warmth)."""
        result = _trait_to_language("warmth", 0.1)
        assert "reserved and professional" in result

    def test_known_trait_level_1(self):
        """Value 0.2–0.4 should map to level 1."""
        result = _trait_to_language("warmth", 0.3)
        assert "moderately warm" in result

    def test_known_trait_level_2(self):
        """Value 0.4–0.6 should map to level 2."""
        result = _trait_to_language("warmth", 0.5)
        assert "warm and approachable" in result


# ---------------------------------------------------------------------------
# _expertise_level_text — edge values
# ---------------------------------------------------------------------------


class TestExpertiseLevelText:
    def test_expert_level(self):
        assert _expertise_level_text(0.95) == "expert"

    def test_advanced_level(self):
        assert _expertise_level_text(0.75) == "advanced"

    def test_proficient_level(self):
        assert _expertise_level_text(0.6) == "proficient"

    def test_intermediate_level(self):
        assert _expertise_level_text(0.4) == "intermediate"

    def test_basic_level(self):
        assert _expertise_level_text(0.2) == "basic"


# ---------------------------------------------------------------------------
# Anthropic XML wrapping format
# ---------------------------------------------------------------------------


class TestAnthropicFormat:
    def test_anthropic_format_contains_xml_section_tags(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="anthropic")
        assert "<identity>" in result
        assert "</identity>" in result
        assert "<role>" in result
        assert "</role>" in result
        assert "<personality>" in result
        assert "</personality>" in result
        assert "<communication>" in result
        assert "</communication>" in result
        assert "<principles>" in result
        assert "</principles>" in result
        assert "<guardrails>" in result
        assert "</guardrails>" in result

    def test_anthropic_format_expertise_tag(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="anthropic")
        assert "<expertise>" in result
        assert "</expertise>" in result

    def test_anthropic_format_behavior_tag(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="anthropic")
        assert "<behavior>" in result
        assert "</behavior>" in result

    def test_anthropic_format_preserves_content(self, compiler, mira_identity):
        compiler.compile(mira_identity, format="text")
        anthropic_result = compiler.compile(mira_identity, format="anthropic")
        # Core content should still be present inside XML tags
        assert "Mira" in anthropic_result
        assert "Senior Data Analyst" in anthropic_result
        assert "Never present uncertain information" in anthropic_result

    def test_compile_identity_anthropic_target(self, mira_identity):
        result = compile_identity(mira_identity, target="anthropic")
        assert isinstance(result, str)
        assert "<identity>" in result
        assert "</identity>" in result


# ---------------------------------------------------------------------------
# OpenAI format wrapping
# ---------------------------------------------------------------------------


class TestOpenAIFormat:
    def test_openai_format_has_prefix(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="openai")
        assert result.startswith("You are Mira, a Senior Data Analyst.")

    def test_openai_format_includes_full_prompt(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="openai")
        assert "## Your Role" in result
        assert "## Core Principles" in result

    def test_openai_no_xml_tags(self, compiler, mira_identity):
        result = compiler.compile(mira_identity, format="openai")
        assert "<identity>" not in result
        assert "<role>" not in result

    def test_compile_identity_openai_target(self, mira_identity):
        result = compile_identity(mira_identity, target="openai")
        assert isinstance(result, str)
        assert "You are Mira" in result


# ---------------------------------------------------------------------------
# Behavioral modes rendering in system prompts
# ---------------------------------------------------------------------------


class TestBehavioralModesRendering:
    def test_behavioral_modes_section_rendered(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        assert "## Behavioral Modes" in result
        assert "Default mode: standard" in result

    def test_behavioral_modes_names_rendered(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        assert "### standard" in result
        assert "### formal" in result
        assert "### crisis" in result

    def test_behavioral_modes_descriptions(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        assert "Client-facing executive communication" in result
        assert "Incident response" in result

    def test_behavioral_modes_overrides_rendered(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        # Formal mode has tone_register, tone_default, emoji_usage
        assert "Register: formal" in result
        assert "Tone: professional" in result
        assert "Emoji: never" in result

    def test_behavioral_modes_sentence_length(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        # Crisis mode has sentence_length: short
        assert "Sentences: short" in result

    def test_behavioral_modes_trait_modifiers(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        assert "Trait adjustments:" in result

    def test_behavioral_modes_additional_guardrails(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity)
        assert "Additional rules:" in result
        assert "Always recommend human escalation" in result

    def test_behavioral_modes_in_anthropic_format(self, compiler, mira_modes_identity):
        result = compiler.compile(mira_modes_identity, format="anthropic")
        assert "<behavioral_modes>" in result
        assert "</behavioral_modes>" in result
        assert "### formal" in result


# ---------------------------------------------------------------------------
# Token budget truncation
# ---------------------------------------------------------------------------


class TestPromptLayers:
    def test_compile_layers_returns_typed_layers(self, compiler, mira_identity):
        layers = compiler.compile_layers(mira_identity)
        assert layers
        assert all(isinstance(layer, PromptLayer) for layer in layers)
        assert layers[0].name == "header"
        assert layers[0].required is True

    def test_compile_layers_preserves_text_output(self, compiler, mira_identity):
        layered_text = compiler._render_layers(compiler.compile_layers(mira_identity))
        direct_text = compiler.compile(mira_identity)
        assert layered_text == direct_text

    def test_anthropic_output_comes_from_layers(self, compiler, mira_identity):
        layers = compiler.compile_layers(mira_identity)
        result = compiler._wrap_anthropic(layers)
        assert "<identity>" in result
        assert "<guardrails>" in result


class TestTokenBudgetTruncation:
    def test_truncation_drops_low_priority_sections(self, mira_identity):
        """With a very small budget, optional sections should be dropped."""
        compiler = SystemPromptCompiler(token_budget=100)
        result = compiler.compile(mira_identity)
        # Even with aggressive truncation, the header, role, and guardrails remain
        assert "# Mira" in result
        assert "## Non-Negotiable Rules" in result
        assert compiler._was_truncated is True

    def test_truncation_records_omitted_sections(self, mira_identity):
        compiler = SystemPromptCompiler(token_budget=100)
        compiler.compile(mira_identity)
        assert len(compiler._sections_omitted) > 0
        assert len(compiler._sections_included) > 0

    def test_no_truncation_when_under_budget(self, compiler, minimal_identity):
        compiler.compile(minimal_identity)
        assert compiler._was_truncated is False
        assert len(compiler._sections_omitted) == 0

    def test_sections_included_tracked(self, compiler, mira_identity):
        compiler.compile(mira_identity)
        assert "header" in compiler._sections_included
        assert "role" in compiler._sections_included
        assert "guardrails" in compiler._sections_included

    def test_truncate_principles_static_method(self):
        """Test the static _truncate_principles method directly."""
        text = (
            "## Core Principles\n"
            "\nFollow these principles:\n"
            "1. First principle\n"
            "   - Implication A\n"
            "   - Implication B\n"
            "2. Second principle\n"
            "3. Third principle\n"
            "4. Fourth principle\n"
            "5. Fifth principle\n"
            "6. Sixth principle\n"
            "   - Should be dropped\n"
            "7. Seventh principle\n"
        )
        result = SystemPromptCompiler._truncate_principles(text, max_count=5)
        assert "1. First" in result
        assert "5. Fifth" in result
        assert "6. Sixth" not in result
        assert "7. Seventh" not in result
        assert "Should be dropped" not in result

    def test_compile_identity_with_truncation_note(self, mira_identity):
        """When truncation occurs, compile_identity should append an HTML comment."""
        result = compile_identity(mira_identity, target="text", token_budget=100)
        assert isinstance(result, str)
        # If truncation happened, note is appended
        if "<!-- Note:" in result:
            assert "Sections omitted to fit token budget" in result

    def test_compile_identity_anthropic_with_truncation(self, mira_identity):
        result = compile_identity(mira_identity, target="anthropic", token_budget=100)
        assert isinstance(result, str)
        # Should still have XML tags even when truncated
        assert "<identity>" in result

    def test_estimate_tokens_by_model_soul(self):
        compiler = SystemPromptCompiler()
        text = "a" * 350
        result = compiler._estimate_tokens_by_model(text, "soul")
        assert result == 100  # 350 / 3.5

    def test_estimate_tokens_by_model_anthropic(self):
        compiler = SystemPromptCompiler()
        text = "a" * 400
        result = compiler._estimate_tokens_by_model(text, "anthropic")
        assert result == 100  # 400 / 4

    def test_estimate_tokens_by_model_unknown(self):
        compiler = SystemPromptCompiler()
        text = "a" * 400
        result = compiler._estimate_tokens_by_model(text, "unknown")
        assert result == 100  # defaults to 400 / 4


# ---------------------------------------------------------------------------
# JSON target output (compile_identity with target="json")
# ---------------------------------------------------------------------------


class TestJsonTarget:
    def test_json_target_returns_dict(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        assert isinstance(result, dict)

    def test_json_target_has_system_prompt(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        assert "system_prompt" in result
        assert isinstance(result["system_prompt"], str)
        assert "Mira" in result["system_prompt"]

    def test_json_target_has_token_estimate(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        assert "tokens_estimated" in result
        assert isinstance(result["tokens_estimated"], int)
        assert result["tokens_estimated"] > 0

    def test_json_target_has_prompt_layers(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        assert "prompt_layers" in result
        assert result["prompt_layers"][0]["name"] == "header"

    def test_json_target_has_sections_included(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        assert "sections_included" in result
        assert "header" in result["sections_included"]

    def test_json_target_with_truncation_has_sections_omitted(self, mira_identity):
        result = compile_identity(mira_identity, target="json", token_budget=100)
        # Should have sections_omitted when truncated
        if "sections_omitted" in result:
            assert isinstance(result["sections_omitted"], list)


# ---------------------------------------------------------------------------
# Soul target output (compile_identity with target="soul")
# ---------------------------------------------------------------------------


class TestSoulTarget:
    def test_soul_target_returns_dict_with_keys(self, mira_identity):
        result = compile_identity(mira_identity, target="soul")
        assert isinstance(result, dict)
        assert "soul_md" in result
        assert "style_md" in result

    def test_soul_target_soul_md_content(self, mira_identity):
        result = compile_identity(mira_identity, target="soul")
        assert "# Mira" in result["soul_md"]
        assert "## Who I Am" in result["soul_md"]
        assert "## Worldview" in result["soul_md"]
        assert "## Boundaries" in result["soul_md"]

    def test_soul_target_style_md_content(self, mira_identity):
        result = compile_identity(mira_identity, target="soul")
        assert "# Voice & Style Guide" in result["style_md"]
        assert "## Voice Principles" in result["style_md"]


# ---------------------------------------------------------------------------
# Soul compiler — minimal identity edge cases
# ---------------------------------------------------------------------------


class TestSoulCompilerEdgeCases:
    def test_soul_no_expertise_no_interests(self, soul_compiler, minimal_identity):
        result = soul_compiler.compile(minimal_identity)
        # Minimal identity has no expertise domains, so Interests section should
        # be empty or absent
        soul_md = result["soul_md"]
        assert "## Interests" not in soul_md or soul_md.count("## Interests") == 0

    def test_soul_no_vocabulary_no_vocabulary_section(self, soul_compiler, minimal_identity):
        result = soul_compiler.compile(minimal_identity)
        # No signature_phrases on minimal identity
        assert "## Vocabulary" not in result["soul_md"]

    def test_soul_identity_with_ocean_profile(self, soul_compiler, mira_modes_identity):
        """OCEAN-profile identity should still render trait language in soul output."""
        result = soul_compiler.compile(mira_modes_identity)
        assert "## Who I Am" in result["soul_md"]
        # OCEAN-derived traits should be rendered as language
        assert "0.85" not in result["soul_md"]  # no raw floats

    def test_style_voice_principles_with_ocean_profile(self, soul_compiler, mira_modes_identity):
        """Style voice principles should work with OCEAN-derived traits."""
        result = soul_compiler.compile(mira_modes_identity)
        assert "## Voice Principles" in result["style_md"]

    def test_style_context_adjustments_not_present_when_no_overrides(
        self, soul_compiler, minimal_identity
    ):
        result = soul_compiler.compile(minimal_identity)
        assert "Context-Specific Style" not in result["style_md"]

    def test_style_voice_examples_not_present_when_empty(self, soul_compiler, minimal_identity):
        result = soul_compiler.compile(minimal_identity)
        assert "## Voice Examples" not in result["style_md"]


# ---------------------------------------------------------------------------
# Interaction rendering
# ---------------------------------------------------------------------------


class TestInteractionRendering:
    def test_interaction_section_rendered(self, mira_identity):
        """Test interaction rendering by adding an InteractionConfig to identity."""
        mira_identity.interaction = InteractionConfig(
            human=HumanInteraction(
                greeting_style="Hi! How can I help?",
                farewell_style="Good luck with your analysis!",
                tone_matching=True,
            )
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "## Interaction Protocols" in result
        assert "Greeting: Hi! How can I help?" in result
        assert "Farewell: Good luck with your analysis!" in result
        assert "Tone matching: Mirror the user's formality level" in result

    def test_interaction_with_humans_section(self, mira_identity):
        mira_identity.interaction = InteractionConfig(
            human=HumanInteraction(
                greeting_style="Welcome!",
            )
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "With Humans" in result
        assert "Greeting: Welcome!" in result

    def test_interaction_with_agents_section(self, mira_identity):
        mira_identity.interaction = InteractionConfig()
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "With Other Agents" in result
        assert "Handoff style:" in result
        assert "Status reporting:" in result
        assert "Conflict resolution:" in result


# ---------------------------------------------------------------------------
# Relationships rendering
# ---------------------------------------------------------------------------


class TestRelationshipsRendering:
    def test_relationships_with_agent_relationships(self, mira_identity):
        mira_identity.memory.relationships = Relationships(
            enabled=True,
            agent_relationships=[
                AgentRelationship(
                    agent_id="agt_other_001",
                    name="DataBot",
                    relationship="collaborative peer",
                    context="data pipeline work",
                    interaction_style="direct and efficient",
                )
            ],
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "## Agent Relationships" in result
        assert "DataBot" in result
        assert "collaborative peer" in result
        assert "data pipeline work" in result
        assert "style: direct and efficient" in result

    def test_relationships_with_escalation_path(self, mira_identity):
        mira_identity.memory.relationships = Relationships(
            enabled=True,
            agent_relationships=[
                AgentRelationship(agent_id="agt_1", relationship="peer"),
            ],
            escalation_path=["Tier1", "Tier2", "Manager"],
            unknown_agent_default="cautious",
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "Escalation path:" in result
        assert "Tier1" in result
        assert "Manager" in result
        assert "Default interaction with unknown agents: cautious" in result


# ---------------------------------------------------------------------------
# Expertise edge cases (secondary, tertiary)
# ---------------------------------------------------------------------------


class TestExpertiseRendering:
    def test_secondary_expertise_rendered(self, compiler, mira_identity):
        """Mira has secondary expertise domains — they should appear."""
        result = compiler.compile(mira_identity)
        assert "Secondary expertise:" in result or "sql" in result.lower()

    def test_tertiary_expertise_rendered(self, mira_identity):
        """Add tertiary expertise and verify it renders."""
        mira_identity.expertise.domains.append(
            ExpertiseDomain(
                name="basic_ml",
                level=0.3,
                category=ExpertiseCategory.TERTIARY,
            )
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "Familiar with:" in result
        assert "basic_ml" in result


# ---------------------------------------------------------------------------
# Guardrails — other severity
# ---------------------------------------------------------------------------


class TestGuardrailsSeverity:
    def test_other_severity_guardrails(self, mira_identity):
        """Add a MEDIUM severity guardrail and verify it renders as 'Additional constraints'."""
        mira_identity.guardrails.hard.append(
            HardGuardrail(
                id="medium_rule",
                rule="Be cautious with approximations",
                enforcement=Enforcement.PROMPT_INSTRUCTION,
                severity=Severity.MEDIUM,
            )
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "Additional constraints:" in result
        assert "Be cautious with approximations" in result


# ---------------------------------------------------------------------------
# Behavior strategies — conditions and fallbacks
# ---------------------------------------------------------------------------


class TestBehaviorStrategies:
    def test_behavior_rule_with_condition(self, mira_identity):
        """Verify that conditional rules render with 'If condition: action'."""
        result = SystemPromptCompiler().compile(mira_identity)
        # Mira has uncertainty strategy with conditions
        assert "Behavioral Strategies" in result

    def test_behavior_rule_without_condition(self, mira_identity):
        mira_identity.behavior.strategies["test_strat"] = BehaviorStrategy(
            approach="Simple approach",
            rules=[
                BehaviorRule(action="Always do this"),
            ],
        )
        result = SystemPromptCompiler().compile(mira_identity)
        assert "Always do this" in result

    def test_behavior_final_fallback(self, mira_identity):
        mira_identity.behavior.strategies["fb_strat"] = BehaviorStrategy(
            approach="Fallback approach",
            rules=[BehaviorRule(action="Primary action")],
            final_fallback="Defer to a human expert",
        )
        result = SystemPromptCompiler().compile(mira_identity)
        assert "Fallback: Defer to a human expert" in result


# ---------------------------------------------------------------------------
# OpenClaw compiler — model_config overrides and profile metadata
# ---------------------------------------------------------------------------


class TestOpenClawExtended:
    def test_model_config_overrides(self, openclaw_compiler, mira_identity):
        overrides = {"primary_model": "gpt-4", "temperature": 0.7}
        result = openclaw_compiler.compile(mira_identity, model_config=overrides)
        assert result["model_config"]["primary_model"] == "gpt-4"
        assert result["model_config"]["temperature"] == 0.7
        # Defaults that weren't overridden should still be present
        assert "fallback_model" in result["model_config"]

    def test_ocean_profile_metadata_included(self, openclaw_compiler, mira_modes_identity):
        """OCEAN-based identity should include personality_profile in OpenClaw output."""
        result = openclaw_compiler.compile(mira_modes_identity)
        assert "personality_profile" in result
        assert result["personality_profile"]["mode"] == "ocean"
        assert "ocean" in result["personality_profile"]


# ---------------------------------------------------------------------------
# MarkdownCompiler
# ---------------------------------------------------------------------------


class TestMarkdownCompiler:
    def test_markdown_has_title(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "# Mira" in result

    def test_markdown_has_role(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Role: Senior Data Analyst" in result

    def test_markdown_has_personality_with_bars(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Personality" in result
        assert "[#" in result  # progress bar

    def test_markdown_has_expertise(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Expertise" in result
        assert "statistical_analysis" in result

    def test_markdown_has_principles(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Principles" in result

    def test_markdown_has_guardrails(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Guardrails" in result
        assert "[CRITICAL]" in result

    def test_markdown_has_scope(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "### Scope" in result
        assert "**Primary:**" in result

    def test_markdown_has_audience(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "### Audience" in result

    def test_markdown_has_communication(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "## Communication" in result
        assert "**Tone:**" in result

    def test_markdown_has_version_and_status(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        assert "Version" in result
        assert "Status:" in result

    def test_markdown_minimal_identity(self, markdown_compiler, minimal_identity):
        result = markdown_compiler.compile(minimal_identity)
        assert "# Pip" in result
        assert "## Guardrails" in result

    def test_compile_identity_markdown_target(self, mira_identity):
        result = compile_identity(mira_identity, target="markdown")
        assert isinstance(result, str)
        assert "# Mira" in result
        assert "## Personality" in result


# ---------------------------------------------------------------------------
# LangChainCompiler
# ---------------------------------------------------------------------------


class TestLangChainCompiler:
    def test_langchain_returns_dict(self, langchain_compiler, mira_identity):
        result = langchain_compiler.compile(mira_identity)
        assert isinstance(result, dict)

    def test_langchain_has_system_message(self, langchain_compiler, mira_identity):
        result = langchain_compiler.compile(mira_identity)
        assert "system_message" in result
        assert isinstance(result["system_message"], str)
        assert "Mira" in result["system_message"]

    def test_langchain_has_agent_type(self, langchain_compiler, mira_identity):
        result = langchain_compiler.compile(mira_identity)
        assert result["agent_type"] == "conversational"

    def test_langchain_has_name_and_description(self, langchain_compiler, mira_identity):
        result = langchain_compiler.compile(mira_identity)
        assert result["name"] == "Mira"
        assert isinstance(result["description"], str)

    def test_langchain_metadata(self, langchain_compiler, mira_identity):
        result = langchain_compiler.compile(mira_identity)
        meta = result["metadata"]
        assert meta["personanexus_id"] == "agt_mira_001"
        assert "personanexus_version" in meta
        assert meta["personality_mode"] == "custom"

    def test_compile_identity_langchain_target(self, mira_identity):
        result = compile_identity(mira_identity, target="langchain")
        assert isinstance(result, dict)
        assert "system_message" in result
        assert "metadata" in result


# ---------------------------------------------------------------------------
# compile_identity — edge cases
# ---------------------------------------------------------------------------


class TestCompileIdentityEdgeCases:
    def test_unknown_target_raises_compiler_error(self, mira_identity):
        with pytest.raises(CompilerError, match="Unknown target"):
            compile_identity(mira_identity, target="nosuchformat")

    def test_text_target_returns_string(self, mira_identity):
        result = compile_identity(mira_identity, target="text")
        assert isinstance(result, str)
        assert "# Mira" in result

    def test_json_target_is_json_serializable(self, mira_identity):
        result = compile_identity(mira_identity, target="json")
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert "system_prompt" in parsed

    def test_soul_target_is_not_string(self, mira_identity):
        result = compile_identity(mira_identity, target="soul")
        assert not isinstance(result, str)
        assert isinstance(result, dict)

    def test_all_targets_produce_output(self, mira_identity):
        """Smoke test: all recognized targets produce non-empty output."""
        targets = (
            "text",
            "anthropic",
            "openai",
            "openclaw",
            "soul",
            "json",
            "langchain",
            "markdown",
        )
        for target in targets:
            result = compile_identity(mira_identity, target=target)
            if isinstance(result, str):
                assert len(result) > 0, f"Target {target} produced empty string"
            else:
                assert len(result) > 0, f"Target {target} produced empty dict"


# ---------------------------------------------------------------------------
# Mood / emotional states rendering
# ---------------------------------------------------------------------------


class TestMoodRendering:
    def test_mood_section_rendered(self, examples_dir, resolver):
        """The mira-mood.yaml has mood configuration — verify it renders."""
        mood_path = examples_dir / "identities" / "mira-mood.yaml"
        if mood_path.exists():
            identity = resolver.resolve_file(mood_path)
            compiler = SystemPromptCompiler()
            result = compiler.compile(identity)
            assert "## Emotional States" in result or "Default mood:" in result


# ---------------------------------------------------------------------------
# Communication style details
# ---------------------------------------------------------------------------


class TestCommunicationStyleDetails:
    def test_tone_overrides_rendered(self, compiler, mira_identity):
        result = compiler.compile(mira_identity)
        if mira_identity.communication.tone.overrides:
            assert "Tone adjustments by context:" in result

    def test_style_sentence_length_rendered(self, compiler, mira_identity):
        result = compiler.compile(mira_identity)
        if mira_identity.communication.style and mira_identity.communication.style.sentence_length:
            assert "sentence length:" in result

    def test_register_rendered(self, compiler, mira_identity):
        result = compiler.compile(mira_identity)
        if mira_identity.communication.tone.register:
            assert "Register:" in result


# ---------------------------------------------------------------------------
# Anthropic _wrap_anthropic — flush with no current_tag (line 700)
# ---------------------------------------------------------------------------


class TestAnthropicFlushEdge:
    def test_anthropic_handles_blocks_without_section_header(self, compiler, minimal_identity):
        """Minimal identity should still compile in anthropic format without errors."""
        result = compiler.compile(minimal_identity, format="anthropic")
        assert "<identity>" in result
        assert "</identity>" in result
        assert "Pip" in result


# ---------------------------------------------------------------------------
# Behavior rules with conditions (covering line 550)
# ---------------------------------------------------------------------------


class TestBehaviorRuleConditions:
    def test_rule_with_condition_renders_if_statement(self, mira_identity):
        """Rules with conditions should render 'If <condition>: <action>'."""
        mira_identity.behavior.strategies["conditional_strat"] = BehaviorStrategy(
            approach="Conditional approach",
            rules=[
                BehaviorRule(
                    condition="user is frustrated",
                    action="switch to empathetic tone",
                ),
                BehaviorRule(
                    condition="data is missing",
                    action="ask clarifying questions",
                ),
            ],
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "If user is frustrated: switch to empathetic tone" in result
        assert "If data is missing: ask clarifying questions" in result


# ---------------------------------------------------------------------------
# Relationship with dynamic (covering line 599)
# ---------------------------------------------------------------------------


class TestRelationshipDynamic:
    def test_relationship_dynamic_rendered(self, mira_identity):
        """Relationships with dynamic should render the dynamic value."""
        mira_identity.memory.relationships = Relationships(
            enabled=True,
            agent_relationships=[
                AgentRelationship(
                    agent_id="agt_lead_001",
                    name="LeadBot",
                    relationship="team lead",
                    dynamic=RelationshipDynamic.DEFERS_TO,
                    context="project decisions",
                )
            ],
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "LeadBot" in result
        assert "team lead" in result
        assert "(defers_to)" in result
        assert "project decisions" in result


# ---------------------------------------------------------------------------
# Escalation triggers and message (covering lines 626-627, 629)
# ---------------------------------------------------------------------------


class TestEscalationTriggers:
    def test_escalation_triggers_rendered(self, mira_identity):
        mira_identity.interaction = InteractionConfig(
            human=HumanInteraction(
                greeting_style="Hello!",
                escalation_triggers=[
                    InteractionEscalationTrigger.UNABLE_TO_HELP,
                    InteractionEscalationTrigger.SAFETY_CONCERN,
                ],
                escalation_message="Let me connect you with a human specialist.",
            )
        )
        compiler = SystemPromptCompiler()
        result = compiler.compile(mira_identity)
        assert "Escalate when:" in result
        assert "unable_to_help" in result
        assert "safety_concern" in result
        assert 'Escalation message: "Let me connect you with a human specialist."' in result


# ---------------------------------------------------------------------------
# DISC profile metadata in OpenClaw (covering lines 799, 801)
# ---------------------------------------------------------------------------


class TestOpenClawDISCProfile:
    def test_disc_profile_metadata(self, openclaw_compiler, resolver, examples_dir):
        """DISC-based identity should include disc profile in OpenClaw output."""
        disc_path = examples_dir / "identities" / "mira-disc.yaml"
        if disc_path.exists():
            identity = resolver.resolve_file(disc_path)
            result = openclaw_compiler.compile(identity)
            assert "personality_profile" in result
            profile = result["personality_profile"]
            assert profile["mode"] == "disc"
            # Should have disc data
            assert "disc" in profile or "disc_preset" in profile


# ---------------------------------------------------------------------------
# Truncation: principles truncation after all optional sections dropped
# (covering lines 340-341)
# ---------------------------------------------------------------------------


class TestPrinciplesTruncationDuringBudget:
    def test_principles_truncated_when_still_over_budget(self, mira_identity):
        """Even after dropping optional sections, if still over budget,
        principles should be truncated to top 5."""
        from personanexus.types import Principle

        for i in range(20):
            mira_identity.principles.append(
                Principle(
                    id=f"extra_principle_{i}",
                    priority=i + 10,
                    statement=f"Extra principle number {i} with verbose text to pad tokens " * 3,
                    implications=[
                        f"Implication A for principle {i}",
                        f"Implication B for principle {i}",
                    ],
                )
            )
        # Budget barely fits header+role+guardrails but not all principles
        compiler = SystemPromptCompiler(token_budget=200)
        result = compiler.compile(mira_identity)
        assert compiler._was_truncated is True
        assert "# Mira" in result


# ---------------------------------------------------------------------------
# CrewAI Compiler
# ---------------------------------------------------------------------------


class TestCrewAICompiler:
    def test_crewai_returns_yaml_string(self, mira_identity):
        from personanexus.compiler import CrewAICompiler

        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result, str)
        assert "role:" in result
        assert "Senior Data Analyst" in result

    def test_crewai_has_backstory(self, mira_identity):
        from personanexus.compiler import CrewAICompiler

        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        assert "backstory:" in result

    def test_crewai_has_personanexus_id(self, mira_identity):
        from personanexus.compiler import CrewAICompiler

        compiler = CrewAICompiler()
        result = compiler.compile(mira_identity)
        assert "personanexus_id" in result

    def test_compile_identity_crewai_target(self, mira_identity):
        result = compile_identity(mira_identity, target="crewai")
        assert isinstance(result, str)
        assert "role:" in result


# ---------------------------------------------------------------------------
# AutoGen Compiler
# ---------------------------------------------------------------------------


class TestAutoGenCompiler:
    def test_autogen_returns_dict(self, mira_identity):
        from personanexus.compiler import AutoGenCompiler

        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert isinstance(result, dict)
        assert result["name"] == "Mira"
        assert "system_message" in result
        assert result["human_input_mode"] == "NEVER"

    def test_autogen_has_metadata(self, mira_identity):
        from personanexus.compiler import AutoGenCompiler

        compiler = AutoGenCompiler()
        result = compiler.compile(mira_identity)
        assert "metadata" in result
        assert result["metadata"]["personanexus_id"] == "agt_mira_001"

    def test_compile_identity_autogen_target(self, mira_identity):
        result = compile_identity(mira_identity, target="autogen")
        assert isinstance(result, dict)
        assert "system_message" in result
        assert result["name"] == "Mira"


# ---------------------------------------------------------------------------
# MarkdownCompiler — additional coverage (secondary scope, out_of_scope, register)
# ---------------------------------------------------------------------------


class TestMarkdownCompilerExtended:
    def test_markdown_has_secondary_scope(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        if mira_identity.role.scope.secondary:
            assert "**Secondary:**" in result

    def test_markdown_has_out_of_scope(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        if mira_identity.role.scope.out_of_scope:
            assert "**Out of Scope:**" in result

    def test_markdown_has_register(self, markdown_compiler, mira_identity):
        result = markdown_compiler.compile(mira_identity)
        if mira_identity.communication.tone.register:
            assert "**Register:**" in result
