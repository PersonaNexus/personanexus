"""Chartis healthcare problem prototypes (synthetic data, stdlib only).

Every module exposes ``run(seed: int = 42) -> dict`` returning the shared
result contract documented in ``common.result``.
"""

MODULES = ["workforce", "patient_flow", "rural", "denials", "ai_portfolio"]
