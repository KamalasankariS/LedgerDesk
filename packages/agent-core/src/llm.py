"""LLM client abstraction."""

import json
import re

import structlog
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential

logger = structlog.get_logger()


class LLMClient:
    """OpenAI-compatible LLM client."""

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        model: str = "gpt-4o",
    ):
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(min=1, max=10))
    async def complete(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.2,
        max_tokens: int = 4000,
    ) -> str:
        """Send a completion request and return the response text."""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                f"{self.base_url}/chat/completions",
                headers={"Authorization": f"Bearer {self.api_key}"},
                json={
                    "model": self.model,
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                },
            )
            resp.raise_for_status()
            data = resp.json()
            return data["choices"][0]["message"]["content"]

    async def complete_json(
        self,
        prompt: str,
        system_prompt: str | None = None,
        temperature: float = 0.1,
    ) -> dict:
        """Send a completion request and parse the response as JSON."""
        text = await self.complete(prompt, system_prompt, temperature)
        return parse_json_response(text)


def parse_json_response(text: str) -> dict:
    """Extract and parse JSON from LLM response text."""
    # Try direct parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", text, re.DOTALL)
    if json_match:
        try:
            return json.loads(json_match.group(1))
        except json.JSONDecodeError:
            pass

    # Try finding first { to last }
    start = text.find("{")
    end = text.rfind("}")
    if start >= 0 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except json.JSONDecodeError:
            pass

    logger.error("json_parse_failed", text=text[:200])
    raise ValueError(f"Could not parse JSON from LLM response: {text[:200]}")


class MockLLMClient:
    """Mock LLM client for development without an API key."""

    async def complete(self, prompt: str, **kwargs) -> str:
        return await self.complete_json(prompt, **kwargs).__str__()

    async def complete_json(self, prompt: str, **kwargs) -> dict:
        """Return realistic mock responses based on prompt content."""
        prompt_lower = prompt.lower()

        if "triage agent" in prompt_lower:
            return self._mock_triage(prompt)
        elif "tool planning agent" in prompt_lower:
            return self._mock_tool_plan(prompt)
        elif "decision agent" in prompt_lower:
            return self._mock_decision(prompt)
        elif "safety validation agent" in prompt_lower:
            return self._mock_safety(prompt)
        elif "case documentation agent" in prompt_lower:
            return self._mock_case_writer(prompt)
        else:
            return {"response": "Mock response", "status": "ok"}

    def _mock_triage(self, prompt: str) -> dict:
        issue_type = "duplicate_charge"
        p = prompt.lower()
        if "authorization" in p or "pending" in p or "hold" in p:
            issue_type = "pending_authorization"
        elif "refund" in p:
            issue_type = "refund_mismatch"
        elif "settlement" in p or "delay" in p:
            issue_type = "settlement_delay"
        elif "reversal" in p or "partial" in p:
            issue_type = "reversal_confusion"
        elif "descriptor" in p or "recognize" in p or "mismatch" in p:
            issue_type = "merchant_reference_mismatch"
        elif "timeline" in p or "sequence" in p or "order" in p:
            issue_type = "timeline_inconsistency"
        elif "eligib" in p or "multiple polic" in p or "which policy" in p:
            issue_type = "policy_eligibility"
        elif "credit limit" in p or "statement" in p or "fee" in p or "account status" in p:
            issue_type = "account_servicing_exception"

        return {
            "issue_type": issue_type,
            "confidence": 0.87,
            "entities": {
                "transaction_ids": [],
                "amounts": [],
                "dates": [],
                "merchants": [],
                "key_facts": ["Case classified by triage agent"],
            },
            "priority_adjustment": None,
            "reasoning": f"Classified as {issue_type} based on case description keywords and context.",
        }

    def _mock_tool_plan(self, prompt: str) -> dict:
        tools = [
            {
                "tool_name": "get_transaction_timeline",
                "params": {"transaction_id": "from_case"},
                "priority": 1,
                "reason": "Review transaction history",
            },
            {
                "tool_name": "get_account_activity",
                "params": {"account_id": "from_case"},
                "priority": 2,
                "reason": "Check account context",
            },
        ]
        if "refund" in prompt.lower():
            tools.append(
                {
                    "tool_name": "get_refund_status",
                    "params": {"reference_id": "from_case"},
                    "priority": 1,
                    "reason": "Check refund status",
                }
            )
        if "settlement" in prompt.lower():
            tools.append(
                {
                    "tool_name": "get_settlement_status",
                    "params": {"reference_id": "from_case"},
                    "priority": 1,
                    "reason": "Check settlement",
                }
            )

        return {
            "tools": tools,
            "reasoning": "Selected tools based on case type and available identifiers.",
        }

    def _mock_decision(self, prompt: str) -> dict:  # noqa: C901
        """Generate a detailed, case-specific mock recommendation."""
        p = prompt.lower()

        # ── Handle new issue types first ──────────────────────────────
        if "timeline" in p and ("inconsisten" in p or "sequence" in p or "before auth" in p):
            return self._mock_decision_timeline(p)
        elif ("eligib" in p or "multiple polic" in p or "which policy" in p
              or "no matching policy" in p or "cryptocurrency" in p):
            return self._mock_decision_eligibility(p)
        elif ("late fee" in p or "credit limit" in p or "statement error" in p
              or "account status" in p or "fee charged" in p or "fee reversal" in p):
            return self._mock_decision_account_exception(p)

        # ── Determine action & confidence ──────────────────────────────
        if "refund" in p and (
            "exceeds" in p or "greater than" in p or "more than" in p
        ):
            action = "initiate_merchant_dispute"
            confidence = 0.85
            risk = "medium"
            res_days = 10
            needs_merch = True
            needs_ch = True
            approval = "analyst"
            rationale = (
                "The refund amount posted to this account exceeds the original transaction charge, "
                "which constitutes an overpayment error that falls squarely within the merchant dispute "
                "framework. The transaction timeline confirms the original purchase date, amount, and "
                "merchant, and the subsequent refund credit exceeds that baseline figure.\n\n"
                "Under the Transaction Exception Policy (Section 2.2 — Refund Integrity Controls), "
                "any refund that exceeds the original settled amount must be challenged through the "
                "card network dispute channel within 60 days of posting. The policy requires the "
                "analyst to verify the original settlement record, confirm the merchant's refund "
                "instruction, and flag the delta amount for chargeback processing.\n\n"
                "The retrieved policy evidence (RAG retrieval: 'Refund Mismatch Resolution') "
                "specifies that amounts exceeding the original charge by more than $0.01 trigger "
                "mandatory dispute initiation rather than a simple write-off. Given the overage "
                "identified in this case, initiating a merchant dispute is the correct and policy-"
                "compliant path. Cardholder notification is required within 2 business days of "
                "dispute filing per Reg E obligations."
            )
            supporting = [
                "Original transaction date and amount confirmed via transaction timeline tool",
                "Refund credit exceeds original settled amount — overpayment confirmed",
                "Policy Section 2.2 explicitly mandates merchant dispute for refund overages",
                "Card network dispute window (60 days) has not elapsed",
            ]
            concerning = [
                "Merchant may contest if refund was intentional goodwill credit — verify with merchant before filing",
                "Amount delta could trigger chargeback fee; weigh cost vs. recovery",
            ]
            missing = [
                "Merchant's refund authorisation record (to confirm if overpayment was intentional)",
                "Cardholder communication log (to check if customer was informed of refund amount)",
            ]
            citations = [
                {
                    "document": "Transaction Exception Policy",
                    "section": "Section 2.2 — Refund Integrity Controls",
                    "quote": "Any refund posted to a cardholder account in excess of the original settled transaction amount shall be treated as an overpayment error and must be disputed through the card network within 60 calendar days of the posting date.",
                    "relevance": "Directly mandates merchant dispute initiation for refund overages — the exact scenario in this case.",
                },
                {
                    "document": "Dispute Resolution Handbook",
                    "section": "Chapter 4 — Chargeback Eligibility Criteria",
                    "quote": "Overpayment chargebacks are eligible under reason code 13.6 (Credit Not Processed) when the refund amount exceeds the original transaction amount by any margin.",
                    "relevance": "Confirms chargeback eligibility and specifies the applicable reason code for filing.",
                },
            ]
        elif "duplicate" in p or "twice" in p or "double" in p or "same charge" in p:
            action = "initiate_merchant_dispute"
            confidence = 0.88
            risk = "medium"
            res_days = 7
            needs_merch = True
            needs_ch = True
            approval = "analyst"
            rationale = (
                "The transaction timeline reveals two identical charge postings from the same merchant "
                "within a short window, which is a strong indicator of a duplicate billing event. "
                "Duplicate charges arise when a merchant's POS system retries an authorisation that "
                "was already approved, or when a settlement file is submitted twice.\n\n"
                "Per the Transaction Exception Policy (Section 3.1 — Duplicate Charge Handling), "
                "a duplicate charge is confirmed when: (1) the merchant name, amount, and currency "
                "match exactly on two separate postings, and (2) both postings occur within 72 hours "
                "of each other without a corresponding reversal. The evidence in this case satisfies "
                "both conditions.\n\n"
                "The recommended action is to initiate a merchant dispute under card network reason "
                "code 12.6 (Duplicate Processing). The cardholder is entitled to a provisional credit "
                "within 5 business days while the dispute is processed. Merchant contact is required "
                "to obtain a refund confirmation or allow the network dispute to proceed to arbitration."
            )
            supporting = [
                "Two identical postings (same amount, same merchant, same currency) confirmed in transaction timeline",
                "No reversal or void recorded for either posting within the 72-hour window",
                "Policy Section 3.1 confirms both criteria for duplicate charge classification are met",
                "Card network reason code 12.6 (Duplicate Processing) is applicable",
            ]
            concerning = [
                "If one posting is an instalment — verify with merchant before filing dispute",
                "Provisional credit creates short-term liability if dispute is lost at arbitration",
            ]
            missing = [
                "Merchant's settlement batch record to confirm whether two separate settlement files were submitted",
                "Cardholder's original receipt or order confirmation to rule out intentional split purchase",
            ]
            citations = [
                {
                    "document": "Transaction Exception Policy",
                    "section": "Section 3.1 — Duplicate Charge Handling",
                    "quote": "When two postings from the same merchant for the same amount are identified within 72 hours without a corresponding reversal, the case shall be classified as a duplicate charge and processed under network dispute procedures.",
                    "relevance": "Confirms duplicate charge classification and mandates the dispute path.",
                },
                {
                    "document": "Provisional Credit Policy",
                    "section": "Section 1.4 — Cardholder Entitlement Timeline",
                    "quote": "Cardholders are entitled to provisional credit within 5 business days of a dispute being filed for amounts under $10,000.",
                    "relevance": "Establishes the timeline obligation for provisional credit issuance alongside the dispute.",
                },
            ]
        elif "authorization" in p or "pending" in p or "hold" in p:
            action = "release_authorization"
            confidence = 0.82
            risk = "low"
            res_days = 3
            needs_merch = True
            needs_ch = False
            approval = "analyst"
            rationale = (
                "The account shows a pending authorization hold that has exceeded the standard "
                "settlement window. Card network rules specify that authorizations must settle within "
                "3 business days for retail transactions and 7 days for travel/hotel holds. A hold "
                "persisting beyond these windows becomes a stale authorisation eligible for release.\n\n"
                "Per the Authorization Management Policy (Section 5.3 — Stale Hold Release), the "
                "issuer is permitted to release holds that have not settled within the network-mandated "
                "window after performing a settlement status check. The settlement status tool confirms "
                "no matching settlement record exists.\n\n"
                "Releasing the hold restores the cardholder's available credit without prejudice. "
                "Should the merchant subsequently submit the settlement, it would post as a new "
                "transaction and the cardholder can dispute it at that time if incorrect. "
                "Merchant notification is recommended to prevent re-authorisation attempts."
            )
            supporting = [
                "Settlement status check confirms no matching settlement received within the allowed window",
                "Authorization age exceeds network-mandated settlement deadline",
                "Policy Section 5.3 explicitly permits hold release under these conditions",
            ]
            concerning = [
                "Merchant may still attempt to settle after release — monitor account for 14 days",
            ]
            missing = [
                "Merchant's reason for delayed settlement (e.g., shipment delay, service not yet rendered)",
            ]
            citations = [
                {
                    "document": "Authorization Management Policy",
                    "section": "Section 5.3 — Stale Hold Release",
                    "quote": "Authorization holds not settled within the applicable card network window (3 days retail, 7 days travel) may be released by the issuer upon confirmation that no settlement record exists.",
                    "relevance": "Directly authorises the release action under these circumstances.",
                },
            ]
        elif "settlement" in p or "delay" in p:
            action = "initiate_refund_tracer"
            confidence = 0.76
            risk = "low"
            res_days = 5
            needs_merch = False
            needs_ch = True
            approval = "analyst"
            rationale = (
                "The transaction has posted to the cardholder's account but the corresponding "
                "settlement funds have not been received within the expected clearing window. "
                "Settlement delays can result from processing errors in the card network, incorrect "
                "routing, or merchant batch failures.\n\n"
                "Per the Settlement Exception Policy (Section 6.1 — Unmatched Settlement Traces), "
                "a refund tracer must be initiated when a credit transaction has been posted but "
                "the underlying funds have not cleared the nostro account within 5 business days. "
                "The tracer engages the card network's settlement reconciliation team to locate "
                "and apply the missing funds.\n\n"
                "Provisional credit is not required at this stage as the transaction is already "
                "posted. The cardholder should be notified that the investigation is underway "
                "and a resolution is expected within 5 business days."
            )
            supporting = [
                "Transaction posted to account confirmed — cardholder's statement already reflects the entry",
                "Settlement status check shows no matching funds received in nostro account",
                "Policy Section 6.1 mandates tracer initiation after 5-day clearing window",
            ]
            concerning = [
                "If tracer returns no match, may need to escalate to card network for forced settlement",
            ]
            missing = [
                "Card network trace number (STAN) from the original transaction record",
                "Merchant's settlement batch confirmation number",
            ]
            citations = [
                {
                    "document": "Settlement Exception Policy",
                    "section": "Section 6.1 — Unmatched Settlement Traces",
                    "quote": "When a posted credit transaction has no corresponding settlement receipt in the nostro account after 5 business days, a network tracer must be initiated within 2 business days.",
                    "relevance": "Mandates the tracer action and establishes the timing requirement.",
                },
            ]
        else:
            action = "escalate_to_senior"
            confidence = 0.65
            risk = "medium"
            res_days = 3
            needs_merch = False
            needs_ch = False
            approval = "senior_analyst"
            rationale = (
                "The evidence gathered from the transaction timeline and account activity tools "
                "does not provide sufficient clarity to apply a standard resolution path with "
                "confidence. The case presents characteristics that do not fit neatly into a "
                "single exception category, and the retrieved policy documents contain "
                "conflicting guidance that requires senior-level interpretation.\n\n"
                "Specifically, the combination of factors in this case — the transaction amount, "
                "the timing of events, and the nature of the exception — sits at the boundary "
                "between two resolution paths. The system's confidence score of 0.65 falls below "
                "the 0.70 threshold required for autonomous recommendation per the Decision "
                "Authority Matrix (Policy Section 8.2).\n\n"
                "A senior analyst should review the full transaction record, apply contextual "
                "judgement about the merchant relationship and customer history, and determine "
                "the appropriate resolution path. This escalation preserves all options and "
                "avoids premature commitment to a resolution that may not be policy-compliant."
            )
            supporting = [
                "Case has been triaged and all available evidence gathered",
                "Policy retrieval completed — relevant sections identified but guidance is ambiguous",
            ]
            concerning = [
                "Confidence score (0.65) is below the 0.70 threshold for autonomous resolution",
                "Multiple resolution paths are plausible — requires senior judgement",
            ]
            missing = [
                "Additional transaction history context beyond the available window",
                "Customer interaction history (previous disputes, relationship tier)",
            ]
            citations = [
                {
                    "document": "Decision Authority Matrix",
                    "section": "Section 8.2 — Confidence Thresholds",
                    "quote": "Recommendations with a confidence score below 0.70 must be reviewed by a senior analyst before any action is taken on the cardholder account.",
                    "relevance": "Mandates senior review given the system's confidence level for this case.",
                },
            ]

        action_label = action.replace("_", " ").title()
        return {
            "recommended_action": action,
            "rationale": rationale,
            "confidence_score": confidence,
            "policy_citations": citations,
            "evidence_summary": {
                "supporting": supporting,
                "concerning": concerning,
                "missing": missing,
            },
            "structured_decision": {
                "action": action,
                "amount_impact": None,
                "requires_merchant_contact": needs_merch,
                "requires_cardholder_notification": needs_ch,
                "estimated_resolution_days": res_days,
                "risk_level": risk,
            },
            "required_approval_level": approval,
            "analyst_summary": (
                f"The system recommends '{action_label}' with {int(confidence * 100)}% confidence, "
                f"grounded in the retrieved policy evidence above. "
                f"Estimated resolution: {res_days} business days. "
                f"Risk level: {risk.upper()}. "
                f"{'Merchant contact required. ' if needs_merch else ''}"
                f"{'Cardholder notification required.' if needs_ch else ''}"
            ),
        }

    def _mock_decision_timeline(self, p: str) -> dict:
        """Mock decision for timeline inconsistency cases."""
        action = "request_additional_info"
        confidence = 0.79
        rationale = (
            "The transaction timeline shows events occurring out of the expected chronological "
            "order. Per the Timeline Inconsistency Handling Policy (POL-TXN-005, Section 3.2), "
            "when a settlement date precedes the authorization date, the case requires additional "
            "information from the merchant's processor to determine whether this is a system "
            "timing error or a processing irregularity.\n\n"
            "The recommended action is to request the merchant's settlement batch records and "
            "processor timestamps. If the merchant confirms a batch processing error, the timeline "
            "can be corrected without further action. If the merchant cannot explain the discrepancy, "
            "the case should be escalated for potential system-level investigation.\n\n"
            "Note: The variance thresholds in POL-TXN-005 Section 3.2 indicate that any settlement "
            "preceding authorization is grounds for immediate additional investigation."
        )
        return {
            "recommended_action": action,
            "rationale": rationale,
            "confidence_score": confidence,
            "policy_citations": [
                {
                    "document": "Timeline Inconsistency Handling Policy",
                    "section": "Section 3.2 — Variance Thresholds",
                    "quote": "Settlement before authorization: Any occurrence requires immediate escalation or additional information request.",
                    "relevance": "Directly applicable to the out-of-order timeline observed in this case.",
                },
            ],
            "evidence_summary": {
                "supporting": [
                    "Transaction timeline confirms settlement date precedes authorization date",
                    "Policy POL-TXN-005 classifies this as requiring investigation",
                ],
                "concerning": [
                    "Could indicate a systemic processing issue affecting other transactions",
                ],
                "missing": [
                    "Merchant's settlement batch records with processor timestamps",
                    "Acquiring bank's authorization log for cross-reference",
                ],
            },
            "structured_decision": {
                "action": action,
                "amount_impact": None,
                "requires_merchant_contact": True,
                "requires_cardholder_notification": False,
                "estimated_resolution_days": 5,
                "risk_level": "medium",
            },
            "required_approval_level": "analyst",
            "analyst_summary": (
                "The system recommends 'Request Additional Info' with 79% confidence. "
                "Timeline inconsistency detected — settlement precedes authorization. "
                "Merchant processor records needed. Estimated resolution: 5 business days."
            ),
        }

    def _mock_decision_eligibility(self, p: str) -> dict:
        """Mock decision for policy eligibility cases."""
        action = "escalate_to_senior"
        confidence = 0.68
        rationale = (
            "This case involves ambiguity in policy applicability. Per the Policy Eligibility "
            "Determination policy (POL-OPS-003, Section 2.2 for multi-policy cases or Section 2.3 "
            "for no-policy cases), when the system cannot determine a single dominant policy with "
            "sufficient confidence, the case must be escalated to a senior analyst.\n\n"
            "The confidence score of 0.68 falls below the 0.80 threshold required for multi-policy "
            "cases (POL-OPS-003, Section 4). A senior analyst should evaluate the competing policy "
            "claims, determine the primary resolution path, and document the eligibility rationale "
            "for audit purposes."
        )
        return {
            "recommended_action": action,
            "rationale": rationale,
            "confidence_score": confidence,
            "policy_citations": [
                {
                    "document": "Policy Eligibility Determination",
                    "section": "Section 2.2 — Multi-Policy Cases / Section 2.3 — No-Policy Cases",
                    "quote": "When two or more policies could apply, evaluate the primary cardholder complaint to determine the dominant issue. Multi-policy cases require confidence >= 0.80 or escalation.",
                    "relevance": "Case involves multiple potentially applicable policies or no matching policy.",
                },
            ],
            "evidence_summary": {
                "supporting": [
                    "Multiple policy documents retrieved but none is clearly dominant",
                    "All available evidence has been gathered via tool calls",
                ],
                "concerning": [
                    "Confidence score 0.68 is below the 0.80 threshold for multi-policy resolution",
                    "Incorrect policy application could result in improper resolution",
                ],
                "missing": [
                    "Senior analyst determination of primary policy applicability",
                    "Additional cardholder context to disambiguate the core complaint",
                ],
            },
            "structured_decision": {
                "action": action,
                "amount_impact": None,
                "requires_merchant_contact": False,
                "requires_cardholder_notification": False,
                "estimated_resolution_days": 3,
                "risk_level": "medium",
            },
            "required_approval_level": "senior_analyst",
            "analyst_summary": (
                "The system recommends 'Escalate To Senior' with 68% confidence. "
                "Policy eligibility is ambiguous — senior analyst review required to determine "
                "the correct resolution path. Estimated resolution: 3 business days."
            ),
        }

    def _mock_decision_account_exception(self, p: str) -> dict:
        """Mock decision for account servicing exception cases."""
        if "fee" in p or "late" in p:
            action = "reverse_fee"
            confidence = 0.86
            rationale = (
                "The account records show payment was received before the due date, yet a late "
                "payment fee was assessed. Per the Account Servicing Exception Policy (POL-ACCT-001, "
                "Section 2.3), fees charged in error must be reversed. The payment posting timeline "
                "confirms the payment cleared before the statement due date.\n\n"
                "The resolution authority table (Section 3.2) permits analyst-level fee reversals "
                "up to $500. Since this fee is $39.00, it falls within analyst authority."
            )
            supporting = [
                "Payment posting date confirmed before due date via account activity tool",
                "Fee assessment appears to be a processing error",
                "Amount within analyst reversal authority ($500 limit)",
            ]
        else:
            action = "escalate_to_senior"
            confidence = 0.74
            rationale = (
                "The account shows a discrepancy between the expected and actual account state. "
                "Per the Account Servicing Exception Policy (POL-ACCT-001, Section 3.2), credit "
                "posting corrections exceeding analyst authority or involving account status changes "
                "require senior analyst or supervisor review.\n\n"
                "The evidence gathered confirms the payment was made but available credit has not "
                "been updated. This may indicate a posting delay or a system-level issue."
            )
            supporting = [
                "Payment confirmed via bank debit records",
                "Account state does not reflect the payment",
                "No account holds or restrictions found",
            ]

        return {
            "recommended_action": action,
            "rationale": rationale,
            "confidence_score": confidence,
            "policy_citations": [
                {
                    "document": "Account Servicing Exception Policy",
                    "section": "Section 2.3 / Section 3.2",
                    "quote": "Fees charged in error must be reversed. Credit posting corrections within analyst authority: up to $5,000.",
                    "relevance": "Defines resolution authority and required action for account servicing exceptions.",
                },
            ],
            "evidence_summary": {
                "supporting": supporting,
                "concerning": [
                    "If issue is systemic, other accounts may be affected",
                ],
                "missing": [
                    "Internal payment processing log to confirm posting pipeline status",
                ],
            },
            "structured_decision": {
                "action": action,
                "amount_impact": None,
                "requires_merchant_contact": False,
                "requires_cardholder_notification": True,
                "estimated_resolution_days": 2,
                "risk_level": "low",
            },
            "required_approval_level": "analyst" if action == "reverse_fee" else "senior_analyst",
            "analyst_summary": (
                f"The system recommends '{action.replace('_', ' ').title()}' with "
                f"{int(confidence * 100)}% confidence. "
                f"Account servicing exception identified. "
                f"Estimated resolution: 2 business days."
            ),
        }

    def _mock_safety(self, prompt: str) -> dict:
        p = prompt.lower()
        flags = []
        safe = True
        approval_override = None

        # Check confidence score in prompt
        import re
        conf_match = re.search(r"confidence.{0,30}?(0\.\d+)", p)
        confidence = float(conf_match.group(1)) if conf_match else 0.8

        # Check amount in prompt — match numbers after "amount" with optional $ or currency
        amt_match = re.search(r"amount.{0,30}?\$?\s*([\d,]+\.?\d*)", p)
        amount = 0.0
        if amt_match and amt_match.group(1).strip():
            try:
                amount = float(amt_match.group(1).replace(",", ""))
            except ValueError:
                pass

        if confidence < 0.70:
            flags.append("low_confidence_below_threshold")
            approval_override = "senior_analyst"
        if confidence < 0.50:
            safe = False
            flags.append("critically_low_confidence")

        if amount > 5000:
            flags.append("high_value_case")
            if approval_override is None:
                approval_override = "senior_analyst"
        if amount > 25000:
            approval_override = "supervisor"
        if amount > 100000:
            approval_override = "operations_manager"

        if "no policy" in p or "no citation" in p or "num_citations: 0" in p:
            flags.append("no_policy_grounding")
            safe = False

        return {
            "safe_to_present": safe,
            "requires_human_review": True,
            "approval_level_override": approval_override,
            "flags": flags,
            "reasoning": (
                f"Safety validation complete. Confidence: {confidence:.2f}, Amount: ${amount:,.2f}. "
                f"{'Flags raised: ' + ', '.join(flags) + '.' if flags else 'No flags raised.'} "
                f"Human review required per standard workflow."
            ),
        }

    def _mock_case_writer(self, prompt: str) -> dict:
        return {
            "case_summary": "The system has analyzed this transaction exception case, gathered relevant evidence from internal tools, and retrieved applicable policy guidance. A recommendation has been generated for analyst review.",
            "analyst_notes": "- Case triaged and classified automatically\n- Policy retrieval identified relevant guidelines\n- Tool evidence gathered: transaction timeline, account activity\n- Recommendation generated with policy citations\n- Awaiting analyst review and approval",
            "closure_template": "Case reviewed and resolved per applicable policy guidelines. Evidence reviewed, recommendation approved by analyst. No further action required.",
        }
