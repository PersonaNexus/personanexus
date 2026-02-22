# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 1.4.x   | :white_check_mark: |
| < 1.4   | :x:                |

## Reporting a Vulnerability

If you discover a security vulnerability in PersonaNexus, please report it responsibly:

1. **Do not** open a public GitHub issue for security vulnerabilities.
2. Email the maintainers at the address listed in `pyproject.toml` with:
   - A description of the vulnerability
   - Steps to reproduce
   - Potential impact
3. You should receive an acknowledgment within 48 hours.
4. We will work with you to understand and address the issue before any public disclosure.

## Scope

PersonaNexus is a library for defining and validating AI agent identity configurations. Security concerns relevant to this project include:

- **YAML parsing vulnerabilities** — we use `yaml.safe_load()` exclusively to prevent arbitrary code execution
- **Path traversal** — file resolution (archetypes, mixins) is constrained to configured search paths
- **Dependency vulnerabilities** — we monitor dependencies for known CVEs

## Out of Scope

- Vulnerabilities in the AI models or platforms that consume compiled identity files
- Social engineering attacks using crafted personality configurations
- Issues in the optional Streamlit web UI (`web/` directory) when exposed to untrusted networks

## Best Practices

When using PersonaNexus in production:

- Validate all identity files before deployment (`personanexus validate`)
- Review compiled system prompts before sending to LLM APIs
- Store identity files in version control with appropriate access controls
- Do not embed secrets or API keys in identity YAML files
