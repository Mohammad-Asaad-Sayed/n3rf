# Security Policy

## Supported versions

Security fixes are made against the latest code on the default branch. Older revisions and
unreleased forks may not receive security updates.

## Reporting a vulnerability

Please report suspected vulnerabilities privately. On GitHub, use the repository's **Security**
tab and choose **Report a vulnerability** to start a private security advisory. Do not open a
public issue or pull request with exploit details.

If private vulnerability reporting is unavailable, contact the repository maintainer through
their GitHub profile and ask for a private channel before sharing technical details.

Include, when possible:

- The affected version, commit, or component.
- A concise description of the security impact.
- Reproduction steps or a minimal proof of concept that does not access other people's data.
- Any relevant logs with credentials, tokens, and personal data removed.

Please allow maintainers a reasonable opportunity to investigate and prepare a fix before
publicly disclosing the issue. We aim to acknowledge reports within five business days and
provide an update as the investigation progresses. These are targets, not a guaranteed service
level.

Do not test against systems, accounts, model providers, or data that you do not own or have
explicit permission to assess. If you discover an exposed credential, avoid using it and notify
the owner; the owner should revoke or rotate it promptly.

## Deployment security notes

n3rf is intended for a trusted, single-operator local deployment. The Code node runs user
workflow code in a resource-limited child process, but its Python sandbox is not a security
boundary for untrusted users or multi-tenant hosting. Do not expose the application to an
untrusted network or allow untrusted people to submit Code-node workflows.

Provider API keys should be supplied to the FastAPI process through environment variables.
Model profiles store the variable name, not the secret. As a second mode, an Ask AI
node (or a model connection test) accepts a pasted key for that one request only:
it is kept in memory, sent to the provider, and never written to SQLite, run
history, logs, or the browser draft (the env-var name is left blank to use an
environment variable, and a pasted key takes precedence for that request).
Treat workflow data, run history,
uploaded files, and the SQLite database as potentially sensitive; secure access to the host and
back up or delete this data according to your needs.

See [README.md](./README.md) for local setup and configuration.
