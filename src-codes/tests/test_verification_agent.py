"""
Unit tests for Verification Agent

Tests cover:
- PAN format validation
- Mobile format validation
- Customer lookup scenarios
- Retry logic
- Error handling
"""

import pytest
import json
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

from agents.verification_agent import VerificationAgent
from agents.base_agent import ValidationError, DataError
from schemas.models import VerificationResult, SalaryVerificationResult


class TestVerificationAgent:
    """Test suite for VerificationAgent."""
    
    @pytest.fixture
    def mock_customer_db(self):
        """Create a temporary customer database for testing."""
        customers_data = {
            "customers": [
                {
                    "customer_id": "CUST001",
                    "name": "Rajesh Kumar",
                    "pan": "ABCDE1234F",
                    "mobile": "9876543210",
                    "email": "rajesh.kumar@example.com",
                    "monthly_income": 75000,
                    "employment_type": "Salaried"
                },
                {
                    "customer_id": "CUST002",
                    "name": "Priya Sharma",
                    "pan": "FGHIJ5678K",
                    "mobile": "9123456789",
                    "email": "priya.sharma@example.com",
                    "monthly_income": 120000,
                    "employment_type": "Salaried"
                },
                {
                    "customer_id": "CUST003",
                    "name": "Amit Patel",
                    "pan": "KLMNO9012P",
                    "mobile": "9988776655",
                    "email": "amit.patel@example.com",
                    "monthly_income": 45000,
                    "employment_type": "Self-Employed"
                }
            ]
        }
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            json.dump(customers_data, f)
            temp_path = f.name
        
        yield temp_path
        
        # Cleanup
        Path(temp_path).unlink()
    
    @pytest.fixture
    def agent(self, mock_customer_db):
        """Create VerificationAgent instance with mock database."""
        return VerificationAgent(customer_db_path=mock_customer_db)
    
    # PAN Format Validation Tests
    
    def test_validate_pan_format_valid(self, agent):
        """Test PAN validation with valid formats."""
        valid_pans = [
            "ABCDE1234F",
            "ZYXWV9876A",
            "PQRST5555M",
            "abcde1234f",  # Should work with lowercase (normalized to uppercase)
        ]
        
        for pan in valid_pans:
            assert agent.validate_pan_format(pan) is True, f"Failed for valid PAN: {pan}"
    
    def test_validate_pan_format_invalid(self, agent):
        """Test PAN validation with invalid formats."""
        invalid_pans = [
            "ABC1234567",      # Too many digits
            "ABCDE12345",      # Too many characters
            "ABCD1234F",       # Only 4 letters at start
            "ABCDE1234",       # Missing last letter
            "12345ABCDEF",     # Numbers first
            "ABCDE-1234F",     # Contains hyphen
            "ABCDE 1234F",     # Contains space
            "",                # Empty string
            "ABCDEFGHIJ",      # All letters
            "1234567890",      # All numbers
            "ABC",             # Too short
        ]
        
        for pan in invalid_pans:
            assert agent.validate_pan_format(pan) is False, f"Should fail for invalid PAN: {pan}"
    
    def test_validate_pan_format_none(self, agent):
        """Test PAN validation with None value."""
        assert agent.validate_pan_format(None) is False
    
    def test_validate_pan_format_non_string(self, agent):
        """Test PAN validation with non-string types."""
        assert agent.validate_pan_format(12345) is False
        assert agent.validate_pan_format([]) is False
        assert agent.validate_pan_format({}) is False
    
    # Mobile Format Validation Tests
    
    def test_validate_mobile_format_valid(self, agent):
        """Test mobile validation with valid formats."""
        valid_mobiles = [
            "9876543210",
            "8123456789",
            "7999888777",
            "6555444333",
        ]
        
        for mobile in valid_mobiles:
            assert agent.validate_mobile_format(mobile) is True, f"Failed for valid mobile: {mobile}"
    
    def test_validate_mobile_format_invalid(self, agent):
        """Test mobile validation with invalid formats."""
        invalid_mobiles = [
            "5876543210",      # Starts with 5
            "1234567890",      # Starts with 1
            "987654321",       # Only 9 digits
            "98765432100",     # 11 digits
            "987-654-3210",    # Contains hyphens
            "987 654 3210",    # Contains spaces
            "+919876543210",   # Contains country code
            "",                # Empty string
            "abcdefghij",      # Letters
            "98765432AB",      # Mixed alphanumeric
        ]
        
        for mobile in invalid_mobiles:
            assert agent.validate_mobile_format(mobile) is False, f"Should fail for invalid mobile: {mobile}"
    
    def test_validate_mobile_format_none(self, agent):
        """Test mobile validation with None value."""
        assert agent.validate_mobile_format(None) is False
    
    def test_validate_mobile_format_non_string(self, agent):
        """Test mobile validation with non-string types."""
        assert agent.validate_mobile_format(9876543210) is False
        assert agent.validate_mobile_format([]) is False
        assert agent.validate_mobile_format({}) is False
    
    # Customer Lookup Tests
    
    def test_lookup_customer_found(self, agent):
        """Test successful customer lookup."""
        customer = agent.lookup_customer("ABCDE1234F", "9876543210")
        
        assert customer is not None
        assert customer['customer_id'] == "CUST001"
        assert customer['name'] == "Rajesh Kumar"
        assert customer['pan'] == "ABCDE1234F"
        assert customer['mobile'] == "9876543210"
    
    def test_lookup_customer_found_lowercase_pan(self, agent):
        """Test customer lookup with lowercase PAN (should normalize)."""
        customer = agent.lookup_customer("abcde1234f", "9876543210")
        
        assert customer is not None
        assert customer['customer_id'] == "CUST001"
    
    def test_lookup_customer_not_found_wrong_pan(self, agent):
        """Test customer lookup with wrong PAN."""
        customer = agent.lookup_customer("ZZZZZ9999Z", "9876543210")
        
        assert customer is None
    
    def test_lookup_customer_not_found_wrong_mobile(self, agent):
        """Test customer lookup with wrong mobile."""
        customer = agent.lookup_customer("ABCDE1234F", "9999999999")
        
        assert customer is None
    
    def test_lookup_customer_not_found_both_wrong(self, agent):
        """Test customer lookup with both PAN and mobile wrong."""
        customer = agent.lookup_customer("ZZZZZ9999Z", "9999999999")
        
        assert customer is None
    
    def test_lookup_customer_multiple_customers(self, agent):
        """Test lookup for different customers."""
        # Customer 1
        customer1 = agent.lookup_customer("ABCDE1234F", "9876543210")
        assert customer1 is not None
        assert customer1['customer_id'] == "CUST001"
        
        # Customer 2
        customer2 = agent.lookup_customer("FGHIJ5678K", "9123456789")
        assert customer2 is not None
        assert customer2['customer_id'] == "CUST002"
        
        # Customer 3
        customer3 = agent.lookup_customer("KLMNO9012P", "9988776655")
        assert customer3 is not None
        assert customer3['customer_id'] == "CUST003"
    
    # Verify Identity Method Tests
    
    def test_verify_identity_success(self, agent):
        """Test successful identity verification."""
        result = agent.verify_identity("ABCDE1234F", "9876543210")
        
        assert isinstance(result, VerificationResult)
        assert result.success is True
        assert result.customer_id == "CUST001"
        assert result.name == "Rajesh Kumar"
        assert result.error_message is None
        assert result.retry_count == 0
    
    def test_verify_identity_invalid_pan(self, agent):
        """Test verification with invalid PAN format."""
        result = agent.verify_identity("INVALID", "9876543210")
        
        assert result.success is False
        assert result.customer_id is None
        assert result.name is None
        assert "Invalid PAN format" in result.error_message
    
    def test_verify_identity_invalid_mobile(self, agent):
        """Test verification with invalid mobile format."""
        result = agent.verify_identity("ABCDE1234F", "123456")
        
        assert result.success is False
        assert result.customer_id is None
        assert result.name is None
        assert "Invalid mobile number" in result.error_message
    
    def test_verify_identity_customer_not_found(self, agent):
        """Test verification when customer doesn't exist."""
        result = agent.verify_identity("ZZZZZ9999Z", "9999999999")
        
        assert result.success is False
        assert result.customer_id is None
        assert result.name is None
        assert "No customer found" in result.error_message
    
    def test_verify_identity_max_retries_exceeded(self, agent):
        """Test verification when max retries exceeded."""
        result = agent.verify_identity("ABCDE1234F", "9876543210", retry_count=3)
        
        assert result.success is False
        assert "Maximum verification attempts exceeded" in result.error_message
        assert result.retry_count == 3
    
    def test_verify_identity_with_retry_count(self, agent):
        """Test verification with retry count tracking."""
        result = agent.verify_identity("ZZZZZ9999Z", "9999999999", retry_count=1)
        
        assert result.success is False
        assert result.retry_count == 1
    
    # Process Method Tests
    
    def test_process_success(self, agent):
        """Test successful process flow."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "9876543210"
        }
        session_state = {
            "retry_counts": {}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is True
        assert response['agent'] == "verification_agent"
        assert response['next_agent'] == "credit_bureau_agent"
        assert 'verification_result' in response['data']
        assert 'customer_data' in response['data']
        assert response['data']['verification_result']['success'] is True
        assert response['data']['customer_data']['customer_id'] == "CUST001"
    
    def test_process_invalid_pan_format(self, agent):
        """Test process with invalid PAN format."""
        input_data = {
            "pan": "INVALID",
            "mobile": "9876543210"
        }
        session_state = {
            "retry_counts": {}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is False
        assert 'verification_result' in response['data']
        assert response['data']['verification_result']['success'] is False
        assert "PAN" in response['data']['verification_result']['error_message']
        assert response['data']['retry_count'] == 1
    
    def test_process_invalid_mobile_format(self, agent):
        """Test process with invalid mobile format."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "123456"
        }
        session_state = {
            "retry_counts": {}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is False
        assert 'verification_result' in response['data']
        assert response['data']['verification_result']['success'] is False
        assert "Mobile" in response['data']['verification_result']['error_message']
        assert response['data']['retry_count'] == 1
    
    def test_process_both_invalid_formats(self, agent):
        """Test process with both PAN and mobile invalid."""
        input_data = {
            "pan": "INVALID",
            "mobile": "123"
        }
        session_state = {
            "retry_counts": {}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is False
        error_msg = response['data']['verification_result']['error_message']
        assert "PAN" in error_msg
        assert "Mobile" in error_msg
    
    def test_process_customer_not_found(self, agent):
        """Test process when customer not found."""
        input_data = {
            "pan": "ZZZZZ9999Z",
            "mobile": "9999999999"
        }
        session_state = {
            "retry_counts": {}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is False
        assert 'verification_result' in response['data']
        assert response['data']['verification_result']['success'] is False
        assert "customer found" in response['data']['verification_result']['error_message'].lower()
        assert response['data']['retry_count'] == 1
    
    def test_process_retry_count_increments(self, agent):
        """Test that retry count increments on failures."""
        input_data = {
            "pan": "INVALID",
            "mobile": "9876543210"
        }
        
        # First attempt
        session_state = {"retry_counts": {"verification": 0}}
        response1 = agent.process(input_data, session_state)
        assert response1['data']['retry_count'] == 1
        
        # Second attempt
        session_state = {"retry_counts": {"verification": 1}}
        response2 = agent.process(input_data, session_state)
        assert response2['data']['retry_count'] == 2
        
        # Third attempt
        session_state = {"retry_counts": {"verification": 2}}
        response3 = agent.process(input_data, session_state)
        assert response3['data']['retry_count'] == 3
    
    def test_process_max_retries_exceeded(self, agent):
        """Test process when max retries exceeded."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "9876543210"
        }
        session_state = {
            "retry_counts": {"verification": 3}
        }
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is False
        assert "Maximum" in response['data']['verification_result']['error_message']
        assert "support team" in response['message'].lower()
    
    def test_process_missing_pan(self, agent):
        """Test process with missing PAN field."""
        input_data = {
            "mobile": "9876543210"
        }
        session_state = {"retry_counts": {}}
        
        with pytest.raises(ValidationError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "Missing required fields" in str(exc_info.value)
        assert "pan" in str(exc_info.value).lower()
    
    def test_process_missing_mobile(self, agent):
        """Test process with missing mobile field."""
        input_data = {
            "pan": "ABCDE1234F"
        }
        session_state = {"retry_counts": {}}
        
        with pytest.raises(ValidationError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "Missing required fields" in str(exc_info.value)
        assert "mobile" in str(exc_info.value).lower()
    
    def test_process_empty_pan(self, agent):
        """Test process with empty PAN value."""
        input_data = {
            "pan": "",
            "mobile": "9876543210"
        }
        session_state = {"retry_counts": {}}
        
        with pytest.raises(ValidationError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "Empty values" in str(exc_info.value)
    
    def test_process_empty_mobile(self, agent):
        """Test process with empty mobile value."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "   "  # Whitespace only
        }
        session_state = {"retry_counts": {}}
        
        with pytest.raises(ValidationError) as exc_info:
            agent.process(input_data, session_state)
        
        assert "Empty values" in str(exc_info.value)
    
    def test_process_whitespace_handling(self, agent):
        """Test that process handles whitespace in inputs."""
        input_data = {
            "pan": "  ABCDE1234F  ",
            "mobile": "  9876543210  "
        }
        session_state = {"retry_counts": {}}
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is True
        assert response['data']['customer_data']['customer_id'] == "CUST001"
    
    def test_process_lowercase_pan_normalization(self, agent):
        """Test that lowercase PAN is normalized to uppercase."""
        input_data = {
            "pan": "abcde1234f",
            "mobile": "9876543210"
        }
        session_state = {"retry_counts": {}}
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is True
        assert response['data']['customer_data']['customer_id'] == "CUST001"
    
    # Input Validation Tests
    
    def test_validate_input_success(self, agent):
        """Test input validation with valid data."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "9876543210"
        }
        
        assert agent.validate_input(input_data) is True
    
    def test_validate_input_missing_fields(self, agent):
        """Test input validation with missing fields."""
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input({})
        
        assert "Missing required fields" in str(exc_info.value)
    
    def test_validate_input_empty_values(self, agent):
        """Test input validation with empty values."""
        input_data = {
            "pan": "",
            "mobile": ""
        }
        
        with pytest.raises(ValidationError) as exc_info:
            agent.validate_input(input_data)
        
        assert "Empty values" in str(exc_info.value)
    
    # Database Loading Tests
    
    def test_database_loading_success(self, mock_customer_db):
        """Test successful database loading."""
        agent = VerificationAgent(customer_db_path=mock_customer_db)
        
        assert len(agent.customers) == 3
        assert ("ABCDE1234F", "9876543210") in agent.customers
        assert ("FGHIJ5678K", "9123456789") in agent.customers
        assert ("KLMNO9012P", "9988776655") in agent.customers
    
    def test_database_loading_file_not_found(self):
        """Test database loading with non-existent file."""
        with pytest.raises(DataError) as exc_info:
            VerificationAgent(customer_db_path="nonexistent.json")
        
        assert "not found" in str(exc_info.value).lower()
    
    def test_database_loading_invalid_json(self):
        """Test database loading with invalid JSON."""
        # Create temporary file with invalid JSON
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            f.write("{ invalid json }")
            temp_path = f.name
        
        try:
            with pytest.raises(DataError) as exc_info:
                VerificationAgent(customer_db_path=temp_path)
            
            assert "corrupted" in str(exc_info.value).lower()
        finally:
            Path(temp_path).unlink()
    
    # Edge Cases
    
    def test_process_with_extra_fields(self, agent):
        """Test process with extra fields in input (should be ignored)."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "9876543210",
            "extra_field": "should be ignored"
        }
        session_state = {"retry_counts": {}}
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is True
    
    def test_process_session_state_without_retry_counts(self, agent):
        """Test process when session_state doesn't have retry_counts."""
        input_data = {
            "pan": "ABCDE1234F",
            "mobile": "9876543210"
        }
        session_state = {}  # No retry_counts
        
        response = agent.process(input_data, session_state)
        
        assert response['success'] is True
    
    def test_multiple_verification_attempts_same_agent(self, agent):
        """Test multiple verification attempts with same agent instance."""
        # First customer
        result1 = agent.verify_identity("ABCDE1234F", "9876543210")
        assert result1.success is True
        assert result1.customer_id == "CUST001"
        
        # Second customer
        result2 = agent.verify_identity("FGHIJ5678K", "9123456789")
        assert result2.success is True
        assert result2.customer_id == "CUST002"
        
        # Invalid attempt
        result3 = agent.verify_identity("ZZZZZ9999Z", "9999999999")
        assert result3.success is False
    
    # Salary Verification Tests
    
    def test_verify_salary_with_valid_document(self, agent):
        """Test salary verification with valid document upload."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 1024 * 1024,  # 1MB
            "simulated_salary": 75000
        }
        
        result = agent.verify_salary(document_data=document_data)
        
        assert result.success is True
        assert result.verified_salary == 75000
        assert result.verification_method == "document_upload"
        assert result.document_filename == "salary_slip.pdf"
        assert result.error_message is None
    
    def test_verify_salary_with_manual_entry(self, agent):
        """Test salary verification with manual entry."""
        result = agent.verify_salary(manual_salary=80000)
        
        assert result.success is True
        assert result.verified_salary == 80000
        assert result.verification_method == "manual_entry"
        assert result.document_filename is None
        assert result.error_message is None
    
    def test_verify_salary_no_input_provided(self, agent):
        """Test salary verification when neither document nor manual salary provided."""
        result = agent.verify_salary()
        
        assert result.success is False
        assert result.verified_salary is None
        assert "provide either" in result.error_message.lower()
    
    def test_verify_salary_document_invalid_format(self, agent):
        """Test salary verification with invalid document format."""
        document_data = {
            "filename": "salary_slip.txt",  # Invalid format
            "file_size": 1024 * 1024
        }
        
        result = agent.verify_salary(document_data=document_data)
        
        assert result.success is False
        assert result.verified_salary is None
        assert "Invalid file format" in result.error_message
    
    def test_verify_salary_document_too_large(self, agent):
        """Test salary verification with document exceeding size limit."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 6 * 1024 * 1024  # 6MB (exceeds 5MB limit)
        }
        
        result = agent.verify_salary(document_data=document_data)
        
        assert result.success is False
        assert result.verified_salary is None
        assert "exceeds maximum limit" in result.error_message
    
    def test_verify_salary_document_extraction_fails(self, agent):
        """Test salary verification when document extraction fails."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 1024 * 1024
            # No simulated_salary - extraction will fail
        }
        
        result = agent.verify_salary(document_data=document_data)
        
        assert result.success is False
        assert result.verified_salary is None
        assert "Could not extract salary" in result.error_message
    
    def test_verify_salary_manual_below_minimum(self, agent):
        """Test salary verification with manual entry below minimum."""
        result = agent.verify_salary(manual_salary=5000)  # Below 10,000 minimum
        
        assert result.success is False
        assert result.verified_salary is None
        assert "at least" in result.error_message
    
    def test_verify_salary_manual_above_maximum(self, agent):
        """Test salary verification with manual entry above maximum."""
        result = agent.verify_salary(manual_salary=1500000)  # Above 1,000,000 maximum
        
        assert result.success is False
        assert result.verified_salary is None
        assert "exceeds maximum limit" in result.error_message
    
    def test_verify_salary_manual_invalid_type(self, agent):
        """Test salary verification with invalid manual salary type."""
        result = agent.verify_salary(manual_salary="not a number")
        
        assert result.success is False
        assert result.verified_salary is None
        assert "valid number" in result.error_message
    
    def test_validate_salary_document_valid_pdf(self, agent):
        """Test document validation with valid PDF."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 2 * 1024 * 1024  # 2MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is True
        assert result["error_message"] is None
    
    def test_validate_salary_document_valid_jpg(self, agent):
        """Test document validation with valid JPG."""
        document_data = {
            "filename": "salary_slip.jpg",
            "file_size": 1024 * 1024  # 1MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is True
        assert result["error_message"] is None
    
    def test_validate_salary_document_valid_png(self, agent):
        """Test document validation with valid PNG."""
        document_data = {
            "filename": "salary_slip.png",
            "file_size": 3 * 1024 * 1024  # 3MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is True
        assert result["error_message"] is None
    
    def test_validate_salary_document_valid_jpeg(self, agent):
        """Test document validation with valid JPEG."""
        document_data = {
            "filename": "salary_slip.jpeg",
            "file_size": 1024 * 1024  # 1MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is True
        assert result["error_message"] is None
    
    def test_validate_salary_document_missing_filename(self, agent):
        """Test document validation with missing filename."""
        document_data = {
            "file_size": 1024 * 1024
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is False
        assert "filename is required" in result["error_message"]
    
    def test_validate_salary_document_missing_file_size(self, agent):
        """Test document validation with missing file size."""
        document_data = {
            "filename": "salary_slip.pdf"
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is False
        assert "file size is required" in result["error_message"]
    
    def test_validate_salary_document_invalid_extensions(self, agent):
        """Test document validation with various invalid extensions."""
        invalid_extensions = [
            "salary_slip.txt",
            "salary_slip.doc",
            "salary_slip.docx",
            "salary_slip.xls",
            "salary_slip.zip",
            "salary_slip",  # No extension
        ]
        
        for filename in invalid_extensions:
            document_data = {
                "filename": filename,
                "file_size": 1024 * 1024
            }
            
            result = agent.validate_salary_document(document_data)
            
            assert result["valid"] is False, f"Should fail for {filename}"
            assert "Invalid file format" in result["error_message"]
    
    def test_validate_salary_document_case_insensitive_extension(self, agent):
        """Test document validation with uppercase extensions."""
        valid_filenames = [
            "salary_slip.PDF",
            "salary_slip.JPG",
            "salary_slip.PNG",
            "salary_slip.JPEG"
        ]
        
        for filename in valid_filenames:
            document_data = {
                "filename": filename,
                "file_size": 1024 * 1024
            }
            
            result = agent.validate_salary_document(document_data)
            
            assert result["valid"] is True, f"Should pass for {filename}"
    
    def test_validate_salary_document_exactly_5mb(self, agent):
        """Test document validation with exactly 5MB file."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 5 * 1024 * 1024  # Exactly 5MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is True
    
    def test_validate_salary_document_just_over_5mb(self, agent):
        """Test document validation with file just over 5MB."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 5 * 1024 * 1024 + 1  # Just over 5MB
        }
        
        result = agent.validate_salary_document(document_data)
        
        assert result["valid"] is False
        assert "exceeds maximum limit" in result["error_message"]
    
    def test_validate_manual_salary_valid_amounts(self, agent):
        """Test manual salary validation with valid amounts."""
        valid_salaries = [
            10000,    # Minimum
            50000,    # Mid-range
            100000,   # High
            1000000,  # Maximum
            75000.50  # With decimals
        ]
        
        for salary in valid_salaries:
            result = agent.validate_manual_salary(salary)
            
            assert result["valid"] is True, f"Should pass for salary: {salary}"
            assert result["error_message"] is None
    
    def test_validate_manual_salary_below_minimum(self, agent):
        """Test manual salary validation below minimum."""
        result = agent.validate_manual_salary(9999)
        
        assert result["valid"] is False
        assert "at least" in result["error_message"]
    
    def test_validate_manual_salary_above_maximum(self, agent):
        """Test manual salary validation above maximum."""
        result = agent.validate_manual_salary(1000001)
        
        assert result["valid"] is False
        assert "exceeds maximum limit" in result["error_message"]
    
    def test_validate_manual_salary_zero(self, agent):
        """Test manual salary validation with zero."""
        result = agent.validate_manual_salary(0)
        
        assert result["valid"] is False
    
    def test_validate_manual_salary_negative(self, agent):
        """Test manual salary validation with negative value."""
        result = agent.validate_manual_salary(-50000)
        
        assert result["valid"] is False
    
    def test_validate_manual_salary_non_numeric(self, agent):
        """Test manual salary validation with non-numeric values."""
        invalid_values = [
            "50000",
            None,
            [],
            {},
            "fifty thousand"
        ]
        
        for value in invalid_values:
            result = agent.validate_manual_salary(value)
            
            assert result["valid"] is False, f"Should fail for value: {value}"
            assert "valid number" in result["error_message"]
    
    def test_extract_salary_from_document_with_simulated_salary(self, agent):
        """Test salary extraction with simulated salary in document data."""
        document_data = {
            "filename": "salary_slip.pdf",
            "simulated_salary": 85000
        }
        
        salary = agent._extract_salary_from_document(document_data)
        
        assert salary == 85000
    
    def test_extract_salary_from_document_with_file_content(self, agent):
        """Test salary extraction with salary in file content."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_content": {
                "salary": 95000
            }
        }
        
        salary = agent._extract_salary_from_document(document_data)
        
        assert salary == 95000
    
    def test_extract_salary_from_document_no_salary_info(self, agent):
        """Test salary extraction when no salary information available."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 1024 * 1024
        }
        
        salary = agent._extract_salary_from_document(document_data)
        
        assert salary is None
    
    def test_verify_salary_document_priority_over_manual(self, agent):
        """Test that document upload takes priority when both provided."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 1024 * 1024,
            "simulated_salary": 75000
        }
        
        result = agent.verify_salary(document_data=document_data, manual_salary=50000)
        
        assert result.success is True
        assert result.verified_salary == 75000  # Document salary, not manual
        assert result.verification_method == "document_upload"
    
    def test_verify_salary_fallback_to_manual_on_extraction_failure(self, agent):
        """Test fallback behavior when document extraction fails."""
        document_data = {
            "filename": "salary_slip.pdf",
            "file_size": 1024 * 1024
            # No salary info - extraction will fail
        }
        
        result = agent.verify_salary(document_data=document_data)
        
        assert result.success is False
        assert "Could not extract salary" in result.error_message
        assert "manually" in result.error_message
    
    def test_verify_salary_multiple_valid_formats(self, agent):
        """Test salary verification with multiple document formats."""
        formats = ["pdf", "jpg", "jpeg", "png"]
        
        for fmt in formats:
            document_data = {
                "filename": f"salary_slip.{fmt}",
                "file_size": 1024 * 1024,
                "simulated_salary": 70000
            }
            
            result = agent.verify_salary(document_data=document_data)
            
            assert result.success is True, f"Should succeed for .{fmt}"
            assert result.verified_salary == 70000
            assert result.verification_method == "document_upload"
