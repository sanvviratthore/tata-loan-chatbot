import os
import streamlit as st
from datetime import datetime

def generate_sanction_text(customer_data, loan_details, loan_type="regular"):
    """Generate sanction letter as text/HTML instead of PDF"""
    
    # Calculate total interest and savings
    total_interest = loan_details.get('emi', 0) * loan_details.get('tenure_years', 0) * 12 - loan_details.get('amount', 0)
    
    if loan_type == "consolidation":
        previous_total_emi = sum(loan['emi'] for loan in loan_details.get('previous_loans', []))
        monthly_savings = previous_total_emi - loan_details.get('emi', 0)
        yearly_savings = monthly_savings * 12
        total_savings = yearly_savings * loan_details.get('tenure_years', 0)
        
        content = f"""
        <div style="border: 2px solid #0066cc; padding: 25px; border-radius: 15px; background: linear-gradient(135deg, #f0f8ff, #e6f3ff); font-family: Arial, sans-serif;">
        <div style="text-align: center; border-bottom: 2px solid #0066cc; padding-bottom: 15px; margin-bottom: 20px;">
            <img src="https://www.tatacapital.com/images/logo.png" alt="Tata Capital" style="height: 40px; margin-bottom: 10px;">
            <h2 style="color: #0066cc; margin: 10px 0 5px 0;">TATA CAPITAL FINANCIAL SERVICES</h2>
            <h3 style="color: #333; margin: 0; font-weight: normal;">LOAN SANCTION LETTER</h3>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="color: #0066cc; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Customer Details</h4>
                <p><strong>Name:</strong> {customer_data.get('name', 'N/A')}</p>
                <p><strong>Customer ID:</strong> {customer_data.get('id', 'CUST' + datetime.now().strftime('%H%M%S'))}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%d-%m-%Y')}</p>
                <p><strong>Contact:</strong> {customer_data.get('phone', 'N/A')}</p>
            </div>
            <div>
                <h4 style="color: #0066cc; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Loan Summary</h4>
                <p><strong>Loan Type:</strong> Debt Consolidation</p>
                <p><strong>Reference No:</strong> TC{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
                <p><strong>Status:</strong> <span style="color: green; font-weight: bold;">APPROVED</span></p>
            </div>
        </div>

        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #0066cc; margin-bottom: 20px;">
            <h4 style="color: #0066cc; margin-top: 0;">Loan Terms & Conditions</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div>
                    <p><strong>Sanctioned Amount:</strong> ₹{loan_details.get('amount', 0):,}</p>
                    <p><strong>Interest Rate:</strong> {loan_details.get('interest_rate', 0)}% p.a.</p>
                    <p><strong>Loan Tenure:</strong> {loan_details.get('tenure_years', 0)} years</p>
                </div>
                <div>
                    <p><strong>Monthly EMI:</strong> ₹{loan_details.get('emi', 0):,}</p>
                    <p><strong>Processing Fee:</strong> 2% + GST</p>
                    <p><strong>Total Interest:</strong> ₹{total_interest:,.0f}</p>
                </div>
            </div>
        </div>

        <div style="background: #e8f5e8; padding: 15px; border-radius: 10px; border: 1px solid #4caf50; margin-bottom: 20px;">
            <h4 style="color: #2e7d32; margin-top: 0;">💰 Consolidation Benefits</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 15px; text-align: center;">
                <div>
                    <p style="font-size: 12px; margin: 0;">Previous EMIs</p>
                    <p style="font-size: 18px; font-weight: bold; color: #666; margin: 5px 0;">₹{previous_total_emi:,}/month</p>
                </div>
                <div>
                    <p style="font-size: 12px; margin: 0;">New EMI</p>
                    <p style="font-size: 18px; font-weight: bold; color: #0066cc; margin: 5px 0;">₹{loan_details.get('emi', 0):,}/month</p>
                </div>
                <div>
                    <p style="font-size: 12px; margin: 0;">Monthly Savings</p>
                    <p style="font-size: 18px; font-weight: bold; color: #4caf50; margin: 5px 0;">₹{monthly_savings:,}</p>
                </div>
            </div>
            <p style="text-align: center; margin: 10px 0 0 0; font-size: 14px; color: #2e7d32;">
                💡 <strong>Total Savings:</strong> ₹{yearly_savings:,}/year (₹{total_savings:,} over loan tenure)
            </p>
        </div>

        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffc107; font-size: 12px;">
            <h4 style="color: #856404; margin-top: 0;">📋 Important Conditions</h4>
            <ul style="margin: 0; padding-left: 20px;">
                <li>This sanction is valid for 30 days from the date of issue</li>
                <li>Loan disbursement subject to verification of submitted documents</li>
                <li>Interest rate subject to change as per market conditions</li>
                <li>Prepayment charges may apply as per Tata Capital policy</li>
            </ul>
        </div>

        <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
            <p style="color: #666; font-size: 14px; margin: 0;">
                <strong>Congratulations on your loan approval!</strong><br>
                For queries: 📞 1800-209-8800 | 📧 customercare@tatacapital.com
            </p>
            <p style="color: #999; font-size: 11px; margin: 10px 0 0 0; font-style: italic;">
                This is a computer-generated document and does not require signature
            </p>
        </div>
        </div>
        """
    else:
        content = f"""
        <div style="border: 2px solid #0066cc; padding: 25px; border-radius: 15px; background: linear-gradient(135deg, #f0f8ff, #e6f3ff); font-family: Arial, sans-serif;">
        <div style="text-align: center; border-bottom: 2px solid #0066cc; padding-bottom: 15px; margin-bottom: 20px;">
            <img src="https://www.tatacapital.com/images/logo.png" alt="Tata Capital" style="height: 40px; margin-bottom: 10px;">
            <h2 style="color: #0066cc; margin: 10px 0 5px 0;">TATA CAPITAL FINANCIAL SERVICES</h2>
            <h3 style="color: #333; margin: 0; font-weight: normal;">LOAN SANCTION LETTER</h3>
        </div>
        
        <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
            <div>
                <h4 style="color: #0066cc; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Customer Details</h4>
                <p><strong>Name:</strong> {customer_data.get('name', 'N/A')}</p>
                <p><strong>Customer ID:</strong> {customer_data.get('id', 'CUST' + datetime.now().strftime('%H%M%S'))}</p>
                <p><strong>Date:</strong> {datetime.now().strftime('%d-%m-%Y')}</p>
                <p><strong>Contact:</strong> {customer_data.get('phone', 'N/A')}</p>
            </div>
            <div>
                <h4 style="color: #0066cc; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Loan Summary</h4>
                <p><strong>Loan Type:</strong> Personal Loan</p>
                <p><strong>Reference No:</strong> TC{datetime.now().strftime('%Y%m%d%H%M%S')}</p>
                <p><strong>Status:</strong> <span style="color: green; font-weight: bold;">APPROVED</span></p>
            </div>
        </div>

        <div style="background: white; padding: 15px; border-radius: 10px; border-left: 4px solid #0066cc;">
            <h4 style="color: #0066cc; margin-top: 0;">Loan Terms & Conditions</h4>
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 10px;">
                <div>
                    <p><strong>Sanctioned Amount:</strong> ₹{loan_details.get('amount', 0):,}</p>
                    <p><strong>Interest Rate:</strong> {loan_details.get('interest_rate', 0)}% p.a.</p>
                    <p><strong>Loan Tenure:</strong> {loan_details.get('tenure_years', 0)} years</p>
                </div>
                <div>
                    <p><strong>Monthly EMI:</strong> ₹{loan_details.get('emi', 0):,}</p>
                    <p><strong>Processing Fee:</strong> 1.5% + GST</p>
                    <p><strong>Total Interest:</strong> ₹{total_interest:,.0f}</p>
                </div>
            </div>
        </div>

        <div style="background: #fff3cd; padding: 15px; border-radius: 10px; border: 1px solid #ffc107; font-size: 12px; margin-top: 20px;">
            <h4 style="color: #856404; margin-top: 0;">📋 Important Conditions</h4>
            <ul style="margin: 0; padding-left: 20px;">
                <li>This sanction is valid for 30 days from the date of issue</li>
                <li>Loan disbursement subject to verification of submitted documents</li>
                <li>Interest rate subject to change as per market conditions</li>
                <li>Prepayment charges may apply as per Tata Capital policy</li>
            </ul>
        </div>

        <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
            <p style="color: #666; font-size: 14px; margin: 0;">
                <strong>Congratulations on your loan approval!</strong><br>
                For queries: 📞 1800-209-8800 | 📧 customercare@tatacapital.com
            </p>
            <p style="color: #999; font-size: 11px; margin: 10px 0 0 0; font-style: italic;">
                This is a computer-generated document and does not require signature
            </p>
        </div>
        </div>
        """
    
    return content

def document_agent(customer_data, loan_details, document_type="sanction", improvement_tips=None):
    """
    Simplified document agent - returns HTML content instead of PDF
    """
    try:
        if document_type == "sanction":
            loan_type = loan_details.get('loan_type', 'regular')
            content = generate_sanction_text(customer_data, loan_details, loan_type)
            message = "📄 Sanction letter generated successfully!"
        else:
            content = generate_health_report_text(customer_data, loan_details, improvement_tips)
            message = "📊 Financial health report generated!"
        
        return {
            "success": True,
            "message": message,
            "content": content,
            "filename": f"document_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": f"❌ Error generating document: {str(e)}",
            "content": None,
            "filename": None
        }

def generate_health_report_text(customer_data, credit_report, improvement_tips):
    """Generate financial health report as HTML"""
    
    score = credit_report.get('credit_score', 0)
    if score >= 750:
        score_color = "#4caf50"
        score_status = "Excellent"
        score_emoji = "🎯"
    elif score >= 700:
        score_color = "#2196f3"
        score_status = "Good"
        score_emoji = "👍"
    elif score >= 650:
        score_color = "#ff9800"
        score_status = "Fair"
        score_emoji = "⚠️"
    else:
        score_color = "#f44336"
        score_status = "Needs Improvement"
        score_emoji = "📉"
    
    # Calculate additional metrics
    total_loans = len(credit_report.get('active_loans', []))
    total_emi = credit_report.get('total_monthly_emi', 0)
    credit_utilization = credit_report.get('credit_utilization', 0)
    
    content = f"""
    <div style="border: 2px solid #ff6b00; padding: 25px; border-radius: 15px; background: linear-gradient(135deg, #fff4e6, #ffe8cc); font-family: Arial, sans-serif;">
    <div style="text-align: center; border-bottom: 2px solid #ff6b00; padding-bottom: 15px; margin-bottom: 20px;">
        <h2 style="color: #ff6b00; margin: 0 0 10px 0;">FINANCIAL HEALTH REPORT</h2>
        <p style="color: #666; margin: 0;">Personalized Credit Assessment</p>
    </div>
    
    <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-bottom: 20px;">
        <div>
            <h4 style="color: #ff6b00; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Personal Details</h4>
            <p><strong>Name:</strong> {customer_data.get('name', 'N/A')}</p>
            <p><strong>Report Date:</strong> {datetime.now().strftime('%d-%m-%Y')}</p>
            <p><strong>Customer ID:</strong> {customer_data.get('id', 'N/A')}</p>
        </div>
        <div>
            <h4 style="color: #ff6b00; border-bottom: 1px solid #ddd; padding-bottom: 5px;">Quick Stats</h4>
            <p><strong>Active Loans:</strong> {total_loans}</p>
            <p><strong>Total Monthly EMI:</strong> ₹{total_emi:,}</p>
            <p><strong>Credit Utilization:</strong> {credit_utilization}%</p>
        </div>
    </div>

    <div style="background: white; padding: 20px; border-radius: 10px; text-align: center; margin-bottom: 20px;">
        <h3 style="color: #333; margin: 0 0 10px 0;">Credit Score Analysis</h3>
        <div style="font-size: 48px; color: {score_color}; font-weight: bold; margin: 10px 0;">
            {score_emoji} {score}/900
        </div>
        <div style="font-size: 18px; color: {score_color}; font-weight: bold; margin-bottom: 15px;">
            {score_status}
        </div>
        <div style="background: #f5f5f5; padding: 10px; border-radius: 5px; font-size: 14px;">
            <div style="display: grid; grid-template-columns: 1fr 1fr 1fr 1fr; gap: 10px; text-align: center;">
                <div>300-649<br><span style="color: #f44336;">Poor</span></div>
                <div>650-699<br><span style="color: #ff9800;">Fair</span></div>
                <div>700-749<br><span style="color: #2196f3;">Good</span></div>
                <div>750-900<br><span style="color: #4caf50;">Excellent</span></div>
            </div>
        </div>
    </div>

    <div style="background: #e8f5e8; padding: 20px; border-radius: 10px; border: 1px solid #4caf50;">
        <h4 style="color: #2e7d32; margin-top: 0;">💡 Personalized Improvement Plan</h4>
        <div style="display: grid; grid-template-columns: 1fr; gap: 10px;">
    """
    
    for i, tip in enumerate(improvement_tips or [], 1):
        content += f"""
            <div style="background: white; padding: 12px; border-radius: 8px; border-left: 4px solid #4caf50;">
                <strong>Step {i}:</strong> {tip}
            </div>
        """
    
    content += """
        </div>
    </div>

    <div style="background: #e3f2fd; padding: 15px; border-radius: 10px; margin-top: 20px; font-size: 14px;">
        <h4 style="color: #1565c0; margin-top: 0;">📈 Next Steps</h4>
        <ul style="margin: 0; padding-left: 20px;">
            <li>Implement the above suggestions for 3-6 months</li>
            <li>Monitor your credit score regularly</li>
            <li>Re-apply when your score improves to 700+</li>
            <li>Contact us for personalized financial guidance</li>
        </ul>
    </div>

    <div style="text-align: center; margin-top: 20px; padding-top: 15px; border-top: 1px solid #ddd;">
        <p style="color: #666; font-size: 14px; margin: 0;">
            <strong>We're here to help you achieve financial wellness!</strong><br>
            📞 1800-209-8800 | 📧 financialhealth@tatacapital.com
        </p>
    </div>
    </div>
    """
    
    return content

# Test function
if __name__ == "__main__":
    test_customer = {"name": "Raj Sharma", "id": "CUST001", "phone": "9876543210"}
    test_loan = {
        "amount": 350000,
        "interest_rate": 11,
        "tenure_years": 4,
        "emi": 11200,
        "loan_type": "consolidation",
        "previous_loans": [{"emi": 8000}, {"emi": 5500}]
    }
    
    result = document_agent(test_customer, test_loan)
    print(result["message"])