# Security Policy

## Supported Versions

| Version | Supported          |
|---------|--------------------|
| 0.1.x   | Yes                |

## Reporting a Vulnerability

If you discover a security vulnerability in LedgerDesk, please report it responsibly.

**Do not open a public GitHub issue for security vulnerabilities.**

Instead, please email: **security@ledgerdesk.dev**

Include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Suggested fix (if any)

We will acknowledge receipt within 48 hours and aim to provide a fix within 7 days for critical issues.

## Security Considerations

LedgerDesk is designed for internal financial operations. Key security controls include:

- **Authentication**: JWT-based auth with bcrypt password hashing
- **Authorization**: Role-based access (analyst, senior_analyst, supervisor, admin)
- **Audit logging**: Every action is recorded with actor, timestamp, and trace ID
- **Input validation**: All inputs validated via Pydantic schemas
- **SQL injection prevention**: SQLAlchemy ORM with parameterized queries
- **CORS**: Restricted to configured origins only
- **Secrets management**: All secrets loaded from environment variables
- **Human-in-the-loop**: Agent recommendations require analyst approval before execution
