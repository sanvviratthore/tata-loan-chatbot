"""
Sales Agent Module

Conversational agent that presents loan offers, answers questions, handles modifications,
and suggests upselling opportunities using LLM-powered interactions.
"""

from typing import Dict, Any, Optional, List, Union
from datetime import datetime, timedelta
import uuid

from agents.base_agent import BaseAgent, handle_errors, ValidationError, BusinessLogicError
from schemas.models import LoanOffer, ConsolidationOffer, Customer
from utils.llm_client import BaseLLM, create_llm_client
from utils.loan_calculator import calculate_emi, calculate_total_interest


class SalesAgent(BaseAgent):
    """
    Sales agent for presenting offers, answering questions, and handling modifications.
    
    Responsibilities:
    - Present loan/consolidation offers in conversational manner
    - Answer customer questions using LLM
    - Modify loan parameters based on customer requests
    - Suggest add-on products and upselling opportunities
    - Handle offer acceptance and route to document generation
    """
    
    def __init__(self, llm_client: Optional[BaseLLM] = None):
        """
        Initialize sales agent.
        
        Args:
            llm_client: LLM client for generating responses (defaults to OpenRouter)
        """
        super().__init__("sales_agent")
        self.llm_client = llm_client or create_llm_client()
        
        # Add-on products catalog
        self.addon_products = {
            "loan_protection_insurance": {
                "name": "Loan Protection Insurance",
                "description": "Covers your loan in case of unforeseen circumstances",
                "cost_percentage": 0.5,  # 0.5% of loan amount
                "benefits": ["Death coverage", "Critical illness coverage", "Job loss protection"]
            },
            "credit_card": {
                "name": "Premium Credit Card",
                "description": "Complimentary credit card with exclusive benefits",
                "annual_fee": 999,
                "benefits": ["2% cashback", "Airport lounge access", "Fuel surcharge waiver"]
            },
            "overdraft_facility": {
                "name": "Overdraft Facility",
                "description": "Emergency credit line linked to your account",
                "interest_rate": 12.0,
                "benefits": ["Instant access to funds", "Pay interest only on usage", "No prepayment charges"]
            }
        }
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process sales agent requests.
        
        Args:
            input_data: Contains action and relevant data
            session_state: Current session state
        
        Returns:
            Response with success status and data
        """
        self.validate_input(input_data)
        
        action = input_data.get("action")
        
        if action == "present_offer":
            return self._handle_present_offer(input_data, session_state)
        
        elif action == "answer_question":
            return self._handle_answer_question(input_data, session_state)
        
        elif action == "modify_offer":
            return self._handle_modify_offer(input_data, session_state)
        
        elif action == "suggest_addons":
            return self._handle_suggest_addons(input_data, session_state)
        
        elif action == "accept_offer":
            return self._handle_accept_offer(input_data, session_state)
        
        else:
            raise ValidationError(f"Unknown action: {action}")
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate input data.
        
        Args:
            input_data: Input data to validate
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If validation fails
        """
        if not isinstance(input_data, dict):
            raise ValidationError("Input data must be a dictionary")
        
        if "action" not in input_data:
            raise ValidationError("Missing required field: action")
        
        valid_actions = ["present_offer", "answer_question", "modify_offer", "suggest_addons", "accept_offer"]
        if input_data["action"] not in valid_actions:
            raise ValidationError(f"Invalid action. Must be one of: {valid_actions}")
        
        return True
    
    def _handle_present_offer(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Present loan or consolidation offer in conversational manner.
        
        Args:
            input_data: Contains offer data and offer_type
            session_state: Current session state
        
        Returns:
            Response with presentation text
        """
        offer_data = input_data.get("offer")
        offer_type = input_data.get("offer_type", "loan")
        
        if not offer_data:
            raise ValidationError("Missing offer data")
        
        self.log_action("present_offer", offer_type=offer_type)
        
        # Generate conversational presentation using LLM
        presentation = self.present_offer(offer_data, offer_type, session_state)
        
        return self.create_response(
            success=True,
            data={
                "presentation": presentation,
                "offer": offer_data,
                "offer_type": offer_type
            },
            message=presentation
        )
    
    def _handle_answer_question(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Answer customer question about the offer.
        
        Args:
            input_data: Contains question and offer context
            session_state: Current session state
        
        Returns:
            Response with answer
        """
        question = input_data.get("question")
        offer = session_state.get("current_offer")
        
        if not question:
            raise ValidationError("Missing question")
        
        if not offer:
            raise BusinessLogicError("No active offer to answer questions about")
        
        self.log_action("answer_question", question=question)
        
        # Generate answer using LLM
        answer = self.answer_question(question, offer, session_state)
        
        return self.create_response(
            success=True,
            data={"answer": answer, "question": question},
            message=answer
        )
    
    def _handle_modify_offer(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify loan parameters based on customer request.
        
        Args:
            input_data: Contains modification request
            session_state: Current session state
        
        Returns:
            Response with modified offer
        """
        modification_request = input_data.get("modification")
        current_offer = session_state.get("current_offer")
        
        if not modification_request:
            raise ValidationError("Missing modification request")
        
        if not current_offer:
            raise BusinessLogicError("No active offer to modify")
        
        self.log_action("modify_offer", modification=modification_request)
        
        # Apply modifications
        modified_offer = self.suggest_modifications(modification_request, current_offer)
        
        # Generate explanation using LLM
        explanation = self._generate_modification_explanation(current_offer, modified_offer)
        
        return self.create_response(
            success=True,
            data={
                "modified_offer": modified_offer,
                "original_offer": current_offer,
                "explanation": explanation
            },
            message=explanation
        )
    
    def _handle_suggest_addons(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Suggest add-on products based on customer profile.
        
        Args:
            input_data: Contains customer profile
            session_state: Current session state
        
        Returns:
            Response with addon suggestions
        """
        customer_data = session_state.get("customer_data", {})
        current_offer = session_state.get("current_offer", {})
        
        self.log_action("suggest_addons")
        
        # Get relevant add-ons
        suggestions = self.upsell_products(customer_data, current_offer)
        
        # Generate conversational presentation
        presentation = self._generate_addon_presentation(suggestions)
        
        return self.create_response(
            success=True,
            data={"suggestions": suggestions, "presentation": presentation},
            message=presentation
        )
    
    def _handle_accept_offer(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle offer acceptance and route to document generation.
        
        Args:
            input_data: Contains acceptance confirmation and offer
            session_state: Current session state
        
        Returns:
            Response routing to document agent
        """
        # Check input_data first, then fall back to session_state
        current_offer = input_data.get("offer") or session_state.get("current_offer")
        
        if not current_offer:
            raise BusinessLogicError("No active offer to accept")
        
        self.log_action("accept_offer", offer_id=current_offer.get("offer_id"))
        
        # Generate acceptance confirmation message
        confirmation = self._generate_acceptance_confirmation(current_offer)
        
        return self.create_response(
            success=True,
            data={"accepted_offer": current_offer, "confirmation": confirmation},
            next_agent="document",
            message=confirmation
        )
    
    def present_offer(self, offer: Dict[str, Any], offer_type: str, context: Dict[str, Any]) -> str:
        """
        Generate conversational presentation of loan offer using LLM.
        
        Args:
            offer: Loan or consolidation offer data
            offer_type: Type of offer ("loan" or "consolidation")
            context: Additional context (customer data, credit profile)
        
        Returns:
            Conversational presentation text
        """
        customer_name = context.get("customer_data", {}).get("name", "valued customer")
        
        if offer_type == "consolidation":
            prompt = self._create_consolidation_presentation_prompt(offer, customer_name)
        else:
            prompt = self._create_loan_presentation_prompt(offer, customer_name)
        
        try:
            presentation = self.llm_client.generate(prompt, temperature=0.7, max_tokens=400)
            return presentation
        except Exception as e:
            self.logger.warning(f"LLM generation failed, using fallback: {e}")
            return self._fallback_presentation(offer, offer_type, customer_name)
    
    def answer_question(self, question: str, offer: Dict[str, Any], context: Dict[str, Any]) -> str:
        """
        Answer customer question about the offer using LLM.
        
        Args:
            question: Customer's question
            offer: Current offer data
            context: Session context
        
        Returns:
            Answer to the question
        """
        prompt = f"""You are a helpful and knowledgeable loan sales agent. A customer has asked a question about their loan offer.

Offer Details:
- Loan Amount: ₹{offer.get('loan_amount', offer.get('consolidated_amount', 0)):,.0f}
- Interest Rate: {offer.get('interest_rate', offer.get('new_interest_rate', 0))}% per annum
- Tenure: {offer.get('tenure_months', offer.get('new_tenure_months', 0))} months
- Monthly EMI: ₹{offer.get('monthly_emi', offer.get('new_monthly_emi', 0)):,.0f}

Customer Question: "{question}"

Provide a clear, friendly, and accurate answer. Keep it concise (2-3 sentences). Use Indian Rupees (₹) for amounts."""

        try:
            answer = self.llm_client.generate(prompt, temperature=0.7, max_tokens=200)
            return answer
        except Exception as e:
            self.logger.warning(f"LLM generation failed, using fallback: {e}")
            return self._fallback_answer(question, offer)
    
    def suggest_modifications(self, user_request: str, current_offer: Dict[str, Any]) -> Dict[str, Any]:
        """
        Modify loan parameters based on user request.
        
        Args:
            user_request: User's modification request (e.g., "increase tenure", "reduce amount")
            context: Current offer details
        
        Returns:
            Modified offer dictionary
        """
        modified_offer = current_offer.copy()
        
        # Extract current values
        loan_amount = current_offer.get("loan_amount", current_offer.get("consolidated_amount", 0))
        interest_rate = current_offer.get("interest_rate", current_offer.get("new_interest_rate", 0))
        tenure_months = current_offer.get("tenure_months", current_offer.get("new_tenure_months", 0))
        
        # Parse modification request
        request_lower = user_request.lower()
        
        # Handle tenure modifications
        if "tenure" in request_lower or "duration" in request_lower or "months" in request_lower:
            if "increase" in request_lower or "longer" in request_lower or "extend" in request_lower:
                new_tenure = min(tenure_months + 12, 84)  # Max 84 months
            elif "decrease" in request_lower or "shorter" in request_lower or "reduce" in request_lower:
                new_tenure = max(tenure_months - 12, 12)  # Min 12 months
            else:
                # Try to extract number
                import re
                numbers = re.findall(r'\d+', request_lower)
                new_tenure = int(numbers[0]) if numbers else tenure_months
            
            tenure_months = new_tenure
        
        # Handle amount modifications
        if "amount" in request_lower or "loan" in request_lower:
            if "increase" in request_lower or "more" in request_lower or "higher" in request_lower:
                loan_amount = min(loan_amount * 1.2, loan_amount + 100000)  # Max 20% or 1L increase
            elif "decrease" in request_lower or "less" in request_lower or "lower" in request_lower or "reduce" in request_lower:
                loan_amount = max(loan_amount * 0.8, loan_amount - 100000)  # Max 20% or 1L decrease
        
        # Recalculate EMI
        new_emi = calculate_emi(loan_amount, interest_rate, tenure_months)
        new_total_interest = calculate_total_interest(loan_amount, new_emi, tenure_months)
        
        # Update offer
        if "loan_amount" in current_offer:
            modified_offer["loan_amount"] = round(loan_amount, 2)
            modified_offer["tenure_months"] = tenure_months
            modified_offer["monthly_emi"] = new_emi
            modified_offer["total_interest"] = new_total_interest
            modified_offer["total_repayment"] = round(loan_amount + new_total_interest, 2)
        else:
            # Consolidation offer
            modified_offer["consolidated_amount"] = round(loan_amount, 2)
            modified_offer["new_tenure_months"] = tenure_months
            modified_offer["new_monthly_emi"] = new_emi
            
            # Recalculate savings
            current_total_emi = current_offer.get("current_total_emi", 0)
            modified_offer["monthly_savings"] = round(current_total_emi - new_emi, 2)
        
        self.log_decision(
            "offer_modified",
            f"Modified based on request: {user_request}",
            original_emi=current_offer.get("monthly_emi", current_offer.get("new_monthly_emi")),
            new_emi=new_emi
        )
        
        return modified_offer
    
    def upsell_products(self, user_profile: Dict[str, Any], current_offer: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Suggest relevant add-on products based on user profile.
        
        Args:
            user_profile: Customer profile data
            current_offer: Current loan offer
        
        Returns:
            List of suggested add-on products
        """
        suggestions = []
        
        loan_amount = current_offer.get("loan_amount", current_offer.get("consolidated_amount", 0))
        credit_score = user_profile.get("credit_score", 700)
        
        # Loan protection insurance (for all customers)
        insurance = self.addon_products["loan_protection_insurance"].copy()
        insurance["cost"] = round(loan_amount * insurance["cost_percentage"] / 100, 2)
        suggestions.append(insurance)
        
        # Credit card (for good credit scores)
        if credit_score >= 700:
            suggestions.append(self.addon_products["credit_card"].copy())
        
        # Overdraft facility (for high-value loans)
        if loan_amount >= 200000:
            overdraft = self.addon_products["overdraft_facility"].copy()
            overdraft["limit"] = round(loan_amount * 0.2, 2)  # 20% of loan amount
            suggestions.append(overdraft)
        
        self.log_action("upsell_generated", product_count=len(suggestions))
        
        return suggestions
    
    def _create_loan_presentation_prompt(self, offer: Dict[str, Any], customer_name: str) -> str:
        """Create prompt for loan offer presentation."""
        return f"""You are a friendly and professional loan sales agent. Present this loan offer to {customer_name} in a warm, conversational manner.

Offer Details:
- Loan Amount: ₹{offer.get('loan_amount', 0):,.0f}
- Interest Rate: {offer.get('interest_rate', 0)}% per annum
- Tenure: {offer.get('tenure_months', 0)} months ({offer.get('tenure_months', 0)//12} years)
- Monthly EMI: ₹{offer.get('monthly_emi', 0):,.0f}
- Processing Fee: ₹{offer.get('processing_fee', 0):,.0f}

Write a brief, enthusiastic presentation (3-4 sentences) highlighting the key benefits. Use Indian Rupees (₹) for amounts. End by asking if they have any questions."""

    def _create_consolidation_presentation_prompt(self, offer: Dict[str, Any], customer_name: str) -> str:
        """Create prompt for consolidation offer presentation."""
        return f"""You are a friendly loan sales agent. Present this debt consolidation offer to {customer_name}, emphasizing the savings.

Consolidation Offer:
- Consolidated Amount: ₹{offer.get('consolidated_amount', 0):,.0f}
- New Interest Rate: {offer.get('new_interest_rate', 0)}% per annum
- New Monthly EMI: ₹{offer.get('new_monthly_emi', 0):,.0f}
- Current Total EMI: ₹{offer.get('current_total_emi', 0):,.0f}
- Monthly Savings: ₹{offer.get('monthly_savings', 0):,.0f}
- Total Interest Savings: ₹{offer.get('total_interest_savings', 0):,.0f}

Write an enthusiastic presentation (3-4 sentences) highlighting the significant savings. Use Indian Rupees (₹). End by asking if they'd like to proceed."""

    def _fallback_presentation(self, offer: Dict[str, Any], offer_type: str, customer_name: str) -> str:
        """Generate fallback presentation when LLM is unavailable."""
        if offer_type == "consolidation":
            return f"""Great news, {customer_name}! We have an excellent consolidation offer for you.

We can consolidate your loans into a single loan of ₹{offer.get('consolidated_amount', 0):,.0f} at {offer.get('new_interest_rate', 0)}% interest. Your new monthly EMI will be just ₹{offer.get('new_monthly_emi', 0):,.0f}, saving you ₹{offer.get('monthly_savings', 0):,.0f} every month!

Over the loan tenure, you'll save ₹{offer.get('total_interest_savings', 0):,.0f} in interest. Would you like to proceed with this offer?"""
        else:
            return f"""Good news, {customer_name}! Your loan application has been approved.

We're pleased to offer you a loan of ₹{offer.get('loan_amount', 0):,.0f} at {offer.get('interest_rate', 0)}% annual interest for {offer.get('tenure_months', 0)} months. Your monthly EMI will be ₹{offer.get('monthly_emi', 0):,.0f}.

Do you have any questions about this offer?"""

    def _fallback_answer(self, question: str, offer: Dict[str, Any]) -> str:
        """Generate fallback answer when LLM is unavailable."""
        question_lower = question.lower()
        
        if "emi" in question_lower:
            emi = offer.get("monthly_emi", offer.get("new_monthly_emi", 0))
            return f"Your monthly EMI will be ₹{emi:,.0f}. This amount will be automatically debited from your account each month."
        
        elif "interest" in question_lower or "rate" in question_lower:
            rate = offer.get("interest_rate", offer.get("new_interest_rate", 0))
            return f"The interest rate for this loan is {rate}% per annum. This is a competitive rate based on your credit profile."
        
        elif "tenure" in question_lower or "duration" in question_lower:
            tenure = offer.get("tenure_months", offer.get("new_tenure_months", 0))
            return f"The loan tenure is {tenure} months ({tenure//12} years). You can request to modify this if needed."
        
        else:
            return "That's a great question! Let me provide you with more details. Please feel free to ask about the EMI, interest rate, tenure, or any other aspect of the offer."

    def _generate_modification_explanation(self, original: Dict[str, Any], modified: Dict[str, Any]) -> str:
        """Generate explanation for offer modification."""
        original_emi = original.get("monthly_emi", original.get("new_monthly_emi", 0))
        modified_emi = modified.get("monthly_emi", modified.get("new_monthly_emi", 0))
        
        original_tenure = original.get("tenure_months", original.get("new_tenure_months", 0))
        modified_tenure = modified.get("tenure_months", modified.get("new_tenure_months", 0))
        
        prompt = f"""You are a loan sales agent. Explain the modification to the customer in a friendly way.

Original Offer:
- Monthly EMI: ₹{original_emi:,.0f}
- Tenure: {original_tenure} months

Modified Offer:
- Monthly EMI: ₹{modified_emi:,.0f}
- Tenure: {modified_tenure} months

Write a brief explanation (2-3 sentences) of how the offer changed and ask if this works better for them. Use Indian Rupees (₹)."""

        try:
            explanation = self.llm_client.generate(prompt, temperature=0.7, max_tokens=150)
            return explanation
        except Exception:
            emi_change = "lower" if modified_emi < original_emi else "higher"
            return f"I've adjusted your offer. Your new monthly EMI is ₹{modified_emi:,.0f} over {modified_tenure} months. This gives you a {emi_change} EMI compared to the original offer. Does this work better for you?"

    def _generate_addon_presentation(self, suggestions: List[Dict[str, Any]]) -> str:
        """Generate conversational presentation for add-on products."""
        if not suggestions:
            return "We don't have any additional products to suggest at this time."
        
        products_text = "\n".join([f"- {p['name']}: {p['description']}" for p in suggestions])
        
        prompt = f"""You are a loan sales agent. Suggest these add-on products to the customer in a helpful, non-pushy way.

Available Products:
{products_text}

Write a brief, friendly suggestion (2-3 sentences) mentioning these products and their benefits. Don't be too salesy."""

        try:
            presentation = self.llm_client.generate(prompt, temperature=0.7, max_tokens=200)
            return presentation
        except Exception:
            return f"We also offer some great add-on products that might interest you: {', '.join([p['name'] for p in suggestions])}. These can provide additional protection and benefits. Would you like to know more about any of these?"

    def _generate_acceptance_confirmation(self, offer: Dict[str, Any]) -> str:
        """Generate confirmation message for offer acceptance."""
        loan_amount = offer.get("loan_amount", offer.get("consolidated_amount", 0))
        
        return f"""Excellent! Thank you for accepting the offer. We're now preparing your loan documents for ₹{loan_amount:,.0f}.

You'll receive a professional offer letter with all the details shortly. The document will include the complete repayment schedule and terms & conditions.

Is there anything else you'd like to know while we prepare your documents?"""
    
    def present_single_loan_comparison(self, comparison: Dict[str, Any], customer_name: str = "valued customer") -> str:
        """
        Present comparison between loan transfer and new loan for single loan customers.
        
        Args:
            comparison: Comparison data from underwriting agent
            customer_name: Customer's name
        
        Returns:
            Conversational presentation of comparison
        """
        existing = comparison["existing_loan"]
        option1 = comparison["option_1_transfer"]
        option2 = comparison["option_2_new_loan"]
        recommendation = comparison.get("recommendation")
        
        prompt = f"""You are a helpful loan sales agent. Present these two loan options to {customer_name} in a clear, friendly way.

Current Situation:
- Existing {existing['loan_type']}: ₹{existing['outstanding']:,.0f} outstanding
- Current EMI: ₹{existing['monthly_emi']:,.0f}

Option 1 - Transfer Existing Loan:
- Total Amount: ₹{option1['total_amount']:,.0f}
- Interest Rate: {option1['interest_rate']}% per annum
- New Monthly EMI: ₹{option1['monthly_emi']:,.0f}
- Single loan to manage

Option 2 - New Separate Loan:
- New Loan Amount: ₹{option2['new_loan_amount']:,.0f}
- Interest Rate: {option2['interest_rate']}% per annum
- New Loan EMI: ₹{option2['new_loan_emi']:,.0f}
- Total Monthly Payment: ₹{option2['total_monthly_payment']:,.0f} (existing + new)
- Two separate loans

Recommendation: {"Option 1 (Transfer)" if recommendation == "transfer" else "Option 2 (New Loan)" if recommendation == "new_loan" else "Discuss both options"}
{f"Reason: {comparison.get('recommendation_reason', '')}" if recommendation else ""}

Write a clear, conversational presentation (4-5 sentences) explaining both options and the recommendation. Use Indian Rupees (₹). Ask which option they prefer."""

        try:
            presentation = self.llm_client.generate(prompt, temperature=0.7, max_tokens=400)
            return presentation
        except Exception as e:
            self.logger.warning(f"LLM generation failed for single loan comparison: {e}")
            return self._fallback_single_loan_comparison(comparison, customer_name)
    
    def _fallback_single_loan_comparison(self, comparison: Dict[str, Any], customer_name: str) -> str:
        """Generate fallback presentation for single loan comparison."""
        existing = comparison["existing_loan"]
        option1 = comparison["option_1_transfer"]
        option2 = comparison["option_2_new_loan"]
        recommendation = comparison.get("recommendation")
        
        presentation = f"""Hello {customer_name}! I have two great options for you.

You currently have a {existing['loan_type']} with ₹{existing['outstanding']:,.0f} outstanding and an EMI of ₹{existing['monthly_emi']:,.0f}.

**Option 1 - Transfer Your Existing Loan:**
We can transfer your existing loan and combine it with the new amount for a total of ₹{option1['total_amount']:,.0f} at {option1['interest_rate']}% interest. Your new single EMI would be ₹{option1['monthly_emi']:,.0f}.

**Option 2 - Keep Loans Separate:**
Take a new loan of ₹{option2['new_loan_amount']:,.0f} at {option2['interest_rate']}% interest with an EMI of ₹{option2['new_loan_emi']:,.0f}. Your total monthly payment would be ₹{option2['total_monthly_payment']:,.0f}.
"""
        
        if recommendation == "transfer":
            monthly_savings = comparison.get("monthly_savings", 0)
            presentation += f"\n**I recommend Option 1** - You'll save ₹{monthly_savings:,.0f} per month and have just one loan to manage!"
        elif recommendation == "new_loan":
            presentation += f"\n**I recommend Option 2** - This gives you more flexibility with separate loans."
        
        presentation += "\n\nWhich option works better for you?"
        
        return presentation
