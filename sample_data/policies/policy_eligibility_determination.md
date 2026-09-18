# Policy: Policy Eligibility Determination
## Document ID: POL-OPS-003
## Version: 3.0 | Effective: 2024-01-01
## Category: Operations

### 1. Purpose
This policy governs how cases are evaluated for eligibility under specific exception handling policies when the issue type does not clearly fall under a single policy category, or when multiple policies may apply simultaneously.

### 2. Eligibility Assessment Framework

#### 2.1 Single-Policy Cases
When a case clearly maps to one exception type (e.g., duplicate charge, pending authorization), apply the corresponding policy directly. No eligibility determination is needed.

#### 2.2 Multi-Policy Cases
When two or more policies could apply:
1. List all potentially applicable policies with their document IDs
2. Evaluate the primary cardholder complaint to determine the dominant issue
3. Apply the dominant policy as the primary resolution path
4. Note secondary policies in the case record for audit purposes

#### 2.3 No-Policy Cases
When no existing policy clearly covers the exception:
1. Document why existing policies do not apply
2. Escalate to senior analyst with a recommended approach
3. Senior analyst may create a one-off resolution or recommend a policy update

### 3. Eligibility Criteria by Policy

| Policy | Eligibility Criteria | Disqualifying Factors |
|---|---|---|
| POL-TXN-001 (Duplicate Charge) | Two identical charges within 72 hours | Confirmed split payment or instalment |
| POL-TXN-002 (Pending Auth) | Auth hold exceeding MCC-specific window | Active rental/hotel stay in progress |
| POL-TXN-003 (Refund Reversal) | Refund not posted within expected window | Refund conditional on return receipt |
| POL-TXN-004 (Settlement Delay) | Settlement exceeding MCC-specific window | Pre-order or backorder transaction |
| POL-TXN-005 (Timeline Inconsistency) | Event sequence violates expected order | Known system maintenance window |

### 4. Confidence Requirements
- Cases with clear single-policy eligibility: confidence >= 0.75 for analyst resolution
- Multi-policy cases: confidence >= 0.80 required, or escalate
- No-policy cases: always escalate to senior analyst

### 5. Documentation Requirements
All eligibility determinations must include:
- List of policies considered
- Rationale for policy selection or exclusion
- Confidence score justification
- Any disqualifying factors evaluated and ruled out
