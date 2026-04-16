"""Structured identity evaluation harness for PersonaNexus."""

from __future__ import annotations

from pathlib import Path
from typing import Any, Literal

import yaml
from pydantic import BaseModel, Field, ValidationError

from personanexus.parser import ParseError
from personanexus.resolver import IdentityResolver, ResolutionError
from personanexus.types import AgentIdentity, Register


class EvalError(Exception):
    """Raised when an eval suite cannot be loaded or executed."""


class EvalWeights(BaseModel):
    persona_consistency: float = Field(0.25, ge=0.0)
    instruction_adherence: float = Field(0.25, ge=0.0)
    guardrails: float = Field(0.25, ge=0.0)
    tone: float = Field(0.25, ge=0.0)

    def normalized(self) -> dict[str, float]:
        raw = self.model_dump()
        total = sum(raw.values())
        if total <= 0:
            return {
                "persona_consistency": 0.25,
                "instruction_adherence": 0.25,
                "guardrails": 0.25,
                "tone": 0.25,
            }
        return {key: value / total for key, value in raw.items()}


class PersonaExpectation(BaseModel):
    min_traits: dict[str, float] = Field(default_factory=dict)
    max_traits: dict[str, float] = Field(default_factory=dict)
    notes_include: list[str] = Field(default_factory=list)


class InstructionExpectation(BaseModel):
    required_principles: list[str] = Field(default_factory=list)
    required_behavior_strategies: list[str] = Field(default_factory=list)
    required_expertise_domains: list[str] = Field(default_factory=list)
    expected_scope: Literal["in_scope", "out_of_scope", "near_scope"] | None = None
    expected_out_of_scope_strategy: str | None = None


class GuardrailExpectation(BaseModel):
    required_hard: list[str] = Field(default_factory=list)
    forbidden_topics: list[str] = Field(default_factory=list)
    required_confirmation_actions: list[str] = Field(default_factory=list)
    forbidden_permissions: list[str] = Field(default_factory=list)


class ToneExpectation(BaseModel):
    register: str | None = None
    tone_keywords: list[str] = Field(default_factory=list)
    preferred_phrases: list[str] = Field(default_factory=list)
    avoided_terms: list[str] = Field(default_factory=list)
    use_headers: bool | None = None
    use_lists: bool | None = None
    use_code_blocks: bool | None = None


class EvalAssertions(BaseModel):
    persona: PersonaExpectation = Field(default_factory=PersonaExpectation)
    instruction_adherence: InstructionExpectation = Field(default_factory=InstructionExpectation)
    guardrails: GuardrailExpectation = Field(default_factory=GuardrailExpectation)
    tone: ToneExpectation = Field(default_factory=ToneExpectation)


class ConversationTurn(BaseModel):
    role: Literal["user", "assistant", "system"]
    content: str


class EvalScenario(BaseModel):
    id: str
    description: str | None = None
    prompt: str | None = None
    conversation: list[ConversationTurn] = Field(default_factory=list)
    assertions: EvalAssertions = Field(default_factory=EvalAssertions)
    weights: EvalWeights | None = None
    # `None` means "inherit from suite defaults"; `0.0` means "any score passes".
    passing_score: float | None = Field(None, ge=0.0, le=1.0)


class EvalSuiteDefaults(BaseModel):
    weights: EvalWeights = Field(default_factory=EvalWeights)
    passing_score: float = Field(0.75, ge=0.0, le=1.0)


class EvalSuite(BaseModel):
    version: str = "1"
    metadata: dict[str, Any] = Field(default_factory=dict)
    defaults: EvalSuiteDefaults = Field(default_factory=EvalSuiteDefaults)
    scenarios: list[EvalScenario] = Field(default_factory=list, min_length=1)


class ScoreCheck(BaseModel):
    label: str
    passed: bool
    expected: str
    actual: str


class DimensionScore(BaseModel):
    name: str
    score: float = Field(ge=0.0, le=1.0)
    checks: list[ScoreCheck] = Field(default_factory=list)


class ScenarioResult(BaseModel):
    scenario_id: str
    description: str | None = None
    weighted_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    dimensions: dict[str, DimensionScore]


class EvalRunResult(BaseModel):
    identity_name: str
    identity_version: str
    suite_name: str
    overall_score: float = Field(ge=0.0, le=1.0)
    passed: bool
    scenarios: list[ScenarioResult]


class ScenarioComparison(BaseModel):
    scenario_id: str
    score_a: float = Field(ge=0.0, le=1.0)
    score_b: float = Field(ge=0.0, le=1.0)
    delta: float
    winner: Literal["a", "b", "tie"]


class EvalComparison(BaseModel):
    identity_a: str
    identity_b: str
    overall_score_a: float = Field(ge=0.0, le=1.0)
    overall_score_b: float = Field(ge=0.0, le=1.0)
    overall_delta: float
    winner: Literal["a", "b", "tie"]
    scenarios: list[ScenarioComparison]


class IdentityEvaluationHarness:
    """Deterministic identity evaluation harness.

    This first slice evaluates whether an identity definition is equipped to
    behave as intended for a scenario by checking explicit identity config:
    traits, principles, behavior strategies, guardrails, scope, and tone.
    """

    def __init__(self, search_paths: list[Path] | None = None):
        self.resolver = IdentityResolver(search_paths=search_paths or [])

    def load_suite(self, suite_path: Path) -> EvalSuite:
        try:
            raw = yaml.safe_load(suite_path.read_text(encoding="utf-8"))
        except FileNotFoundError as exc:
            raise EvalError(f"Eval suite not found: {suite_path}") from exc
        except yaml.YAMLError as exc:
            raise EvalError(f"Failed to parse eval suite: {exc}") from exc

        if not isinstance(raw, dict):
            raise EvalError("Eval suite must be a YAML/JSON object")

        try:
            return EvalSuite.model_validate(raw)
        except ValidationError as exc:
            raise EvalError(f"Invalid eval suite: {exc}") from exc

    def evaluate(self, identity_path: Path, suite_path: Path) -> EvalRunResult:
        suite = self.load_suite(suite_path)
        try:
            identity = self.resolver.resolve_file(identity_path)
        except (ParseError, ResolutionError, ValidationError) as exc:
            raise EvalError(f"Failed to resolve identity: {exc}") from exc

        scenario_results = [
            self._evaluate_scenario(identity, scenario, suite) for scenario in suite.scenarios
        ]
        overall = sum(item.weighted_score for item in scenario_results) / len(scenario_results)
        passed = all(item.passed for item in scenario_results)
        raw_suite_name = suite.metadata.get("name")
        suite_name = str(raw_suite_name) if raw_suite_name else suite_path.stem
        return EvalRunResult(
            identity_name=identity.metadata.name,
            identity_version=identity.metadata.version,
            suite_name=suite_name,
            overall_score=overall,
            passed=passed,
            scenarios=scenario_results,
        )

    def compare(self, run_a: EvalRunResult, run_b: EvalRunResult) -> EvalComparison:
        scenario_map_b = {item.scenario_id: item for item in run_b.scenarios}
        ids_a = {item.scenario_id for item in run_a.scenarios}
        missing_in_b = ids_a - scenario_map_b.keys()
        missing_in_a = scenario_map_b.keys() - ids_a
        if missing_in_b or missing_in_a:
            detail = []
            if missing_in_b:
                detail.append(f"missing in B: {sorted(missing_in_b)}")
            if missing_in_a:
                detail.append(f"missing in A: {sorted(missing_in_a)}")
            raise EvalError(
                "Cannot compare runs with different scenario sets — " + "; ".join(detail)
            )

        scenarios: list[ScenarioComparison] = []
        for item_a in run_a.scenarios:
            item_b = scenario_map_b[item_a.scenario_id]
            delta = item_b.weighted_score - item_a.weighted_score
            winner: Literal["a", "b", "tie"] = "tie"
            if delta > 0.001:
                winner = "b"
            elif delta < -0.001:
                winner = "a"
            scenarios.append(
                ScenarioComparison(
                    scenario_id=item_a.scenario_id,
                    score_a=item_a.weighted_score,
                    score_b=item_b.weighted_score,
                    delta=delta,
                    winner=winner,
                )
            )

        overall_delta = run_b.overall_score - run_a.overall_score
        overall_winner: Literal["a", "b", "tie"] = "tie"
        if overall_delta > 0.001:
            overall_winner = "b"
        elif overall_delta < -0.001:
            overall_winner = "a"

        return EvalComparison(
            identity_a=run_a.identity_name,
            identity_b=run_b.identity_name,
            overall_score_a=run_a.overall_score,
            overall_score_b=run_b.overall_score,
            overall_delta=overall_delta,
            winner=overall_winner,
            scenarios=scenarios,
        )

    def _evaluate_scenario(
        self,
        identity: AgentIdentity,
        scenario: EvalScenario,
        suite: EvalSuite,
    ) -> ScenarioResult:
        weights = (scenario.weights or suite.defaults.weights).normalized()
        passing_score = (
            scenario.passing_score
            if scenario.passing_score is not None
            else suite.defaults.passing_score
        )

        dimensions = {
            "persona_consistency": self._score_persona(identity, scenario),
            "instruction_adherence": self._score_instruction(identity, scenario),
            "guardrails": self._score_guardrails(identity, scenario),
            "tone": self._score_tone(identity, scenario),
        }

        # Dimensions with no checks don't count toward the weighted score — a
        # scenario that asserts nothing about guardrails shouldn't get a free
        # 100% in that slot and inflate the overall result.
        active = {name: dim for name, dim in dimensions.items() if dim.checks}
        if active:
            active_weight_total = sum(weights[name] for name in active)
            if active_weight_total > 0:
                weighted_score = sum(
                    dim.score * weights[name] / active_weight_total for name, dim in active.items()
                )
            else:
                weighted_score = sum(dim.score for dim in active.values()) / len(active)
        else:
            weighted_score = 1.0

        return ScenarioResult(
            scenario_id=scenario.id,
            description=scenario.description,
            weighted_score=weighted_score,
            passed=weighted_score >= passing_score,
            dimensions=dimensions,
        )

    def _score_persona(self, identity: AgentIdentity, scenario: EvalScenario) -> DimensionScore:
        checks: list[ScoreCheck] = []
        traits = identity.personality.traits.defined_traits()
        expected = scenario.assertions.persona

        for trait, minimum in expected.min_traits.items():
            actual = traits.get(trait)
            passed = actual is not None and actual >= minimum
            checks.append(
                ScoreCheck(
                    label=f"trait_min:{trait}",
                    passed=passed,
                    expected=f">= {minimum:.2f}",
                    actual="missing" if actual is None else f"{actual:.2f}",
                )
            )

        for trait, maximum in expected.max_traits.items():
            actual = traits.get(trait)
            passed = actual is not None and actual <= maximum
            checks.append(
                ScoreCheck(
                    label=f"trait_max:{trait}",
                    passed=passed,
                    expected=f"<= {maximum:.2f}",
                    actual="missing" if actual is None else f"{actual:.2f}",
                )
            )

        notes_blob = (identity.personality.notes or "").lower()
        for phrase in expected.notes_include:
            passed = phrase.lower() in notes_blob
            checks.append(
                ScoreCheck(
                    label="personality_notes",
                    passed=passed,
                    expected=f"include '{phrase}'",
                    actual=identity.personality.notes or "",
                )
            )

        return DimensionScore(
            name="persona_consistency",
            score=_score_checks(checks),
            checks=checks,
        )

    def _score_instruction(self, identity: AgentIdentity, scenario: EvalScenario) -> DimensionScore:
        checks: list[ScoreCheck] = []
        expected = scenario.assertions.instruction_adherence

        principle_ids = {item.id for item in identity.principles}
        for principle in expected.required_principles:
            checks.append(
                ScoreCheck(
                    label=f"principle:{principle}",
                    passed=principle in principle_ids,
                    expected="present",
                    actual=", ".join(sorted(principle_ids)),
                )
            )

        strategy_names = set(identity.behavior.strategies.keys())
        for strategy in expected.required_behavior_strategies:
            checks.append(
                ScoreCheck(
                    label=f"behavior:{strategy}",
                    passed=strategy in strategy_names,
                    expected="present",
                    actual=", ".join(sorted(strategy_names)),
                )
            )

        expertise_names = {item.name for item in identity.expertise.domains}
        for domain in expected.required_expertise_domains:
            checks.append(
                ScoreCheck(
                    label=f"expertise:{domain}",
                    passed=domain in expertise_names,
                    expected="present",
                    actual=", ".join(sorted(expertise_names)),
                )
            )

        if expected.expected_scope:
            scope_primary = {item.lower() for item in identity.role.scope.primary}
            scope_secondary = {item.lower() for item in identity.role.scope.secondary}
            scope_out = {item.lower() for item in identity.role.scope.out_of_scope}
            prompt_blob = _scenario_text(scenario)
            if expected.expected_scope == "in_scope":
                matched = any(item in prompt_blob for item in scope_primary | scope_secondary)
                actual = (
                    "matched primary/secondary scope" if matched else "no scope keywords matched"
                )
            elif expected.expected_scope == "out_of_scope":
                matched = any(item in prompt_blob for item in scope_out)
                actual = "matched out_of_scope" if matched else "no out_of_scope keywords matched"
            else:
                matched = not any(item in prompt_blob for item in scope_out)
                actual = "not explicitly out_of_scope" if matched else "matched out_of_scope"
            checks.append(
                ScoreCheck(
                    label="expected_scope",
                    passed=matched,
                    expected=expected.expected_scope,
                    actual=actual,
                )
            )

        if expected.expected_out_of_scope_strategy:
            actual_strategy = identity.expertise.out_of_expertise_strategy.value
            checks.append(
                ScoreCheck(
                    label="out_of_scope_strategy",
                    passed=actual_strategy == expected.expected_out_of_scope_strategy,
                    expected=expected.expected_out_of_scope_strategy,
                    actual=actual_strategy,
                )
            )

        return DimensionScore(
            name="instruction_adherence",
            score=_score_checks(checks),
            checks=checks,
        )

    def _score_guardrails(self, identity: AgentIdentity, scenario: EvalScenario) -> DimensionScore:
        checks: list[ScoreCheck] = []
        expected = scenario.assertions.guardrails
        hard_ids = {item.id for item in identity.guardrails.hard}
        forbidden_categories = {item.category for item in identity.guardrails.topics.forbidden}
        confirmation_actions = {
            item.action for item in identity.guardrails.permissions.requires_confirmation
        }
        forbidden_permissions = set(identity.guardrails.permissions.forbidden)

        for hard in expected.required_hard:
            checks.append(
                ScoreCheck(
                    label=f"hard_guardrail:{hard}",
                    passed=hard in hard_ids,
                    expected="present",
                    actual=", ".join(sorted(hard_ids)),
                )
            )

        for topic in expected.forbidden_topics:
            checks.append(
                ScoreCheck(
                    label=f"forbidden_topic:{topic}",
                    passed=topic in forbidden_categories,
                    expected="forbidden",
                    actual=", ".join(sorted(forbidden_categories)),
                )
            )

        for action in expected.required_confirmation_actions:
            checks.append(
                ScoreCheck(
                    label=f"confirm_action:{action}",
                    passed=action in confirmation_actions,
                    expected="requires_confirmation",
                    actual=", ".join(sorted(confirmation_actions)),
                )
            )

        for permission in expected.forbidden_permissions:
            checks.append(
                ScoreCheck(
                    label=f"forbidden_permission:{permission}",
                    passed=permission in forbidden_permissions,
                    expected="forbidden",
                    actual=", ".join(sorted(forbidden_permissions)),
                )
            )

        return DimensionScore(name="guardrails", score=_score_checks(checks), checks=checks)

    def _score_tone(self, identity: AgentIdentity, scenario: EvalScenario) -> DimensionScore:
        checks: list[ScoreCheck] = []
        expected = scenario.assertions.tone
        tone_default = identity.communication.tone.default
        vocabulary = identity.communication.vocabulary
        preferred = vocabulary.preferred if vocabulary else []
        avoided = vocabulary.avoided if vocabulary else []
        style = identity.communication.style

        if expected.register:
            actual_register = identity.communication.tone.register
            actual_value = (
                actual_register.value
                if isinstance(actual_register, Register)
                else str(actual_register)
            )
            checks.append(
                ScoreCheck(
                    label="register",
                    passed=actual_value == expected.register,
                    expected=expected.register,
                    actual=actual_value,
                )
            )

        tone_blob = tone_default.lower()
        for keyword in expected.tone_keywords:
            checks.append(
                ScoreCheck(
                    label=f"tone_keyword:{keyword}",
                    passed=keyword.lower() in tone_blob,
                    expected=f"keyword '{keyword}'",
                    actual=tone_default,
                )
            )

        for phrase in expected.preferred_phrases:
            checks.append(
                ScoreCheck(
                    label=f"preferred_phrase:{phrase}",
                    passed=phrase in preferred,
                    expected="present",
                    actual=", ".join(preferred),
                )
            )

        for term in expected.avoided_terms:
            checks.append(
                ScoreCheck(
                    label=f"avoided_term:{term}",
                    passed=term in avoided,
                    expected="avoided",
                    actual=", ".join(avoided),
                )
            )

        if expected.use_headers is not None:
            actual_headers = style.use_headers if style else None
            checks.append(
                ScoreCheck(
                    label="use_headers",
                    passed=actual_headers == expected.use_headers,
                    expected=str(expected.use_headers).lower(),
                    actual=str(actual_headers).lower(),
                )
            )
        if expected.use_lists is not None:
            actual_lists = style.use_lists if style else None
            checks.append(
                ScoreCheck(
                    label="use_lists",
                    passed=actual_lists == expected.use_lists,
                    expected=str(expected.use_lists).lower(),
                    actual=str(actual_lists).lower(),
                )
            )
        if expected.use_code_blocks is not None:
            actual_code = style.use_code_blocks if style else None
            checks.append(
                ScoreCheck(
                    label="use_code_blocks",
                    passed=actual_code == expected.use_code_blocks,
                    expected=str(expected.use_code_blocks).lower(),
                    actual=str(actual_code).lower(),
                )
            )

        return DimensionScore(name="tone", score=_score_checks(checks), checks=checks)


def _scenario_text(scenario: EvalScenario) -> str:
    chunks: list[str] = []
    if scenario.prompt:
        chunks.append(scenario.prompt.lower())
    for turn in scenario.conversation:
        chunks.append(turn.content.lower())
    return "\n".join(chunks)


def _score_checks(checks: list[ScoreCheck]) -> float:
    if not checks:
        return 1.0
    return sum(1 for item in checks if item.passed) / len(checks)
