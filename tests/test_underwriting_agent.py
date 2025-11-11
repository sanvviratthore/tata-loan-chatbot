import math
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))

from agents.underwriting_agent import (
    UnderwritingDecision,
    summarize_for_master_agent,
    underwrite,
)
from utils.loan_calculator import calculate_emi


def _base_profiles(**overrides):
    customer_profile = {
        "name": "Test Customer",
        "monthly_income": 75000,
        "pre_approved_limit": 500000,
    }
    credit_profile = {
        "credit_score": 780,
        "active_loans": [],
        "total_monthly_emi": 0,
    }
    customer_profile.update(overrides.get("customer_profile", {}))
    credit_profile.update(overrides.get("credit_profile", {}))
    return customer_profile, credit_profile


def test_low_credit_score_rejection():
    customer_profile, credit_profile = _base_profiles(
        credit_profile={"credit_score": 650},
    )

    decision = underwrite(
        pan="PAN123",
        requested_amount=200000,
        prefer_consolidation=False,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    assert decision["status"] == "REJECTED"
    assert decision["reason"] == "LOW_CREDIT_SCORE"
    assert any("on time" in rec.lower() for rec in decision["recommendations"])
    assert "reapply" in " ".join(decision["recommendations"]).lower()


def test_consolidation_happy_path_matches_expected_emi():
    customer_profile, credit_profile = _base_profiles(
        customer_profile={"monthly_income": 75000},
        credit_profile={
            "credit_score": 780,
            "active_loans": [
                {"emi": 8000, "outstanding_amount": 120000},
                {"emi": 5500, "outstanding_amount": 80000},
            ],
            "total_monthly_emi": 13500,
        },
    )

    decision = underwrite(
        pan="ABCP1234X",
        requested_amount=350000,
        prefer_consolidation=True,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    assert decision["status"] == "APPROVED"
    assert decision["offers"], "Expected at least one offer"
    primary_offer = decision["offers"][0]
    assert primary_offer["consolidation"] is True
    expected_emi = int(round(calculate_emi(350000, 11.0, 4)))
    assert math.isclose(primary_offer["emi"], expected_emi, rel_tol=0.05)
    assert primary_offer["tenure_months"] == 48


def test_requested_amount_above_limit_requires_salary_slips():
    customer_profile, credit_profile = _base_profiles(
        customer_profile={"monthly_income": 60000, "pre_approved_limit": 150000},
        credit_profile={
            "credit_score": 720,
            "total_monthly_emi": 12000,
            "active_loans": [],
        },
    )

    decision = underwrite(
        pan="PAN777",
        requested_amount=400000,
        prefer_consolidation=False,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    assert decision["status"] == "CONDITIONALLY_APPROVED"
    assert decision["reason"] == "MISSING_INCOME_PROOF"
    assert "salary_slip_last_3_months" in decision["needed_documents"]


def test_single_loan_generates_dual_offers():
    customer_profile, credit_profile = _base_profiles(
        credit_profile={
            "credit_score": 735,
            "active_loans": [
                {"emi": 9500, "outstanding_amount": 180000},
            ],
            "total_monthly_emi": 9500,
        },
    )

    decision = underwrite(
        pan="PAN998",
        requested_amount=150000,
        prefer_consolidation=False,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    offers = decision["offers"]
    assert len(offers) == 2
    assert any(not offer["consolidation"] for offer in offers)
    assert any(offer["consolidation"] for offer in offers)


def test_no_existing_loans_best_personal_offer():
    customer_profile, credit_profile = _base_profiles(
        customer_profile={"monthly_income": 90000},
        credit_profile={
            "credit_score": 810,
            "active_loans": [],
            "total_monthly_emi": 0,
        },
    )

    decision: UnderwritingDecision = underwrite(
        pan="PAN555",
        requested_amount=250000,
        prefer_consolidation=False,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    assert decision["status"] == "APPROVED"
    assert decision["offers"], "Expected a personal loan offer"
    offer = decision["offers"][0]
    assert offer["consolidation"] is False
    assert offer["interest_rate_pct"] <= 10.75

    summary = summarize_for_master_agent(decision)
    assert "approved" in summary.lower()
    assert "credit score" in summary.lower()

