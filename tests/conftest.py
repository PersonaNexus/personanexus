"""Shared test fixtures."""

from pathlib import Path

import pytest

EXAMPLES_DIR = Path(__file__).parent.parent / "examples"
FIXTURES_DIR = Path(__file__).parent / "fixtures"


@pytest.fixture
def examples_dir() -> Path:
    return EXAMPLES_DIR


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def ada_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "ada.yaml"


@pytest.fixture
def minimal_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "minimal.yaml"


@pytest.fixture
def analyst_archetype_path(examples_dir: Path) -> Path:
    return examples_dir / "archetypes" / "analyst.yaml"


@pytest.fixture
def empathetic_mixin_path(examples_dir: Path) -> Path:
    return examples_dir / "mixins" / "empathetic.yaml"


@pytest.fixture
def ada_ocean_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "ada-ocean.yaml"


@pytest.fixture
def ada_disc_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "ada-disc.yaml"


@pytest.fixture
def hybrid_path(examples_dir: Path) -> Path:
    return examples_dir / "identities" / "hybrid-example.yaml"
