"""
Loan Calculator Utility Module

Provides functions for EMI calculation, interest calculation, and amortization schedule generation.
"""

from typing import List, Dict
import math


def calculate_emi(principal: float, annual_interest_rate: float, tenure_months: int) -> float:
    """
    Calculate Equated Monthly Installment (EMI) using the standard formula.
    
    Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    where:
        P = Principal loan amount
        r = Monthly interest rate (annual rate / 12 / 100)
        n = Tenure in months
    
    Args:
        principal: Loan amount in currency units
        annual_interest_rate: Annual interest rate as percentage (e.g., 12.5 for 12.5%)
        tenure_months: Loan tenure in months
    
    Returns:
        Monthly EMI amount rounded to 2 decimal places
    
    Raises:
        ValueError: If any input parameter is invalid
    """
    if principal <= 0:
        raise ValueError("Principal amount must be greater than 0")
    if annual_interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")
    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than 0")
    
    # Handle zero interest rate case
    if annual_interest_rate == 0:
        return round(principal / tenure_months, 2)
    
    # Convert annual rate to monthly rate
    monthly_rate = annual_interest_rate / 12 / 100
    
    # Calculate EMI using formula
    emi = principal * monthly_rate * math.pow(1 + monthly_rate, tenure_months) / \
          (math.pow(1 + monthly_rate, tenure_months) - 1)
    
    return round(emi, 2)


def calculate_total_interest(principal: float, emi: float, tenure_months: int) -> float:
    """
    Calculate total interest payable over the loan tenure.
    
    Args:
        principal: Loan amount
        emi: Monthly EMI amount
        tenure_months: Loan tenure in months
    
    Returns:
        Total interest amount rounded to 2 decimal places
    """
    total_payment = emi * tenure_months
    total_interest = total_payment - principal
    return round(total_interest, 2)


def generate_amortization_schedule(
    principal: float,
    annual_interest_rate: float,
    tenure_months: int,
    emi: float = None
) -> List[Dict[str, float]]:
    """
    Generate complete amortization schedule showing month-by-month breakdown.
    
    Args:
        principal: Loan amount
        annual_interest_rate: Annual interest rate as percentage
        tenure_months: Loan tenure in months
        emi: Pre-calculated EMI (optional, will calculate if not provided)
    
    Returns:
        List of dictionaries, each containing:
            - month: Month number (1 to tenure_months)
            - opening_balance: Outstanding balance at start of month
            - emi: EMI paid for the month
            - interest: Interest component
            - principal: Principal component
            - closing_balance: Outstanding balance at end of month
    
    Raises:
        ValueError: If any input parameter is invalid
    """
    if principal <= 0:
        raise ValueError("Principal amount must be greater than 0")
    if annual_interest_rate < 0:
        raise ValueError("Interest rate cannot be negative")
    if tenure_months <= 0:
        raise ValueError("Tenure must be greater than 0")
    
    # Calculate EMI if not provided
    if emi is None:
        emi = calculate_emi(principal, annual_interest_rate, tenure_months)
    
    monthly_rate = annual_interest_rate / 12 / 100
    schedule = []
    outstanding_balance = principal
    
    for month in range(1, tenure_months + 1):
        opening_balance = outstanding_balance
        
        # Calculate interest for this month
        interest_component = round(outstanding_balance * monthly_rate, 2)
        
        # Calculate principal component
        principal_component = round(emi - interest_component, 2)
        
        # For last month, adjust to clear remaining balance
        if month == tenure_months:
            principal_component = opening_balance
            emi_adjusted = round(principal_component + interest_component, 2)
        else:
            emi_adjusted = emi
        
        # Update outstanding balance
        outstanding_balance = round(opening_balance - principal_component, 2)
        
        # Ensure balance doesn't go negative
        if outstanding_balance < 0:
            outstanding_balance = 0
        
        schedule.append({
            "month": month,
            "opening_balance": opening_balance,
            "emi": emi_adjusted,
            "interest": interest_component,
            "principal": principal_component,
            "closing_balance": outstanding_balance
        })
    
    return schedule


def calculate_savings(
    current_total_emi: float,
    new_emi: float,
    current_total_interest: float,
    new_total_interest: float,
    tenure_months: int
) -> Dict[str, float]:
    """
    Calculate savings from loan consolidation or refinancing.
    
    Args:
        current_total_emi: Sum of all current EMIs
        new_emi: New consolidated/refinanced EMI
        current_total_interest: Total interest on current loans
        new_total_interest: Total interest on new loan
        tenure_months: Tenure of new loan
    
    Returns:
        Dictionary containing:
            - monthly_savings: Reduction in monthly EMI
            - total_interest_savings: Reduction in total interest
            - total_savings: Total amount saved over tenure
    """
    monthly_savings = round(current_total_emi - new_emi, 2)
    interest_savings = round(current_total_interest - new_total_interest, 2)
    total_savings = round(monthly_savings * tenure_months, 2)
    
    return {
        "monthly_savings": monthly_savings,
        "total_interest_savings": interest_savings,
        "total_savings": total_savings
    }


def calculate_max_loan_amount(
    monthly_income: float,
    existing_emi: float,
    annual_interest_rate: float,
    tenure_months: int,
    max_dti_ratio: float = 0.5
) -> float:
    """
    Calculate maximum loan amount based on income and DTI ratio.
    
    Args:
        monthly_income: Monthly income of applicant
        existing_emi: Sum of existing EMI obligations
        annual_interest_rate: Interest rate for new loan
        tenure_months: Desired tenure
        max_dti_ratio: Maximum debt-to-income ratio (default 0.5 = 50%)
    
    Returns:
        Maximum eligible loan amount
    """
    if monthly_income <= 0:
        raise ValueError("Monthly income must be greater than 0")
    if existing_emi < 0:
        raise ValueError("Existing EMI cannot be negative")
    if max_dti_ratio <= 0 or max_dti_ratio > 1:
        raise ValueError("DTI ratio must be between 0 and 1")
    
    # Calculate maximum affordable total EMI
    max_total_emi = monthly_income * max_dti_ratio
    
    # Calculate available EMI for new loan
    available_emi = max_total_emi - existing_emi
    
    if available_emi <= 0:
        return 0.0
    
    # Handle zero interest rate
    if annual_interest_rate == 0:
        return round(available_emi * tenure_months, 2)
    
    # Reverse EMI formula to get principal
    monthly_rate = annual_interest_rate / 12 / 100
    
    principal = available_emi * (math.pow(1 + monthly_rate, tenure_months) - 1) / \
                (monthly_rate * math.pow(1 + monthly_rate, tenure_months))
    
    return round(principal, 2)
