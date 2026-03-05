"""AI PersonaNexus Framework — define, validate, and compose AI agent identities."""

__version__ = "1.4.1"

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
from personanexus.conflict import MergeTrace, MergeTraceEntry
from personanexus.drift import (
    DriftReport,
    detect_drift,
    detect_drift_from_files,
    format_drift_report,
)
from personanexus.dynamics import (
    DynamicSession,
    DynamicsResult,
    InteractionContext,
    apply_dynamics_to_traits,
    run_dynamics_pipeline,
)
from personanexus.linter import IdentityLinter, LintWarning
from personanexus.memory import (
    MemoryBackendJSON,
    UserState,
    record_interaction,
    update_sentiment,
    update_trust,
)
from personanexus.parser import IdentityParser, parse_file, parse_identity_file, parse_yaml
from personanexus.personality import (
    compute_personality_traits,
    disc_to_traits,
    get_disc_preset,
    get_jungian_preset,
    jungian_to_traits,
    list_disc_presets,
    list_jungian_presets,
    ocean_to_traits,
    traits_to_disc,
    traits_to_jungian,
    traits_to_ocean,
)
from personanexus.resolver import IdentityResolver
from personanexus.team_types import (
    TeamComposition,
    TeamConfiguration,
    TeamSpec,
)
from personanexus.types import (
    TRAIT_ORDER,
    AgentIdentity,
    DiscProfile,
    DynamicMode,
    DynamicMood,
    DynamicsConfig,
    DynamicTrigger,
    JungianProfile,
    MemoryInfluenceRule,
    OceanProfile,
    PersonalityMode,
    PersonalityProfile,
)
from personanexus.validator import IdentityValidator, ValidationResult

__all__ = [
    "AgentIdentity",
    "DynamicSession",
    "DynamicsConfig",
    "DynamicMood",
    "DynamicMode",
    "DynamicTrigger",
    "DynamicsResult",
    "InteractionContext",
    "MemoryBackendJSON",
    "MemoryInfluenceRule",
    "UserState",
    "apply_dynamics_to_traits",
    "record_interaction",
    "run_dynamics_pipeline",
    "update_sentiment",
    "update_trust",
    "IdentityLinter",
    "LintWarning",
    "AnalysisResult",
    "ComparisonResult",
    "DriftReport",
    "detect_drift",
    "detect_drift_from_files",
    "format_drift_report",
    "DiscProfile",
    "IdentityParser",
    "IdentityResolver",
    "IdentityValidator",
    "JungianProfile",
    "MergeTrace",
    "MergeTraceEntry",
    "OceanProfile",
    "OpenClawCompiler",
    "PersonalityMode",
    "PersonalityProfile",
    "SoulAnalyzer",
    "SystemPromptCompiler",
    "TeamComposition",
    "TeamConfiguration",
    "TRAIT_ORDER",
    "TeamSpec",
    "ValidationResult",
    "compile_identity",
    "compute_personality_traits",
    "disc_to_traits",
    "get_disc_preset",
    "get_jungian_preset",
    "jungian_to_traits",
    "list_disc_presets",
    "list_jungian_presets",
    "ocean_to_traits",
    "parse_file",
    "parse_identity_file",
    "parse_yaml",
    "traits_to_disc",
    "traits_to_jungian",
    "traits_to_ocean",
]
