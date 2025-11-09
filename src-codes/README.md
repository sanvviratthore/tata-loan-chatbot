# Tata Loan Chatbot

An end-to-end multi-agent conversational AI system for personal loan processing, built for the EY Hackathon 2025. The system guides users through identity verification, credit analysis, loan consolidation, underwriting, and document generation—all within a single chat interface.

## Features

- **Multi-Agent Architecture**: Specialized agents for verification, credit analysis, underwriting, consolidation, sales, and document generation
- **Intelligent Routing**: Master agent orchestrates workflow based on user context and intent
- **Debt Consolidation**: Automatic consolidation offers for users with multiple loans
- **Instant Decisions**: Real-time loan approval/rejection with personalized recommendations
- **Professional Documents**: Auto-generated PDF offer letters and reports
- **Free & Open Source**: Built entirely with free tools and APIs

## Architecture

The system uses a modular agent-based architecture:

- **Verification Agent**: Identity validation using PAN and mobile number
- **Credit Bureau Agent**: Credit profile analysis and portfolio assessment
- **Underwriting Agent**: Eligibility assessment and loan offer generation
- **Debt Consolidation Agent**: Multi-loan consolidation with savings calculation
- **Sales Agent**: Conversational offer presentation and Q&A
- **Document Agent**: Professional PDF generation
- **Master Agent**: Central orchestrator for workflow routing

## Prerequisites

- Python 3.9 or higher
- OpenRouter API key (free tier available)

## Installation

1. **Clone the repository**
   ```bash
   git clone <repository-url>
   cd tata-loan-chatbot
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   
   # On Windows
   venv\Scripts\activate
   
   # On macOS/Linux
   source venv/bin/activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   # Copy the example file
   copy .env.example .env  # Windows
   cp .env.example .env    # macOS/Linux
   
   # Edit .env and add your OpenRouter API key
   ```

5. **Get your OpenRouter API key**
   - Visit [OpenRouter](https://openrouter.ai/)
   - Sign up for a free account
   - Generate an API key
   - Add it to your `.env` file

## Usage

1. **Run the Streamlit application**
   ```bash
   streamlit run app.py
   ```

2. **Access the chatbot**
   - Open your browser to `http://localhost:8501`
   - Start chatting with the loan assistant

3. **Test with sample data**
   - Use the mock customer data in `data/customers.json`
   - Example PAN: `ABCDE1234F`, Mobile: `9876543210`

## Project Structure

```
tata-loan-chatbot/
├── app.py                          # Streamlit UI
├── master_agent.py                 # Orchestrator
├── requirements.txt                # Dependencies
├── .env.example                    # Environment template
├── README.md                       # This file
│
├── agents/                         # Specialized agents
│   ├── __init__.py
│   ├── base_agent.py
│   ├── verification_agent.py
│   ├── credit_bureau_agent.py
│   ├── underwriting_agent.py
│   ├── debt_consolidation_agent.py
│   ├── sales_agent.py
│   └── document_agent.py
│
├── data/                           # Mock data files
│   ├── customers.json
│   └── credit_bureau_data.json
│
├── utils/                          # Utility modules
│   ├── __init__.py
│   ├── loan_calculator.py
│   ├── session_manager.py
│   ├── llm_client.py
│   └── logger.py
│
├── schemas/                        # Data models
│   ├── __init__.py
│   └── models.py
│
├── tests/                          # Test suite
│   ├── __init__.py
│   ├── test_verification_agent.py
│   ├── test_credit_bureau_agent.py
│   ├── test_underwriting_agent.py
│   ├── test_consolidation_agent.py
│   ├── test_loan_calculator.py
│   └── test_integration.py
│
└── logs/                           # Application logs
    └── .gitkeep
```

## Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_verification_agent.py

# Run with coverage
pytest --cov=. --cov-report=html
```

## Configuration

### Environment Variables

- `OPENROUTER_API_KEY`: Your OpenRouter API key (required)
- `OPENROUTER_MODEL`: LLM model to use (default: `meta-llama/llama-3.1-8b-instruct:free`)
- `LOG_LEVEL`: Logging level (default: `INFO`)

### Mock Data

The system uses mock JSON files for customer and credit bureau data:

- `data/customers.json`: Customer profiles with PAN, mobile, income
- `data/credit_bureau_data.json`: Credit scores and active loan details

You can modify these files to test different scenarios.

## Workflow Examples

### Scenario 1: Multiple Loans (Consolidation)
1. User provides PAN and mobile
2. System verifies identity
3. Credit bureau finds 3 active loans
4. Consolidation agent generates offer with savings
5. Sales agent presents benefits
6. User accepts, receives PDF offer letter

### Scenario 2: Low Credit Score
1. User provides PAN and mobile
2. System verifies identity
3. Credit bureau finds score < 650
4. System provides credit improvement plan
5. User receives PDF with actionable steps

### Scenario 3: New Loan Application
1. User provides PAN and mobile
2. System verifies identity
3. Credit bureau finds no existing loans
4. Underwriting agent assesses eligibility
5. Sales agent presents loan offer
6. User accepts, receives PDF offer letter

## Troubleshooting

### Common Issues

**Issue**: `ModuleNotFoundError: No module named 'streamlit'`
- **Solution**: Ensure you've activated the virtual environment and installed dependencies

**Issue**: `OpenRouter API key not found`
- **Solution**: Check that your `.env` file exists and contains `OPENROUTER_API_KEY`

**Issue**: `Customer not found in database`
- **Solution**: Use PAN and mobile combinations from `data/customers.json`

**Issue**: Streamlit app won't start
- **Solution**: Check if port 8501 is already in use, or specify a different port:
  ```bash
  streamlit run app.py --server.port 8502
  ```

## Technical Constraints

- Uses only free and open-source tools
- OpenRouter free tier for LLM capabilities
- Mock data for all external integrations
- No paid third-party services or APIs
- Fully deployable locally without external dependencies

## Contributing

This project was built for the EY Hackathon 2025. For questions or contributions, please refer to the project documentation.

## License

[Specify your license here]

## Acknowledgments

- Built with Streamlit, LangChain, and OpenRouter
- Designed for the EY Hackathon 2025
- Uses free and open-source technologies throughout
