# Security Policy

## Supported versions

biblioteq-web is maintained on a best-effort basis. Security fixes are made
against the latest minor release line only. Fixes land in the newest patch
release of that line; earlier minor lines are not patched.

| Version | Supported |
| --- | --- |
| Latest minor line (current patch release) | ✅ |
| Earlier minor lines and all older releases | ❌ |

If you run a deployment that cannot be upgraded quickly, say so when you
report, and we can discuss options.

## Reporting a vulnerability

Please do not report security vulnerabilities through public GitHub issues,
discussions, or pull requests.

Use GitHub's private vulnerability reporting on this repository: open the
**Security** tab and choose **Report a vulnerability**. This opens a private
advisory visible only to you and the maintainer, and is the only supported
reporting channel.

Please include, as far as you can:

- the affected version or commit,
- the deployment shape (PostgreSQL or SQLite, reverse proxy, sub-path hosting),
- steps to reproduce, or a proof of concept,
- the impact you believe it has,
- how you would like to be credited, if at all.

## What to expect

| Stage | Target |
| --- | --- |
| Acknowledgement of your report | 5 business days |
| Initial assessment and severity | 10 business days |
| Fix for high or critical issues | 30 days |
| Fix for moderate or low issues | 90 days |

These are targets, not guarantees: this is a single-maintainer project. We will
tell you if a timeline slips, and we will keep you informed of progress. If a
report is out of scope we will say so and explain why.

## Scope

### In scope

- Vulnerabilities in the application code in `app/`, `static/`, and the
  container and deployment files shipped in this repository.
- SQL injection, including anything that defeats the parameterized-query and
  item-type registry design.
- Cross-site scripting and template injection in server-rendered pages.
- Path traversal or identifier confusion in routes such as `/cover/{type}/{id}`,
  `/item/{type}/{id}`, and `/browse/{type}`.
- Exposure of data beyond what the application is documented to read.
- Credential or connection-string leakage through errors, logs, or the health
  endpoints.
- Vulnerabilities in our own code that arise from a dependency, where the
  dependency is used in a way that makes the issue exploitable here.

### Out of scope

- **Deployments without access control.** biblioteq-web has no authentication
  of its own by design. A public catalog is a valid deployment, but an operator
  who needs access control must provide it in the reverse proxy. "The site has
  no login" is not a vulnerability.
- Missing TLS, missing security headers, permissive CORS, or other proxy and
  web-server configuration. See `docs/deploy/` and ADR-0004.
- Volumetric or resource-exhaustion denial of service, and rate limiting.
- Vulnerabilities in BiblioteQ itself (`textbrowser/biblioteq`) or in the
  upstream database engines. Report those to the relevant upstream project.
- Dependency versions with a published CVE that are not exploitable in
  biblioteq-web as configured.
- Findings from automated scanners reported without a demonstrated impact.
- Social engineering, and physical attacks on an operator's host.

## Disclosure policy

We follow coordinated disclosure. We ask that you give us 90 days from
acknowledgement before publishing details, so that operators have time to
upgrade. We are happy to publish earlier by mutual agreement once a fix is
available, and we will not ask you to extend the window indefinitely.

Where a vulnerability warrants it, we will request a CVE through GitHub's
advisory process. Fixes are noted in `CHANGELOG.md`, and advisories are
published on this repository.

## Credit

We are glad to credit reporters by name or handle in the advisory and the
changelog. Tell us how you would like to be credited, or say that you would
rather not be named — we will respect either.

## No bug bounty

There is no paid bug bounty program. We are grateful for reports regardless.

## Safe harbour

We consider security research conducted in good faith under this policy to be
authorized. If you stay within the scope above, avoid privacy violations,
avoid degrading service for other users, and give us reasonable time to
respond before disclosure, we will not pursue or support legal action against
you, and we will say so publicly if asked. This does not waive any rights of
third parties, including operators of individual deployments.

## Security design notes for operators

Understanding the intended design helps you tell a vulnerability from a
misconfiguration:

- The application is strictly read-only and never writes to the database.
- Borrower personal data is never read or displayed; availability is computed
  from counts only.
- The recommended PostgreSQL role grants `SELECT` on item tables and
  column-level `SELECT (item_oid, type)` on `item_borrower`, so borrower
  identities stay unreadable even if the application is compromised. SQLite
  deployments should mount the database read-only and open it read-only.
- There is no authentication layer. Put access control in the reverse proxy
  (basic auth, IP allow-list, or an OIDC proxy) if the catalog is not meant to
  be public, and terminate TLS there.
- `/healthz` and `/readyz` are unauthenticated and are intended for load
  balancers and supervision. Do not expose them more widely than necessary.
- Run the service on a loopback address behind the proxy, as in the example
  systemd and nginx configuration.
