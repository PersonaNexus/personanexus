# DISC Naming Cleanup Report
Generated for: /home/node/.openclaw/.openclaw/workspace/repos/personanexus

## Summary: 29 issues found

### Mixed Case (1 issues)

- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/.venv/lib/python3.11/site-packages/charset_normalizer/constant.py:200`: "Phaistos Disc": range(66000, 66048),

### Inconsistent Preset Names (24 issues)

- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_personality.py:6`: DISC_PRESETS,
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_personality.py:262`: class TestDiscPresets:
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_e2e_workflows.py:710`: result = runner.invoke(app, ["personality", "list-disc-presets"])
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:15`: DiscPresetMatch,
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:26`: from personanexus.personality import DISC_PRESETS, disc_to_traits
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:260`: class TestDiscPresetMatching:
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:262`: preset = DISC_PRESETS["the_commander"]
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:268`: preset = DISC_PRESETS["the_analyst"]
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/tests/test_analyzer.py:283`: for name, preset in DISC_PRESETS.items():
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/src/personanexus/analyzer.py:19`: DISC_PRESETS,
- ... and 14 more

### Doc Inconsistencies (4 issues)

- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/README.md:519`: print(result.disc)              # DiscProfile
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/CHANGELOG.md:50`: - `personality` CLI subcommand group with `ocean-to-traits`, `disc-to-traits`, `preset`, `show-profile`
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/examples/identities/ada-disc.yaml:22`: tags: ["analyst", "data", "disc"]
- `/home/node/.openclaw/.openclaw/workspace/repos/personanexus/examples/identities/ada-disc.yaml:44`: mode: disc

## Standardization Recommendations

1. **User-facing text**: Use 'DISC' (all caps) in documentation, CLI help, and UI
2. **Code fields**: Use 'disc' (lowercase) for field names and variables
3. **Preset names**: Standardize on 'disc_preset' field name
4. **Function names**: Use snake_case consistently (get_disc_preset, list_disc_presets)
5. **Documentation**: Ensure consistent capitalization based on context
