"""
Verification Agent

Handles user identity verification using PAN and mobile number.
Validates input formats and checks against mock customer database.
"""

import json
import re
from typing import Dict, Any, Optional
from pathlib import Path

from agents.base_agent import BaseAgent, ValidationError, DataError, handle_errors
from schemas.models import VerificationResult, Customer, SalaryVerificationResult


class VerificationAgent(BaseAgent):
    """
    Agent responsible for verifying user identity.
    
    Validates PAN and mobile number formats, then checks against
    the customer database. Implements retry logic with max 3 attempts.
    """
    
    MAX_RETRY_ATTEMPTS = 3
    
    def __init__(self, customer_db_path: str = "data/customers.json"):
        """
        Initialize verification agent.
        
        Args:
            customer_db_path: Path to customer database JSON file
        """
        super().__init__("verification_agent")
        self.customer_db_path = Path(customer_db_path)
        self._load_customer_database()
    
    def _load_customer_database(self):
        """Load customer database from JSON file."""
        try:
            with open(self.customer_db_path, 'r') as f:
                data = json.load(f)
                self.customers = {
                    (c['pan'].upper(), c['mobile']): c 
                    for c in data.get('customers', [])
                }
            
            self.log_action(
                "database_loaded",
                customer_count=len(self.customers),
                db_path=str(self.customer_db_path)
            )
        
        except FileNotFoundError:
            self.logger.error(f"Customer database not found: {self.customer_db_path}")
            raise DataError(
                f"Customer database not found at {self.customer_db_path}",
                context={"db_path": str(self.customer_db_path)}
            )
        
        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON in customer database: {e}")
            raise DataError(
                "Customer database is corrupted",
                context={"error": str(e)}
            )
    
    @handle_errors
    def process(self, input_data: Dict[str, Any], session_state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process identity verification request.
        
        Args:
            input_data: Dictionary containing 'pan' and 'mobile'
            session_state: Current session state
        
        Returns:
            Dictionary with verification result and next agent routing
        """
        self.log_action("process_verification", input_data_keys=list(input_data.keys()))
        
        # Validate input
        self.validate_input(input_data)
        
        # Extract and normalize inputs
        pan = input_data.get('pan', '').strip().upper()
        mobile = input_data.get('mobile', '').strip()
        
        # Get retry count from session state
        retry_count = session_state.get('retry_counts', {}).get('verification', 0)
        
        # Check retry limit
        if retry_count >= self.MAX_RETRY_ATTEMPTS:
            self.log_decision(
                "verification_failed",
                "Maximum retry attempts exceeded",
                retry_count=retry_count
            )
            
            return self.create_response(
                success=False,
                data={
                    "verification_result": VerificationResult(
                        success=False,
                        error_message="Maximum verification attempts exceeded. Please contact support.",
                        retry_count=retry_count
                    ).model_dump()
                },
                message="You have exceeded the maximum number of verification attempts. Please contact our support team for assistance."
            )
        
        # Validate formats
        pan_valid = self.validate_pan_format(pan)
        mobile_valid = self.validate_mobile_format(mobile)
        
        if not pan_valid or not mobile_valid:
            # Increment retry count
            new_retry_count = retry_count + 1
            
            error_parts = []
            if not pan_valid:
                error_parts.append("PAN must be in format: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)")
            if not mobile_valid:
                error_parts.append("Mobile number must be 10 digits starting with 6-9")
            
            error_message = ". ".join(error_parts)
            
            self.log_action(
                "validation_failed",
                pan_valid=pan_valid,
                mobile_valid=mobile_valid,
                retry_count=new_retry_count
            )
            
            return self.create_response(
                success=False,
                data={
                    "verification_result": VerificationResult(
                        success=False,
                        error_message=error_message,
                        retry_count=new_retry_count
                    ).model_dump(),
                    "retry_count": new_retry_count
                },
                message=f"{error_message}. Attempt {new_retry_count} of {self.MAX_RETRY_ATTEMPTS}."
            )
        
        # Lookup customer
        customer = self.lookup_customer(pan, mobile)
        
        if customer is None:
            # Increment retry count
            new_retry_count = retry_count + 1
            
            self.log_action(
                "customer_not_found",
                pan=pan[:5] + "****",  # Mask PAN for logging
                mobile="*****" + mobile[-5:],  # Mask mobile for logging
                retry_count=new_retry_count
            )
            
            return self.create_response(
                success=False,
                data={
                    "verification_result": VerificationResult(
                        success=False,
                        error_message="No customer found with the provided PAN and mobile number. Please verify your details.",
                        retry_count=new_retry_count
                    ).model_dump(),
                    "retry_count": new_retry_count
                },
                message=f"We couldn't find a customer with these details. Please check and try again. Attempt {new_retry_count} of {self.MAX_RETRY_ATTEMPTS}."
            )
        
        # Verification successful
        verification_result = VerificationResult(
            success=True,
            customer_id=customer['customer_id'],
            name=customer['name'],
            retry_count=retry_count
        )
        
        self.log_decision(
            "verification_successful",
            f"Customer {customer['customer_id']} verified successfully",
            customer_id=customer['customer_id'],
            customer_name=customer['name']
        )
        
        return self.create_response(
            success=True,
            data={
                "verification_result": verification_result.model_dump(),
                "customer_data": customer
            },
            next_agent="credit_bureau",
            message=f"Welcome, {customer['name']}! Your identity has been verified successfully."
        )
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        """
        Validate that required input fields are present.
        
        Args:
            input_data: Input data to validate
        
        Returns:
            True if validation passes
        
        Raises:
            ValidationError: If required fields are missing
        """
        required_fields = ['pan', 'mobile']
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            raise ValidationError(
                f"Missing required fields: {', '.join(missing_fields)}",
                context={"missing_fields": missing_fields}
            )
        
        # Check for empty values
        empty_fields = [
            field for field in required_fields 
            if not input_data.get(field) or not str(input_data[field]).strip()
        ]
        
        if empty_fields:
            raise ValidationError(
                f"Empty values for required fields: {', '.join(empty_fields)}",
                context={"empty_fields": empty_fields}
            )
        
        return True
    
    def validate_pan_format(self, pan: str) -> bool:
        """
        Validate PAN card format.
        
        PAN format: 5 letters, 4 digits, 1 letter (e.g., ABCDE1234F)
        
        Args:
            pan: PAN card number to validate
        
        Returns:
            True if format is valid, False otherwise
        """
        if not pan or not isinstance(pan, str):
            return False
        
        pan_pattern = r'^[A-Z]{5}[0-9]{4}[A-Z]$'
        is_valid = bool(re.match(pan_pattern, pan.upper()))
        
        self.log_action(
            "pan_validation",
            is_valid=is_valid,
            pan_length=len(pan)
        )
        
        return is_valid
    
    def validate_mobile_format(self, mobile: str) -> bool:
        """
        Validate mobile number format.
        
        Mobile format: 10 digits starting with 6-9
        
        Args:
            mobile: Mobile number to validate
        
        Returns:
            True if format is valid, False otherwise
        """
        if not mobile or not isinstance(mobile, str):
            return False
        
        mobile_pattern = r'^[6-9][0-9]{9}$'
        is_valid = bool(re.match(mobile_pattern, mobile))
        
        self.log_action(
            "mobile_validation",
            is_valid=is_valid,
            mobile_length=len(mobile)
        )
        
        return is_valid
    
    def lookup_customer(self, pan: str, mobile: str) -> Optional[Dict[str, Any]]:
        """
        Look up customer in database by PAN and mobile number.
        
        Args:
            pan: PAN card number (normalized to uppercase)
            mobile: Mobile number
        
        Returns:
            Customer data dictionary if found, None otherwise
        """
        lookup_key = (pan.upper(), mobile)
        customer = self.customers.get(lookup_key)
        
        self.log_action(
            "customer_lookup",
            found=customer is not None,
            lookup_key_hash=hash(lookup_key)  # Log hash instead of actual values
        )
        
        return customer
    
    def verify_identity(self, pan: str, mobile: str, retry_count: int = 0) -> VerificationResult:
        """
        High-level method to verify identity.
        
        This is a convenience method that can be called directly
        without going through the process() method.
        
        Args:
            pan: PAN card number
            mobile: Mobile number
            retry_count: Current retry attempt count
        
        Returns:
            VerificationResult object
        """
        # Normalize inputs
        pan = pan.strip().upper()
        mobile = mobile.strip()
        
        # Check retry limit
        if retry_count >= self.MAX_RETRY_ATTEMPTS:
            return VerificationResult(
                success=False,
                error_message="Maximum verification attempts exceeded",
                retry_count=retry_count
            )
        
        # Validate formats
        if not self.validate_pan_format(pan):
            return VerificationResult(
                success=False,
                error_message="Invalid PAN format. Expected format: ABCDE1234F",
                retry_count=retry_count
            )
        
        if not self.validate_mobile_format(mobile):
            return VerificationResult(
                success=False,
                error_message="Invalid mobile number. Must be 10 digits starting with 6-9",
                retry_count=retry_count
            )
        
        # Lookup customer
        customer = self.lookup_customer(pan, mobile)
        
        if customer is None:
            return VerificationResult(
                success=False,
                error_message="No customer found with provided details",
                retry_count=retry_count
            )
        
        # Success
        return VerificationResult(
            success=True,
            customer_id=customer['customer_id'],
            name=customer['name'],
            retry_count=retry_count
        )
    
    def _get_user_friendly_message(self, error) -> str:
        """
        Convert technical error to user-friendly message.
        
        Args:
            error: Agent error
        
        Returns:
            User-friendly error message
        """
        if "Missing required fields" in error.message:
            return "Please provide both your PAN card number and mobile number."
        elif "Empty values" in error.message:
            return "PAN card number and mobile number cannot be empty."
        elif "database not found" in error.message.lower():
            return "We're experiencing technical difficulties. Please try again later."
        else:
            return error.message
    
    @handle_errors
    def verify_salary(
        self,
        document_data: Optional[Dict[str, Any]] = None,
        manual_salary: Optional[float] = None
    ) -> SalaryVerificationResult:
        """
        Verify salary through document upload or manual entry.
        
        Args:
            document_data: Dictionary containing:
                - filename: Name of uploaded file
                - file_size: Size in bytes
                - file_content: File content (bytes or base64)
            manual_salary: Manually entered salary amount
        
        Returns:
            SalaryVerificationResult with verification outcome
        """
        self.log_action(
            "verify_salary",
            has_document=document_data is not None,
            has_manual_salary=manual_salary is not None
        )
        
        # Validate that at least one method is provided
        if document_data is None and manual_salary is None:
            return SalaryVerificationResult(
                success=False,
                error_message="Please provide either a salary document or enter your salary manually"
            )
        
        # If document is provided, validate and process it
        if document_data is not None:
            validation_result = self.validate_salary_document(document_data)
            
            if not validation_result["valid"]:
                return SalaryVerificationResult(
                    success=False,
                    error_message=validation_result["error_message"]
                )
            
            # Extract salary from document (simplified - in production would use OCR)
            extracted_salary = self._extract_salary_from_document(document_data)
            
            if extracted_salary is None:
                # Fallback to manual entry if extraction fails
                self.log_action(
                    "salary_extraction_failed",
                    filename=document_data.get("filename")
                )
                
                return SalaryVerificationResult(
                    success=False,
                    error_message="Could not extract salary from document. Please enter your salary manually."
                )
            
            self.log_decision(
                "salary_verified_from_document",
                f"Salary verified: ₹{extracted_salary:,.2f}",
                salary=extracted_salary,
                filename=document_data.get("filename")
            )
            
            return SalaryVerificationResult(
                success=True,
                verified_salary=extracted_salary,
                verification_method="document_upload",
                document_filename=document_data.get("filename")
            )
        
        # Manual salary entry
        if manual_salary is not None:
            validation_result = self.validate_manual_salary(manual_salary)
            
            if not validation_result["valid"]:
                return SalaryVerificationResult(
                    success=False,
                    error_message=validation_result["error_message"]
                )
            
            self.log_decision(
                "salary_verified_manually",
                f"Salary verified: ₹{manual_salary:,.2f}",
                salary=manual_salary
            )
            
            return SalaryVerificationResult(
                success=True,
                verified_salary=manual_salary,
                verification_method="manual_entry"
            )
    
    def validate_salary_document(self, document_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validate uploaded salary document.
        
        Validates:
        - File format (PDF, JPG, PNG)
        - File size (max 5MB)
        - Required fields present
        
        Args:
            document_data: Document information
        
        Returns:
            Dictionary with validation result
        """
        # Check required fields
        if "filename" not in document_data:
            return {
                "valid": False,
                "error_message": "Document filename is required"
            }
        
        if "file_size" not in document_data:
            return {
                "valid": False,
                "error_message": "Document file size is required"
            }
        
        filename = document_data["filename"]
        file_size = document_data["file_size"]
        
        # Validate file format
        allowed_extensions = [".pdf", ".jpg", ".jpeg", ".png"]
        file_extension = Path(filename).suffix.lower()
        
        if file_extension not in allowed_extensions:
            self.log_action(
                "invalid_file_format",
                filename=filename,
                extension=file_extension
            )
            
            return {
                "valid": False,
                "error_message": f"Invalid file format. Allowed formats: PDF, JPG, PNG. Got: {file_extension}"
            }
        
        # Validate file size (max 5MB)
        max_size_bytes = 5 * 1024 * 1024  # 5MB
        
        if file_size > max_size_bytes:
            self.log_action(
                "file_too_large",
                filename=filename,
                file_size=file_size,
                max_size=max_size_bytes
            )
            
            return {
                "valid": False,
                "error_message": f"File size exceeds maximum limit of 5MB. Your file: {file_size / (1024*1024):.2f}MB"
            }
        
        self.log_action(
            "document_validation_passed",
            filename=filename,
            file_size=file_size,
            extension=file_extension
        )
        
        return {
            "valid": True,
            "error_message": None
        }
    
    def validate_manual_salary(self, salary: float) -> Dict[str, Any]:
        """
        Validate manually entered salary.
        
        Args:
            salary: Salary amount to validate
        
        Returns:
            Dictionary with validation result
        """
        # Check if salary is a valid number
        if not isinstance(salary, (int, float)):
            return {
                "valid": False,
                "error_message": "Salary must be a valid number"
            }
        
        # Check minimum salary (₹10,000)
        min_salary = 10000
        if salary < min_salary:
            self.log_action(
                "salary_below_minimum",
                salary=salary,
                min_salary=min_salary
            )
            
            return {
                "valid": False,
                "error_message": f"Salary must be at least ₹{min_salary:,}"
            }
        
        # Check maximum salary (₹10,00,000 - 10 lakhs)
        max_salary = 1000000
        if salary > max_salary:
            self.log_action(
                "salary_above_maximum",
                salary=salary,
                max_salary=max_salary
            )
            
            return {
                "valid": False,
                "error_message": f"Salary exceeds maximum limit of ₹{max_salary:,}. Please contact support for high-value applications."
            }
        
        self.log_action(
            "manual_salary_validation_passed",
            salary=salary
        )
        
        return {
            "valid": True,
            "error_message": None
        }
    
    def _extract_salary_from_document(self, document_data: Dict[str, Any]) -> Optional[float]:
        """
        Extract salary from uploaded document.
        
        In a production system, this would use OCR (Optical Character Recognition)
        to extract salary information from the document. For this implementation,
        we simulate the extraction process.
        
        Args:
            document_data: Document information
        
        Returns:
            Extracted salary amount or None if extraction fails
        """
        # Simulate OCR extraction
        # In production, this would use libraries like pytesseract, AWS Textract, etc.
        
        # For testing purposes, check if document_data contains a simulated salary
        if "simulated_salary" in document_data:
            return document_data["simulated_salary"]
        
        # If file_content is provided and contains salary info (for testing)
        if "file_content" in document_data:
            content = document_data["file_content"]
            if isinstance(content, dict) and "salary" in content:
                return content["salary"]
        
        # In real implementation, would return None if OCR fails
        # For now, return None to indicate manual entry is needed
        return None
