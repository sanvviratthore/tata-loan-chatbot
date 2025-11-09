"""
Unit tests for loan calculator utility module.
"""

import pytest
import math
from utils.loan_calculator import (
    calculate_emi,
    calculate_total_interest,
    generate_amortization_schedule,
    calculate_savings,
    calculate_max_loan_amount
)


class TestCalculateEMI:
    """Test cases for EMI calculation."""
    
    def test_standard_emi_calculation(self):
        """Test EMI calculation with standard values."""
        principal = 100000
        rate = 12.0
        tenure = 12
        
        emi = calculate_emi(principal, rate, tenure)
        
        # Expected EMI for 100000 at 12% for 12 months is approximately 8884.88
        assert isinstance(emi, float)
        assert emi > 0
        assert 8884 <= emi <= 8885
    
    def test_emi_with_different_tenure(self):
        """Test EMI calculation with longer tenure."""
        principal = 200000
        rate = 10.5
        tenure = 24
        
        emi = calculate_emi(principal, rate, tenure)
        
        # Longer tenure should result in lower EMI
        assert emi > 0
        assert 9200 <= emi <= 9300
    
    def test_emi_with_zero_interest(self):
        """Test EMI calculation with zero interest rate."""
        principal = 120000
        rate = 0.0
        tenure = 12
        
        emi = calculate_emi(principal, rate, tenure)
        
        # With 0% interest, EMI should be principal/tenure
        expected = 120000 / 12
        assert emi == expected
    
    def test_emi_with_high_interest(self):
        """Test EMI calculation with high interest rate."""
        principal = 50000
        rate = 18.0
        tenure = 6
        
        emi = calculate_emi(principal, rate, tenure)
        
        assert emi > principal / tenure  # EMI should be higher than simple division
        assert 8700 <= emi <= 8800
    
    def test_invalid_principal(self):
        """Test that invalid principal raises ValueError."""
        with pytest.raises(ValueError, match="Principal amount must be greater than 0"):
            calculate_emi(0, 12.0, 12)
        
        with pytest.raises(ValueError, match="Principal amount must be greater than 0"):
            calculate_emi(-1000, 12.0, 12)
    
    def test_invalid_interest_rate(self):
        """Test that negative interest rate raises ValueError."""
        with pytest.raises(ValueError, match="Interest rate cannot be negative"):
            calculate_emi(100000, -5.0, 12)
    
    def test_invalid_tenure(self):
        """Test that invalid tenure raises ValueError."""
        with pytest.raises(ValueError, match="Tenure must be greater than 0"):
            calculate_emi(100000, 12.0, 0)
        
        with pytest.raises(ValueError, match="Tenure must be greater than 0"):
            calculate_emi(100000, 12.0, -12)


class TestCalculateTotalInterest:
    """Test cases for total interest calculation."""
    
    def test_total_interest_calculation(self):
        """Test total interest calculation."""
        principal = 100000
        emi = 8884.88
        tenure = 12
        
        total_interest = calculate_total_interest(principal, emi, tenure)
        
        # Total payment - principal = interest
        expected = (emi * tenure) - principal
        assert abs(total_interest - expected) < 0.1
    
    def test_total_interest_with_zero_interest_loan(self):
        """Test total interest for zero interest loan."""
        principal = 120000
        emi = 10000
        tenure = 12
        
        total_interest = calculate_total_interest(principal, emi, tenure)
        
        # Should be zero for zero interest loan
        assert total_interest == 0.0


class TestGenerateAmortizationSchedule:
    """Test cases for amortization schedule generation."""
    
    def test_schedule_length(self):
        """Test that schedule has correct number of entries."""
        principal = 100000
        rate = 12.0
        tenure = 12
        
        schedule = generate_amortization_schedule(principal, rate, tenure)
        
        assert len(schedule) == tenure
    
    def test_schedule_structure(self):
        """Test that each schedule entry has required fields."""
        principal = 50000
        rate = 10.0
        tenure = 6
        
        schedule = generate_amortization_schedule(principal, rate, tenure)
        
        for entry in schedule:
            assert "month" in entry
            assert "opening_balance" in entry
            assert "emi" in entry
            assert "interest" in entry
            assert "principal" in entry
            assert "closing_balance" in entry
    
    def test_schedule_first_month(self):
        """Test first month of schedule."""
        principal = 100000
        rate = 12.0
        tenure = 12
        
        schedule = generate_amortization_schedule(principal, rate, tenure)
        
        first_month = schedule[0]
        assert first_month["month"] == 1
        assert first_month["opening_balance"] == principal
        assert first_month["interest"] > 0
        assert first_month["principal"] > 0
        assert first_month["closing_balance"] < principal
    
    def test_schedule_last_month(self):
        """Test last month of schedule clears balance."""
        principal = 100000
        rate = 12.0
        tenure = 12
        
        schedule = generate_amortization_schedule(principal, rate, tenure)
        
        last_month = schedule[-1]
        assert last_month["month"] == tenure
        assert last_month["closing_balance"] == 0.0
    
    def test_schedule_balance_progression(self):
        """Test that balance decreases monotonically."""
        principal = 100000
        rate = 12.0
        tenure = 12
        
        schedule = generate_amortization_schedule(principal, rate, tenure)
        
        for i in range(len(schedule) - 1):
            assert schedule[i]["closing_balance"] >= schedule[i + 1]["opening_balance"]
    
    def test_schedule_with_provided_emi(self):
        """Test schedule generation with pre-calculated EMI."""
        principal = 100000
        rate = 12.0
        tenure = 12
        emi = 8884.88
        
        schedule = generate_amortization_schedule(principal, rate, tenure, emi)
        
        assert len(schedule) == tenure
        assert schedule[0]["emi"] == emi
    
    def test_invalid_schedule_parameters(self):
        """Test that invalid parameters raise ValueError."""
        with pytest.raises(ValueError):
            generate_amortization_schedule(0, 12.0, 12)
        
        with pytest.raises(ValueError):
            generate_amortization_schedule(100000, -5.0, 12)
        
        with pytest.raises(ValueError):
            generate_amortization_schedule(100000, 12.0, 0)


class TestCalculateSavings:
    """Test cases for savings calculation."""
    
    def test_savings_calculation(self):
        """Test savings calculation with consolidation scenario."""
        current_emi = 15000
        new_emi = 12000
        current_interest = 50000
        new_interest = 35000
        tenure = 24
        
        savings = calculate_savings(current_emi, new_emi, current_interest, new_interest, tenure)
        
        assert savings["monthly_savings"] == 3000
        assert savings["total_interest_savings"] == 15000
        assert savings["total_savings"] == 3000 * 24
    
    def test_no_savings(self):
        """Test when there are no savings."""
        current_emi = 10000
        new_emi = 10000
        current_interest = 20000
        new_interest = 20000
        tenure = 12
        
        savings = calculate_savings(current_emi, new_emi, current_interest, new_interest, tenure)
        
        assert savings["monthly_savings"] == 0
        assert savings["total_interest_savings"] == 0
        assert savings["total_savings"] == 0
    
    def test_negative_savings(self):
        """Test when new loan is more expensive (negative savings)."""
        current_emi = 8000
        new_emi = 9000
        current_interest = 15000
        new_interest = 20000
        tenure = 12
        
        savings = calculate_savings(current_emi, new_emi, current_interest, new_interest, tenure)
        
        assert savings["monthly_savings"] < 0
        assert savings["total_interest_savings"] < 0


class TestCalculateMaxLoanAmount:
    """Test cases for maximum loan amount calculation."""
    
    def test_max_loan_with_no_existing_emi(self):
        """Test max loan calculation with no existing EMI."""
        monthly_income = 50000
        existing_emi = 0
        rate = 12.0
        tenure = 24
        max_dti = 0.5
        
        max_loan = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, max_dti)
        
        assert max_loan > 0
        # With 50% DTI, max EMI = 25000
        # Verify the loan amount makes sense
        assert 500000 <= max_loan <= 600000
    
    def test_max_loan_with_existing_emi(self):
        """Test max loan calculation with existing EMI obligations."""
        monthly_income = 50000
        existing_emi = 10000
        rate = 12.0
        tenure = 24
        max_dti = 0.5
        
        max_loan = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, max_dti)
        
        assert max_loan > 0
        # Available EMI = (50000 * 0.5) - 10000 = 15000
        assert 300000 <= max_loan <= 400000
    
    def test_max_loan_when_dti_exceeded(self):
        """Test max loan when existing EMI exceeds DTI limit."""
        monthly_income = 50000
        existing_emi = 30000  # Already exceeds 50% DTI
        rate = 12.0
        tenure = 24
        max_dti = 0.5
        
        max_loan = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, max_dti)
        
        assert max_loan == 0.0
    
    def test_max_loan_with_zero_interest(self):
        """Test max loan calculation with zero interest."""
        monthly_income = 50000
        existing_emi = 0
        rate = 0.0
        tenure = 24
        max_dti = 0.5
        
        max_loan = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, max_dti)
        
        # With 0% interest, max loan = available EMI * tenure
        expected = (50000 * 0.5) * 24
        assert max_loan == expected
    
    def test_max_loan_with_different_dti_ratios(self):
        """Test max loan with different DTI ratios."""
        monthly_income = 60000
        existing_emi = 0
        rate = 10.0
        tenure = 36
        
        max_loan_40 = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, 0.4)
        max_loan_50 = calculate_max_loan_amount(monthly_income, existing_emi, rate, tenure, 0.5)
        
        # Higher DTI should allow higher loan amount
        assert max_loan_50 > max_loan_40
    
    def test_invalid_income(self):
        """Test that invalid income raises ValueError."""
        with pytest.raises(ValueError, match="Monthly income must be greater than 0"):
            calculate_max_loan_amount(0, 0, 12.0, 24, 0.5)
        
        with pytest.raises(ValueError, match="Monthly income must be greater than 0"):
            calculate_max_loan_amount(-5000, 0, 12.0, 24, 0.5)
    
    def test_invalid_existing_emi(self):
        """Test that negative existing EMI raises ValueError."""
        with pytest.raises(ValueError, match="Existing EMI cannot be negative"):
            calculate_max_loan_amount(50000, -1000, 12.0, 24, 0.5)
    
    def test_invalid_dti_ratio(self):
        """Test that invalid DTI ratio raises ValueError."""
        with pytest.raises(ValueError, match="DTI ratio must be between 0 and 1"):
            calculate_max_loan_amount(50000, 0, 12.0, 24, 0)
        
        with pytest.raises(ValueError, match="DTI ratio must be between 0 and 1"):
            calculate_max_loan_amount(50000, 0, 12.0, 24, 1.5)


class TestIntegrationScenarios:
    """Integration tests for realistic loan scenarios."""
    
    def test_complete_loan_scenario(self):
        """Test complete loan calculation flow."""
        principal = 500000
        rate = 11.5
        tenure = 36
        
        # Calculate EMI
        emi = calculate_emi(principal, rate, tenure)
        assert emi > 0
        
        # Calculate total interest
        total_interest = calculate_total_interest(principal, emi, tenure)
        assert total_interest > 0
        
        # Generate schedule
        schedule = generate_amortization_schedule(principal, rate, tenure, emi)
        assert len(schedule) == tenure
        assert schedule[-1]["closing_balance"] == 0.0
        
        # Verify total payments match
        total_paid = sum(entry["emi"] for entry in schedule)
        assert abs(total_paid - (principal + total_interest)) < 1.0
    
    def test_consolidation_scenario(self):
        """Test loan consolidation savings calculation."""
        # Current loans
        loan1_principal = 150000
        loan1_rate = 14.5
        loan1_tenure = 18
        loan1_emi = calculate_emi(loan1_principal, loan1_rate, loan1_tenure)
        
        loan2_principal = 50000
        loan2_rate = 18.0
        loan2_tenure = 12
        loan2_emi = calculate_emi(loan2_principal, loan2_rate, loan2_tenure)
        
        current_total_emi = loan1_emi + loan2_emi
        
        # Consolidated loan
        consolidated_principal = loan1_principal + loan2_principal
        consolidated_rate = 12.5  # Reduced rate
        consolidated_tenure = max(loan1_tenure, loan2_tenure)
        consolidated_emi = calculate_emi(consolidated_principal, consolidated_rate, consolidated_tenure)
        
        # Calculate savings
        loan1_interest = calculate_total_interest(loan1_principal, loan1_emi, loan1_tenure)
        loan2_interest = calculate_total_interest(loan2_principal, loan2_emi, loan2_tenure)
        current_total_interest = loan1_interest + loan2_interest
        
        consolidated_interest = calculate_total_interest(
            consolidated_principal, consolidated_emi, consolidated_tenure
        )
        
        savings = calculate_savings(
            current_total_emi,
            consolidated_emi,
            current_total_interest,
            consolidated_interest,
            consolidated_tenure
        )
        
        # Consolidation should provide savings
        assert savings["monthly_savings"] > 0
        assert consolidated_emi < current_total_emi
