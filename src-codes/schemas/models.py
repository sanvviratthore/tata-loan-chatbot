"""
Pydantic models for data validation and schema enforcement across all agents.
"""

from typing import Optional, List
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re


class VerificationResult(BaseModel):
    """Result of identity verification process."""
    
    success: bool = Field(..., description="Whether verification succeeded")
    customer_id: Optional[str] = Field(None, description="Unique customer identifier")
    name: Optional[str] = Field(None, description="Customer name")
    error_message: Optional[str] = Field(None, description="Error message if verification failed")
    retry_count: int = Field(default=0, ge=0, le=3, description="Number of retry attempts")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "customer_id": "CUST001",
            "name": "Rajesh Kumar",
            "error_message": None,
            "retry_count": 0
        }
    })


class Loan(BaseModel):
    """Individual loan details."""
    
    loan_id: str = Field(..., description="Unique loan identifier")
    loan_type: str = Field(..., description="Type of loan (Personal, Credit Card, etc.)")
    lender: Optional[str] = Field(None, description="Lending institution name")
    principal: float = Field(..., gt=0, description="Original loan amount")
    outstanding: float = Field(..., ge=0, description="Current outstanding amount")
    interest_rate: float = Field(..., gt=0, le=50, description="Annual interest rate percentage")
    monthly_emi: float = Field(..., gt=0, description="Monthly EMI amount")
    remaining_tenure: int = Field(..., gt=0, description="Remaining tenure in months")
    
    @field_validator('outstanding')
    @classmethod
    def validate_outstanding(cls, v: float, info) -> float:
        """Ensure outstanding amount doesn't exceed principal."""
        if 'principal' in info.data and v > info.data['principal']:
            raise ValueError("Outstanding amount cannot exceed principal")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "loan_id": "LOAN001",
            "loan_type": "Personal Loan",
            "lender": "Bank A",
            "principal": 200000,
            "outstanding": 150000,
            "interest_rate": 14.5,
            "monthly_emi": 8500,
            "remaining_tenure": 18
        }
    })


class CreditProfile(BaseModel):
    """Complete credit profile with active loans."""
    
    customer_id: str = Field(..., description="Unique customer identifier")
    credit_score: int = Field(..., ge=300, le=900, description="Credit score (300-900 range)")
    active_loans: List[Loan] = Field(default_factory=list, description="List of active loans")
    total_outstanding: float = Field(..., ge=0, description="Total outstanding across all loans")
    total_monthly_emi: float = Field(..., ge=0, description="Total monthly EMI obligations")
    debt_to_income_ratio: Optional[float] = Field(None, ge=0, le=100, description="DTI ratio as percentage")
    monthly_income: Optional[float] = Field(None, gt=0, description="Monthly income")
    
    @field_validator('credit_score')
    @classmethod
    def validate_credit_score(cls, v: int) -> int:
        """Validate credit score is in acceptable range."""
        if v < 300 or v > 900:
            raise ValueError("Credit score must be between 300 and 900")
        return v
    
    @field_validator('active_loans')
    @classmethod
    def validate_loan_count(cls, v: List[Loan]) -> List[Loan]:
        """Validate loan count doesn't exceed reasonable limits."""
        if len(v) > 10:
            raise ValueError("Too many active loans (max 10)")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "customer_id": "CUST001",
            "credit_score": 720,
            "active_loans": [],
            "total_outstanding": 200000,
            "total_monthly_emi": 13500,
            "debt_to_income_ratio": 35.0,
            "monthly_income": 75000
        }
    })


class UnderwritingDecision(BaseModel):
    """Underwriting decision with loan terms or rejection reason."""
    
    approved: bool = Field(..., description="Whether loan is approved")
    loan_amount: Optional[float] = Field(None, gt=0, description="Approved loan amount")
    interest_rate: Optional[float] = Field(None, gt=0, le=50, description="Annual interest rate percentage")
    tenure_months: Optional[int] = Field(None, gt=0, le=360, description="Loan tenure in months")
    monthly_emi: Optional[float] = Field(None, gt=0, description="Monthly EMI amount")
    rejection_reason: Optional[str] = Field(None, description="Reason for rejection if not approved")
    improvement_plan: Optional[List[str]] = Field(None, description="Credit improvement recommendations")
    credit_score_tier: Optional[str] = Field(None, description="Credit score tier (Excellent, Good, Fair, Poor)")
    max_eligible_amount: Optional[float] = Field(None, ge=0, description="Maximum eligible loan amount")
    
    @field_validator('loan_amount', 'interest_rate', 'tenure_months', 'monthly_emi')
    @classmethod
    def validate_approval_fields(cls, v, info) -> Optional[float]:
        """Ensure required fields are present when approved."""
        if info.data.get('approved') and v is None and info.field_name != 'max_eligible_amount':
            raise ValueError(f"{info.field_name} is required when loan is approved")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "approved": True,
            "loan_amount": 300000,
            "interest_rate": 10.5,
            "tenure_months": 60,
            "monthly_emi": 6420,
            "rejection_reason": None,
            "improvement_plan": None,
            "credit_score_tier": "Excellent",
            "max_eligible_amount": 500000
        }
    })


class LoanOffer(BaseModel):
    """Complete loan offer details."""
    
    offer_id: str = Field(..., description="Unique offer identifier")
    customer_id: str = Field(..., description="Customer identifier")
    loan_amount: float = Field(..., gt=0, description="Loan amount")
    interest_rate: float = Field(..., gt=0, le=50, description="Annual interest rate percentage")
    tenure_months: int = Field(..., gt=0, le=360, description="Loan tenure in months")
    monthly_emi: float = Field(..., gt=0, description="Monthly EMI amount")
    processing_fee: float = Field(default=0, ge=0, description="Processing fee amount")
    total_interest: float = Field(..., ge=0, description="Total interest payable")
    total_repayment: float = Field(..., gt=0, description="Total amount to be repaid")
    offer_valid_until: Optional[str] = Field(None, description="Offer validity date")
    special_conditions: Optional[List[str]] = Field(None, description="Special terms or conditions")
    
    @field_validator('total_repayment')
    @classmethod
    def validate_total_repayment(cls, v: float, info) -> float:
        """Ensure total repayment is greater than loan amount."""
        if 'loan_amount' in info.data and v < info.data['loan_amount']:
            raise ValueError("Total repayment must be greater than loan amount")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "offer_id": "OFFER001",
            "customer_id": "CUST001",
            "loan_amount": 300000,
            "interest_rate": 10.5,
            "tenure_months": 60,
            "monthly_emi": 6420,
            "processing_fee": 3000,
            "total_interest": 85200,
            "total_repayment": 385200,
            "offer_valid_until": "2025-01-15",
            "special_conditions": ["Pre-payment allowed after 6 months"]
        }
    })


class ConsolidationOffer(BaseModel):
    """Debt consolidation offer with savings analysis."""
    
    offer_id: str = Field(..., description="Unique offer identifier")
    customer_id: str = Field(..., description="Customer identifier")
    consolidated_amount: float = Field(..., gt=0, description="Total amount being consolidated")
    new_interest_rate: float = Field(..., gt=0, le=50, description="New consolidated interest rate")
    new_tenure_months: int = Field(..., gt=0, le=360, description="New loan tenure in months")
    new_monthly_emi: float = Field(..., gt=0, description="New monthly EMI after consolidation")
    current_total_emi: float = Field(..., gt=0, description="Current total EMI across all loans")
    monthly_savings: float = Field(..., description="Monthly EMI savings (can be negative)")
    total_interest_savings: float = Field(..., description="Total interest savings over tenure")
    loans_being_consolidated: List[Loan] = Field(..., min_length=2, description="Loans being consolidated")
    comparison_table: dict = Field(..., description="Side-by-side comparison data")
    
    @field_validator('monthly_savings')
    @classmethod
    def calculate_monthly_savings(cls, v: float, info) -> float:
        """Calculate and validate monthly savings."""
        if 'current_total_emi' in info.data and 'new_monthly_emi' in info.data:
            expected_savings = info.data['current_total_emi'] - info.data['new_monthly_emi']
            if abs(v - expected_savings) > 1:  # Allow 1 rupee tolerance for rounding
                raise ValueError("Monthly savings calculation mismatch")
        return v
    
    @field_validator('loans_being_consolidated')
    @classmethod
    def validate_loan_count(cls, v: List[Loan]) -> List[Loan]:
        """Ensure at least 2 loans for consolidation."""
        if len(v) < 2:
            raise ValueError("Consolidation requires at least 2 loans")
        if len(v) > 5:
            raise ValueError("Cannot consolidate more than 5 loans")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "offer_id": "CONSOL001",
            "customer_id": "CUST001",
            "consolidated_amount": 200000,
            "new_interest_rate": 12.5,
            "new_tenure_months": 24,
            "new_monthly_emi": 9500,
            "current_total_emi": 13500,
            "monthly_savings": 4000,
            "total_interest_savings": 50000,
            "loans_being_consolidated": [],
            "comparison_table": {}
        }
    })


class Customer(BaseModel):
    """Customer information from database."""
    
    customer_id: str = Field(..., description="Unique customer identifier")
    name: str = Field(..., min_length=1, description="Customer full name")
    pan: str = Field(..., description="PAN card number")
    mobile: str = Field(..., description="Mobile number")
    email: Optional[str] = Field(None, description="Email address")
    monthly_income: float = Field(..., gt=0, description="Monthly income")
    employment_type: str = Field(..., description="Employment type (Salaried, Self-Employed, etc.)")
    
    @field_validator('pan')
    @classmethod
    def validate_pan_format(cls, v: str) -> str:
        """Validate PAN format: 5 letters, 4 digits, 1 letter."""
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
        if not re.match(pan_pattern, v.upper()):
            raise ValueError("Invalid PAN format. Expected format: ABCDE1234F")
        return v.upper()
    
    @field_validator('mobile')
    @classmethod
    def validate_mobile_format(cls, v: str) -> str:
        """Validate mobile number format: 10 digits."""
        mobile_pattern = r'^[6-9][0-9]{9}$'
        if not re.match(mobile_pattern, v):
            raise ValueError("Invalid mobile number. Must be 10 digits starting with 6-9")
        return v
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "customer_id": "CUST001",
            "name": "Rajesh Kumar",
            "pan": "ABCDE1234F",
            "mobile": "9876543210",
            "email": "rajesh.kumar@example.com",
            "monthly_income": 75000,
            "employment_type": "Salaried"
        }
    })


class SavingsBreakdown(BaseModel):
    """Detailed savings breakdown for consolidation."""
    
    monthly_savings: float = Field(..., description="Monthly EMI savings")
    annual_savings: float = Field(..., description="Annual savings")
    total_interest_savings: float = Field(..., description="Total interest savings over tenure")
    current_total_interest: float = Field(..., ge=0, description="Total interest on current loans")
    new_total_interest: float = Field(..., ge=0, description="Total interest on consolidated loan")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "monthly_savings": 4000,
            "annual_savings": 48000,
            "total_interest_savings": 50000,
            "current_total_interest": 150000,
            "new_total_interest": 100000
        }
    })


class PortfolioAnalysis(BaseModel):
    """Analysis of customer's loan portfolio."""
    
    total_loans: int = Field(..., ge=0, description="Number of active loans")
    total_outstanding: float = Field(..., ge=0, description="Total outstanding amount")
    total_monthly_emi: float = Field(..., ge=0, description="Total monthly EMI")
    average_interest_rate: float = Field(..., ge=0, description="Weighted average interest rate")
    debt_to_income_ratio: Optional[float] = Field(None, ge=0, le=100, description="DTI ratio percentage")
    recommended_flow: str = Field(..., description="Recommended workflow (consolidation, underwriting, etc.)")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "total_loans": 3,
            "total_outstanding": 200000,
            "total_monthly_emi": 13500,
            "average_interest_rate": 14.5,
            "debt_to_income_ratio": 35.0,
            "recommended_flow": "consolidation"
        }
    })


class SalaryVerificationResult(BaseModel):
    """Result of salary verification process."""
    
    success: bool = Field(..., description="Whether verification succeeded")
    verified_salary: Optional[float] = Field(None, gt=0, description="Verified monthly salary")
    verification_method: Optional[str] = Field(None, description="Method used (document_upload, manual_entry)")
    document_filename: Optional[str] = Field(None, description="Uploaded document filename")
    error_message: Optional[str] = Field(None, description="Error message if verification failed")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "verified_salary": 75000,
            "verification_method": "document_upload",
            "document_filename": "salary_slip.pdf",
            "error_message": None
        }
    })


class SessionState(BaseModel):
    """Session state for conversation management."""
    
    session_id: str = Field(..., description="Unique session identifier")
    user_id: Optional[str] = Field(None, description="Customer ID if verified")
    current_agent: str = Field(default="master", description="Currently active agent")
    workflow_stage: str = Field(default="INIT", description="Current workflow stage")
    customer_data: Optional[Customer] = Field(None, description="Customer information")
    credit_profile: Optional[CreditProfile] = Field(None, description="Credit profile data")
    current_offer: Optional[dict] = Field(None, description="Current loan or consolidation offer")
    conversation_history: List[dict] = Field(default_factory=list, description="Message history")
    retry_counts: dict = Field(default_factory=dict, description="Retry counters for various operations")
    timestamp: str = Field(..., description="Session creation timestamp")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "session_id": "sess_123456",
            "user_id": "CUST001",
            "current_agent": "verification",
            "workflow_stage": "VERIFICATION",
            "customer_data": None,
            "credit_profile": None,
            "current_offer": None,
            "conversation_history": [],
            "retry_counts": {},
            "timestamp": "2025-01-08T10:30:00Z"
        }
    })
