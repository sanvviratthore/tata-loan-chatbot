// EY Tata Capital - Frontend JavaScript

let sessionId = null;
let currentScreen = 'welcomeScreen';

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('EY Tata Capital App Initialized');
    initializeChat();
});

// Screen Navigation
function showScreen(screenId) {
    document.querySelectorAll('.screen').forEach(screen => {
        screen.classList.remove('active');
    });
    document.getElementById(screenId).classList.add('active');
    currentScreen = screenId;
    
    if (screenId === 'chatScreen' && !sessionId) {
        createSession();
    }
}

// Create Session
async function createSession() {
    try {
        const response = await fetch('/api/session/create', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' }
        });
        const data = await response.json();
        sessionId = data.session_id;
        console.log('Session created:', sessionId);
        
        // Send initial greeting
        addBotMessage(
            `Hello! Welcome to **EY Tata Capital**. I'm here to help you with your personal loan needs.\n\n` +
            `To get started, I'll need to verify your identity. Please provide:\n` +
            `1. Your PAN card number (format: ABCDE1234F)\n` +
            `2. Your registered mobile number\n\n` +
            `You can provide both details in your next message.`,
            'Master'
        );
    } catch (error) {
        console.error('Error creating session:', error);
        addSystemMessage('Failed to create session. Please refresh the page.');
    }
}

// Send Message
async function sendMessage() {
    const input = document.getElementById('messageInput');
    const message = input.value.trim();
    
    if (!message) return;
    
    // Add user message to UI
    addUserMessage(message);
    input.value = '';
    
    // Show typing indicator
    const typingId = addTypingIndicator();
    
    try {
        const response = await fetch('/api/chat', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                message: message,
                session_id: sessionId
            })
        });
        
        const data = await response.json();
        
        // Remove typing indicator
        removeTypingIndicator(typingId);
        
        if (data.success) {
            sessionId = data.session_id;
            addBotMessage(data.message, data.agent);
            
            // Check if response contains profile data
            if (data.data && data.data.profile) {
                updateProfile(data.data.profile);
            }
            
            // Check for customer data in response
            if (data.data && data.data.customer_data) {
                updateProfile(data.data.customer_data);
            }
            
            // Check for PDF document
            if (data.data && data.data.pdf_content) {
                console.log('PDF detected!', data.data);
                const filename = data.data.filename || 'loan_document.pdf';
                // PDF is base64 encoded, create download link
                const pdfData = data.data.pdf_content;
                addPdfDownload(filename, pdfData);
            } else if (data.data) {
                console.log('Response data:', Object.keys(data.data));
            }
        } else {
            addSystemMessage('Error: ' + data.message);
        }
    } catch (error) {
        removeTypingIndicator(typingId);
        console.error('Error sending message:', error);
        addSystemMessage('Failed to send message. Please try again.');
    }
}

// Handle Enter Key
function handleKeyPress(event) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
    }
}

// Add User Message
function addUserMessage(message) {
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message user-message';
    messageDiv.innerHTML = `
        <div class="message-content">
            <div class="message-text">${escapeHtml(message)}</div>
            <div class="message-time">
                <span>${getCurrentTime()}</span>
                <i data-lucide="check-circle"></i>
            </div>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
    lucide.createIcons();
}

// Add Bot Message
function addBotMessage(message, agent = 'Assistant') {
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    
    // Format message (support markdown-like syntax)
    const formattedMessage = formatMessage(message);
    
    messageDiv.innerHTML = `
        <div class="bot-avatar">
            <i data-lucide="message-circle"></i>
        </div>
        <div class="message-content">
            <div class="agent-badge">${agent} Agent</div>
            <div class="message-text">${formattedMessage}</div>
            <div class="message-time">
                <i data-lucide="clock"></i>
                <span>Just now</span>
            </div>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
    lucide.createIcons();
}

// Add System Message
function addSystemMessage(message) {
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message system-message';
    messageDiv.innerHTML = `
        <div class="system-content">
            <i data-lucide="info"></i>
            <span>${escapeHtml(message)}</span>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
    lucide.createIcons();
}

// Add Typing Indicator
function addTypingIndicator() {
    const container = document.getElementById('messagesContainer');
    const typingDiv = document.createElement('div');
    const id = 'typing-' + Date.now();
    typingDiv.id = id;
    typingDiv.className = 'message bot-message typing-indicator';
    typingDiv.innerHTML = `
        <div class="bot-avatar">
            <i data-lucide="message-circle"></i>
        </div>
        <div class="message-content">
            <div class="typing-dots">
                <span></span>
                <span></span>
                <span></span>
            </div>
        </div>
    `;
    container.appendChild(typingDiv);
    scrollToBottom();
    lucide.createIcons();
    return id;
}

// Remove Typing Indicator
function removeTypingIndicator(id) {
    const element = document.getElementById(id);
    if (element) {
        element.remove();
    }
}

// Reset Chat
async function resetChat() {
    if (sessionId) {
        try {
            await fetch(`/api/session/${sessionId}`, {
                method: 'DELETE'
            });
        } catch (error) {
            console.error('Error resetting session:', error);
        }
    }
    
    sessionId = null;
    const container = document.getElementById('messagesContainer');
    container.innerHTML = `
        <div class="welcome-banner">
            <div class="welcome-icon">✨</div>
            <div class="welcome-title">Welcome to EY Tata Capital</div>
            <div class="welcome-subtitle">Your intelligent loan assistant powered by AI</div>
            <div class="welcome-features">
                <div class="welcome-feature">
                    <div class="feature-emoji">⚡</div>
                    <div class="feature-title">2-Min Approval</div>
                    <div class="feature-desc">Instant loan decisions</div>
                </div>
                <div class="welcome-feature">
                    <div class="feature-emoji">💰</div>
                    <div class="feature-title">Save ₹2.8L+</div>
                    <div class="feature-desc">Average savings</div>
                </div>
                <div class="welcome-feature">
                    <div class="feature-emoji">🛡️</div>
                    <div class="feature-title">100% Secure</div>
                    <div class="feature-desc">Bank-grade encryption</div>
                </div>
            </div>
        </div>
    `;
    
    // Reset sidebar to welcome state
    showSidebarWelcome();
    
    createSession();
}

// Toggle Sidebar (Mobile)
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('active');
}

// Initialize Chat
function initializeChat() {
    // File upload handler
    document.getElementById('fileInput').addEventListener('change', handleFileUpload);
    
    // Initialize sidebar
    showSidebarWelcome();
}

// Show Sidebar Welcome
function showSidebarWelcome() {
    const welcome = document.getElementById('sidebarWelcome');
    const profile = document.getElementById('profileSection');
    
    if (welcome) welcome.style.display = 'block';
    if (profile) profile.style.display = 'none';
}

// Update Profile (called when user data is available)
function updateProfile(data) {
    console.log('Updating profile with data:', data);
    
    const welcome = document.getElementById('sidebarWelcome');
    const profile = document.getElementById('profileSection');
    
    // Hide welcome, show profile
    if (welcome) welcome.style.display = 'none';
    if (profile) profile.style.display = 'block';
    
    // Update profile data
    if (data.name) {
        const initials = data.name.split(' ').map(n => n[0]).join('').toUpperCase();
        document.getElementById('profileAvatar').textContent = initials;
        document.getElementById('profileName').textContent = data.name;
    }
    
    // Handle both camelCase and snake_case
    const customerId = data.customerId || data.customer_id;
    if (customerId) {
        document.getElementById('profileId').textContent = `ID: ${customerId}`;
    }
    
    if (data.verified) {
        const statusBadge = document.getElementById('profileStatus');
        statusBadge.style.display = 'inline-flex';
        document.getElementById('statusText').textContent = 'Verified';
    }
    
    // Update credit score (handle both camelCase and snake_case)
    const creditScore = data.creditScore || data.credit_score;
    if (creditScore) {
        const creditCard = document.getElementById('creditScoreCard');
        creditCard.style.display = 'block';
        document.getElementById('creditScore').textContent = creditScore;
        document.getElementById('creditBadge').textContent = getCreditRating(creditScore);
        document.getElementById('creditUpdate').textContent = '📈 Just updated';
    }
    
    // Update loans
    if (data.loans && data.loans.length > 0) {
        const loansCard = document.getElementById('activeLoansCard');
        loansCard.style.display = 'block';
        document.getElementById('loanCount').textContent = data.loans.length;
        
        const loansList = document.getElementById('loansList');
        loansList.innerHTML = '';
        
        data.loans.forEach(loan => {
            const loanCard = createLoanCard(loan);
            loansList.appendChild(loanCard);
        });
    }
    
    // Update financial overview
    if (data.financial) {
        const financialCard = document.getElementById('financialOverviewCard');
        financialCard.style.display = 'block';
        
        const metrics = document.getElementById('financialMetrics');
        metrics.innerHTML = '';
        
        if (data.financial.totalOutstanding) {
            metrics.appendChild(createMetricRow('Total Outstanding', data.financial.totalOutstanding));
        }
        if (data.financial.monthlyEMI) {
            metrics.appendChild(createMetricRow('Monthly EMI', data.financial.monthlyEMI));
        }
        if (data.financial.dtiRatio) {
            const dtiDiv = document.createElement('div');
            dtiDiv.className = 'metric-row';
            dtiDiv.innerHTML = `
                <span>DTI Ratio</span>
                <div>
                    <span class="metric-value-text">${data.financial.dtiRatio}%</span>
                    <span class="badge-excellent">Excellent</span>
                </div>
            `;
            metrics.appendChild(dtiDiv);
        }
        if (data.financial.availableLimit) {
            metrics.appendChild(createMetricRow('Available Limit', data.financial.availableLimit));
        }
    }
    
    // Reinitialize icons
    lucide.createIcons();
}

// Helper: Get credit rating
function getCreditRating(score) {
    if (score >= 750) return 'Excellent';
    if (score >= 700) return 'Good';
    if (score >= 650) return 'Fair';
    return 'Poor';
}

// Helper: Create loan card
function createLoanCard(loan) {
    const div = document.createElement('div');
    div.className = 'loan-card';
    div.innerHTML = `
        <div class="loan-header">
            <div>
                <div class="loan-type">${loan.type}</div>
                <div class="loan-bank">${loan.bank}</div>
            </div>
            <i data-lucide="credit-card"></i>
        </div>
        <div class="loan-details">
            <div>
                <div class="loan-label">Outstanding</div>
                <div class="loan-amount">${loan.outstanding}</div>
            </div>
            <div>
                <div class="loan-label">EMI</div>
                <div class="loan-emi">${loan.emi}</div>
            </div>
        </div>
    `;
    return div;
}

// Helper: Create metric row
function createMetricRow(label, value) {
    const div = document.createElement('div');
    div.className = 'metric-row';
    div.innerHTML = `
        <span>${label}</span>
        <span class="metric-value-text">${value}</span>
    `;
    return div;
}

// Add PDF download
function addPdfDownload(filename, base64Data) {
    console.log('Adding PDF download button for:', filename);
    
    // Shorten filename for display
    const displayName = filename.length > 40 ? filename.substring(0, 37) + '...' : filename;
    
    // Add to messages
    const container = document.getElementById('messagesContainer');
    const messageDiv = document.createElement('div');
    messageDiv.className = 'message bot-message';
    messageDiv.style.maxWidth = '100%';
    messageDiv.innerHTML = `
        <div class="bot-avatar">
            <i data-lucide="file-text"></i>
        </div>
        <div class="message-content" style="max-width: 650px;">
            <div class="agent-badge">Document Agent</div>
            <div style="background: linear-gradient(135deg, #d1fae5, #a7f3d0); border: 2px solid #10b981; border-radius: 12px; padding: 1.5rem; margin-bottom: 0.5rem;">
                <div style="display: flex; align-items: center; gap: 1rem; margin-bottom: 1.25rem;">
                    <div style="width: 48px; height: 48px; background: #10b981; border-radius: 12px; display: flex; align-items: center; justify-content: center; font-size: 1.75rem; flex-shrink: 0;">
                        ✅
                    </div>
                    <div style="flex: 1;">
                        <div style="font-weight: 800; font-size: 1.125rem; color: #065f46; margin-bottom: 0.25rem;">Document Ready!</div>
                        <div style="font-size: 0.875rem; color: #047857; word-break: break-all;">Loan consolidation report generated</div>
                    </div>
                </div>
                <a href="data:application/pdf;base64,${base64Data}" 
                   download="${filename}"
                   style="display: flex; align-items: center; justify-content: center; gap: 0.75rem; background: linear-gradient(135deg, #FFB81C, #FFA500); color: #1a1a1a; padding: 1rem 1.5rem; border-radius: 10px; text-decoration: none; font-weight: 700; font-size: 1rem; box-shadow: 0 4px 12px rgba(255, 184, 28, 0.4); transition: all 0.2s;"
                   onmouseover="this.style.transform='translateY(-2px)'; this.style.boxShadow='0 6px 16px rgba(255, 184, 28, 0.5)';"
                   onmouseout="this.style.transform='translateY(0)'; this.style.boxShadow='0 4px 12px rgba(255, 184, 28, 0.4)';">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                        <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"></path>
                        <polyline points="7 10 12 15 17 10"></polyline>
                        <line x1="12" y1="15" x2="12" y2="3"></line>
                    </svg>
                    <span>Download PDF Report</span>
                </a>
                <div style="margin-top: 0.75rem; text-align: center; font-size: 0.75rem; color: #047857; opacity: 0.8;">
                    ${filename}
                </div>
            </div>
            <div class="message-time">
                <i data-lucide="clock"></i>
                <span>Just now</span>
            </div>
        </div>
    `;
    container.appendChild(messageDiv);
    scrollToBottom();
    lucide.createIcons();
}

// Handle File Upload
async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    
    try {
        const response = await fetch('/api/upload', {
            method: 'POST',
            body: formData
        });
        
        const data = await response.json();
        
        if (data.success) {
            addSystemMessage(`✅ Uploaded: ${data.filename}`);
            // Automatically send message about upload
            setTimeout(() => {
                document.getElementById('messageInput').value = `I have uploaded my salary slip: ${data.filename}`;
                sendMessage();
            }, 500);
        } else {
            addSystemMessage('Failed to upload file. Please try again.');
        }
    } catch (error) {
        console.error('Error uploading file:', error);
        addSystemMessage('Failed to upload file. Please try again.');
    }
    
    // Reset file input
    event.target.value = '';
}

// Utility Functions
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatMessage(message) {
    // Simple markdown-like formatting
    let formatted = escapeHtml(message);
    
    // Bold: **text**
    formatted = formatted.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // Line breaks
    formatted = formatted.replace(/\n/g, '<br>');
    
    return formatted;
}

function getCurrentTime() {
    const now = new Date();
    return now.toLocaleTimeString('en-US', { 
        hour: '2-digit', 
        minute: '2-digit',
        hour12: true 
    });
}

function scrollToBottom() {
    const container = document.getElementById('messagesContainer');
    container.scrollTop = container.scrollHeight;
}
