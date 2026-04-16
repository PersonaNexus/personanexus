from __future__ import annotations

import json
from pathlib import Path

from typer.testing import CliRunner

from personanexus.cli import app
from personanexus.packs import (
    PackMetadata,
    build_gallery_index,
    create_pack,
    default_packs_root,
    discover_packs,
    find_pack,
    install_pack,
    list_installed_packs,
    remove_installed_pack,
    search_packs,
    validate_pack_dir,
)

runner = CliRunner()


def test_seed_packs_exist():
    records = discover_packs(default_packs_root())
    refs = {record.ref for record in records}
    assert "strategic-advisory-council" in refs
    assert "chief-of-staff" in refs
    assert "ocean-disc-bridge" in refs


def test_validate_seed_pack():
    pack = find_pack("chief-of-staff", default_packs_root())
    result = validate_pack_dir(pack.path, packs_root=default_packs_root())
    assert result.errors == []
    assert result.metadata is not None
    assert result.metadata.name == "chief-of-staff"


def test_build_gallery_index(tmp_path: Path):
    output = build_gallery_index(default_packs_root(), tmp_path / "index.json")
    payload = json.loads(output.read_text(encoding="utf-8"))
    assert any(entry["ref"] == "chief-of-staff" for entry in payload)


def test_search_packs_by_tag_and_text():
    results = search_packs("chief", packs_root=default_packs_root())
    assert any(record.metadata.name == "chief-of-staff" for record in results)
    tag_results = search_packs("official", packs_root=default_packs_root(), tag="official")
    assert tag_results


def test_install_and_remove_pack(tmp_path: Path):
    destination = install_pack(
        "chief-of-staff",
        packs_root=default_packs_root(),
        cache_dir=tmp_path,
    )
    assert (destination / "pack.json").exists()
    installed = list_installed_packs(tmp_path)
    assert any(record.metadata.name == "chief-of-staff" for record in installed)
    removed = remove_installed_pack("chief-of-staff", cache_dir=tmp_path)
    assert removed == destination
    assert not destination.exists()


def test_create_pack_from_persona(tmp_path: Path):
    persona = Path("examples/identities/minimal.yaml")
    output = tmp_path / "new-pack"
    create_pack(
        persona,
        output,
        author="tester",
        category="personas",
        description="Test persona pack",
        tags=["test"],
    )
    metadata = PackMetadata.model_validate(json.loads((output / "pack.json").read_text()))
    assert metadata.author == "tester"
    assert (output / "persona.yaml").exists()
    assert (output / "README.md").exists()


def test_pack_cli_list_and_show():
    listed = runner.invoke(app, ["pack", "list"])
    assert listed.exit_code == 0
    assert "chief-of-staff" in listed.output

    shown = runner.invoke(app, ["pack", "show", "chief-of-staff"])
    assert shown.exit_code == 0
    assert "Pack Details" in shown.output


def test_pack_cli_search_install_remove(tmp_path: Path, monkeypatch):
    from personanexus import packs as packs_module

    monkeypatch.setattr(packs_module, "default_pack_cache", lambda: tmp_path)

    searched = runner.invoke(app, ["pack", "search", "advisory"])
    assert searched.exit_code == 0
    assert "strategic-advisory-council" in searched.output

    installed = runner.invoke(app, ["pack", "install", "chief-of-staff"])
    assert installed.exit_code == 0
    assert "Installed to" in installed.output

    removed = runner.invoke(app, ["pack", "remove", "chief-of-staff"])
    assert removed.exit_code == 0
    assert "Removed" in removed.output


def test_pack_cli_create(tmp_path: Path):
    out = tmp_path / "pack"
    result = runner.invoke(
        app,
        [
            "pack",
            "create",
            "examples/identities/minimal.yaml",
            "--output",
            str(out),
            "--author",
            "tester",
            "--category",
            "personas",
            "--description",
            "CLI test pack",
            "--tag",
            "test",
        ],
    )
    assert result.exit_code == 0
    assert (out / "pack.json").exists()


def test_pack_validate_rejects_bad_semver(tmp_path: Path):
    pack_dir = tmp_path / "bad-pack"
    pack_dir.mkdir()
    (pack_dir / "persona.yaml").write_text(
        Path("examples/identities/minimal.yaml").read_text(),
        encoding="utf-8",
    )
    (pack_dir / "README.md").write_text("bad pack", encoding="utf-8")
    (pack_dir / "pack.json").write_text(
        json.dumps(
            {
                "name": "bad-pack",
                "author": "tester",
                "version": "not-semver",
                "license": "MIT",
                "description": "bad",
                "category": "personas",
                "requires_personanexus": ">=1.5.0",
            }
        ),
        encoding="utf-8",
    )
    result = validate_pack_dir(pack_dir)
    assert any("semver" in error for error in result.errors)
