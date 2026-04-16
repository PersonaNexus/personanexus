"""GitHub-native pack marketplace helpers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

from pydantic import BaseModel, Field, ValidationError

from personanexus.compiler import SystemPromptCompiler
from personanexus.parser import parse_identity_file
from personanexus.validator import IdentityValidator

DEFAULT_GITHUB_REPO = "PersonaNexus/personanexus"
DEFAULT_GITHUB_REF = "main"
SEMVER_RE = re.compile(
    r"^(0|[1-9]\d*)\.(0|[1-9]\d*)\.(0|[1-9]\d*)"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?$"
)
INJECTION_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in [
        r"ignore previous instructions",
        r"you are now",
        r"browse to https?://",
        r"run this shell",
        r"curl https?://",
    ]
]


class PackMetadata(BaseModel):
    name: str
    author: str
    version: str
    license: str
    description: str
    category: str
    requires_personanexus: str
    tags: list[str] = Field(default_factory=list)
    evolved_from: str | None = None
    evolution_deltas: str | None = None
    homepage: str | None = None
    example_usage: str | None = None
    created: str | None = None
    stats: dict[str, int] = Field(default_factory=dict)


@dataclass
class PackRecord:
    metadata: PackMetadata
    path: Path
    scope: str
    namespace: str
    persona_path: Path
    readme_path: Path

    @property
    def ref(self) -> str:
        if self.namespace != "official":
            return f"{self.namespace}/{self.metadata.name}"
        return self.metadata.name


class PackValidationResult(BaseModel):
    errors: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    metadata: PackMetadata | None = None


class GalleryEntry(BaseModel):
    name: str
    author: str
    ref: str
    scope: str
    category: str
    version: str
    description: str
    tags: list[str] = Field(default_factory=list)
    path: str


REPO_ROOT = Path(__file__).resolve().parents[2]


def default_packs_root() -> Path:
    return REPO_ROOT / "packs"


def default_pack_cache() -> Path:
    return Path.home() / ".personanexus" / "packs"


def _read_json(path: Path) -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(path.read_text(encoding="utf-8")))


def _write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _pack_record(pack_dir: Path, packs_root: Path) -> PackRecord:
    metadata = PackMetadata.model_validate(_read_json(pack_dir / "pack.json"))
    rel = pack_dir.relative_to(packs_root)
    scope = rel.parts[0]
    namespace = rel.parts[1] if scope == "community" else "official"
    return PackRecord(
        metadata=metadata,
        path=pack_dir,
        scope=scope,
        namespace=namespace,
        persona_path=pack_dir / "persona.yaml",
        readme_path=pack_dir / "README.md",
    )


def discover_packs(packs_root: Path | None = None) -> list[PackRecord]:
    root = packs_root or default_packs_root()
    if not root.exists():
        return []
    records: list[PackRecord] = []
    for pack_json in sorted(root.glob("**/pack.json")):
        try:
            records.append(_pack_record(pack_json.parent, root))
        except (ValidationError, json.JSONDecodeError):
            continue
    return records


def find_pack(ref: str, packs_root: Path | None = None) -> PackRecord:
    normalized = ref.strip().lower()
    matches: list[PackRecord] = []
    for record in discover_packs(packs_root):
        if normalized in {
            record.metadata.name.lower(),
            f"{record.namespace}/{record.metadata.name}".lower(),
            f"{record.metadata.author}/{record.metadata.name}".lower(),
        }:
            matches.append(record)
    if not matches:
        raise FileNotFoundError(f"Pack not found: {ref}")
    official = [record for record in matches if record.scope == "official"]
    return official[0] if official else matches[0]


def _scan_injection(text: str) -> list[str]:
    warnings: list[str] = []
    for pattern in INJECTION_PATTERNS:
        if pattern.search(text):
            warnings.append(f"suspicious prompt pattern matched: {pattern.pattern}")
    return warnings


def validate_pack_dir(pack_dir: Path, *, packs_root: Path | None = None) -> PackValidationResult:
    result = PackValidationResult()
    pack_json = pack_dir / "pack.json"
    persona_yaml = pack_dir / "persona.yaml"
    readme = pack_dir / "README.md"

    if not pack_json.exists():
        result.errors.append("pack.json is required")
        return result
    if not persona_yaml.exists():
        result.errors.append("persona.yaml is required")
    if not readme.exists():
        result.errors.append("README.md is required")
    elif not readme.read_text(encoding="utf-8").strip():
        result.errors.append("README.md must be non-empty")

    try:
        metadata = PackMetadata.model_validate(_read_json(pack_json))
        result.metadata = metadata
    except (ValidationError, json.JSONDecodeError) as exc:
        result.errors.append(f"invalid pack.json: {exc}")
        return result

    if not SEMVER_RE.match(metadata.version):
        result.errors.append("version must be valid semver")
    if metadata.category not in {"boards", "personas", "frameworks"}:
        result.errors.append("category must be one of: boards, personas, frameworks")

    root = packs_root or default_packs_root()
    rel = pack_dir.relative_to(root) if pack_dir.is_relative_to(root) else None
    if rel is not None:
        if rel.parts[0] == "community":
            if len(rel.parts) < 3:
                result.errors.append("community pack path must be packs/community/<author>/<name>")
            else:
                if rel.parts[1] != metadata.author:
                    result.errors.append(
                        "community pack author directory must match pack.json author"
                    )
                if rel.parts[2] != metadata.name:
                    result.errors.append("pack directory name must match pack.json name")
        elif rel.parts[0] == "official":
            if len(rel.parts) < 3:
                result.errors.append("official pack path must be packs/official/<category>/<name>")
            elif rel.parts[1] != metadata.category:
                result.errors.append(
                    "official pack category directory must match pack.json category"
                )
            elif rel.parts[2] != metadata.name:
                result.errors.append("pack directory name must match pack.json name")

    if persona_yaml.exists():
        validator = IdentityValidator()
        validation = validator.validate_file(persona_yaml)
        if validation.errors:
            result.errors.extend(f"persona.yaml: {error}" for error in validation.errors)
        else:
            identity = parse_identity_file(persona_yaml)
            compiler = SystemPromptCompiler(token_budget=8000)
            prompt = compiler.compile(identity)
            if compiler.estimate_tokens(prompt) > 8000:
                result.warnings.append("compiled prompt exceeds 8000 estimated tokens")
            result.warnings.extend(_scan_injection(prompt))

    if result.metadata and result.metadata.evolved_from:
        evolved_from = root / result.metadata.evolved_from.split("@")[0]
        if not evolved_from.exists():
            result.errors.append("evolved_from reference does not exist")

    if (
        result.metadata
        and result.metadata.evolution_deltas
        and not (pack_dir / result.metadata.evolution_deltas).exists()
    ):
        result.errors.append("evolution_deltas file does not exist")

    if result.metadata and result.metadata.example_usage and not readme.exists():
        result.warnings.append("example_usage is set but README.md is missing")

    return result


def build_gallery_index(packs_root: Path | None = None, output_path: Path | None = None) -> Path:
    root = packs_root or default_packs_root()
    output = output_path or root / "_gallery" / "index.json"
    entries = [
        GalleryEntry(
            name=record.metadata.name,
            author=record.metadata.author,
            ref=record.ref,
            scope=record.scope,
            category=record.metadata.category,
            version=record.metadata.version,
            description=record.metadata.description,
            tags=record.metadata.tags,
            path=str(record.path.relative_to(root)),
        ).model_dump(mode="json")
        for record in discover_packs(root)
    ]
    _write_json(output, entries)
    return output


def list_installed_packs(cache_dir: Path | None = None) -> list[PackRecord]:
    return discover_packs(cache_dir or default_pack_cache())


def install_pack(
    ref: str,
    *,
    packs_root: Path | None = None,
    cache_dir: Path | None = None,
    dry_run: bool = False,
) -> Path:
    record = find_pack(ref, packs_root)
    validator = validate_pack_dir(record.path, packs_root=packs_root)
    if validator.errors:
        raise ValueError("; ".join(validator.errors))
    if dry_run:
        return record.path

    destination = (cache_dir or default_pack_cache()) / record.scope
    if record.scope == "community":
        destination = destination / record.metadata.author / record.metadata.name
    else:
        destination = destination / record.metadata.category / record.metadata.name
    if destination.exists():
        shutil.rmtree(destination)
    shutil.copytree(record.path, destination)
    return destination


def remove_installed_pack(ref: str, cache_dir: Path | None = None) -> Path:
    record = find_pack(ref, cache_dir or default_pack_cache())
    shutil.rmtree(record.path)
    return record.path


def search_packs(
    query: str,
    *,
    packs_root: Path | None = None,
    category: str | None = None,
    tag: str | None = None,
) -> list[PackRecord]:
    needle = query.lower()
    results = []
    for record in discover_packs(packs_root):
        haystack = " ".join(
            [
                record.metadata.name,
                record.metadata.author,
                record.metadata.description,
                *record.metadata.tags,
            ]
        ).lower()
        if category and record.metadata.category != category:
            continue
        if tag and tag not in record.metadata.tags:
            continue
        if needle in haystack:
            results.append(record)
    return results


def create_pack(
    persona_file: Path,
    output_dir: Path,
    *,
    author: str,
    category: str,
    description: str,
    license_name: str = "MIT",
    homepage: str | None = None,
    tags: list[str] | None = None,
    evolved_from: str | None = None,
) -> Path:
    identity = parse_identity_file(persona_file)
    name = persona_file.stem
    output_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(persona_file, output_dir / "persona.yaml")

    evolution_path = persona_file.parent / ".evolution" / f"{persona_file.stem}.json"
    evolution_deltas = None
    if evolution_path.exists():
        target = output_dir / ".evolution" / "deltas.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(evolution_path, target)
        evolution_deltas = ".evolution/deltas.json"

    metadata = PackMetadata(
        name=name,
        author=author,
        version=identity.metadata.version,
        license=license_name,
        description=description,
        category=category,
        requires_personanexus=">=1.5.0",
        tags=tags or [],
        evolved_from=evolved_from,
        evolution_deltas=evolution_deltas,
        homepage=homepage,
        example_usage="README.md#example",
        created=str(identity.metadata.updated_at.date()),
        stats={"install_count": 0, "stars": 0},
    )
    _write_json(output_dir / "pack.json", metadata.model_dump(mode="json"))
    if not (output_dir / "README.md").exists():
        (output_dir / "README.md").write_text(
            (
                f"# {identity.metadata.name}\n\n{description}\n\n## Example\n\n"
                f"```bash\npersonanexus pack install {name}\n```\n"
            ),
            encoding="utf-8",
        )
    return output_dir


def publish_pack(
    pack_dir: Path,
    *,
    repo_root: Path | None = None,
    branch_name: str | None = None,
    create_pr: bool = True,
) -> Path:
    root = repo_root or REPO_ROOT
    metadata = PackMetadata.model_validate(_read_json(pack_dir / "pack.json"))
    destination = root / "packs" / "community" / metadata.author / metadata.name
    if destination.exists():
        raise FileExistsError(f"Pack already exists at {destination}")
    result = validate_pack_dir(pack_dir)
    if result.errors:
        raise ValueError("; ".join(result.errors))

    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(pack_dir, destination)
    build_gallery_index(root / "packs")

    if branch_name:
        subprocess.run(["git", "checkout", "-b", branch_name], cwd=root, check=True)
    subprocess.run(
        ["git", "add", str(destination.relative_to(root)), "packs/_gallery/index.json"],
        cwd=root,
        check=True,
    )
    subprocess.run(
        ["git", "commit", "-m", f"Add pack: {metadata.author}/{metadata.name}"],
        cwd=root,
        check=True,
    )

    if create_pr:
        subprocess.run(
            [
                "gh",
                "pr",
                "create",
                "--title",
                f"Add pack: {metadata.author}/{metadata.name}",
                "--body",
                f"Adds the community pack `{metadata.author}/{metadata.name}`.",
            ],
            cwd=root,
            check=True,
        )
    return destination


def load_gallery_index_from_github(
    *,
    repo: str = DEFAULT_GITHUB_REPO,
    ref: str = DEFAULT_GITHUB_REF,
) -> list[dict[str, Any]]:
    url = f"https://raw.githubusercontent.com/{repo}/{ref}/packs/_gallery/index.json"
    try:
        with urllib.request.urlopen(url) as response:  # noqa: S310
            return cast(list[dict[str, Any]], json.loads(response.read().decode("utf-8")))
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Failed to fetch gallery index: {exc}")
