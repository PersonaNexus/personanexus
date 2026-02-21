"""AI PersonaNexus Framework — define, validate, and compose AI agent identities."""

__version__ = "1.3.0"

from personanexus.analyzer import (
    AnalysisResult,
    ComparisonResult,
    SoulAnalyzer,
)
from personanexus.compiler import (
    OpenClawCompiler,
    SystemPromptCompiler,
    compile_identity,
)
from personanexus.parser import IdentityParser, parse_file, parse_yaml, parse_identity_file
from personanexus.personality import (
    compute_personality_traits,
    disc_to_traits,
    get_disc_preset,
    list_disc_presets,
    ocean_to_traits,
    traits_to_disc,
    traits_to_ocean,
)
from personanexus.resolver import IdentityResolver
from personanexus.team_types import (
    TeamConfiguration,
    TeamComposition,
    TeamSpec,
)
from personanexus.types import (
    AgentIdentity,
    DiscProfile,
    OceanProfile,
    PersonalityMode,
    PersonalityProfile,
)
from personanexus.validator import IdentityValidator, ValidationResult

__all__ = [
    "AgentIdentity",
    "AnalysisResult",
    "ComparisonResult",
    "DiscProfile",
    "IdentityParser",
    "IdentityResolver",
    "IdentityValidator",
    "OceanProfile",
    "OpenClawCompiler",
    "PersonalityMode",
    "PersonalityProfile",
    "SoulAnalyzer",
    "SystemPromptCompiler",
    "TeamComposition",
    "TeamConfiguration",
    "TeamSpec",
    "ValidationResult",
    "compile_identity",
    "compute_personality_traits",
    "disc_to_traits",
    "get_disc_preset",
    "list_disc_presets",
    "ocean_to_traits",
    "parse_file",
    "parse_identity_file",
    "parse_yaml",
    "traits_to_disc",
    "traits_to_ocean",
]
