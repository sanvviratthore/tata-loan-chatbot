"""
Credit Bureau Agent

Retrieves and analyzes user's credit profile and active loans from mock credit bureau data.
Determines appropriate workflow based on credit score and loan portfolio.
"""

import json
import os
from typing import Dict, Any, List, Optional
from pathlib import Path

from agents.base_agent import BaseAgent, handle_errors, ValidationError, DataError, BusinessLogicError
from schemas.models import CreditProfile, Loan, PortfolioAnalysis


class CreditBureauAgent(BaseAgent):
    """
    Agent responsible for credit profile retrieval and analysis.
    
    Determines workflow routing based on:
    - Credit score thresholds
    - Number of active loans
    - Debt-to-income ratio
    """
    
    def __init__(self, data_path: Optional[str] = None):
        """
        Initialize credit bureau agent.
        
        Args:
            data_path: Path to credit bureau data file (optional, defaults to data/credit_bureau_data.json)
        """
        super().__init__("credit_bureau_agent")
        
        # Set data path
        if data_path is None:
            # Default to data/credit_bureau_data.json relative to project root
            project_root = Path(__file__).parent.parent
            data_path = project_root / "data" / "credit_bureau_data.json"
        
        self.data_path = Path(data_path)
        self._credit_data = None
        
        self.log_action("initialized", data_path=str(self.data_path))
    
    def _load_credit_data(self) -> Dict[str, Any]:
        """
        Load credit bureau data from JSON file.
        
        Returns:
            Dictionary containing credit profiles
        
        Raises:
            DataError: If file cannot be loaded
        """
        if self._credit_data is not None:
            return self._credit_data
        
        try:
            with open(self.data_path, 'r') as f:
                self._credit_data = json.load(f)
            
            self.log_action("credit_data_loaded", 
                          profiles_count=len(self._credit_data.get('credit_profiles', [])))
            return self._credit_data
        
        except FileNotFoundError:
            error_msg = f"Credit bureau data file not found: {self.data_path}"
            self.logger.error(error_msg)
            raise DataError(error_msg, context={"file_path": str(self.data_path)})
        
        except json.JSONDecodeError as e:
            error_msg = f"Invalid JSON in credit bureau data file: {str(e)}"
            self.logger.error(error_msg)
            raise DataError(error_msg, context={"file_path": str(self.data_path)})
    
    @handle_errors
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data for credit profile retrieval.
        
        Args:
            input_data: Must contain 'customer_id'
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(input_data, dict):
            raise ValidationError("Input must be a dictionary", context={"input_type": type(input_data).__name__})
        
        if 'customer_id' not in input_data:
            raise ValidationError("Missing required field: customer_id", field="customer_id")
        
        customer_id = input_data['customer_id']
        if not isinstance(customer_id, str) or not customer_id.strip():
            raise ValidationError("customer_id must be a non-empty string", field="customer_id")
        
        return True
    
    @handle_errors
    def fetch_credit_profile(self, customer_id: str) -> CreditProfile:
        """
        Retrieve credit profile for a customer from mock data.
        
        Args:
            customer_id: Unique customer identifier
        
        Returns:
            CreditProfile object with credit score and active loans
        
        Raises:
            DataError: If customer not found or data is invalid
        """
        self.log_action("fetch_credit_profile", customer_id=customer_id)
        
        # Load credit data
        credit_data = self._load_credit_data()
        
        # Find customer's credit profile
        profiles = credit_data.get('credit_profiles', [])
        customer_profile = None
        
        for profile in profiles:
            if profile.get('customer_id') == customer_id:
                customer_profile = profile
                break
        
        if customer_profile is None:
            error_msg = f"Credit profile not found for customer: {customer_id}"
            self.logger.warning(error_msg)
            raise DataError(error_msg, context={"customer_id": customer_id})
        
        # Convert to Pydantic model
        try:
            credit_profile = CreditProfile(**customer_profile)
            
            self.log_action("credit_profile_retrieved",
                          customer_id=customer_id,
                          credit_score=credit_profile.credit_score,
                          active_loans_count=len(credit_profile.active_loans),
                          total_outstanding=credit_profile.total_outstanding)
            
            return credit_profile
        
        except Exception as e:
            error_msg = f"Invalid credit profile data for customer {customer_id}: {str(e)}"
            self.logger.error(error_msg)
            raise DataError(error_msg, context={"customer_id": customer_id, "error": str(e)})
    
    @handle_errors
    def analyze_loan_portfolio(self, loans: List[Loan], monthly_income: Optional[float] = None) -> PortfolioAnalysis:
        """
        Analyze customer's loan portfolio.
        
        Args:
            loans: List of active loans
            monthly_income: Customer's monthly income (optional)
        
        Returns:
            PortfolioAnalysis with aggregated metrics
        """
        self.log_action("analyze_loan_portfolio", loan_count=len(loans))
        
        total_loans = len(loans)
        total_outstanding = sum(loan.outstanding for loan in loans)
        total_monthly_emi = sum(loan.monthly_emi for loan in loans)
        
        # Calculate weighted average interest rate
        if total_outstanding > 0:
            weighted_interest = sum(
                loan.outstanding * loan.interest_rate for loan in loans
            ) / total_outstanding
        else:
            weighted_interest = 0.0
        
        # Calculate DTI ratio if income provided
        dti_ratio = None
        if monthly_income and monthly_income > 0:
            dti_ratio = (total_monthly_emi / monthly_income) * 100
        
        # Determine recommended flow (will be set by determine_flow method)
        recommended_flow = "unknown"
        
        analysis = PortfolioAnalysis(
            total_loans=total_loans,
            total_outstanding=total_outstanding,
            total_monthly_emi=total_monthly_emi,
            average_interest_rate=round(weighted_interest, 2),
            debt_to_income_ratio=round(dti_ratio, 2) if dti_ratio is not None else None,
            recommended_flow=recommended_flow
        )
        
        self.log_action("portfolio_analyzed",
                       total_loans=total_loans,
                       total_outstanding=total_outstanding,
                       total_monthly_emi=total_monthly_emi,
                       average_interest_rate=analysis.average_interest_rate,
                       dti_ratio=dti_ratio)
        
        return analysis
    
    def calculate_debt_to_income(self, loans: List[Loan], monthly_income: float) -> float:
        """
        Calculate debt-to-income ratio.
        
        Args:
            loans: List of active loans
            monthly_income: Monthly income
        
        Returns:
            DTI ratio as percentage
        
        Raises:
            ValidationError: If monthly_income is invalid
        """
        if monthly_income <= 0:
            raise ValidationError("Monthly income must be greater than 0", field="monthly_income")
        
        total_monthly_emi = sum(loan.monthly_emi for loan in loans)
        dti_ratio = (total_monthly_emi / monthly_income) * 100
        
        self.log_action("dti_calculated",
                       total_monthly_emi=total_monthly_emi,
                       monthly_income=monthly_income,
                       dti_ratio=round(dti_ratio, 2))
        
        return round(dti_ratio, 2)
    
    @handle_errors
    def determine_flow(self, credit_profile: CreditProfile) -> str:
        """
        Determine appropriate workflow based on credit profile.
        
        Flow determination logic:
        - Credit score < 650: credit_improvement
        - > 5 active loans: rejection
        - 2-5 active loans: consolidation
        - 1 active loan: underwriting (with single loan option)
        - 0 active loans: underwriting (standard flow)
        
        Args:
            credit_profile: Customer's credit profile
        
        Returns:
            Flow name: 'credit_improvement', 'rejection', 'consolidation', or 'underwriting'
        """
        credit_score = credit_profile.credit_score
        loan_count = len(credit_profile.active_loans)
        
        self.log_action("determine_flow",
                       credit_score=credit_score,
                       loan_count=loan_count)
        
        # Rule 1: Low credit score (< 650) -> credit improvement
        if credit_score < 650:
            self.log_decision(
                decision="credit_improvement",
                reasoning=f"Credit score {credit_score} is below 650 threshold",
                credit_score=credit_score
            )
            return "credit_improvement"
        
        # Rule 2: Too many loans (> 5) -> rejection
        if loan_count > 5:
            self.log_decision(
                decision="rejection",
                reasoning=f"Customer has {loan_count} active loans, exceeding limit of 5",
                loan_count=loan_count
            )
            return "rejection"
        
        # Rule 3: Multiple loans (2-5) -> consolidation
        if loan_count >= 2:
            self.log_decision(
                decision="consolidation",
                reasoning=f"Customer has {loan_count} active loans, eligible for consolidation",
                loan_count=loan_count
            )
            return "consolidation"
        
        # Rule 4: Single loan or no loans -> underwriting
        if loan_count == 1:
            self.log_decision(
                decision="underwriting",
                reasoning="Customer has 1 active loan, offer both transfer and new loan options",
                loan_count=loan_count
            )
        else:
            self.log_decision(
                decision="underwriting",
                reasoning="Customer has no active loans, standard loan offer",
                loan_count=loan_count
            )
        
        return "underwriting"
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Main processing method for credit bureau agent.
        
        Args:
            input_data: Must contain 'customer_id'
            session_state: Current session state
        
        Returns:
            Dictionary containing:
                - success: True if processing succeeded
                - data: Credit profile and portfolio analysis
                - next_agent: Name of next agent to route to
                - message: User-facing message
        """
        # Validate input
        self.validate_input(input_data)
        
        customer_id = input_data['customer_id']
        
        # Fetch credit profile
        credit_profile = self.fetch_credit_profile(customer_id)
        
        # Analyze portfolio
        portfolio_analysis = self.analyze_loan_portfolio(
            credit_profile.active_loans,
            credit_profile.monthly_income
        )
        
        # Determine workflow
        recommended_flow = self.determine_flow(credit_profile)
        portfolio_analysis.recommended_flow = recommended_flow
        
        # Map flow to next agent
        flow_to_agent_map = {
            "credit_improvement": "underwriting",  # Underwriting agent handles improvement plans
            "rejection": "sales",  # Sales agent delivers rejection with empathy
            "consolidation": "consolidation",
            "underwriting": "underwriting"
        }
        
        next_agent = flow_to_agent_map.get(recommended_flow, "underwriting")
        
        # Generate user message based on flow
        messages = {
            "credit_improvement": f"I've reviewed your credit profile. Your credit score is {credit_profile.credit_score}. Let me help you understand your options for improving your credit.",
            "rejection": f"I've reviewed your credit profile. You currently have {len(credit_profile.active_loans)} active loans. Let me discuss your situation.",
            "consolidation": f"Great news! I found {len(credit_profile.active_loans)} active loans that we can consolidate to save you money on interest and reduce your monthly payments.",
            "underwriting": f"I've reviewed your credit profile. Your credit score is {credit_profile.credit_score}. Let me check your loan eligibility."
        }
        
        message = messages.get(recommended_flow, "I've retrieved your credit profile.")
        
        # Create response
        response = self.create_response(
            success=True,
            data={
                "credit_profile": credit_profile.model_dump(),
                "portfolio_analysis": portfolio_analysis.model_dump(),
                "recommended_flow": recommended_flow
            },
            next_agent=next_agent,
            message=message
        )
        
        self.log_action("process_complete",
                       customer_id=customer_id,
                       recommended_flow=recommended_flow,
                       next_agent=next_agent)
        
        return response
