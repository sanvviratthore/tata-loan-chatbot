"""
Debt Consolidation Agent

Generates consolidation offers for users with multiple loans, showing potential savings
and creating comparison tables between current loans and consolidated loan.
"""

from typing import Dict, Any, List
from datetime import datetime, timedelta
import uuid

from agents.base_agent import BaseAgent, handle_errors, ValidationError, BusinessLogicError
from schemas.models import ConsolidationOffer, Loan, CreditProfile
from utils.loan_calculator import (
    calculate_emi,
    calculate_total_interest,
    generate_amortization_schedule
)


class DebtConsolidationAgent(BaseAgent):
    """
    Agent responsible for generating debt consolidation offers.
    
    Analyzes multiple active loans and creates a consolidated loan offer with:
    - Reduced interest rate
    - Single monthly EMI
    - Savings calculation (monthly and total interest)
    - Side-by-side comparison table
    """
    
    def __init__(self):
        """Initialize debt consolidation agent."""
        super().__init__("debt_consolidation_agent")
        
        # Consolidation configuration
        self.min_loans_for_consolidation = 2
        self.max_loans_for_consolidation = 5
        self.interest_rate_reduction = 2.0  # Percentage points reduction
        self.min_interest_rate = 9.5  # Minimum consolidated rate
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for debt consolidation.
        
        Args:
            input_data: Dictionary containing:
                - credit_profile: CreditProfile object with active loans
            session_state: Current session state
        
        Returns:
            Dictionary containing:
                - success: bool
                - data: ConsolidationOffer object
                - next_agent: "sales" for offer presentation
                - message: User-friendly message
        """
        self.log_action("process_consolidation_request", session_id=session_state.get("session_id"))
        
        # Validate input
        self.validate_input(input_data)
        
        # Extract credit profile
        credit_profile_data = input_data.get("credit_profile")
        if isinstance(credit_profile_data, dict):
            credit_profile = CreditProfile(**credit_profile_data)
        else:
            credit_profile = credit_profile_data
        
        # Generate consolidation offer
        consolidation_offer = self.generate_consolidation_offer(
            active_loans=credit_profile.active_loans,
            credit_score=credit_profile.credit_score,
            customer_id=credit_profile.customer_id
        )
        
        # Log decision
        self.log_decision(
            decision="consolidation_offer_generated",
            reasoning=f"Consolidating {len(credit_profile.active_loans)} loans with "
                     f"monthly savings of ₹{consolidation_offer.monthly_savings:.2f}",
            customer_id=credit_profile.customer_id,
            monthly_savings=consolidation_offer.monthly_savings,
            total_interest_savings=consolidation_offer.total_interest_savings
        )
        
        # Create response
        return self.create_response(
            success=True,
            data=consolidation_offer.model_dump(),
            next_agent="sales",
            message=f"Great news! We can consolidate your {len(credit_profile.active_loans)} loans "
                   f"and save you ₹{consolidation_offer.monthly_savings:.2f} per month!"
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for consolidation.
        
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
        
        credit_profile_data = input_data["credit_profile"]
        
        # Extract active loans
        if isinstance(credit_profile_data, dict):
            active_loans = credit_profile_data.get("active_loans", [])
        else:
            active_loans = credit_profile_data.active_loans
        
        # Validate loan count
        loan_count = len(active_loans)
        if loan_count < self.min_loans_for_consolidation:
            raise BusinessLogicError(
                f"Consolidation requires at least {self.min_loans_for_consolidation} loans. "
                f"You have {loan_count} loan(s).",
                context={"loan_count": loan_count}
            )
        
        if loan_count > self.max_loans_for_consolidation:
            raise BusinessLogicError(
                f"Cannot consolidate more than {self.max_loans_for_consolidation} loans. "
                f"You have {loan_count} loans.",
                context={"loan_count": loan_count}
            )
        
        return True
    
    def generate_consolidation_offer(
        self,
        active_loans: List[Loan],
        credit_score: int,
        customer_id: str
    ) -> ConsolidationOffer:
        """
        Generate a complete consolidation offer with savings analysis.
        
        Args:
            active_loans: List of active loans to consolidate
            credit_score: Customer's credit score
            customer_id: Customer identifier
        
        Returns:
            ConsolidationOffer object with all details
        """
        self.log_action(
            "generate_consolidation_offer",
            customer_id=customer_id,
            loan_count=len(active_loans),
            credit_score=credit_score
        )
        
        # Calculate current loan totals
        total_outstanding = sum(loan.outstanding for loan in active_loans)
        current_total_emi = sum(loan.monthly_emi for loan in active_loans)
        
        # Calculate weighted average interest rate
        weighted_rate = sum(
            loan.outstanding * loan.interest_rate for loan in active_loans
        ) / total_outstanding if total_outstanding > 0 else 0
        
        # Calculate current total interest
        current_total_interest = self._calculate_current_total_interest(active_loans)
        
        # Determine consolidated loan terms
        consolidated_terms = self._calculate_consolidated_terms(
            total_outstanding=total_outstanding,
            credit_score=credit_score,
            active_loans=active_loans,
            current_avg_rate=weighted_rate
        )
        
        # Calculate new loan details
        new_emi = calculate_emi(
            principal=total_outstanding,
            annual_interest_rate=consolidated_terms["interest_rate"],
            tenure_months=consolidated_terms["tenure_months"]
        )
        
        new_total_interest = calculate_total_interest(
            principal=total_outstanding,
            emi=new_emi,
            tenure_months=consolidated_terms["tenure_months"]
        )
        
        # Calculate savings
        monthly_savings = current_total_emi - new_emi
        total_interest_savings = current_total_interest - new_total_interest
        
        # Create comparison table
        comparison_table = self._create_comparison_table(
            current_loans=active_loans,
            consolidated_amount=total_outstanding,
            new_interest_rate=consolidated_terms["interest_rate"],
            new_tenure=consolidated_terms["tenure_months"],
            new_emi=new_emi,
            current_total_emi=current_total_emi,
            current_total_interest=current_total_interest,
            new_total_interest=new_total_interest
        )
        
        # Generate offer ID
        offer_id = f"CONSOL_{customer_id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}"
        
        # Create ConsolidationOffer object
        consolidation_offer = ConsolidationOffer(
            offer_id=offer_id,
            customer_id=customer_id,
            consolidated_amount=total_outstanding,
            new_interest_rate=consolidated_terms["interest_rate"],
            new_tenure_months=consolidated_terms["tenure_months"],
            new_monthly_emi=new_emi,
            current_total_emi=current_total_emi,
            monthly_savings=monthly_savings,
            total_interest_savings=total_interest_savings,
            loans_being_consolidated=active_loans,
            comparison_table=comparison_table
        )
        
        self.log_action(
            "consolidation_offer_created",
            offer_id=offer_id,
            consolidated_amount=total_outstanding,
            monthly_savings=monthly_savings,
            total_interest_savings=total_interest_savings
        )
        
        return consolidation_offer
    
    def _calculate_consolidated_terms(
        self,
        total_outstanding: float,
        credit_score: int,
        active_loans: List[Loan],
        current_avg_rate: float
    ) -> Dict[str, Any]:
        """
        Calculate terms for the consolidated loan.
        
        Args:
            total_outstanding: Total amount to consolidate
            credit_score: Customer's credit score
            active_loans: List of active loans
            current_avg_rate: Current weighted average interest rate
        
        Returns:
            Dictionary with interest_rate and tenure_months
        """
        # Calculate new interest rate (reduce by configured percentage)
        new_rate = current_avg_rate - self.interest_rate_reduction
        
        # Apply minimum rate floor
        new_rate = max(new_rate, self.min_interest_rate)
        
        # Adjust based on credit score
        if credit_score >= 750:
            new_rate = max(new_rate - 0.5, self.min_interest_rate)
        elif credit_score < 650:
            new_rate = new_rate + 1.0
        
        # Determine tenure (use maximum of existing tenures or 60 months)
        max_existing_tenure = max(loan.remaining_tenure for loan in active_loans)
        new_tenure = max(max_existing_tenure, 60)
        
        # Cap tenure at reasonable maximum
        new_tenure = min(new_tenure, 84)  # Max 7 years
        
        return {
            "interest_rate": round(new_rate, 2),
            "tenure_months": new_tenure
        }
    
    def _calculate_current_total_interest(self, active_loans: List[Loan]) -> float:
        """
        Calculate total interest that would be paid on current loans.
        
        Args:
            active_loans: List of active loans
        
        Returns:
            Total interest amount across all loans
        """
        total_interest = 0.0
        
        for loan in active_loans:
            # Total payment = EMI * remaining tenure
            total_payment = loan.monthly_emi * loan.remaining_tenure
            # Interest = Total payment - Outstanding principal
            interest = total_payment - loan.outstanding
            total_interest += interest
        
        return round(total_interest, 2)
    
    def _create_comparison_table(
        self,
        current_loans: List[Loan],
        consolidated_amount: float,
        new_interest_rate: float,
        new_tenure: int,
        new_emi: float,
        current_total_emi: float,
        current_total_interest: float,
        new_total_interest: float
    ) -> Dict[str, Any]:
        """
        Create a side-by-side comparison table.
        
        Args:
            current_loans: List of current loans
            consolidated_amount: Consolidated loan amount
            new_interest_rate: New interest rate
            new_tenure: New tenure in months
            new_emi: New monthly EMI
            current_total_emi: Current total EMI
            current_total_interest: Current total interest
            new_total_interest: New total interest
        
        Returns:
            Dictionary with comparison data
        """
        # Current loans summary
        current_loans_summary = []
        for loan in current_loans:
            current_loans_summary.append({
                "loan_id": loan.loan_id,
                "loan_type": loan.loan_type,
                "lender": loan.lender,
                "outstanding": loan.outstanding,
                "interest_rate": loan.interest_rate,
                "monthly_emi": loan.monthly_emi,
                "remaining_tenure": loan.remaining_tenure
            })
        
        # Consolidated loan summary
        consolidated_summary = {
            "loan_type": "Consolidated Personal Loan",
            "lender": "Tata Capital",
            "amount": consolidated_amount,
            "interest_rate": new_interest_rate,
            "monthly_emi": new_emi,
            "tenure_months": new_tenure
        }
        
        # Comparison metrics
        comparison = {
            "current_loans": current_loans_summary,
            "consolidated_loan": consolidated_summary,
            "comparison_metrics": {
                "total_outstanding": {
                    "current": sum(loan.outstanding for loan in current_loans),
                    "consolidated": consolidated_amount
                },
                "monthly_emi": {
                    "current": current_total_emi,
                    "consolidated": new_emi,
                    "savings": current_total_emi - new_emi,
                    "savings_percentage": round(
                        ((current_total_emi - new_emi) / current_total_emi * 100), 2
                    ) if current_total_emi > 0 else 0
                },
                "total_interest": {
                    "current": current_total_interest,
                    "consolidated": new_total_interest,
                    "savings": current_total_interest - new_total_interest
                },
                "number_of_emis": {
                    "current": "Multiple EMIs",
                    "consolidated": "Single EMI"
                }
            }
        }
        
        return comparison
    
    def calculate_savings_breakdown(
        self,
        consolidation_offer: ConsolidationOffer
    ) -> Dict[str, float]:
        """
        Calculate detailed savings breakdown.
        
        Args:
            consolidation_offer: ConsolidationOffer object
        
        Returns:
            Dictionary with detailed savings metrics
        """
        monthly_savings = consolidation_offer.monthly_savings
        annual_savings = monthly_savings * 12
        total_interest_savings = consolidation_offer.total_interest_savings
        
        # Calculate total savings over tenure
        total_emi_savings = monthly_savings * consolidation_offer.new_tenure_months
        
        return {
            "monthly_savings": round(monthly_savings, 2),
            "annual_savings": round(annual_savings, 2),
            "total_interest_savings": round(total_interest_savings, 2),
            "total_emi_savings": round(total_emi_savings, 2),
            "savings_percentage": round(
                (monthly_savings / consolidation_offer.current_total_emi * 100), 2
            ) if consolidation_offer.current_total_emi > 0 else 0
        }
