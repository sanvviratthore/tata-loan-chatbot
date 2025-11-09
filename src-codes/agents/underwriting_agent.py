"""
Underwriting Agent

Assesses loan eligibility based on credit profile, calculates maximum loan amounts,
determines risk-based interest rates, and generates loan offers.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import uuid

from agents.base_agent import BaseAgent, handle_errors, ValidationError, BusinessLogicError
from schemas.models import CreditProfile, UnderwritingDecision, LoanOffer
from utils.loan_calculator import calculate_emi, calculate_total_interest, calculate_max_loan_amount
from utils.llm_client import create_llm_client


class UnderwritingAgent(BaseAgent):
    """
    Agent responsible for loan underwriting and eligibility assessment.
    
    Evaluates applicants based on:
    - Credit score tiers
    - Debt-to-income ratio
    - Existing loan count
    - Requested loan amount
    """
    
    # Credit score tiers and corresponding interest rates
    CREDIT_TIERS = {
        "EXCELLENT": {"min_score": 750, "interest_rate": 10.5, "max_dti": 0.40},
        "GOOD": {"min_score": 650, "interest_rate": 12.5, "max_dti": 0.50},
        "FAIR": {"min_score": 600, "interest_rate": 15.0, "max_dti": 0.45},
        "POOR": {"min_score": 0, "interest_rate": 18.0, "max_dti": 0.35}
    }
    
    # Business rules
    MAX_LOAN_COUNT = 5
    MIN_CREDIT_SCORE = 650
    DEFAULT_TENURE_MONTHS = 60
    PROCESSING_FEE_PERCENTAGE = 0.01  # 1% of loan amount
    
    def __init__(self, llm_client=None):
        """Initialize underwriting agent."""
        super().__init__("underwriting_agent")
        self.llm_client = llm_client or create_llm_client()
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process underwriting request and generate loan decision.
        
        Args:
            input_data: Dictionary containing:
                - credit_profile: CreditProfile object or dict
                - requested_amount: Optional requested loan amount
                - requested_tenure: Optional requested tenure in months
            session_state: Current session state
        
        Returns:
            Dictionary containing underwriting decision and loan offer if approved
        """
        self.log_action("process_underwriting", session_id=session_state.get("session_id"))
        
        # Validate input
        self.validate_input(input_data)
        
        # Extract credit profile
        credit_profile_data = input_data.get("credit_profile")
        if isinstance(credit_profile_data, dict):
            credit_profile = CreditProfile(**credit_profile_data)
        else:
            credit_profile = credit_profile_data
        
        # Get requested parameters
        requested_amount = input_data.get("requested_amount")
        requested_tenure = input_data.get("requested_tenure", self.DEFAULT_TENURE_MONTHS)
        
        # Assess eligibility
        decision = self.assess_eligibility(credit_profile, requested_amount, requested_tenure)
        
        # Log decision
        self.log_decision(
            decision="APPROVED" if decision.approved else "REJECTED",
            reasoning=decision.rejection_reason or f"Credit tier: {decision.credit_score_tier}",
            credit_score=credit_profile.credit_score,
            loan_amount=decision.loan_amount,
            interest_rate=decision.interest_rate
        )
        
        # Generate loan offer if approved
        loan_offer = None
        if decision.approved:
            loan_offer = self.generate_loan_offer(
                decision=decision,
                customer_id=credit_profile.customer_id
            )
        
        # Prepare response
        response_data = {
            "decision": decision.model_dump(),
            "loan_offer": loan_offer.model_dump() if loan_offer else None
        }
        
        # Determine next agent
        if decision.approved:
            next_agent = "sales"
            message = "Congratulations! Your loan has been approved. Let me explain the offer details."
        else:
            next_agent = "document" if decision.improvement_plan else None
            message = decision.rejection_reason
        
        return self.create_response(
            success=True,
            data=response_data,
            next_agent=next_agent,
            message=message
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for underwriting.
        
        Args:
            input_data: Input data to validate
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If validation fails
        """
        if not input_data:
            raise ValidationError("Input data is required")
        
        if "credit_profile" not in input_data:
            raise ValidationError("Credit profile is required", field="credit_profile")
        
        # Validate requested amount if provided
        requested_amount = input_data.get("requested_amount")
        if requested_amount is not None:
            if not isinstance(requested_amount, (int, float)):
                raise ValidationError("Requested amount must be a number", field="requested_amount")
            if requested_amount <= 0:
                raise ValidationError("Requested amount must be greater than 0", field="requested_amount")
            if requested_amount > 10000000:  # 1 crore max
                raise ValidationError("Requested amount exceeds maximum limit of ₹1,00,00,000", field="requested_amount")
        
        # Validate requested tenure if provided
        requested_tenure = input_data.get("requested_tenure")
        if requested_tenure is not None:
            if not isinstance(requested_tenure, int):
                raise ValidationError("Requested tenure must be an integer", field="requested_tenure")
            if requested_tenure < 12 or requested_tenure > 360:
                raise ValidationError("Tenure must be between 12 and 360 months", field="requested_tenure")
        
        return True
    
    def assess_eligibility(
        self,
        credit_profile: CreditProfile,
        requested_amount: Optional[float] = None,
        requested_tenure: int = DEFAULT_TENURE_MONTHS
    ) -> UnderwritingDecision:
        """
        Assess loan eligibility based on credit profile.
        
        Args:
            credit_profile: Customer's credit profile
            requested_amount: Requested loan amount (optional)
            requested_tenure: Requested tenure in months
        
        Returns:
            UnderwritingDecision with approval status and terms
        """
        self.log_action(
            "assess_eligibility",
            customer_id=credit_profile.customer_id,
            credit_score=credit_profile.credit_score,
            active_loans=len(credit_profile.active_loans),
            requested_amount=requested_amount
        )
        
        # Special handling for customers with no existing loans
        if len(credit_profile.active_loans) == 0:
            self.log_action(
                "new_customer_detected",
                customer_id=credit_profile.customer_id,
                credit_score=credit_profile.credit_score
            )
        
        # Check loan count limit
        if len(credit_profile.active_loans) > self.MAX_LOAN_COUNT:
            loan_count = len(credit_profile.active_loans)
            return self._create_rejection(
                credit_profile=credit_profile,
                reason=f"We appreciate your interest in our loan products. However, we've noticed you currently have "
                       f"{loan_count} active loans. To ensure responsible lending and your financial wellbeing, "
                       f"we can only process applications for customers with up to {self.MAX_LOAN_COUNT} active loans. "
                       f"\n\nWe're here to help you manage your existing debt effectively. Please review our "
                       f"personalized debt management recommendations below. Once you've reduced your loan count, "
                       f"we'd be happy to reconsider your application.",
                improvement_plan=self._generate_too_many_loans_advice(credit_profile)
            )
        
        # Check minimum credit score
        if credit_profile.credit_score < self.MIN_CREDIT_SCORE:
            return self._create_rejection(
                credit_profile=credit_profile,
                reason=f"Your credit score of {credit_profile.credit_score} is below our minimum requirement of {self.MIN_CREDIT_SCORE}. "
                       f"We've prepared a personalized credit improvement plan to help you qualify in the future.",
                improvement_plan=self._generate_credit_improvement_plan(credit_profile)
            )
        
        # Determine credit tier
        credit_tier = self._determine_credit_tier(credit_profile.credit_score)
        tier_config = self.CREDIT_TIERS[credit_tier]
        
        # Apply competitive rate for new customers with no existing loans
        interest_rate = tier_config["interest_rate"]
        if len(credit_profile.active_loans) == 0 and credit_profile.credit_score >= 700:
            # Offer 0.5% discount for new customers with good credit
            interest_rate = max(interest_rate - 0.5, 9.5)  # Minimum 9.5%
            self.log_action(
                "new_customer_discount_applied",
                customer_id=credit_profile.customer_id,
                original_rate=tier_config["interest_rate"],
                discounted_rate=interest_rate
            )
        
        # Calculate maximum eligible loan amount
        max_loan_amount = self._calculate_max_loan_amount(
            credit_profile=credit_profile,
            interest_rate=interest_rate,
            tenure_months=requested_tenure,
            max_dti=tier_config["max_dti"]
        )
        
        # Check if customer can afford any loan
        if max_loan_amount <= 0:
            return self._create_rejection(
                credit_profile=credit_profile,
                reason=f"Based on your current income and existing EMI obligations, "
                       f"your debt-to-income ratio is too high to qualify for additional loans. "
                       f"Current DTI: {credit_profile.debt_to_income_ratio:.1f}%",
                improvement_plan=self._generate_high_dti_advice(credit_profile)
            )
        
        # Determine final loan amount
        if requested_amount is None:
            # Offer maximum eligible amount
            loan_amount = max_loan_amount
        elif requested_amount <= max_loan_amount:
            # Approve requested amount
            loan_amount = requested_amount
        else:
            # Requested amount exceeds eligibility, offer maximum
            loan_amount = max_loan_amount
        
        # Calculate EMI
        monthly_emi = calculate_emi(loan_amount, interest_rate, requested_tenure)
        
        # Create approval decision
        return UnderwritingDecision(
            approved=True,
            loan_amount=loan_amount,
            interest_rate=interest_rate,
            tenure_months=requested_tenure,
            monthly_emi=monthly_emi,
            rejection_reason=None,
            improvement_plan=None,
            credit_score_tier=credit_tier,
            max_eligible_amount=max_loan_amount
        )
    
    def _determine_credit_tier(self, credit_score: int) -> str:
        """
        Determine credit tier based on credit score.
        
        Args:
            credit_score: Credit score
        
        Returns:
            Credit tier name (EXCELLENT, GOOD, FAIR, POOR)
        """
        if credit_score >= self.CREDIT_TIERS["EXCELLENT"]["min_score"]:
            return "EXCELLENT"
        elif credit_score >= self.CREDIT_TIERS["GOOD"]["min_score"]:
            return "GOOD"
        elif credit_score >= self.CREDIT_TIERS["FAIR"]["min_score"]:
            return "FAIR"
        else:
            return "POOR"
    
    def _calculate_max_loan_amount(
        self,
        credit_profile: CreditProfile,
        interest_rate: float,
        tenure_months: int,
        max_dti: float
    ) -> float:
        """
        Calculate maximum loan amount based on DTI constraints.
        
        Args:
            credit_profile: Customer's credit profile
            interest_rate: Interest rate for the loan
            tenure_months: Loan tenure
            max_dti: Maximum allowed DTI ratio
        
        Returns:
            Maximum eligible loan amount
        """
        if credit_profile.monthly_income is None or credit_profile.monthly_income <= 0:
            # Default income assumption if not available
            monthly_income = 50000
        else:
            monthly_income = credit_profile.monthly_income
        
        existing_emi = credit_profile.total_monthly_emi
        
        max_amount = calculate_max_loan_amount(
            monthly_income=monthly_income,
            existing_emi=existing_emi,
            annual_interest_rate=interest_rate,
            tenure_months=tenure_months,
            max_dti_ratio=max_dti
        )
        
        return max_amount
    
    def _create_rejection(
        self,
        credit_profile: CreditProfile,
        reason: str,
        improvement_plan: Optional[List[str]] = None
    ) -> UnderwritingDecision:
        """
        Create a rejection decision.
        
        Args:
            credit_profile: Customer's credit profile
            reason: Rejection reason
            improvement_plan: Credit improvement recommendations
        
        Returns:
            UnderwritingDecision with rejection
        """
        credit_tier = self._determine_credit_tier(credit_profile.credit_score)
        
        return UnderwritingDecision(
            approved=False,
            loan_amount=None,
            interest_rate=None,
            tenure_months=None,
            monthly_emi=None,
            rejection_reason=reason,
            improvement_plan=improvement_plan,
            credit_score_tier=credit_tier,
            max_eligible_amount=0.0
        )
    
    def _generate_credit_improvement_plan(self, credit_profile: CreditProfile) -> List[str]:
        """
        Generate personalized credit improvement plan using LLM.
        
        Args:
            credit_profile: Customer's credit profile
        
        Returns:
            List of actionable recommendations
        """
        # Build context for LLM
        context = f"""
Generate a personalized credit improvement plan for a customer with the following profile:
- Current Credit Score: {credit_profile.credit_score}
- Number of Active Loans: {len(credit_profile.active_loans)}
- Total Outstanding Debt: ₹{credit_profile.total_outstanding:,.2f}
- Monthly EMI Obligations: ₹{credit_profile.total_monthly_emi:,.2f}
- Debt-to-Income Ratio: {credit_profile.debt_to_income_ratio:.1f}%

Provide 5-6 specific, actionable steps to improve their credit score to at least 650 within 6-12 months.
Each recommendation should be practical and tailored to their situation.
Format as a numbered list with clear action items.
"""
        
        try:
            # Get LLM-generated recommendations
            llm_response = self.llm_client.generate(context, temperature=0.7, max_tokens=600)
            
            # Parse response into list
            recommendations = []
            for line in llm_response.split('\n'):
                line = line.strip()
                # Remove numbering and extract recommendation
                if line and (line[0].isdigit() or line.startswith('-') or line.startswith('•')):
                    # Clean up the line
                    cleaned = line.lstrip('0123456789.-•) ').strip()
                    if cleaned:
                        recommendations.append(cleaned)
            
            # If we got good recommendations, use them
            if len(recommendations) >= 4:
                self.log_action("llm_credit_improvement_plan_generated", 
                              customer_id=credit_profile.customer_id,
                              recommendations_count=len(recommendations))
                return recommendations
        
        except Exception as e:
            # Log error but continue with fallback
            self.log_action("llm_credit_improvement_plan_failed", 
                          error=str(e),
                          customer_id=credit_profile.customer_id)
        
        # Fallback to rule-based recommendations
        plan = [
            f"Pay all bills on time for the next 6-12 months to improve payment history",
            f"Reduce credit utilization to below 30% on all credit cards",
            f"Avoid applying for new credit for at least 6 months",
        ]
        
        if credit_profile.total_outstanding > 0:
            plan.append(f"Focus on paying down existing debt of ₹{credit_profile.total_outstanding:,.2f}")
        
        plan.append(f"Check your credit report for errors and dispute any inaccuracies")
        plan.append(f"Consider becoming an authorized user on a family member's credit card with good history")
        
        return plan
    
    def _generate_too_many_loans_advice(self, credit_profile: CreditProfile) -> List[str]:
        """
        Generate empathetic advice for customers with too many loans.
        
        Args:
            credit_profile: Customer's credit profile
        
        Returns:
            List of recommendations with debt management strategies
        """
        loan_count = len(credit_profile.active_loans)
        
        advice = [
            f"We understand managing {loan_count} loans can be challenging. Here's how we can help:",
            f"Focus on paying off your smallest loans first (debt snowball method) to reduce the total count quickly",
            f"Consider consolidating some of your existing loans to simplify repayment and potentially lower interest rates",
            f"Create a debt repayment plan prioritizing high-interest loans to save money",
            f"Set up automatic payments to avoid missing EMIs and damaging your credit score",
            f"Avoid taking on any new debt until you've reduced your loan count to {self.MAX_LOAN_COUNT} or fewer",
            f"Once you've paid off 1-2 loans, you'll be eligible to reapply for additional financing",
            f"Consider consulting with a financial advisor for personalized debt management strategies"
        ]
        
        # Add specific advice based on total outstanding
        if credit_profile.total_outstanding > 500000:
            advice.append(f"With ₹{credit_profile.total_outstanding:,.0f} in total debt, focus on reducing this by at least 20% before applying again")
        
        return advice
    
    def _generate_high_dti_advice(self, credit_profile: CreditProfile) -> List[str]:
        """
        Generate advice for customers with high DTI ratio.
        
        Args:
            credit_profile: Customer's credit profile
        
        Returns:
            List of recommendations
        """
        return [
            f"Work on increasing your monthly income through additional sources",
            f"Focus on paying down existing loans to reduce your monthly EMI of ₹{credit_profile.total_monthly_emi:,.2f}",
            f"Consider refinancing high-interest loans to lower your monthly obligations",
            f"Create a budget to identify areas where you can reduce expenses",
            f"Aim to bring your debt-to-income ratio below 40% before reapplying"
        ]
    
    def generate_loan_offer(
        self,
        decision: UnderwritingDecision,
        customer_id: str
    ) -> LoanOffer:
        """
        Generate complete loan offer from underwriting decision.
        
        Args:
            decision: Approved underwriting decision
            customer_id: Customer identifier
        
        Returns:
            LoanOffer with complete details
        """
        if not decision.approved:
            raise BusinessLogicError("Cannot generate offer for rejected application")
        
        # Generate unique offer ID
        offer_id = f"OFFER_{uuid.uuid4().hex[:8].upper()}"
        
        # Calculate financial details
        total_interest = calculate_total_interest(
            principal=decision.loan_amount,
            emi=decision.monthly_emi,
            tenure_months=decision.tenure_months
        )
        
        total_repayment = decision.loan_amount + total_interest
        processing_fee = round(decision.loan_amount * self.PROCESSING_FEE_PERCENTAGE, 2)
        
        # Calculate offer validity (7 days from now)
        valid_until = (datetime.now() + timedelta(days=7)).strftime("%Y-%m-%d")
        
        # Special conditions based on credit tier
        special_conditions = self._get_special_conditions(decision.credit_score_tier)
        
        loan_offer = LoanOffer(
            offer_id=offer_id,
            customer_id=customer_id,
            loan_amount=decision.loan_amount,
            interest_rate=decision.interest_rate,
            tenure_months=decision.tenure_months,
            monthly_emi=decision.monthly_emi,
            processing_fee=processing_fee,
            total_interest=total_interest,
            total_repayment=total_repayment,
            offer_valid_until=valid_until,
            special_conditions=special_conditions
        )
        
        self.log_action(
            "loan_offer_generated",
            offer_id=offer_id,
            customer_id=customer_id,
            loan_amount=decision.loan_amount,
            interest_rate=decision.interest_rate,
            tenure_months=decision.tenure_months
        )
        
        return loan_offer
    
    def _get_special_conditions(self, credit_tier: str) -> List[str]:
        """
        Get special conditions based on credit tier.
        
        Args:
            credit_tier: Credit tier
        
        Returns:
            List of special conditions
        """
        conditions = [
            "No prepayment charges after 6 months",
            "Processing fee of 1% applicable",
            "Loan disbursement within 48 hours of documentation"
        ]
        
        if credit_tier == "EXCELLENT":
            conditions.append("Eligible for top-up loan after 12 months")
            conditions.append("Priority customer service")
        elif credit_tier == "GOOD":
            conditions.append("Eligible for top-up loan after 18 months")
        
        return conditions
    
    def recalculate_with_verified_income(
        self,
        credit_profile: CreditProfile,
        verified_income: float,
        requested_amount: Optional[float] = None,
        requested_tenure: int = DEFAULT_TENURE_MONTHS
    ) -> UnderwritingDecision:
        """
        Recalculate eligibility with verified income.
        
        Args:
            credit_profile: Customer's credit profile
            verified_income: Verified monthly income
            requested_amount: Requested loan amount
            requested_tenure: Requested tenure
        
        Returns:
            Updated underwriting decision
        """
        # Update credit profile with verified income
        updated_profile = credit_profile.model_copy()
        updated_profile.monthly_income = verified_income
        
        # Recalculate DTI ratio
        if verified_income > 0:
            updated_profile.debt_to_income_ratio = (
                credit_profile.total_monthly_emi / verified_income * 100
            )
        
        self.log_action(
            "recalculate_with_verified_income",
            customer_id=credit_profile.customer_id,
            verified_income=verified_income,
            new_dti=updated_profile.debt_to_income_ratio
        )
        
        # Reassess eligibility
        return self.assess_eligibility(updated_profile, requested_amount, requested_tenure)
    
    def generate_new_customer_offer(
        self,
        credit_profile: CreditProfile,
        requested_amount: Optional[float] = None,
        requested_tenure: int = DEFAULT_TENURE_MONTHS
    ) -> Dict[str, Any]:
        """
        Generate standard loan offer for new customers with no existing loans.
        
        Args:
            credit_profile: Customer's credit profile with no active loans
            requested_amount: Requested loan amount
            requested_tenure: Requested tenure
        
        Returns:
            Dictionary with offer details and new customer benefits
        """
        if len(credit_profile.active_loans) != 0:
            raise BusinessLogicError("This method is only for customers with no existing loans")
        
        self.log_action(
            "generate_new_customer_offer",
            customer_id=credit_profile.customer_id,
            credit_score=credit_profile.credit_score
        )
        
        # Assess eligibility (will apply new customer discount automatically)
        decision = self.assess_eligibility(
            credit_profile=credit_profile,
            requested_amount=requested_amount,
            requested_tenure=requested_tenure
        )
        
        # Build new customer offer with benefits
        offer_details = {
            "decision": decision,
            "is_new_customer": True,
            "new_customer_benefits": [
                "Competitive interest rate for first-time borrowers",
                "No hidden charges or prepayment penalties after 6 months",
                "Fast approval and disbursement within 48 hours",
                "Flexible repayment options"
            ]
        }
        
        # Add special benefits based on credit score
        if credit_profile.credit_score >= 750:
            offer_details["new_customer_benefits"].extend([
                "Premium customer status with dedicated relationship manager",
                "Pre-approved top-up loan eligibility after 12 months"
            ])
            offer_details["special_rate_applied"] = True
        elif credit_profile.credit_score >= 700:
            offer_details["new_customer_benefits"].append(
                "Eligible for top-up loan after 18 months"
            )
            offer_details["special_rate_applied"] = True
        
        return offer_details
    
    def generate_new_customer_offer(
        self,
        credit_profile: CreditProfile,
        requested_amount: Optional[float] = None,
        requested_tenure: int = DEFAULT_TENURE_MONTHS
    ) -> UnderwritingDecision:
        """
        Generate standard loan offer for customers with no existing loans.
        The competitive rate discount is automatically applied in assess_eligibility.
        
        Args:
            credit_profile: Customer's credit profile with no active loans
            requested_amount: Requested loan amount
            requested_tenure: Requested tenure
        
        Returns:
            UnderwritingDecision with competitive new customer rates
        """
        if len(credit_profile.active_loans) != 0:
            raise BusinessLogicError("This offer is only for customers with no existing loans")
        
        self.log_action(
            "generate_new_customer_offer",
            customer_id=credit_profile.customer_id,
            credit_score=credit_profile.credit_score,
            requested_amount=requested_amount
        )
        
        # Assess eligibility - discount is automatically applied for new customers
        # with credit score >= 700 in the assess_eligibility method
        decision = self.assess_eligibility(
            credit_profile=credit_profile,
            requested_amount=requested_amount,
            requested_tenure=requested_tenure
        )
        
        return decision
    
    def compare_single_loan_options(
        self,
        credit_profile: CreditProfile,
        requested_amount: Optional[float] = None,
        requested_tenure: int = DEFAULT_TENURE_MONTHS
    ) -> Dict[str, Any]:
        """
        Compare loan transfer vs new loan for customers with single existing loan.
        
        Args:
            credit_profile: Customer's credit profile with one active loan
            requested_amount: Requested loan amount
            requested_tenure: Requested tenure
        
        Returns:
            Dictionary with comparison data for both options
        """
        if len(credit_profile.active_loans) != 1:
            raise BusinessLogicError("This comparison is only for customers with exactly one active loan")
        
        existing_loan = credit_profile.active_loans[0]
        
        self.log_action(
            "compare_single_loan_options",
            customer_id=credit_profile.customer_id,
            existing_loan_id=existing_loan.loan_id,
            existing_outstanding=existing_loan.outstanding
        )
        
        # Option 1: Transfer existing loan (consolidation-like)
        transfer_amount = existing_loan.outstanding + (requested_amount or 0)
        transfer_decision = self.assess_eligibility(
            credit_profile=credit_profile,
            requested_amount=transfer_amount,
            requested_tenure=requested_tenure
        )
        
        # Option 2: New loan (keep existing loan separate)
        new_loan_decision = self.assess_eligibility(
            credit_profile=credit_profile,
            requested_amount=requested_amount,
            requested_tenure=requested_tenure
        )
        
        # Calculate comparison metrics
        comparison = {
            "existing_loan": {
                "loan_id": existing_loan.loan_id,
                "loan_type": existing_loan.loan_type,
                "outstanding": existing_loan.outstanding,
                "interest_rate": existing_loan.interest_rate,
                "monthly_emi": existing_loan.monthly_emi,
                "remaining_tenure": existing_loan.remaining_tenure
            },
            "option_1_transfer": {
                "description": "Transfer existing loan + new amount",
                "total_amount": transfer_amount,
                "approved": transfer_decision.approved,
                "interest_rate": transfer_decision.interest_rate if transfer_decision.approved else None,
                "monthly_emi": transfer_decision.monthly_emi if transfer_decision.approved else None,
                "tenure_months": transfer_decision.tenure_months if transfer_decision.approved else None,
                "total_monthly_payment": transfer_decision.monthly_emi if transfer_decision.approved else None
            },
            "option_2_new_loan": {
                "description": "New loan (keep existing loan separate)",
                "new_loan_amount": requested_amount,
                "approved": new_loan_decision.approved,
                "interest_rate": new_loan_decision.interest_rate if new_loan_decision.approved else None,
                "new_loan_emi": new_loan_decision.monthly_emi if new_loan_decision.approved else None,
                "tenure_months": new_loan_decision.tenure_months if new_loan_decision.approved else None,
                "total_monthly_payment": (existing_loan.monthly_emi + new_loan_decision.monthly_emi) if new_loan_decision.approved else None
            }
        }
        
        # Add recommendation
        if transfer_decision.approved and new_loan_decision.approved:
            transfer_emi = transfer_decision.monthly_emi
            combined_emi = existing_loan.monthly_emi + new_loan_decision.monthly_emi
            
            if transfer_emi < combined_emi:
                comparison["recommendation"] = "transfer"
                comparison["recommendation_reason"] = f"Lower monthly payment: ₹{transfer_emi:,.0f} vs ₹{combined_emi:,.0f}"
                comparison["monthly_savings"] = combined_emi - transfer_emi
            else:
                comparison["recommendation"] = "new_loan"
                comparison["recommendation_reason"] = f"Keep loans separate for flexibility"
                comparison["monthly_savings"] = 0
        elif transfer_decision.approved:
            comparison["recommendation"] = "transfer"
            comparison["recommendation_reason"] = "Only transfer option is approved"
        elif new_loan_decision.approved:
            comparison["recommendation"] = "new_loan"
            comparison["recommendation_reason"] = "Only new loan option is approved"
        else:
            comparison["recommendation"] = None
            comparison["recommendation_reason"] = "Neither option approved"
        
        return comparison
