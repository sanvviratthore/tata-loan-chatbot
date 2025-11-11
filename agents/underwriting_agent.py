"""
Underwriting agent module.

Implements deterministic underwriting logic that evaluates credit and income
signals, produces structured offers, and communicates a canonical decision
object to the master agent.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Literal, Optional, TypedDict

from utils.loan_calculator import (
    calculate_emi,
    reverse_emi_calculation,
)

logger = logging.getLogger(__name__)

DecisionStatus = Literal["APPROVED", "CONDITIONALLY_APPROVED", "REJECTED"]
ReasonCode = Literal[
    "OK",
    "LOW_CREDIT_SCORE",
    "HIGH_DTI",
    "TOO_MANY_ACTIVE_LOANS",
    "MISSING_INCOME_PROOF",
    "INTERNAL_LIMIT_EXCEEDED",
    "INCOMPLETE_PROFILE",
]


class Offer(TypedDict):
    amount: int
    interest_rate_pct: float
    tenure_months: int
    emi: int
    consolidation: bool
    notes: str


class UnderwritingDecision(TypedDict):
    status: DecisionStatus
    reason: ReasonCode
    financial_health_score: int
    credit_score: int
    dti_ratio: float
    active_loans_count: int
    preapproved_limit: int
    requested_amount: Optional[int]
    needed_documents: List[str]
    offers: List[Offer]
    recommendations: List[str]
    raw: Dict[str, Any]


# Business rule constants
MIN_CREDIT_SCORE_STANDARD = 680
MIN_CREDIT_SCORE_CONSOLIDATION = 700
DTI_CONDITIONAL_THRESHOLD = 0.45
DTI_REJECTION_THRESHOLD = 0.6
MAX_ACTIVE_LOANS_FOR_CONSOLIDATION = 3
BASE_PERSONAL_RATE = 11.0
BASE_CONSOLIDATION_RATE = 11.0
PERSONAL_TENURE_MONTHS = 36
CONSOLIDATION_TENURE_MONTHS = 48
AFFORDABILITY_RATE = 11.0
AFFORDABILITY_TENURE_MONTHS = 48


@dataclass(frozen=True)
class CustomerContext:
    pan: Optional[str]
    credit_score: int
    monthly_income: float
    active_loans: List[Dict[str, Any]]
    total_monthly_emi: float
    requested_amount: Optional[int]
    prefer_consolidation: bool
    internal_limit: Optional[int]

    @property
    def active_loans_count(self) -> int:
        return len(self.active_loans)


def underwrite(
    pan: Optional[str],
    requested_amount: Optional[int],
    prefer_consolidation: bool,
    customer_profile: Dict[str, Any],
    credit_profile: Dict[str, Any],
) -> UnderwritingDecision:
    """
    Pure function that produces an underwriting decision per canonical schema.
    """

    context = _build_context(
        pan=pan,
        requested_amount=requested_amount,
        prefer_consolidation=prefer_consolidation,
        customer_profile=customer_profile,
        credit_profile=credit_profile,
    )

    missing_fields = _detect_missing_fields(context)
    if missing_fields:
        logger.info("Rejecting due to incomplete profile", extra={"missing": missing_fields})
        return _build_decision(
            context=context,
            status="REJECTED",
            reason="INCOMPLETE_PROFILE",
            needed_documents=[],
            recommendations=["Please update the missing information: " + ", ".join(sorted(missing_fields))],
            offers=[],
        )

    logger.debug(
        "Underwriting inputs",
        extra={
            "pan": context.pan,
            "credit_score": context.credit_score,
            "income": context.monthly_income,
            "total_monthly_emi": context.total_monthly_emi,
            "requested_amount": context.requested_amount,
            "prefer_consolidation": context.prefer_consolidation,
            "active_loans": context.active_loans_count,
        },
    )

    # Credit score rule
    min_score = (
        MIN_CREDIT_SCORE_CONSOLIDATION
        if context.prefer_consolidation and context.active_loans_count > 0
        else MIN_CREDIT_SCORE_STANDARD
    )
    if context.credit_score < min_score:
        logger.info(
            "Rejected due to low credit score",
            extra={"credit_score": context.credit_score, "required": min_score},
        )
        recommendations = [
            "Pay all EMIs on time for the next 3 months.",
            "Reduce credit card utilization below 30%.",
            "Reapply once your credit score improves to 700+.",
        ]
        return _build_decision(
            context=context,
            status="REJECTED",
            reason="LOW_CREDIT_SCORE",
            needed_documents=[],
            recommendations=recommendations,
            offers=[],
        )

    # DTI rules
    dti_ratio = _calculate_dti(context.total_monthly_emi, context.monthly_income)
    if dti_ratio > DTI_REJECTION_THRESHOLD:
        logger.info("Rejected due to high DTI ratio", extra={"dti_ratio": dti_ratio})
        recommendations = [
            "Reduce existing EMIs by closing one or two smaller loans.",
            "Increase monthly income or add a co-applicant to lower the DTI.",
            "Maintain on-time payments for at least 3 months before reapplying.",
        ]
        return _build_decision(
            context=context,
            status="REJECTED",
            reason="HIGH_DTI",
            needed_documents=[],
            recommendations=recommendations,
            offers=[],
        )

    needed_documents: List[str] = []
    reason: ReasonCode = "OK"
    status: DecisionStatus = "APPROVED"
    recommendations: List[str] = []

    if DTI_CONDITIONAL_THRESHOLD < dti_ratio <= DTI_REJECTION_THRESHOLD:
        status = "CONDITIONALLY_APPROVED"
        reason = "MISSING_INCOME_PROOF"
        needed_documents.append("salary_slip_last_3_months")
        recommendations.append("Upload the last 3 months' salary slips to validate affordability.")
        logger.info(
            "Conditional approval due to borderline DTI",
            extra={"dti_ratio": dti_ratio},
        )

    if context.prefer_consolidation and context.active_loans_count > MAX_ACTIVE_LOANS_FOR_CONSOLIDATION:
        status = "CONDITIONALLY_APPROVED"
        reason = "TOO_MANY_ACTIVE_LOANS"
        recommendations.append("Close 1-2 smallest loans to simplify your profile before disbursal.")
        logger.info(
            "Too many active loans for consolidation",
            extra={"active_loans": context.active_loans_count},
        )

    preapproved_limit = _calculate_preapproved_limit(context)
    logger.debug(
        "Computed preapproved limit",
        extra={"preapproved_limit": preapproved_limit},
    )

    if context.requested_amount and context.requested_amount > preapproved_limit:
        status = "CONDITIONALLY_APPROVED"
        reason = "MISSING_INCOME_PROOF"
        if "salary_slip_last_3_months" not in needed_documents:
            needed_documents.append("salary_slip_last_3_months")
        recommendations.append(
            "Requested amount exceeds the current internal limit. Provide salary slips to reassess the limit."
        )
        logger.info(
            "Requested amount above limit; flagged for income proof",
            extra={
                "requested": context.requested_amount,
                "limit": preapproved_limit,
            },
        )

    offers = _build_offers(context, preapproved_limit, dti_ratio)
    if not offers and status == "APPROVED":
        status = "CONDITIONALLY_APPROVED"
        reason = "INTERNAL_LIMIT_EXCEEDED"
        recommendations.append("Reduce the requested amount or opt for a shorter tenure.")

    decision = _build_decision(
        context=context,
        status=status,
        reason=reason,
        needed_documents=needed_documents,
        recommendations=recommendations,
        offers=offers,
        dti_ratio=dti_ratio,
        preapproved_limit=preapproved_limit,
    )

    logger.info(
        "Underwriting decision finalised",
        extra={
            "status": decision["status"],
            "reason": decision["reason"],
            "offers": len(decision["offers"]),
            "preapproved_limit": decision["preapproved_limit"],
        },
    )
    return decision


def summarize_for_master_agent(decision: UnderwritingDecision) -> str:
    """
    Generate a concise paragraph summarising the underwriting decision.
    """

    status_text = {
        "APPROVED": "approved",
        "CONDITIONALLY_APPROVED": "conditionally approved",
        "REJECTED": "declined",
    }[decision["status"]]

    offers_summary = ""
    if decision["offers"]:
        primary_offer = decision["offers"][0]
        emi_formatted = f"₹{primary_offer['emi']:,}"
        amount_formatted = f"₹{primary_offer['amount']:,}"
        offer_type = "consolidation" if primary_offer["consolidation"] else "personal"
        offers_summary = (
            f" Lead offer: {offer_type} loan of {amount_formatted} for "
            f"{primary_offer['tenure_months']} months at {primary_offer['interest_rate_pct']:.2f}% "
            f"with a monthly EMI of {emi_formatted}."
        )

    docs_summary = ""
    if decision["needed_documents"]:
        docs_summary = " Documents required: " + ", ".join(decision["needed_documents"]) + "."

    recommendations = ""
    if decision["recommendations"]:
        recommendations = " Next steps: " + " ".join(decision["recommendations"])

    return (
        f"Application {status_text} citing {decision['reason']}."
        f" Credit score {decision['credit_score']} with DTI {decision['dti_ratio'] * 100:.1f}%."
        f"{offers_summary}{docs_summary}{recommendations}"
    )


def _build_context(
    pan: Optional[str],
    requested_amount: Optional[int],
    prefer_consolidation: bool,
    customer_profile: Dict[str, Any],
    credit_profile: Dict[str, Any],
) -> CustomerContext:
    credit_score = int(credit_profile.get("credit_score", 0))
    monthly_income = _infer_monthly_income(customer_profile)

    active_loans = credit_profile.get("active_loans") or []
    total_monthly_emi = _infer_total_monthly_emi(credit_profile, active_loans)

    internal_limit = customer_profile.get("pre_approved_limit") or customer_profile.get("preapproved_limit")
    internal_limit = int(internal_limit) if internal_limit else None

    return CustomerContext(
        pan=pan,
        credit_score=credit_score,
        monthly_income=monthly_income,
        active_loans=list(active_loans),
        total_monthly_emi=total_monthly_emi,
        requested_amount=int(requested_amount) if requested_amount else None,
        prefer_consolidation=prefer_consolidation,
        internal_limit=internal_limit,
    )


def _detect_missing_fields(context: CustomerContext) -> List[str]:
    missing = []
    if context.credit_score <= 0:
        missing.append("credit_score")
    if context.monthly_income <= 0:
        missing.append("monthly_income")
    if context.total_monthly_emi < 0:
        missing.append("total_monthly_emi")
    return missing


def _infer_monthly_income(customer_profile: Dict[str, Any]) -> float:
    if not customer_profile:
        return 0.0
    for key in ("monthly_income", "income", "net_salary"):
        value = customer_profile.get(key)
        if value is not None:
            return float(value)
    return 0.0


def _infer_total_monthly_emi(credit_profile: Dict[str, Any], active_loans: List[Dict[str, Any]]) -> float:
    if credit_profile.get("total_monthly_emi") is not None:
        return float(credit_profile["total_monthly_emi"])
    total = 0.0
    for loan in active_loans:
        emi = loan.get("emi")
        if emi is not None:
            total += float(emi)
    return total


def _calculate_dti(total_monthly_emi: float, monthly_income: float) -> float:
    if monthly_income <= 0:
        return 1.0
    ratio = total_monthly_emi / monthly_income
    return max(0.0, ratio)


def _calculate_preapproved_limit(context: CustomerContext) -> int:
    max_emi_affordable = max(0.0, context.monthly_income * 0.4 - context.total_monthly_emi)
    if max_emi_affordable <= 0:
        logger.debug("No EMI headroom; preapproved limit is zero")
        return 0

    principal = reverse_emi_calculation(
        emi=max_emi_affordable,
        annual_rate=AFFORDABILITY_RATE,
        years=AFFORDABILITY_TENURE_MONTHS / 12,
    )
    limit = int(max(0, round(principal)))
    if context.internal_limit is not None:
        limit = min(limit, context.internal_limit)
    return limit


def _build_offers(
    context: CustomerContext,
    preapproved_limit: int,
    dti_ratio: float,
) -> List[Offer]:
    offers: List[Offer] = []

    if preapproved_limit <= 0:
        logger.debug("No preapproved limit available; skipping offer generation")
        return offers

    if context.active_loans_count == 1:
        offers.extend(
            _build_single_loan_offers(
                context=context,
                preapproved_limit=preapproved_limit,
            )
        )
        return offers

    if context.prefer_consolidation and context.active_loans_count > 0:
        consolidation_offer = _build_consolidation_offer(context, preapproved_limit)
        if consolidation_offer:
            offers.append(consolidation_offer)
        return offers

    personal_offer = _build_personal_offer(context, preapproved_limit, dti_ratio)
    if personal_offer:
        offers.append(personal_offer)
    if context.active_loans_count > 1 and not context.prefer_consolidation:
        consolidation_offer = _build_consolidation_offer(context, preapproved_limit)
        if consolidation_offer:
            offers.append(consolidation_offer)
    return offers


def _build_personal_offer(context: CustomerContext, preapproved_limit: int, dti_ratio: float) -> Optional[Offer]:
    amount = context.requested_amount or preapproved_limit
    amount = min(amount, preapproved_limit)
    if amount <= 0:
        return None

    base_rate = _determine_personal_rate(context.credit_score, context.active_loans_count)
    tenure_months = PERSONAL_TENURE_MONTHS if amount <= 400000 else 48
    emi_value = _emi_for_months(amount, base_rate, tenure_months)

    notes_parts = [
        "Standard personal loan offer",
        f"Estimated EMI keeps DTI at {(context.total_monthly_emi + emi_value) / context.monthly_income * 100:.1f}%"
        if context.monthly_income > 0
        else "Please ensure repayment comfort",
    ]
    if dti_ratio > DTI_CONDITIONAL_THRESHOLD:
        notes_parts.append("Salary slip verification required before disbursal.")

    return Offer(
        amount=int(amount),
        interest_rate_pct=round(base_rate, 2),
        tenure_months=tenure_months,
        emi=int(emi_value),
        consolidation=False,
        notes=" ".join(notes_parts),
    )


def _build_consolidation_offer(context: CustomerContext, preapproved_limit: int) -> Optional[Offer]:
    if context.active_loans_count == 0:
        return None

    outstanding_total = sum(float(loan.get("outstanding_amount") or loan.get("principal_outstanding") or loan.get("outstanding") or 0) for loan in context.active_loans)
    current_total_emi = sum(float(loan.get("emi", 0)) for loan in context.active_loans)

    target_amount = context.requested_amount or 0
    if target_amount <= 0:
        target_amount = outstanding_total
    else:
        target_amount = max(target_amount, outstanding_total)

    amount = min(preapproved_limit, int(round(target_amount))) if target_amount else preapproved_limit
    if amount <= 0:
        return None

    rate = _determine_consolidation_rate(context.credit_score)
    emi_value = _emi_for_months(amount, rate, CONSOLIDATION_TENURE_MONTHS)
    monthly_savings = current_total_emi - emi_value

    notes = (
        f"Consolidate {context.active_loans_count} loan(s) into one EMI."
        f" Estimated monthly savings of ₹{int(round(monthly_savings)):,}."
    )

    return Offer(
        amount=int(amount),
        interest_rate_pct=round(rate, 2),
        tenure_months=CONSOLIDATION_TENURE_MONTHS,
        emi=int(emi_value),
        consolidation=True,
        notes=notes,
    )


def _build_single_loan_offers(context: CustomerContext, preapproved_limit: int) -> List[Offer]:
    existing_loan = context.active_loans[0]
    outstanding = float(
        existing_loan.get("outstanding_amount")
        or existing_loan.get("principal_outstanding")
        or existing_loan.get("outstanding")
        or 0
    )
    existing_emi = float(existing_loan.get("emi") or 0)

    requested = context.requested_amount or min(preapproved_limit, int(round(outstanding)))
    approved_new_amount = min(preapproved_limit, requested)
    offers: List[Offer] = []

    # Offer 1: New loan alongside existing
    personal_rate = _determine_personal_rate(context.credit_score, context.active_loans_count)
    personal_tenure = PERSONAL_TENURE_MONTHS
    personal_emi = _emi_for_months(approved_new_amount, personal_rate, personal_tenure)
    offers.append(
        Offer(
            amount=int(approved_new_amount),
            interest_rate_pct=round(personal_rate, 2),
            tenure_months=personal_tenure,
            emi=int(personal_emi),
            consolidation=False,
            notes=(
                "Retain existing loan and add a fresh personal loan."
                f" Combined EMI becomes ₹{int(round(personal_emi + existing_emi)):,}."
            ),
        )
    )

    # Offer 2: Transfer existing loan plus top-up
    transfer_amount = min(preapproved_limit, int(round(outstanding + (context.requested_amount or 0))))
    if transfer_amount > 0:
        consolidation_rate = _determine_consolidation_rate(context.credit_score)
        consolidation_emi = _emi_for_months(transfer_amount, consolidation_rate, CONSOLIDATION_TENURE_MONTHS)
        savings = existing_emi + personal_emi - consolidation_emi
        offers.append(
            Offer(
                amount=int(transfer_amount),
                interest_rate_pct=round(consolidation_rate, 2),
                tenure_months=CONSOLIDATION_TENURE_MONTHS,
                emi=int(consolidation_emi),
                consolidation=True,
                notes=(
                    "Transfer current loan and add top-up for a single EMI."
                    f" Monthly cash-flow change: ₹{int(round(savings)):,}."
                ),
            )
        )

    return offers


def _determine_personal_rate(credit_score: int, active_loans_count: int) -> float:
    if credit_score >= 800:
        base = 10.5
    elif credit_score >= 750:
        base = 10.75
    elif credit_score >= 700:
        base = 11.0
    else:
        base = 11.5

    if active_loans_count == 0:
        base -= 0.25
    return round(max(base, 9.5), 2)


def _determine_consolidation_rate(credit_score: int) -> float:
    if credit_score >= 780:
        return 10.75
    if credit_score >= 720:
        return 11.0
    return 11.25


def _emi_for_months(principal: float, annual_rate: float, tenure_months: int) -> int:
    years = tenure_months / 12
    emi = calculate_emi(principal, annual_rate, years)
    return int(round(emi))


def _build_decision(
    context: CustomerContext,
    status: DecisionStatus,
    reason: ReasonCode,
    needed_documents: List[str],
    recommendations: List[str],
    offers: List[Offer],
    dti_ratio: Optional[float] = None,
    preapproved_limit: Optional[int] = None,
) -> UnderwritingDecision:
    dti_ratio = dti_ratio if dti_ratio is not None else _calculate_dti(context.total_monthly_emi, context.monthly_income)
    preapproved_limit = preapproved_limit if preapproved_limit is not None else 0
    financial_health_score = _calculate_financial_health_score(
        credit_score=context.credit_score,
        dti_ratio=dti_ratio,
        active_loans=context.active_loans_count,
    )

    raw_snapshot = {
        "pan": context.pan,
        "requested_amount": context.requested_amount,
        "prefer_consolidation": context.prefer_consolidation,
        "monthly_income": context.monthly_income,
        "total_monthly_emi": context.total_monthly_emi,
        "active_loans_count": context.active_loans_count,
    }

    return UnderwritingDecision(
        status=status,
        reason=reason,
        financial_health_score=financial_health_score,
        credit_score=context.credit_score,
        dti_ratio=round(dti_ratio, 4),
        active_loans_count=context.active_loans_count,
        preapproved_limit=int(preapproved_limit),
        requested_amount=context.requested_amount,
        needed_documents=list(dict.fromkeys(needed_documents)),
        offers=offers,
        recommendations=recommendations,
        raw=raw_snapshot,
    )


def _calculate_financial_health_score(
    credit_score: int,
    dti_ratio: float,
    active_loans: int,
) -> int:
    score = 0
    if credit_score >= 800:
        score += 4
    elif credit_score >= 750:
        score += 3
    elif credit_score >= 700:
        score += 2
    elif credit_score >= 650:
        score += 1

    if dti_ratio <= 0.3:
        score += 3
    elif dti_ratio <= 0.45:
        score += 2
    elif dti_ratio <= 0.6:
        score += 1

    if active_loans == 0:
        score += 2
    elif active_loans == 1:
        score += 1
    elif active_loans >= 4:
        score -= 1

    return max(0, min(score, 10))

