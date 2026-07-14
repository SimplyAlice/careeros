# Security Architecture

## 1. Threat-to-Control Mapping

| Concern | Control |
|---|---|
| Password compromise | Hashed with bcrypt/argon2, never logged, never returned in any API response |
| Transport interception | HTTPS enforced everywhere (App Service managed/custom certs) |
| Token theft (XSS) | Refresh token in httpOnly, Secure, SameSite=Strict cookie — never accessible to JS, never in localStorage |
| Stolen/leaked refresh token | Refresh tokens stored hashed with a server-side revocation list — logout-everywhere and password-change invalidation both work |
| Unauthorized data access | Role-based dependency injection (`require_role`) at the route level; resource ownership checks scoped by verified JWT `user_id`, never by client-supplied ID |
| Secret leakage | Azure Key Vault in cloud (accessed via managed identity — no stored access key), `.env` (gitignored) locally, `.env.example` with placeholders only committed |
| SQL injection | SQLAlchemy parameterized queries exclusively; no raw string-interpolated SQL anywhere in the codebase |
| XSS | React escapes by default; any `dangerouslySetInnerHTML` usage (e.g. rendering AI-generated rich text) passes through `DOMPurify` first |
| CSRF | SameSite=Strict cookie for the refresh token + bearer-token auth (not cookie-based auth) for state-changing requests |
| Credential stuffing / brute force | Stricter, separate rate limits on `/auth/login` and `/auth/register` |
| Malicious file upload | Server-side type/size validation (not just extension check); stored in private Blob containers; served via short-lived signed URLs; never executed |
| Insider/accidental misuse | Append-only `audit_logs` for security-relevant events (login, password change, data export/delete), access-restricted separately from operational logs |
| Dependency vulnerabilities | `pip-audit` / `npm audit` run in CI; Dependabot enabled on the repo |
| Automated-action abuse (e.g. auto-apply spam) | Full-auto submission requires explicit per-portal opt-in (`auto_apply_enabled`, default false), and every action is tagged `applied_via` for audit |

## 2. Authentication & Session Model

See `architecture/api-design.md` for the full auth sequence diagram. Key
security-relevant properties:

- Short-lived access tokens (~15 min) limit the exposure window if one is
  intercepted.
- Refresh tokens are the only long-lived credential, and they're revocable —
  a compromised refresh token can be invalidated without forcing a password
  reset.
- Password change and "logout everywhere" both work by revoking all
  outstanding refresh tokens for a user in one DB operation.

## 3. Authorization Model

- `users.role` (`user`, `admin`) drives route-level access via FastAPI
  dependencies.
- All data-access queries are scoped by the authenticated user's ID extracted
  from the verified JWT — never trusted from a URL path parameter or request
  body. A request for `/applications/{id}` additionally verifies the
  application belongs to the requesting user before returning it (object-level
  authorization, not just endpoint-level).

## 4. Secure File Handling

- Uploaded documents (resumes users bring in) are validated server-side by
  actual content type, not filename extension.
- Stored in a private Blob container — no public read access at any point.
- Served back to the client via short-lived SAS tokens or an authenticated
  proxy endpoint, never a permanent public URL.
- Never executed, parsed by a vulnerable library without sandboxing, or
  passed to any code-execution path.

## 5. AI-Specific Security Considerations

- Prompt inputs (job descriptions, user profile data) are treated as
  untrusted text — the system prompt constrains the model's behavior (no
  fabricated facts, no acting outside the defined task), reducing the blast
  radius of prompt-injection attempts embedded in a scraped job description.
- Generated content is never auto-executed or auto-submitted without a human
  review step — this is a security property as much as a product one: an
  injected instruction in a job description can't cause the system to take an
  unreviewed automated action.

## 6. Known Limitations (documented, not hidden)

Being upfront about what v1 does **not** cover is itself a sign of engineering
maturity for a portfolio project:

- No formal penetration test has been performed — CI-based dependency
  scanning and secure-coding practices are the current control, not a
  substitute for one.
- No WAF (Web Application Firewall) in front of the API in v1 — a reasonable
  addition once the app is internet-facing with real traffic, tracked as a
  future improvement.
- Rate limiting is application-level (not yet enforced at a CDN/edge layer) —
  acceptable at current scale, documented as a scaling trigger.
