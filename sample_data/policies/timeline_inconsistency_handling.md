# Policy: Timeline Inconsistency Handling
## Document ID: POL-TXN-005
## Version: 2.0 | Effective: 2024-01-01
## Category: Transaction Exceptions

### 1. Definition
A timeline inconsistency occurs when the sequence or timing of transaction events (authorization, settlement, refund, reversal) does not follow the expected chronological order or contains gaps that cannot be explained by normal processing delays.

### 2. Common Patterns
- Settlement posted before authorization recorded
- Refund posted without corresponding original charge
- Authorization date significantly after cardholder-reported purchase date
- Multiple authorization timestamps for a single transaction
- Settlement amount different from authorization with no amendment record

### 3. Investigation Procedure

#### 3.1 Initial Assessment
1. Pull full transaction timeline using `get_transaction_timeline`
2. Compare authorization date, settlement date, and posting date
3. Check for any reversals or amendments in the timeline
4. Verify merchant settlement batch timing

#### 3.2 Variance Thresholds
| Variance Type | Acceptable Window | Action Required |
|---|---|---|
| Auth-to-settlement gap | 1-7 business days | No action |
| Auth-to-settlement gap | 8-14 business days | Monitor |
| Auth-to-settlement gap | 15+ business days | Request additional info |
| Settlement before auth | Any | Escalate immediately |
| Amount variance (auth vs settlement) | Within 20% (restaurants, gas) | Acceptable per MCC rules |
| Amount variance (auth vs settlement) | > 20% or > $50 difference | Request merchant clarification |

#### 3.3 Resolution Paths
- **Request Additional Info**: When timeline gaps are explainable but need merchant confirmation
- **Close No Action**: When variance falls within acceptable thresholds per MCC rules
- **Escalate**: When settlement precedes authorization or timeline suggests system error

### 4. Evidence Requirements
All timeline inconsistency investigations must document:
- Full transaction timeline with all event timestamps
- MCC code and applicable variance rules
- Merchant batch submission records (if obtainable)
- Any cardholder-provided receipts or documentation

### 5. Escalation Criteria
Escalate to Level 2 (Supervisor) when:
- Timeline suggests potential system-level processing error
- Pattern affects multiple transactions on the same account
- Merchant's processor reports no matching record
