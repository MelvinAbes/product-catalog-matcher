# Security policy

## Supported version

Security fixes are applied to the current `main` branch. This project does not currently publish
versioned releases with separate support windows.

## Reporting a vulnerability

Please use GitHub's private vulnerability reporting for this repository when available. Include
the affected endpoint or component, reproduction steps, impact, and a suggested mitigation if
known. Do not open a public issue for an unpatched vulnerability or include live credentials,
supplier data, or personal information in a report.

## Security boundaries

The local deployment is a development environment. It does not provide authentication,
authorization, tenant isolation, transport-layer encryption, or malware scanning for uploaded
files. Do not expose it to an untrusted network without adding those controls.

Uploads are limited by bytes and row count, parsed as UTF-8 CSV or JSON, and stored with a content
hash. Containers use pinned base images; both services run as non-root users, and the application
also uses a read-only root filesystem and dropped Linux capabilities. CI audits locked Python
dependencies, scans repository history for secrets, scans configuration and container images,
and runs integration and smoke tests.

Never commit environment files, database dumps, access tokens, real supplier feeds, or model
credentials. Rotate a secret immediately if it is exposed, then remove it from all active
systems; deleting it in a later commit is not sufficient.
