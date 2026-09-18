# Policy: Account Servicing Exception Handling
## Document ID: POL-ACCT-001
## Version: 2.0 | Effective: 2024-01-01
## Category: Account Management

### 1. Definition
Account servicing exceptions are non-transaction-specific issues that affect the overall account state, including credit limit discrepancies, statement errors, fee disputes, account status changes, and cross-account posting errors.

### 2. Exception Types

#### 2.1 Credit Limit Discrepancies
- Available credit does not reflect recent payments
- Temporary credit limit increase not applied
- Credit limit reduction without notification
- **Resolution**: Verify payment posting, check for pending authorizations reducing available credit

#### 2.2 Statement Errors
- Incorrect balance carried forward
- Missing transactions on statement
- Duplicate entries on statement
- **Resolution**: Reconcile against transaction ledger, issue corrected statement if confirmed

#### 2.3 Fee Disputes
- Late payment fee charged despite on-time payment
- Annual fee charged after account downgrade
- Foreign transaction fee on domestic purchase
- **Resolution**: Verify fee eligibility, reverse if charged in error

#### 2.4 Account Status Issues
- Account restricted without documented cause
- Fraud hold placed in error
- Account closure processed without cardholder request
- **Resolution**: Review account flags, escalate to account management team

### 3. Investigation Procedure

#### 3.1 Required Tools
1. `get_account_activity` - Full account status and recent transactions
2. `get_transaction_timeline` - Chronological event log
3. `search_similar_cases` - Check for systemic issues affecting multiple accounts

#### 3.2 Resolution Authority
| Exception Sub-type | Resolution Level | Max Adjustment |
|---|---|---|
| Fee reversal | Analyst | $500 |
| Credit posting correction | Analyst | $5,000 |
| Statement correction | Senior Analyst | N/A |
| Account status change | Supervisor | N/A |
| Cross-account correction | Operations Manager | N/A |

### 4. Escalation Triggers
Escalate immediately when:
- Exception affects account balances > $10,000
- Multiple accounts show the same exception pattern (systemic issue)
- Account has active fraud investigation
- Cardholder is a VIP/premium tier member with prior escalations

### 5. Documentation Requirements
- Screenshot or reference to the account state showing the exception
- Timeline of events leading to the exception
- All fee calculations or balance reconciliation work
- Cardholder communication log
