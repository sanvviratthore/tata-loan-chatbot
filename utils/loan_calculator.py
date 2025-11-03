"""
Loan Calculator Utility
Handles EMI calculations, savings comparisons, and financial health scoring
"""

def calculate_emi(principal, annual_rate, years):
    """
    Calculate EMI using standard formula
    
    Formula: EMI = P × r × (1 + r)^n / ((1 + r)^n - 1)
    Where:
    P = Principal loan amount
    r = Monthly interest rate (annual rate / 12 / 100)
    n = Loan tenure in months
    """
    try:
        monthly_rate = annual_rate / 12 / 100
        months = years * 12
        
        if monthly_rate == 0:
            emi = principal / months
        else:
            emi = (principal * monthly_rate * (1 + monthly_rate) ** months) / ((1 + monthly_rate) ** months - 1)
        
        return round(emi, 2)
    except:
        return 0

def calculate_total_interest(principal, emi, years):
    """Calculate total interest payable over loan tenure"""
    total_payment = emi * years * 12
    return round(total_payment - principal, 2)

def calculate_consolidation_savings(current_loans, new_loan_amount, new_interest_rate, new_tenure_years):
    """
    Calculate savings from debt consolidation
    
    Parameters:
    - current_loans: List of existing loans with EMI amounts
    - new_loan_amount: Consolidated loan amount
    - new_interest_rate: New interest rate for consolidation
    - new_tenure_years: New loan tenure
    """
    try:
        # Calculate current total EMI
        current_total_emi = sum(loan.get('emi', 0) for loan in current_loans)
        
        # Calculate new EMI for consolidation
        new_emi = calculate_emi(new_loan_amount, new_interest_rate, new_tenure_years)
        
        # Calculate savings
        monthly_savings = current_total_emi - new_emi
        yearly_savings = monthly_savings * 12
        total_savings = yearly_savings * new_tenure_years
        
        return {
            'current_total_emi': round(current_total_emi, 2),
            'new_emi': new_emi,
            'monthly_savings': round(monthly_savings, 2),
            'yearly_savings': round(yearly_savings, 2),
            'total_savings': round(total_savings, 2),
            'savings_percentage': round((monthly_savings / current_total_emi) * 100, 1) if current_total_emi > 0 else 0
        }
    except:
        return {
            'current_total_emi': 0,
            'new_emi': 0,
            'monthly_savings': 0,
            'yearly_savings': 0,
            'total_savings': 0,
            'savings_percentage': 0
        }

def calculate_debt_to_income_ratio(monthly_income, total_monthly_emi):
    """Calculate Debt-to-Income ratio (DTI)"""
    try:
        dti = (total_monthly_emi / monthly_income) * 100
        return round(dti, 1)
    except:
        return 0

def calculate_loan_affordability(monthly_income, existing_emi=0, max_dti=50):
    """
    Calculate maximum loan amount customer can afford
    
    Parameters:
    - monthly_income: Customer's monthly income
    - existing_emi: Existing monthly EMIs
    - max_dti: Maximum allowed Debt-to-Income ratio (default 50%)
    """
    try:
        max_total_emi = (max_dti / 100) * monthly_income
        available_for_new_loan = max_total_emi - existing_emi
        
        if available_for_new_loan <= 0:
            return 0
            
        # Assuming 11% interest and 3-year tenure for affordability calculation
        affordable_loan = reverse_emi_calculation(available_for_new_loan, 11, 3)
        return round(affordable_loan, 2)
    except:
        return 0

def reverse_emi_calculation(emi, annual_rate, years):
    """
    Calculate principal amount from EMI (reverse calculation)
    
    Formula: P = EMI × ((1 + r)^n - 1) / (r × (1 + r)^n)
    """
    try:
        monthly_rate = annual_rate / 12 / 100
        months = years * 12
        
        if monthly_rate == 0:
            principal = emi * months
        else:
            principal = (emi * ((1 + monthly_rate) ** months - 1)) / (monthly_rate * (1 + monthly_rate) ** months)
        
        return principal
    except:
        return 0

def calculate_financial_health_score(credit_score, dti_ratio, existing_loans_count, payment_history):
    """
    Calculate Financial Health Score (1-10)
    
    Parameters:
    - credit_score: Credit score (300-900)
    - dti_ratio: Debt-to-Income ratio
    - existing_loans_count: Number of active loans
    - payment_history: "Excellent", "Good", "Average", "Poor"
    """
    score = 0
    
    # Credit Score Component (0-4 points)
    if credit_score >= 800:
        score += 4
    elif credit_score >= 750:
        score += 3
    elif credit_score >= 700:
        score += 2
    elif credit_score >= 650:
        score += 1
    
    # DTI Ratio Component (0-3 points)
    if dti_ratio <= 30:
        score += 3
    elif dti_ratio <= 40:
        score += 2
    elif dti_ratio <= 50:
        score += 1
    
    # Existing Loans Component (0-2 points)
    if existing_loans_count == 0:
        score += 2
    elif existing_loans_count == 1:
        score += 1
    
    # Payment History Component (0-1 point)
    if payment_history in ["Excellent", "Very Good"]:
        score += 1
    
    return min(score, 10)  # Cap at 10

def get_improvement_tips(credit_score, dti_ratio, existing_loans_count, financial_health_score):
    """Generate personalized improvement tips based on financial health"""
    tips = []
    
    if credit_score < 700:
        tips.append(f"Increase credit score from {credit_score} to 700+ by paying EMIs on time and reducing credit card utilization")
    
    if dti_ratio > 50:
        tips.append(f"Reduce Debt-to-Income ratio from {dti_ratio}% to below 50% by paying off smaller loans first")
    
    if existing_loans_count >= 3:
        tips.append(f"Consolidate {existing_loans_count} existing loans into one for better management")
    
    if financial_health_score <= 5:
        tips.append("Maintain consistent payment history for 3-6 months")
    
    if credit_score < 650:
        tips.append("Keep credit card utilization below 30% of your limit")
    
    # Always include these general tips
    general_tips = [
        "Avoid multiple loan applications in short period",
        "Maintain healthy mix of secured and unsecured credit",
        "Review your credit report regularly for errors"
    ]
    
    # Add 1-2 general tips if we don't have enough specific ones
    if len(tips) < 3:
        tips.extend(general_tips[:3 - len(tips)])
    
    return tips[:4]  # Return max 4 tips

def suggest_loan_terms(credit_score, monthly_income, existing_loans):
    """
    Suggest optimal loan terms based on customer profile
    """
    total_existing_emi = sum(loan.get('emi', 0) for loan in existing_loans)
    dti_ratio = calculate_debt_to_income_ratio(monthly_income, total_existing_emi)
    
    # Determine interest rate based on credit score
    if credit_score >= 800:
        interest_rate = 10.0
    elif credit_score >= 750:
        interest_rate = 10.5
    elif credit_score >= 700:
        interest_rate = 11.0
    elif credit_score >= 650:
        interest_rate = 12.0
    else:
        interest_rate = 13.5
    
    # Determine maximum loan amount based on DTI
    max_affordable = calculate_loan_affordability(monthly_income, total_existing_emi)
    
    # Suggest tenure based on loan amount
    suggested_tenure = 3  # Default 3 years
    
    if max_affordable > 500000:
        suggested_tenure = 5
    elif max_affordable > 200000:
        suggested_tenure = 4
    
    return {
        'suggested_interest_rate': interest_rate,
        'suggested_tenure_years': suggested_tenure,
        'max_affordable_amount': max_affordable,
        'estimated_emi': calculate_emi(max_affordable, interest_rate, suggested_tenure),
        'debt_to_income_ratio': dti_ratio
    }

# Example usage and testing
if __name__ == "__main__":
    # Test EMI calculation
    emi = calculate_emi(300000, 11, 3)
    print(f"EMI for ₹3L @ 11% for 3 years: ₹{emi:,.2f}")
    
    # Test consolidation savings
    current_loans = [
        {'emi': 8000},
        {'emi': 5500}
    ]
    savings = calculate_consolidation_savings(current_loans, 350000, 11, 4)
    print(f"Consolidation savings: ₹{savings['monthly_savings']:,.2f}/month")
    
    # Test financial health score
    health_score = calculate_financial_health_score(780, 35, 2, "Excellent")
    print(f"Financial Health Score: {health_score}/10")
    
    # Test improvement tips
    tips = get_improvement_tips(650, 55, 3, 4)
    print("Improvement tips:", tips)