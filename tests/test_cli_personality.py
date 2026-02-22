"""Tests for personality CLI commands."""

from typer.testing import CliRunner

from personanexus.cli import app

runner = CliRunner()


# ---------------------------------------------------------------------------
# ocean-to-traits command
# ---------------------------------------------------------------------------


class TestOceanToTraits:
    def test_basic_invocation(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "ocean-to-traits",
                "--openness",
                "0.7",
                "--conscientiousness",
                "0.8",
                "--extraversion",
                "0.5",
                "--agreeableness",
                "0.6",
                "--neuroticism",
                "0.3",
            ],
        )
        assert result.exit_code == 0
        assert "warmth" in result.output
        assert "rigor" in result.output

    def test_extreme_values(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "ocean-to-traits",
                "--openness",
                "1.0",
                "--conscientiousness",
                "1.0",
                "--extraversion",
                "1.0",
                "--agreeableness",
                "1.0",
                "--neuroticism",
                "1.0",
            ],
        )
        assert result.exit_code == 0

    def test_zero_values(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "ocean-to-traits",
                "--openness",
                "0.0",
                "--conscientiousness",
                "0.0",
                "--extraversion",
                "0.0",
                "--agreeableness",
                "0.0",
                "--neuroticism",
                "0.0",
            ],
        )
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# disc-to-traits command
# ---------------------------------------------------------------------------


class TestDiscToTraits:
    def test_basic_invocation(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "disc-to-traits",
                "--dominance",
                "0.9",
                "--influence",
                "0.4",
                "--steadiness",
                "0.2",
                "--conscientiousness",
                "0.5",
            ],
        )
        assert result.exit_code == 0
        assert "assertiveness" in result.output
        assert "rigor" in result.output


# ---------------------------------------------------------------------------
# preset command
# ---------------------------------------------------------------------------


class TestPresetCommand:
    def test_commander_preset(self):
        result = runner.invoke(
            app,
            ["personality", "preset", "the_commander"],
        )
        assert result.exit_code == 0
        assert "the_commander" in result.output
        assert "D=0.9" in result.output

    def test_analyst_preset(self):
        result = runner.invoke(
            app,
            ["personality", "preset", "the_analyst"],
        )
        assert result.exit_code == 0
        assert "the_analyst" in result.output

    def test_influencer_preset(self):
        result = runner.invoke(
            app,
            ["personality", "preset", "the_influencer"],
        )
        assert result.exit_code == 0

    def test_steady_hand_preset(self):
        result = runner.invoke(
            app,
            ["personality", "preset", "the_steady_hand"],
        )
        assert result.exit_code == 0

    def test_unknown_preset_fails(self):
        result = runner.invoke(
            app,
            ["personality", "preset", "the_pirate"],
        )
        assert result.exit_code == 1
        assert "Unknown DISC preset" in result.output


# ---------------------------------------------------------------------------
# show-profile command
# ---------------------------------------------------------------------------


class TestShowProfileCommand:
    def test_show_custom_profile(self, mira_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(mira_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Mira" in result.output
        assert "Mode: custom" in result.output

    def test_show_ocean_profile(self, mira_ocean_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "personality",
                "show-profile",
                str(mira_ocean_path),
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Mode: ocean" in result.output
        assert "OCEAN:" in result.output

    def test_show_disc_profile(self, mira_disc_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "personality",
                "show-profile",
                str(mira_disc_path),
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Mode: disc" in result.output
        assert "DISC Preset: the_analyst" in result.output

    def test_show_hybrid_profile(self, hybrid_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(hybrid_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Mode: hybrid" in result.output

    def test_show_profile_nonexistent(self):
        result = runner.invoke(
            app,
            ["personality", "show-profile", "/nonexistent.yaml"],
        )
        assert result.exit_code == 1
        assert "not found" in result.output.lower()

    def test_show_profile_includes_reverse_mapping(self, mira_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(mira_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Reverse Mapping" in result.output
        assert "OCEAN:" in result.output
        assert "DISC:" in result.output

    def test_show_jungian_profile(self, mira_jungian_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "personality",
                "show-profile",
                str(mira_jungian_path),
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Mode: jungian" in result.output
        assert "Jungian Preset: intj" in result.output

    def test_show_hybrid_jungian_profile(self, hybrid_jungian_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "personality",
                "show-profile",
                str(hybrid_jungian_path),
                "--search-path",
                str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Mode: hybrid" in result.output
        assert "Jungian" in result.output

    def test_show_profile_includes_jungian_reverse_mapping(self, mira_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(mira_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Jungian:" in result.output
        assert "closest:" in result.output


# ---------------------------------------------------------------------------
# jungian-to-traits command
# ---------------------------------------------------------------------------


class TestJungianToTraits:
    def test_with_preset(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-to-traits", "--preset", "intj"],
        )
        assert result.exit_code == 0
        assert "rigor" in result.output
        assert "warmth" in result.output

    def test_with_preset_case_insensitive(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-to-traits", "--preset", "ENFP"],
        )
        assert result.exit_code == 0

    def test_with_manual_dimensions(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "jungian-to-traits",
                "--ei",
                "0.8",
                "--sn",
                "0.7",
                "--tf",
                "0.3",
                "--jp",
                "0.2",
            ],
        )
        assert result.exit_code == 0
        assert "rigor" in result.output

    def test_missing_dimensions_fails(self):
        result = runner.invoke(
            app,
            [
                "personality",
                "jungian-to-traits",
                "--ei",
                "0.8",
                "--sn",
                "0.7",
            ],
        )
        assert result.exit_code == 1

    def test_invalid_preset_fails(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-to-traits", "--preset", "xxxx"],
        )
        assert result.exit_code == 1


# ---------------------------------------------------------------------------
# list-jungian-presets command
# ---------------------------------------------------------------------------


class TestListJungianPresets:
    def test_lists_all_16(self):
        result = runner.invoke(
            app,
            ["personality", "list-jungian-presets"],
        )
        assert result.exit_code == 0
        assert "INTJ" in result.output
        assert "ENFP" in result.output
        assert "ESFJ" in result.output
        assert "ISTP" in result.output


# ---------------------------------------------------------------------------
# jungian-recommend command
# ---------------------------------------------------------------------------


class TestJungianRecommend:
    def test_list_categories(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-recommend"],
        )
        assert result.exit_code == 0
        assert "data_science" in result.output
        assert "creative_writing" in result.output

    def test_specific_category(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-recommend", "strategic_analysis"],
        )
        assert result.exit_code == 0
        assert "INTJ" in result.output

    def test_unknown_category_fails(self):
        result = runner.invoke(
            app,
            ["personality", "jungian-recommend", "underwater_basket_weaving"],
        )
        assert result.exit_code == 1
