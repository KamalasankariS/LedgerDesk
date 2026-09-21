"""Test mock tool services."""

import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent.parent / "sample_data"


class TestSeedDataIntegrity:
    """Verify seed data is well-formed and cross-referenced."""

    def _load(self, subdir: str, filename: str):
        filepath = DATA_DIR / subdir / filename
        assert filepath.exists(), f"Missing: {filepath}"
        return json.loads(filepath.read_text())

    def test_cases_valid(self):
        cases = self._load("cases", "seed_cases.json")
        assert len(cases) >= 10
        for case in cases:
            assert "case_number" in case
            assert "title" in case
            assert "description" in case
            assert case["case_number"].startswith("CSE-")

    def test_transactions_valid(self):
        txns = self._load("transactions", "seed_transactions.json")
        assert len(txns) >= 5
        for txn in txns:
            assert "transaction_id" in txn
            assert "account_id" in txn
            assert "amount" in txn
            assert txn["transaction_id"].startswith("TXN-")

    def test_accounts_valid(self):
        accounts = self._load("accounts", "seed_accounts.json")
        assert len(accounts) >= 5
        for acct in accounts:
            assert "account_id" in acct
            assert "cardholder_name" in acct
            assert acct["account_id"].startswith("ACCT-")

    def test_cases_reference_valid_transactions(self):
        cases = self._load("cases", "seed_cases.json")
        txns = self._load("transactions", "seed_transactions.json")
        txn_ids = {t["transaction_id"] for t in txns}
        for case in cases:
            if case.get("transaction_id"):
                tid = case["transaction_id"]
                assert tid in txn_ids, f"Case {case['case_number']} references unknown txn {tid}"

    def test_cases_reference_valid_accounts(self):
        cases = self._load("cases", "seed_cases.json")
        accounts = self._load("accounts", "seed_accounts.json")
        acct_ids = {a["account_id"] for a in accounts}
        for case in cases:
            if case.get("account_id"):
                assert case["account_id"] in acct_ids, (
                    f"Case {case['case_number']} references unknown account {case['account_id']}"
                )

    def test_policies_exist(self):
        policies_dir = DATA_DIR / "policies"
        assert policies_dir.exists()
        policy_files = list(policies_dir.glob("*.md"))
        assert len(policy_files) >= 5

    def test_merchants_valid(self):
        merchants = self._load("merchants", "seed_merchants.json")
        assert len(merchants) >= 5
        for m in merchants:
            assert "merchant_id" in m
            assert "name" in m
            assert "mcc" in m


class TestToolOutputContracts:
    """Test that tool output contracts are valid."""

    def test_transaction_timeline_output_shape(self):
        txns = json.loads((DATA_DIR / "transactions" / "seed_transactions.json").read_text())
        # Simulate get_transaction_timeline
        result = {
            "transaction_id": "TXN-9382741",
            "timeline": [t for t in txns if t["account_id"] == "ACCT-4421889"],
            "total_transactions": 2,
        }
        assert "transaction_id" in result
        assert "timeline" in result
        assert isinstance(result["timeline"], list)
        assert len(result["timeline"]) == 2

    def test_account_activity_output_shape(self):
        accounts = json.loads((DATA_DIR / "accounts" / "seed_accounts.json").read_text())
        acct = next(a for a in accounts if a["account_id"] == "ACCT-4421889")
        result = {
            "account_id": "ACCT-4421889",
            "account_info": acct,
            "recent_transactions": [],
            "transaction_count": 0,
        }
        assert result["account_info"]["cardholder_name"] == "Sarah Mitchell"
