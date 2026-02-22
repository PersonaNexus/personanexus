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
                "personality", "ocean-to-traits",
                "--openness", "0.7",
                "--conscientiousness", "0.8",
                "--extraversion", "0.5",
                "--agreeableness", "0.6",
                "--neuroticism", "0.3",
            ],
        )
        assert result.exit_code == 0
        assert "warmth" in result.output
        assert "rigor" in result.output

    def test_extreme_values(self):
        result = runner.invoke(
            app,
            [
                "personality", "ocean-to-traits",
                "--openness", "1.0",
                "--conscientiousness", "1.0",
                "--extraversion", "1.0",
                "--agreeableness", "1.0",
                "--neuroticism", "1.0",
            ],
        )
        assert result.exit_code == 0

    def test_zero_values(self):
        result = runner.invoke(
            app,
            [
                "personality", "ocean-to-traits",
                "--openness", "0.0",
                "--conscientiousness", "0.0",
                "--extraversion", "0.0",
                "--agreeableness", "0.0",
                "--neuroticism", "0.0",
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
                "personality", "disc-to-traits",
                "--dominance", "0.9",
                "--influence", "0.4",
                "--steadiness", "0.2",
                "--conscientiousness", "0.5",
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
    def test_show_custom_profile(self, ada_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(ada_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Ada" in result.output
        assert "Mode: custom" in result.output

    def test_show_ocean_profile(self, ada_ocean_path, examples_dir):
        result = runner.invoke(
            app,
            [
                "personality", "show-profile",
                str(ada_ocean_path), "--search-path", str(examples_dir),
            ],
        )
        assert result.exit_code == 0
        assert "Mode: ocean" in result.output
        assert "OCEAN:" in result.output

    def test_show_disc_profile(self, ada_disc_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(ada_disc_path), "--search-path", str(examples_dir)],
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

    def test_show_profile_includes_reverse_mapping(self, ada_path, examples_dir):
        result = runner.invoke(
            app,
            ["personality", "show-profile", str(ada_path), "--search-path", str(examples_dir)],
        )
        assert result.exit_code == 0
        assert "Reverse Mapping" in result.output
        assert "OCEAN:" in result.output
        assert "DISC:" in result.output
