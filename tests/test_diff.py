"""Tests for identity diff and compatibility features."""

from personanexus.diff import (
    _calculate_disc_compatibility,
    _calculate_traits_compatibility,
    _flatten_dict,
    _get_disc_traits,
    _get_ocean_traits,
    compatibility_score,
    diff_identities,
    format_diff,
    format_diff_markdown,
)


class TestFlattenDict:
    def test_empty_dict(self):
        assert _flatten_dict({}) == {}

    def test_flat_dict(self):
        d = {"a": 1, "b": 2}
        assert _flatten_dict(d) == {"a": 1, "b": 2}

    def test_nested_dict(self):
        d = {"a": {"b": 1, "c": 2}, "d": 3}
        result = _flatten_dict(d)
        assert result == {"a.b": 1, "a.c": 2, "d": 3}

    def test_deeply_nested_dict(self):
        d = {"a": {"b": {"c": 1}}}
        result = _flatten_dict(d)
        assert result == {"a.b.c": 1}


class TestGetOceanTraits:
    def test_ocean_present(self, mira_ocean_path):
        identity = {
            "personality": {
                "profile": {
                    "mode": "ocean",
                    "ocean": {
                        "openness": 0.7,
                        "conscientiousness": 0.85,
                        "extraversion": 0.5,
                        "agreeableness": 0.6,
                        "neuroticism": 0.2,
                    },
                }
            }
        }
        result = _get_ocean_traits(identity)
        assert result == {
            "openness": 0.7,
            "conscientiousness": 0.85,
            "extraversion": 0.5,
            "agreeableness": 0.6,
            "neuroticism": 0.2,
        }

    def test_ocean_missing(self):
        identity = {"personality": {"profile": {"mode": "disc"}}}
        assert _get_ocean_traits(identity) is None

    def test_no_personality(self):
        identity = {}
        assert _get_ocean_traits(identity) is None


class TestGetDiscTraits:
    def test_disc_present(self):
        identity = {
            "personality": {
                "profile": {
                    "mode": "disc",
                    "disc": {
                        "dominance": 0.3,
                        "influence": 0.2,
                        "steadiness": 0.6,
                        "conscientiousness": 0.9,
                    },
                }
            }
        }
        result = _get_disc_traits(identity)
        assert result == {
            "dominance": 0.3,
            "influence": 0.2,
            "steadiness": 0.6,
            "conscientiousness": 0.9,
        }

    def test_disc_preset(self):
        identity = {"personality": {"profile": {"mode": "disc", "disc_preset": "the_analyst"}}}
        result = _get_disc_traits(identity)
        assert result == {
            "dominance": 0.3,
            "influence": 0.2,
            "steadiness": 0.6,
            "conscientiousness": 0.9,
        }

    def test_disc_missing(self):
        identity = {"personality": {"profile": {"mode": "ocean"}}}
        assert _get_disc_traits(identity) is None


class TestDiffIdentities:
    def test_identical_files(self, mira_ocean_path):
        diff = diff_identities(str(mira_ocean_path), str(mira_ocean_path))
        assert diff["changed_fields"] == []
        assert diff["added_fields"] == []
        assert diff["removed_fields"] == []

    def test_different_files(self, mira_path, mira_ocean_path):
        diff = diff_identities(str(mira_path), str(mira_ocean_path))
        assert len(diff["changed_fields"]) > 0

    def test_added_fields(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text('schema_version: "1.0"\nmetadata:\n  id: "test1"\n')
        file2.write_text('schema_version: "1.0"\nmetadata:\n  id: "test1"\n  version: "1.0.0"\n')

        diff = diff_identities(str(file1), str(file2))
        assert "metadata.version" in diff["added_fields"]

    def test_removed_fields(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text('schema_version: "1.0"\nmetadata:\n  id: "test1"\n  version: "1.0.0"\n')
        file2.write_text('schema_version: "1.0"\nmetadata:\n  id: "test1"\n')

        diff = diff_identities(str(file1), str(file2))
        assert "metadata.version" in diff["removed_fields"]

    def test_personality_diff_ocean(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.5\n"
            "      conscientiousness: 0.8\n"
            "      extraversion: 0.3\n"
            "      agreeableness: 0.6\n"
            "      neuroticism: 0.4\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.7\n"
            "      conscientiousness: 0.6\n"
            "      extraversion: 0.5\n"
            "      agreeableness: 0.8\n"
            "      neuroticism: 0.2\n"
        )

        diff = diff_identities(str(file1), str(file2))
        assert "personality_diff" in diff
        assert "ocean" in diff["personality_diff"]
        assert abs(diff["personality_diff"]["ocean"]["openness"]["delta"] - 0.2) < 0.0001
        consc_delta = diff["personality_diff"]["ocean"]["conscientiousness"]["delta"]
        assert abs(consc_delta - (-0.2)) < 0.0001


class TestCompatibilityScore:
    def test_identical_ocean_personality(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.5\n"
            "      conscientiousness: 0.8\n"
            "      extraversion: 0.3\n"
            "      agreeableness: 0.6\n"
            "      neuroticism: 0.4\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.5\n"
            "      conscientiousness: 0.8\n"
            "      extraversion: 0.3\n"
            "      agreeableness: 0.6\n"
            "      neuroticism: 0.4\n"
        )

        score = compatibility_score(str(file1), str(file2))
        assert score == 100.0

    def test_different_ocean_personality(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.0\n"
            "      conscientiousness: 0.0\n"
            "      extraversion: 0.0\n"
            "      agreeableness: 0.0\n"
            "      neuroticism: 0.0\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 1.0\n"
            "      conscientiousness: 1.0\n"
            "      extraversion: 1.0\n"
            "      agreeableness: 1.0\n"
            "      neuroticism: 1.0\n"
        )

        score = compatibility_score(str(file1), str(file2))
        # Perfectly opposite should give very low score
        assert score < 20.0

    def test_no_personality(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text('schema_version: "1.0"\nmetadata:\n  id: "test1"\n')
        file2.write_text('schema_version: "1.0"\nmetadata:\n  id: "test2"\n')

        score = compatibility_score(str(file1), str(file2))
        assert score == 50.0


class TestFormatDiff:
    def test_text_format(self, mira_path, mira_ocean_path):
        diff = diff_identities(str(mira_path), str(mira_ocean_path))
        formatted = format_diff(diff, "text")
        assert "IDENTITY DIFF REPORT" in formatted
        assert "CHANGED FIELDS:" in formatted
        assert "PERSONALITY DIFFERENCES:" in formatted

    def test_json_format(self, mira_path, mira_ocean_path):
        diff = diff_identities(str(mira_path), str(mira_ocean_path))
        formatted = format_diff(diff, "json")
        assert '"changed_fields"' in formatted
        assert '"added_fields"' in formatted

    def test_empty_diff(self, mira_path):
        diff = diff_identities(str(mira_path), str(mira_path))
        formatted = format_diff(diff, "text")
        assert "CHANGED FIELDS: (none)" in formatted
        assert "ADDED FIELDS: (none)" in formatted
        assert "REMOVED FIELDS: (none)" in formatted


# ---------------------------------------------------------------------------
# DISC diff & compatibility (covers lines 107-116, 196, 272-287)
# ---------------------------------------------------------------------------


class TestDiscDiff:
    def test_personality_diff_disc(self, tmp_path):
        file1 = tmp_path / "disc1.yaml"
        file2 = tmp_path / "disc2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.3\n"
            "      influence: 0.2\n"
            "      steadiness: 0.6\n"
            "      conscientiousness: 0.9\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.7\n"
            "      influence: 0.5\n"
            "      steadiness: 0.4\n"
            "      conscientiousness: 0.8\n"
        )

        diff = diff_identities(str(file1), str(file2))
        assert "personality_diff" in diff
        assert "disc" in diff["personality_diff"]
        dom_delta = diff["personality_diff"]["disc"]["dominance"]["delta"]
        assert abs(dom_delta - 0.4) < 0.0001

    def test_disc_compatibility_identical(self, tmp_path):
        file1 = tmp_path / "disc1.yaml"
        file2 = tmp_path / "disc2.yaml"

        content = (
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.5\n"
            "      influence: 0.5\n"
            "      steadiness: 0.5\n"
            "      conscientiousness: 0.5\n"
        )
        file1.write_text(content)
        file2.write_text(content)

        score = compatibility_score(str(file1), str(file2))
        assert score == 100.0

    def test_disc_compatibility_opposite(self, tmp_path):
        file1 = tmp_path / "disc1.yaml"
        file2 = tmp_path / "disc2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.0\n"
            "      influence: 0.0\n"
            "      steadiness: 0.0\n"
            "      conscientiousness: 0.0\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 1.0\n"
            "      influence: 1.0\n"
            "      steadiness: 1.0\n"
            "      conscientiousness: 1.0\n"
        )

        score = compatibility_score(str(file1), str(file2))
        assert score < 5.0  # Nearly zero


class TestCalculateDiscCompatibility:
    def test_perfect_match(self):
        disc = {
            "dominance": 0.5,
            "influence": 0.5,
            "steadiness": 0.5,
            "conscientiousness": 0.5,
        }
        assert _calculate_disc_compatibility(disc, disc) == 100.0

    def test_complete_mismatch(self):
        disc1 = {
            "dominance": 0.0,
            "influence": 0.0,
            "steadiness": 0.0,
            "conscientiousness": 0.0,
        }
        disc2 = {
            "dominance": 1.0,
            "influence": 1.0,
            "steadiness": 1.0,
            "conscientiousness": 1.0,
        }
        score = _calculate_disc_compatibility(disc1, disc2)
        assert score == 0.0

    def test_partial_difference(self):
        disc1 = {
            "dominance": 0.3,
            "influence": 0.2,
            "steadiness": 0.6,
            "conscientiousness": 0.9,
        }
        disc2 = {
            "dominance": 0.5,
            "influence": 0.4,
            "steadiness": 0.5,
            "conscientiousness": 0.8,
        }
        score = _calculate_disc_compatibility(disc1, disc2)
        assert 50 < score < 100


class TestCalculateTraitsCompatibility:
    def test_no_common_traits(self):
        """Returns 50.0 when no traits in common."""
        traits1 = {"warmth": 0.8, "humor": 0.6}
        traits2 = {"rigor": 0.9, "patience": 0.7}
        assert _calculate_traits_compatibility(traits1, traits2) == 50.0

    def test_identical_traits(self):
        traits = {"warmth": 0.8, "rigor": 0.7, "humor": 0.6}
        assert _calculate_traits_compatibility(traits, traits) == 100.0


# ---------------------------------------------------------------------------
# Text format with DISC (covers lines 352-368)
# ---------------------------------------------------------------------------


class TestFormatDiffDisc:
    def test_text_format_with_disc(self, tmp_path):
        file1 = tmp_path / "disc1.yaml"
        file2 = tmp_path / "disc2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.3\n"
            "      influence: 0.2\n"
            "      steadiness: 0.6\n"
            "      conscientiousness: 0.9\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.7\n"
            "      influence: 0.5\n"
            "      steadiness: 0.4\n"
            "      conscientiousness: 0.8\n"
        )

        diff = diff_identities(str(file1), str(file2))
        formatted = format_diff(diff, "text")
        assert "DISC Traits:" in formatted
        assert "dominance:" in formatted


# ---------------------------------------------------------------------------
# Markdown format (covers lines 378-451)
# ---------------------------------------------------------------------------


class TestFormatDiffMarkdown:
    def test_markdown_empty_diff(self, mira_path):
        diff = diff_identities(str(mira_path), str(mira_path))
        md = format_diff_markdown(diff)
        assert "# Identity Diff Report" in md
        assert "*None*" in md

    def test_markdown_with_changes(self, mira_path, mira_ocean_path):
        diff = diff_identities(str(mira_path), str(mira_ocean_path))
        md = format_diff_markdown(diff)
        assert "# Identity Diff Report" in md
        assert "## Changed Fields" in md
        assert "**Old:**" in md
        assert "**New:**" in md

    def test_markdown_with_added_removed(self, tmp_path):
        file1 = tmp_path / "file1.yaml"
        file2 = tmp_path / "file2.yaml"

        file1.write_text('schema_version: "1.0"\nmetadata:\n  id: "test"\n  version: "1.0.0"\n')
        file2.write_text('schema_version: "1.0"\nmetadata:\n  id: "test"\n  status: "active"\n')

        diff = diff_identities(str(file1), str(file2))
        md = format_diff_markdown(diff)
        assert "## Added Fields" in md
        assert "## Removed Fields" in md
        assert "`+ " in md
        assert "`- " in md

    def test_markdown_with_ocean_personality(self, tmp_path):
        file1 = tmp_path / "ocean1.yaml"
        file2 = tmp_path / "ocean2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.5\n"
            "      conscientiousness: 0.8\n"
            "      extraversion: 0.3\n"
            "      agreeableness: 0.6\n"
            "      neuroticism: 0.4\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: ocean\n"
            "    ocean:\n"
            "      openness: 0.8\n"
            "      conscientiousness: 0.6\n"
            "      extraversion: 0.5\n"
            "      agreeableness: 0.7\n"
            "      neuroticism: 0.2\n"
        )

        diff = diff_identities(str(file1), str(file2))
        md = format_diff_markdown(diff)
        assert "### OCEAN Traits" in md
        assert "openness" in md

    def test_markdown_with_disc_personality(self, tmp_path):
        file1 = tmp_path / "disc1.yaml"
        file2 = tmp_path / "disc2.yaml"

        file1.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.3\n"
            "      influence: 0.2\n"
            "      steadiness: 0.6\n"
            "      conscientiousness: 0.9\n"
        )
        file2.write_text(
            "personality:\n"
            "  profile:\n"
            "    mode: disc\n"
            "    disc:\n"
            "      dominance: 0.7\n"
            "      influence: 0.4\n"
            "      steadiness: 0.5\n"
            "      conscientiousness: 0.8\n"
        )

        diff = diff_identities(str(file1), str(file2))
        md = format_diff_markdown(diff)
        assert "### DISC Traits" in md
        assert "dominance" in md

    def test_markdown_format_standalone(self, mira_path, mira_ocean_path):
        """format_diff_markdown produces valid markdown output."""
        diff = diff_identities(str(mira_path), str(mira_ocean_path))
        md = format_diff_markdown(diff)
        assert "# Identity Diff Report" in md
        assert "## Changed Fields" in md
