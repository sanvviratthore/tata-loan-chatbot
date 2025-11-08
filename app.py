import streamlit as st
import time
from datetime import datetime
import json

# Page Configuration
st.set_page_config(
    page_title="Tata Personal Loan Assistant",
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded"
)

# EY Theme Colors
st.markdown("""
<style>
    /* EY Yellow and Black Theme */
    :root {
        --ey-yellow: #FFE600;
        --ey-black: #2E2E38;
        --ey-dark: #1A1A1F;
    }
    
    /* Sidebar styling */
    section[data-testid="stSidebar"] {
        background-color: #2E2E38 !important;
    }
    
    section[data-testid="stSidebar"] * {
        color: white !important;
    }
    
    /* Main background */
    .main {
        background-color: #2E2E38;
    }
    
    /* All text white except buttons */
    .main * {
        color: white !important;
    }
    
    /* Headers */
    h1, h2, h3, h4, h5, h6 {
        color: white !important;
    }
    
    /* Paragraphs and spans */
    p, span, div, label {
        color: white !important;
    }
    
    /* Buttons - black text on yellow background */
    .stButton>button {
        background-color: #FFE600 !important;
        color: #000000 !important;
        border: none !important;
        font-weight: 600 !important;
    }
    
    .stButton>button:hover {
        background-color: #E6CF00 !important;
        border: 2px solid #FFE600 !important;
        color: #000000 !important;
    }
    
    .stButton>button p {
        color: #000000 !important;
    }
    
    .stButton>button span {
        color: #000000 !important;
    }
    
    .stButton>button div {
        color: #000000 !important;
    }
    
    /* Metrics */
    [data-testid="stMetricValue"] {
        color: white !important;
    }
    
    [data-testid="stMetricLabel"] {
        color: white !important;
    }
    
    [data-testid="stMetricDelta"] {
        color: #FFE600 !important;
    }
    
    /* Progress bar */
    .stProgress > div > div > div > div {
        background-color: #FFE600 !important;
    }
    
    /* Info boxes */
    .stAlert {
        background-color: #3E3E48 !important;
        border-left: 4px solid #FFE600 !important;
        color: white !important;
    }
    
    /* Chat messages */
    .stChatMessage {
        background-color: #3E3E48 !important;
        border: 1px solid #FFE600 !important;
        color: white !important;
    }
    
    /* Chat input */
    .stChatInput textarea {
        background-color: #3E3E48 !important;
        color: white !important;
        border: 1px solid #FFE600 !important;
    }
    
    /* Text input */
    .stTextInput input {
        background-color: #3E3E48 !important;
        color: white !important;
        border: 1px solid #FFE600 !important;
    }
    
    /* Dividers */
    hr {
        border-color: #FFE600 !important;
    }
    
    /* Caption text */
    .caption {
        color: #CCCCCC !important;
    }
</style>
""", unsafe_allow_html=True)

# Initialize session state
if 'messages' not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Hello! I'm your Tata Personal Loan Assistant. I can help you with loan applications, eligibility checks, and document verification. How can I assist you today?", "timestamp": datetime.now()}
    ]

if 'customer_data' not in st.session_state:
    st.session_state.customer_data = {}

if 'loan_stage' not in st.session_state:
    st.session_state.loan_stage = "initial"  # initial, bureau_check, verification, underwriting, approved

if 'credit_score' not in st.session_state:
    st.session_state.credit_score = None

if 'existing_loans' not in st.session_state:
    st.session_state.existing_loans = 0

if 'auto_detected' not in st.session_state:
    st.session_state.auto_detected = False

if 'hero_feature_used' not in st.session_state:
    st.session_state.hero_feature_used = False

# Sidebar - Application Status & Features
with st.sidebar:
    st.title("Application Status")
    st.divider()
    
    # Stage Progress
    stages = {
        "initial": 0,
        "bureau_check": 25,
        "verification": 50,
        "underwriting": 75,
        "approved": 100,
        "rejected": 100
    }
    
    current_progress = stages.get(st.session_state.loan_stage, 0)
    
    st.subheader("Application Progress")
    st.progress(current_progress / 100)
    st.caption(f"{current_progress}% Complete")
    
    # Current Stage Display
    stage_names = {
        "initial": "Initial Inquiry",
        "bureau_check": "Credit Bureau Check",
        "verification": "Document Verification",
        "underwriting": "Underwriting Review",
        "approved": "Approved",
        "rejected": "Rejected"
    }
    st.info(stage_names.get(st.session_state.loan_stage, "Unknown"))
    
    st.divider()
    
    # Smart Features Display
    st.subheader("Smart Features")
    
    if st.session_state.auto_detected:
        st.success("Auto-detected via Bureau")
    else:
        st.caption("Auto-detection pending")
    
    if st.session_state.credit_score:
        st.metric("Credit Score", st.session_state.credit_score)
    
    if st.session_state.existing_loans > 0:
        st.metric("Existing Loans", st.session_state.existing_loans)
    
    if st.session_state.hero_feature_used:
        st.success("Hero Feature Active")
    
    st.divider()
    
    # Customer Info
    if st.session_state.customer_data:
        st.subheader("Customer Details")
        for key, value in st.session_state.customer_data.items():
            if key not in ['password', 'pin']:
                st.caption(f"**{key.replace('_', ' ').title()}:** {value}")

# Navigation Bar
nav_col1, nav_col2, nav_col3, nav_col4, nav_col5 = st.columns([1, 1, 1, 1, 1])

with nav_col1:
    if st.button("Check Eligibility", use_container_width=True, key="nav_eligibility"):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "Let me check your eligibility. I'll need to verify your credit score and existing loans. Please provide your PAN number to proceed with auto-detection.",
            "timestamp": datetime.now()
        })
        st.session_state.loan_stage = "bureau_check"
        st.rerun()

with nav_col2:
    if st.button("Upload Documents", use_container_width=True, key="nav_documents"):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I'm ready to help you upload your documents. Please share:\n1. PAN Card\n2. Aadhaar Card\n3. Salary Slips (last 3 months)\n4. Bank Statements (last 6 months)",
            "timestamp": datetime.now()
        })
        st.session_state.loan_stage = "verification"
        st.rerun()

with nav_col3:
    if st.button("Calculate EMI", use_container_width=True, key="nav_emi"):
        st.session_state.messages.append({
            "role": "assistant",
            "content": "I can help you calculate your EMI. Please tell me:\n1. Desired loan amount\n2. Preferred tenure (in months)\n\nBased on your credit profile, I'll provide personalized interest rates.",
            "timestamp": datetime.now()
        })
        st.rerun()

with nav_col4:
    if st.button("Application Status", use_container_width=True, key="nav_status"):
        stage_info = {
            "initial": "Your application is in initial stage. Please proceed with eligibility check.",
            "bureau_check": "We are checking your credit bureau records.",
            "verification": "Please upload required documents for verification.",
            "underwriting": "Your application is under review by our underwriting team.",
            "approved": "Congratulations! Your loan has been approved.",
            "rejected": "Unfortunately, your application was not approved at this time."
        }
        st.session_state.messages.append({
            "role": "assistant",
            "content": stage_info.get(st.session_state.loan_stage, "Unknown status"),
            "timestamp": datetime.now()
        })
        st.rerun()

with nav_col5:
    if st.button("Reset Chat", use_container_width=True, key="nav_reset"):
        st.session_state.messages = [
            {"role": "assistant", "content": "Hello! I'm your Tata Personal Loan Assistant. I can help you with loan applications, eligibility checks, and document verification. How can I assist you today?", "timestamp": datetime.now()}
        ]
        st.session_state.loan_stage = "initial"
        st.session_state.customer_data = {}
        st.session_state.credit_score = None
        st.session_state.existing_loans = 0
        st.session_state.auto_detected = False
        st.session_state.hero_feature_used = False
        st.rerun()

st.divider()

# Quick Stats Row
stats_col1, stats_col2, stats_col3, stats_col4 = st.columns(4)

with stats_col1:
    st.metric("Processing Speed", "< 5 min", "Fast")

with stats_col2:
    st.metric("Approval Rate", "85%", "+5%")

with stats_col3:
    st.metric("Applications Today", "247", "+12")

with stats_col4:
    st.metric("Avg Loan Amount", "₹5.2L", "+₹0.3L")

st.divider()

# Chat Interface
st.subheader("Chat with Assistant")

# Chat Container
chat_container = st.container()
with chat_container:
    # Display chat messages
    for idx, message in enumerate(st.session_state.messages):
        if message["role"] == "user":
            with st.chat_message("user"):
                st.write(message["content"])
        else:
            with st.chat_message("assistant"):
                st.write(message["content"])
                
                # Show special badges for certain messages
                if "approved" in message["content"].lower():
                    st.success("Application Approved!")
                elif "rejected" in message["content"].lower():
                    st.error("Application Rejected")
                elif "credit score" in message["content"].lower():
                    st.info("Credit Bureau Data Retrieved")

# Chat Input
user_input = st.chat_input("Type your message here...")

# Handle user input
if user_input:
    # Add user message
    st.session_state.messages.append({
        "role": "user",
        "content": user_input,
        "timestamp": datetime.now()
    })
    
    # Simulate bot response (this will be replaced with actual agent logic)
    with st.spinner("Processing..."):
        time.sleep(1)
        
        # Placeholder logic - will be replaced with actual master_agent integration
        bot_response = "Thank you for your message. I'm processing your request..."
        
        # Update stage based on keywords (temporary logic)
        if "loan" in user_input.lower() and st.session_state.loan_stage == "initial":
            st.session_state.loan_stage = "bureau_check"
            bot_response = "I'll check your credit bureau records to expedite your application. Please provide your PAN number."
            st.session_state.auto_detected = True
        
        st.session_state.messages.append({
            "role": "assistant",
            "content": bot_response,
            "timestamp": datetime.now()
        })
    
    st.rerun()

st.divider()

# Footer
footer_col1, footer_col2, footer_col3 = st.columns(3)

with footer_col1:
    st.caption("**Secure & Confidential**")

with footer_col2:
    st.caption("**Fast Processing (< 5 minutes)**")

with footer_col3:
    st.caption("**85% Approval Rate**")

st.caption("---")
st.caption("© 2025 Tata Personal Loan Assistant | Powered by AI | All Rights Reserved")
