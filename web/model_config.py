"""Model configuration and multi-provider chat simulation.

Provides a ModelConfig dataclass for target model selection and
functions for rendering the config UI and running chat simulations
across multiple LLM providers (Anthropic, OpenAI, Google).
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Any

import streamlit as st

# ---------------------------------------------------------------------------
# Provider / model catalogue
# ---------------------------------------------------------------------------

PROVIDER_MODELS: dict[str, list[str]] = {
    "Anthropic": [
        "claude-opus-4",
        "claude-sonnet-4",
        "claude-haiku-4",
    ],
    "OpenAI": [
        "gpt-4o",
        "gpt-4o-mini",
        "o1",
        "o3-mini",
    ],
    "Google": [
        "gemini-2.0-flash",
        "gemini-2.0-pro",
    ],
    "Meta (via API)": [
        "llama-3.3-70b",
        "llama-3.1-405b",
    ],
    "Custom": [],
}

PROVIDER_ENV_KEYS: dict[str, str] = {
    "Anthropic": "ANTHROPIC_API_KEY",
    "OpenAI": "OPENAI_API_KEY",
    "Google": "GOOGLE_API_KEY",
}


# ---------------------------------------------------------------------------
# ModelConfig dataclass
# ---------------------------------------------------------------------------


@dataclass
class ModelConfig:
    """Target model configuration for identity export and chat."""

    provider: str = "Anthropic"
    model_name: str = "claude-sonnet-4"
    temperature: float = 0.7
    max_tokens: int = 4096
    top_p: float = 0.9

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a dict suitable for OpenClaw model_config."""
        return {
            "primary_model": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "top_p": self.top_p,
        }


# ---------------------------------------------------------------------------
# UI rendering
# ---------------------------------------------------------------------------


def render_model_config(key_prefix: str = "mc") -> ModelConfig:
    """Render model configuration UI and return the selected config."""
    provider = st.selectbox(
        "Provider",
        list(PROVIDER_MODELS.keys()),
        key=f"{key_prefix}_provider",
    )

    models = PROVIDER_MODELS.get(provider, [])
    if models:
        model_name = st.selectbox(
            "Model",
            models,
            key=f"{key_prefix}_model",
        )
    else:
        model_name = st.text_input(
            "Model name",
            value="custom-model",
            key=f"{key_prefix}_model_custom",
        )

    col_t, col_m = st.columns(2)
    with col_t:
        temperature = st.slider(
            "Temperature",
            0.0, 2.0, 0.7,
            step=0.1,
            help="Lower = more focused and deterministic. Higher = more creative.",
            key=f"{key_prefix}_temp",
        )
    with col_m:
        max_tokens = st.number_input(
            "Max tokens",
            min_value=256,
            max_value=32768,
            value=4096,
            step=256,
            key=f"{key_prefix}_max_tokens",
        )

    env_key = PROVIDER_ENV_KEYS.get(provider)
    if env_key:
        has_key = bool(os.environ.get(env_key))
        if has_key:
            st.success(f"`{env_key}` detected \u2014 chat simulation available")
        else:
            st.info(f"Set `{env_key}` to enable live chat with {provider}")

    return ModelConfig(
        provider=provider,
        model_name=model_name,
        temperature=temperature,
        max_tokens=int(max_tokens),
    )


# ---------------------------------------------------------------------------
# Multi-provider chat
# ---------------------------------------------------------------------------


def run_chat(
    system_prompt: str,
    messages: list[dict[str, str]],
    config: ModelConfig,
) -> str | None:
    """Run a single chat completion against the selected provider.

    Returns the assistant reply text, or None if the provider
    is unavailable or missing an API key.
    """
    provider = config.provider

    # --- Anthropic ---
    if provider == "Anthropic":
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            st.info("Set `ANTHROPIC_API_KEY` to enable live chat with Anthropic.")
            return None
        try:
            import anthropic  # noqa: E402

            client = anthropic.Anthropic(api_key=api_key)
            # Anthropic expects messages without the system role
            user_messages = [
                {"role": m["role"], "content": m["content"]}
                for m in messages
                if m["role"] in ("user", "assistant")
            ]
            response = client.messages.create(
                model=config.model_name,
                system=system_prompt,
                messages=user_messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            return response.content[0].text
        except Exception as e:
            st.error(f"Anthropic chat error: {e}")
            return None

    # --- OpenAI ---
    if provider == "OpenAI":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            st.info("Set `OPENAI_API_KEY` to enable live chat with OpenAI.")
            return None
        try:
            from openai import OpenAI  # noqa: E402

            client = OpenAI(api_key=api_key)
            response = client.chat.completions.create(
                model=config.model_name,
                messages=[{"role": "system", "content": system_prompt}] + messages,
                temperature=config.temperature,
                max_tokens=config.max_tokens,
            )
            return response.choices[0].message.content
        except Exception as e:
            st.error(f"OpenAI chat error: {e}")
            return None

    # --- Google ---
    if provider == "Google":
        api_key = os.environ.get("GOOGLE_API_KEY")
        if not api_key:
            st.info("Set `GOOGLE_API_KEY` to enable live chat with Google.")
            return None
        try:
            import google.generativeai as genai  # noqa: E402

            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                config.model_name,
                system_instruction=system_prompt,
            )
            # Build conversation history
            history = []
            for m in messages[:-1]:
                role = "user" if m["role"] == "user" else "model"
                history.append({"role": role, "parts": [m["content"]]})
            chat = model.start_chat(history=history)
            last_msg = messages[-1]["content"] if messages else ""
            response = chat.send_message(last_msg)
            return response.text
        except Exception as e:
            st.error(f"Google chat error: {e}")
            return None

    # --- Fallback ---
    st.info(f"Chat simulation is not available for **{provider}**. "
            "Select Anthropic, OpenAI, or Google for live chat.")
    return None
