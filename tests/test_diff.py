"""Tests for identity diff and compatibility features."""



from personanexus.diff import (
    _flatten_dict,
    _get_disc_traits,
    _get_ocean_traits,
    compatibility_score,
    diff_identities,
    format_diff,
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
    def test_ocean_present(self, ada_ocean_path):
        identity = {"personality": {"profile": {"mode": "ocean", "ocean": {
            "openness": 0.7,
            "conscientiousness": 0.85,
            "extraversion": 0.5,
            "agreeableness": 0.6,
            "neuroticism": 0.2,
        }}}}
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
        identity = {"personality": {"profile": {"mode": "disc", "disc": {
            "dominance": 0.3, "influence": 0.2, "steadiness": 0.6, "conscientiousness": 0.9,
        }}}}
        result = _get_disc_traits(identity)
        assert result == {
            "dominance": 0.3, "influence": 0.2,
            "steadiness": 0.6, "conscientiousness": 0.9,
        }

    def test_disc_preset(self):
        identity = {"personality": {"profile": {"mode": "disc", "disc_preset": "the_analyst"}}}
        result = _get_disc_traits(identity)
        assert result == {
            "dominance": 0.3, "influence": 0.2,
            "steadiness": 0.6, "conscientiousness": 0.9,
        }

    def test_disc_missing(self):
        identity = {"personality": {"profile": {"mode": "ocean"}}}
        assert _get_disc_traits(identity) is None


class TestDiffIdentities:
    def test_identical_files(self, ada_ocean_path):
        diff = diff_identities(str(ada_ocean_path), str(ada_ocean_path))
        assert diff["changed_fields"] == []
        assert diff["added_fields"] == []
        assert diff["removed_fields"] == []

    def test_different_files(self, ada_path, ada_ocean_path):
        diff = diff_identities(str(ada_path), str(ada_ocean_path))
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
    def test_text_format(self, ada_path, ada_ocean_path):
        diff = diff_identities(str(ada_path), str(ada_ocean_path))
        formatted = format_diff(diff, "text")
        assert "IDENTITY DIFF REPORT" in formatted
        assert "CHANGED FIELDS:" in formatted
        assert "PERSONALITY DIFFERENCES:" in formatted

    def test_json_format(self, ada_path, ada_ocean_path):
        diff = diff_identities(str(ada_path), str(ada_ocean_path))
        formatted = format_diff(diff, "json")
        assert '"changed_fields"' in formatted
        assert '"added_fields"' in formatted

    def test_empty_diff(self, ada_path):
        diff = diff_identities(str(ada_path), str(ada_path))
        formatted = format_diff(diff, "text")
        assert "CHANGED FIELDS: (none)" in formatted
        assert "ADDED FIELDS: (none)" in formatted
        assert "REMOVED FIELDS: (none)" in formatted
