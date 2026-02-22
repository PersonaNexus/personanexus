"""Tests for the identity compiler."""

import json

import pytest
from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.compiler import (
    CompilerError,
    OpenClawCompiler,
    SoulCompiler,
    SystemPromptCompiler,
    compile_identity,
)
from personanexus.resolver import IdentityResolver
from personanexus.types import Influence, Narrative, Opinion, VoiceExample, VoiceExamples

runner = CliRunner()


@pytest.fixture
def resolver(examples_dir):
    return IdentityResolver(search_paths=[examples_dir])


@pytest.fixture
def ada_identity(resolver, ada_path):
    return resolver.resolve_file(ada_path)


@pytest.fixture
def minimal_identity(resolver, minimal_path):
    return resolver.resolve_file(minimal_path)


@pytest.fixture
def compiler():
    return SystemPromptCompiler()


@pytest.fixture
def openclaw_compiler():
    return OpenClawCompiler()


# ---------------------------------------------------------------------------
# SystemPromptCompiler
# ---------------------------------------------------------------------------


class TestSystemPromptCompiler:
    def test_compile_minimal_has_required_sections(self, compiler, minimal_identity):
        result = compiler.compile(minimal_identity)
        assert "# Helper" in result
        assert "## Your Role" in result
        assert "## Your Personality" in result
        assert "## Communication Style" in result
        assert "## Core Principles" in result
        assert "## Non-Negotiable Rules" in result

    def test_compile_ada_has_all_sections(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "# Ada" in result
        assert "## Your Role: Senior Data Analyst" in result
        assert "## Your Personality" in result
        assert "## Communication Style" in result
        assert "## Your Expertise" in result
        assert "## Core Principles" in result
        assert "## Non-Negotiable Rules" in result

    def test_traits_rendered_as_language_not_numbers(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        # High rigor (0.9) should use high-level language
        assert "rigorous" in result.lower()
        # Should not contain raw float values for traits
        assert "0.9" not in result
        assert "0.7" not in result

    def test_high_rigor_contains_rigorous(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        # Ada has rigor: 0.9 which maps to level 4 "exceptionally rigorous"
        assert "rigorous" in result.lower()

    def test_principles_sorted_by_priority(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        # Principles should be numbered in priority order
        accuracy_pos = result.find("Never present uncertain information")
        clarity_pos = result.find("clear partial answer")
        assert accuracy_pos < clarity_pos, "accuracy_first (p1) should come before clarity (p2)"

    def test_guardrails_grouped_by_severity(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "CRITICAL" in result
        # Critical guardrails should appear before high
        critical_pos = result.find("CRITICAL")
        high_pos = result.find("High priority constraints")
        if high_pos != -1:
            assert critical_pos < high_pos

    def test_anthropic_format_has_xml_tags(self, compiler, ada_identity):
        result = compiler.compile(ada_identity, format="anthropic")
        assert "<identity>" in result
        assert "</identity>" in result

    def test_openai_format_is_plain_text(self, compiler, ada_identity):
        result = compiler.compile(ada_identity, format="openai")
        assert "<identity>" not in result
        assert "# Ada" in result

    def test_text_format_default(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "<identity>" not in result
        assert "# Ada" in result

    def test_token_estimation(self, compiler):
        text = "a" * 400
        estimate = compiler.estimate_tokens(text)
        assert estimate == 100

    def test_empty_expertise_no_crash(self, compiler, minimal_identity):
        # Minimal identity has no expertise domains
        result = compiler.compile(minimal_identity)
        assert "## Your Expertise" not in result

    def test_expertise_domains_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "statistical_analysis" in result
        assert "expert" in result.lower()  # 0.95 level
        assert "Primary expertise" in result

    def test_communication_tone_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "professional-warm" in result

    def test_vocabulary_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "Let's dig in" in result
        assert "As an AI" in result  # in the "avoided" section

    def test_behavior_strategies_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "Behavioral Strategies" in result
        assert "uncertainty" in result.lower()

    def test_personality_notes_included(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "cooking metaphors" in result

    def test_scope_out_of_scope_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "Out of scope" in result
        assert "legal advice" in result

    def test_audience_rendered(self, compiler, ada_identity):
        result = compiler.compile(ada_identity)
        assert "business analysts" in result


# ---------------------------------------------------------------------------
# OpenClawCompiler
# ---------------------------------------------------------------------------


class TestOpenClawCompiler:
    def test_output_has_required_keys(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        required_keys = {
            "agent_name",
            "agent_role",
            "version",
            "system_prompt",
            "greeting",
            "personality_traits",
            "model_config",
            "guidelines",
            "domain_expertise",
            "example_phrases",
            "behavioral_settings",
            "response_format",
            "tool_preferences",
        }
        assert required_keys.issubset(result.keys())

    def test_agent_name_matches(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert result["agent_name"] == "Ada"

    def test_agent_role_is_lowercase_underscored(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert result["agent_role"] == "senior_data_analyst"

    def test_personality_traits_preserves_floats(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        traits = result["personality_traits"]
        assert traits["rigor"] == 0.9
        assert traits["warmth"] == 0.7
        assert traits["empathy"] == 0.7

    def test_guidelines_from_principles_in_order(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        guidelines = result["guidelines"]
        assert len(guidelines) > 0
        # First guideline should be from highest priority principle
        assert "uncertain information" in guidelines[0].lower()

    def test_domain_expertise_is_name_list(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        domains = result["domain_expertise"]
        assert isinstance(domains, list)
        assert "statistical_analysis" in domains
        assert "sql" in domains

    def test_output_is_json_serializable(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        json_str = json.dumps(result)
        parsed = json.loads(json_str)
        assert parsed["agent_name"] == "Ada"

    def test_system_prompt_is_string(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert isinstance(result["system_prompt"], str)
        assert len(result["system_prompt"]) > 100

    def test_greeting_includes_name(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert "Ada" in result["greeting"]

    def test_model_config_has_primary_model(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert "primary_model" in result["model_config"]

    def test_example_phrases_from_signature(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert "Let's dig in" in result["example_phrases"]

    def test_minimal_identity_compiles(self, openclaw_compiler, minimal_identity):
        result = openclaw_compiler.compile(minimal_identity)
        assert result["agent_name"] == "Helper"
        assert isinstance(result["system_prompt"], str)

    def test_response_format_has_tone(self, openclaw_compiler, ada_identity):
        result = openclaw_compiler.compile(ada_identity)
        assert "tone" in result["response_format"]


# ---------------------------------------------------------------------------
# compile_identity convenience function
# ---------------------------------------------------------------------------


class TestCompileIdentity:
    @pytest.mark.parametrize(
        "target,result_type,expected_content",
        [
            ("text", str, "# Ada"),
            ("anthropic", str, "<identity>"),
            ("openai", str, "Ada"),
            ("openclaw", dict, "agent_name"),
            ("json", dict, "system_prompt"),
        ],
        ids=["text", "anthropic", "openai", "openclaw", "json"],
    )
    def test_compile_targets(self, ada_identity, target, result_type, expected_content):
        result = compile_identity(ada_identity, target=target)
        assert isinstance(result, result_type)
        if isinstance(result, str):
            assert expected_content in result
        else:
            assert expected_content in result

    def test_json_target_has_token_estimate(self, ada_identity):
        result = compile_identity(ada_identity, target="json")
        assert "tokens_estimated" in result

    def test_unknown_target_raises(self, ada_identity):
        with pytest.raises(CompilerError, match="Unknown target"):
            compile_identity(ada_identity, target="foobar")

    def test_token_budget_passed(self, ada_identity):
        result = compile_identity(ada_identity, target="json", token_budget=1000)
        assert isinstance(result, dict)


# ---------------------------------------------------------------------------
# CLI compile command
# ---------------------------------------------------------------------------


class TestCompileCommand:
    def test_compile_text_output(self, ada_path, examples_dir, tmp_path):
        output_file = tmp_path / "ada.compiled.md"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--search-path",
                str(examples_dir),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert "Compiled" in result.output
        content = output_file.read_text()
        assert "Ada" in content

    def test_compile_anthropic_target(self, ada_path, examples_dir, tmp_path):
        output_file = tmp_path / "ada.compiled.anthropic.md"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "anthropic",
                "--search-path",
                str(examples_dir),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "<identity>" in content

    def test_compile_openclaw_target(self, ada_path, examples_dir, tmp_path):
        output_file = tmp_path / "ada.personality.json"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "openclaw",
                "--search-path",
                str(examples_dir),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        parsed = json.loads(output_file.read_text())
        assert parsed["agent_name"] == "Ada"
        assert "agent_role" in parsed

    def test_compile_auto_output_path(self, ada_path, examples_dir):
        """Without --output, auto-generates a file next to the source YAML."""
        result = runner.invoke(
            app,
            ["compile", str(ada_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Compiled" in result.output

        # Auto-generated file: ada.compiled.md next to ada.yaml
        auto_file = ada_path.parent / "ada.compiled.md"
        assert auto_file.exists()
        content = auto_file.read_text()
        assert "Ada" in content
        # Clean up
        auto_file.unlink()

    def test_compile_auto_output_openclaw(self, ada_path, examples_dir):
        """Without --output and --target openclaw, auto-generates a .personality.json."""
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "openclaw",
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0

        auto_file = ada_path.parent / "ada.personality.json"
        assert auto_file.exists()
        parsed = json.loads(auto_file.read_text())
        assert parsed["agent_name"] == "Ada"
        # Clean up
        auto_file.unlink()

    def test_compile_to_explicit_output_file(self, ada_path, examples_dir, tmp_path):
        output_file = tmp_path / "custom_output.txt"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--search-path",
                str(examples_dir),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert "Compiled" in result.output
        assert output_file.exists()
        content = output_file.read_text()
        assert "Ada" in content

    def test_compile_nonexistent_file(self):
        result = runner.invoke(app, ["compile", "/nonexistent.yaml"])
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_compile_invalid_target(self, ada_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "badformat",
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 1
        assert "Invalid target" in result.output

    def test_compile_minimal_identity(self, minimal_path, tmp_path):
        output_file = tmp_path / "minimal.compiled.md"
        result = runner.invoke(
            app,
            ["compile", str(minimal_path), "--output", str(output_file)],
        )
        assert result.exit_code == 0
        content = output_file.read_text()
        assert "Helper" in content

    def test_compile_shows_token_estimate(self, minimal_path, tmp_path):
        output_file = tmp_path / "minimal.compiled.md"
        result = runner.invoke(
            app,
            ["compile", str(minimal_path), "--output", str(output_file)],
        )
        assert result.exit_code == 0
        assert "Estimated tokens" in result.output

    def test_compile_openclaw_to_file(self, ada_path, examples_dir, tmp_path):
        output_file = tmp_path / "personality.json"
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "openclaw",
                "--search-path",
                str(examples_dir),
                "--output",
                str(output_file),
            ],
        )
        assert result.exit_code == 0
        assert output_file.exists()
        parsed = json.loads(output_file.read_text())
        assert parsed["agent_name"] == "Ada"
        assert "system_prompt" in parsed


# ---------------------------------------------------------------------------
# SoulCompiler
# ---------------------------------------------------------------------------


@pytest.fixture
def soul_compiler():
    return SoulCompiler()


class TestSoulCompiler:
    def test_returns_dict_with_both_keys(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "soul_md" in result
        assert "style_md" in result
        assert isinstance(result["soul_md"], str)
        assert isinstance(result["style_md"], str)

    def test_soul_has_name_header(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "# Ada" in result["soul_md"]

    def test_soul_has_who_i_am(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Who I Am" in result["soul_md"]

    def test_soul_has_worldview(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Worldview" in result["soul_md"]

    def test_soul_has_interests(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Interests" in result["soul_md"]

    def test_soul_has_boundaries(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Boundaries" in result["soul_md"]

    def test_soul_includes_personality_notes(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "cooking metaphors" in result["soul_md"]

    def test_soul_includes_trait_language(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "rigorous" in result["soul_md"].lower()

    def test_soul_no_raw_floats(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        # Trait values should be rendered as language, not numbers
        assert "0.9" not in result["soul_md"]
        assert "0.7" not in result["soul_md"]

    def test_soul_vocabulary_from_signature_phrases(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "Let's dig in" in result["soul_md"]

    def test_soul_boundaries_from_guardrails(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "Won't:" in result["soul_md"]

    def test_soul_minimal_identity(self, soul_compiler, minimal_identity):
        result = soul_compiler.compile(minimal_identity)
        assert "# Helper" in result["soul_md"]
        assert "## Who I Am" in result["soul_md"]
        assert "## Worldview" in result["soul_md"]
        assert "## Boundaries" in result["soul_md"]

    def test_style_has_voice_principles(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Voice Principles" in result["style_md"]
        assert "professional-warm" in result["style_md"]

    def test_style_has_vocabulary(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Vocabulary" in result["style_md"]
        assert "Words & Phrases You Use" in result["style_md"]
        assert "Words You Never Use" in result["style_md"]

    def test_style_has_formatting(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Punctuation & Formatting" in result["style_md"]

    def test_style_has_context_adjustments(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "Context-Specific Style" in result["style_md"]

    def test_style_has_anti_patterns(self, soul_compiler, ada_identity):
        result = soul_compiler.compile(ada_identity)
        assert "## Anti-Patterns" in result["style_md"]
        assert "As an AI" in result["style_md"]


class TestSoulCompilerNarrative:
    """Tests for narrative-enriched identities."""

    def test_opinions_rendered(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(
            opinions=[
                Opinion(domain="Technology", takes=["Open source wins", "Types > no types"]),
            ]
        )
        result = soul_compiler.compile(ada_identity)
        assert "## Opinions" in result["soul_md"]
        assert "### Technology" in result["soul_md"]
        assert "Open source wins" in result["soul_md"]

    def test_influences_rendered(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(
            influences=[
                Influence(name="Tukey", category="person", insight="EDA pioneer"),
                Influence(name="Tufte", category="person", insight="Visual clarity"),
            ]
        )
        result = soul_compiler.compile(ada_identity)
        assert "## Influences" in result["soul_md"]
        assert "### Person" in result["soul_md"]
        assert "**Tukey**" in result["soul_md"]
        assert "EDA pioneer" in result["soul_md"]

    def test_tensions_rendered(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(
            tensions=[
                "Values rigor but also knows when 80% is good enough",
                "Loves clean data but works with messy datasets daily",
            ]
        )
        result = soul_compiler.compile(ada_identity)
        assert "## Tensions & Contradictions" in result["soul_md"]
        assert "80% is good enough" in result["soul_md"]

    def test_pet_peeves_rendered(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(
            pet_peeves=["Cherry-picked statistics", "Pie charts for comparison"]
        )
        result = soul_compiler.compile(ada_identity)
        assert "## Pet Peeves" in result["soul_md"]
        assert "Cherry-picked statistics" in result["soul_md"]

    def test_current_focus_rendered(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(current_focus=["Building better health dashboards"])
        result = soul_compiler.compile(ada_identity)
        assert "## Current Focus" in result["soul_md"]
        assert "health dashboards" in result["soul_md"]

    def test_backstory_overrides_purpose(self, soul_compiler, ada_identity):
        ada_identity.narrative = Narrative(
            backstory="Started as a spreadsheet nerd, evolved into a data scientist."
        )
        result = soul_compiler.compile(ada_identity)
        assert "spreadsheet nerd" in result["soul_md"]

    def test_voice_examples_in_style(self, soul_compiler, ada_identity):
        ada_identity.communication.voice_examples = VoiceExamples(
            good=[
                VoiceExample(
                    text="The data tells an interesting story here.",
                    context="analysis",
                )
            ],
            bad=[VoiceExample(text="As an AI, I cannot determine the answer.")],
        )
        result = soul_compiler.compile(ada_identity)
        assert "## Voice Examples" in result["style_md"]
        assert "### Right Voice" in result["style_md"]
        assert "### Wrong Voice" in result["style_md"]
        assert "interesting story" in result["style_md"]

    def test_empty_narrative_no_extra_sections(self, soul_compiler, ada_identity):
        # Default narrative has no opinions, influences, etc.
        result = soul_compiler.compile(ada_identity)
        assert "## Opinions" not in result["soul_md"]
        assert "## Influences" not in result["soul_md"]
        assert "## Tensions" not in result["soul_md"]
        assert "## Pet Peeves" not in result["soul_md"]
        assert "## Current Focus" not in result["soul_md"]


# ---------------------------------------------------------------------------
# compile_identity with soul target
# ---------------------------------------------------------------------------


class TestCompileIdentitySoul:
    def test_soul_target_returns_dict(self, ada_identity):
        result = compile_identity(ada_identity, target="soul")
        assert isinstance(result, dict)
        assert "soul_md" in result
        assert "style_md" in result

    def test_soul_target_content(self, ada_identity):
        result = compile_identity(ada_identity, target="soul")
        assert "# Ada" in result["soul_md"]
        assert "Voice & Style Guide" in result["style_md"]


# ---------------------------------------------------------------------------
# CLI compile soul target
# ---------------------------------------------------------------------------


class TestCompileSoulCommand:
    def test_compile_soul_creates_two_files(self, ada_path, examples_dir, tmp_path):
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "soul",
                "--search-path",
                str(examples_dir),
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        assert "SOUL.md" in result.output
        assert "STYLE.md" in result.output

        soul_file = tmp_path / "ada.SOUL.md"
        style_file = tmp_path / "ada.STYLE.md"
        assert soul_file.exists()
        assert style_file.exists()

        soul_content = soul_file.read_text()
        assert "# Ada" in soul_content
        assert "## Who I Am" in soul_content

        style_content = style_file.read_text()
        assert "Voice & Style Guide" in style_content

    def test_compile_soul_auto_output(self, ada_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "compile",
                str(ada_path),
                "--target",
                "soul",
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0

        # Auto-generated files next to source
        soul_file = ada_path.parent / "ada.SOUL.md"
        style_file = ada_path.parent / "ada.STYLE.md"
        assert soul_file.exists()
        assert style_file.exists()
        # Clean up
        soul_file.unlink()
        style_file.unlink()

    def test_compile_soul_minimal(self, minimal_path, tmp_path):
        result = runner.invoke(
            app,
            [
                "compile",
                str(minimal_path),
                "--target",
                "soul",
                "--output",
                str(tmp_path),
            ],
        )
        assert result.exit_code == 0
        soul_content = (tmp_path / "minimal.SOUL.md").read_text()
        assert "# Helper" in soul_content
