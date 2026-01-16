// Initialize Lucide Icons
lucide.createIcons();

// DOM Elements
const auditBtn = document.getElementById('auditBtn');
const userInput = document.getElementById('userInput');
const outputContent = document.getElementById('outputContent');
const gaugeFill = document.getElementById('gaugeFill');
const gaugeValue = document.getElementById('gaugeValue');
const confidenceLabel = document.getElementById('confidenceLabel');
const loader = document.getElementById('loader');
const btnText = document.getElementById('btnText');
const btnIcon = document.getElementById('btnIcon');
const copyBtn = document.getElementById('copyBtn');
const downloadBtn = document.getElementById('downloadBtn');

// Configuration
const API_ENDPOINT = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/audit'
    : '/audit'; // Use relative path if deployed

// ============================================
// GAUGE ANIMATION
// ============================================

function setConfidence(percent, animated = true) {
    const circumference = 2 * Math.PI * 42; // 264
    const offset = circumference - (percent / 100 * circumference);
    
    if (animated) {
        // Animate from current position
        gaugeFill.style.transition = 'stroke-dashoffset 2s cubic-bezier(0.4, 0, 0.2, 1)';
    } else {
        gaugeFill.style.transition = 'none';
    }
    
    gaugeFill.style.strokeDashoffset = offset;
    
    // Animate number count
    animateValue(gaugeValue, parseInt(gaugeValue.textContent) || 0, percent, 2000);
    
    // Update confidence label with descriptive text
    updateConfidenceLabel(percent);
}

function animateValue(element, start, end, duration) {
    const range = end - start;
    const increment = range / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
            current = end;
            clearInterval(timer);
        }
        element.textContent = Math.round(current);
    }, 16);
}

function updateConfidenceLabel(percent) {
    let label = '';
    let color = '';
    
    if (percent >= 80) {
        label = 'High Confidence - Models Agree';
        color = '#10b981';
    } else if (percent >= 60) {
        label = 'Moderate Confidence - Some Variance';
        color = '#f59e0b';
    } else if (percent >= 40) {
        label = 'Low Confidence - Significant Uncertainty';
        color = '#ef4444';
    } else {
        label = 'Very Low Confidence - High Risk';
        color = '#dc2626';
    }
    
    confidenceLabel.textContent = label;
    confidenceLabel.style.color = color;
}

// ============================================
// UI STATE MANAGEMENT
// ============================================

function setLoadingState(isLoading) {
    auditBtn.disabled = isLoading;
    
    if (isLoading) {
        btnText.style.display = 'none';
        btnIcon.style.display = 'none';
        loader.style.display = 'block';
    } else {
        btnText.style.display = 'block';
        btnIcon.style.display = 'block';
        loader.style.display = 'none';
    }
}

function showError(message) {
    outputContent.textContent = `╔═══════════════════════════════════════════════════════════════╗
║                         ⚠️  ERROR                            ║
╚═══════════════════════════════════════════════════════════════╝

${message}

Please check:
• API endpoint is running at ${API_ENDPOINT}
• Network connection is stable
• API keys are configured correctly

Try again or contact system administrator.`;
}

// ============================================
// API COMMUNICATION
// ============================================

async function executeAudit() {
    const question = userInput.value.trim();
    
    if (!question) {
        showError('❌ No query entered. Please provide a question for analysis.');
        return;
    }
    
    // Reset UI
    setConfidence(0, false);
    setLoadingState(true);
    
    // Show processing message
    outputContent.textContent = `╔═══════════════════════════════════════════════════════════════╗
║           🔄 MULTI-MODEL AUDIT IN PROGRESS                   ║
╚═══════════════════════════════════════════════════════════════╝

⚡ Initializing secure handshake...
🔒 Establishing encrypted connection...
🤖 Querying GPT-4, Claude, and Gemini...
📊 Cross-validating responses...
🔍 Analyzing confidence metrics...

This may take 10-30 seconds depending on query complexity...`;
    
    try {
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ question: question })
        });
        
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        
        const data = await response.json();
        
        if (!data.success) {
            throw new Error(data.error || 'Unknown error occurred');
        }
        
        const textReport = data.report;
        
        // Display report with typing effect
        await typeText(outputContent, textReport, 5);
        
        // Extract and update confidence score
        extractAndUpdateConfidence(textReport);
        
        // Success feedback
        showNotification('Audit completed successfully!', 'success');
        
    } catch (error) {
        console.error('Audit error:', error);
        showError(`Connection failed: ${error.message}\n\nEndpoint: ${API_ENDPOINT}`);
        setConfidence(0, false);
        confidenceLabel.textContent = 'System Error';
        confidenceLabel.style.color = '#ef4444';
        
        showNotification('Audit failed. Check console for details.', 'error');
    } finally {
        setLoadingState(false);
    }
}

// ============================================
// TEXT EFFECTS
// ============================================

async function typeText(element, text, speed = 10) {
    // For long reports, show immediately instead of typing
    if (text.length > 500) {
        element.textContent = text;
        return;
    }
    
    element.textContent = '';
    for (let i = 0; i < text.length; i++) {
        element.textContent += text.charAt(i);
        if (i % 10 === 0) {
            await new Promise(resolve => setTimeout(resolve, speed));
        }
    }
}

// ============================================
// CONFIDENCE EXTRACTION
// ============================================

function extractAndUpdateConfidence(report) {
    // Try multiple patterns to extract confidence
    const patterns = [
        /Average Confidence:\s*(\d+\.?\d*)%/i,
        /Combined Consensus Confidence:\s*(\d+)%/i,
        /Consensus:\s*(\d+)%/i,
        /Confidence.*?(\d+)%/i
    ];
    
    for (const pattern of patterns) {
        const match = report.match(pattern);
        if (match && match[1]) {
            const confidence = parseFloat(match[1]);
            setConfidence(Math.round(confidence), true);
            return;
        }
    }
    
    // If no confidence found, show warning
    console.warn('Could not extract confidence from report');
    confidenceLabel.textContent = 'Confidence score unavailable';
    confidenceLabel.style.color = '#64748b';
}

// ============================================
// COPY & DOWNLOAD FUNCTIONALITY
// ============================================

function copyToClipboard() {
    const text = outputContent.textContent;
    
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Report copied to clipboard!', 'success');
    }).catch(err => {
        console.error('Copy failed:', err);
        showNotification('Copy failed. Please select and copy manually.', 'error');
    });
}

function downloadReport() {
    const text = outputContent.textContent;
    const blob = new Blob([text], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    
    const timestamp = new Date().toISOString().replace(/[:.]/g, '-').slice(0, -5);
    a.href = url;
    a.download = `AuditTrail_Report_${timestamp}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    
    showNotification('Report downloaded successfully!', 'success');
}

// ============================================
// NOTIFICATIONS
// ============================================

function showNotification(message, type = 'info') {
    // Create notification element
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.textContent = message;
    
    // Style based on type
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        info: '#3b82f6'
    };
    
    notification.style.cssText = `
        position: fixed;
        bottom: 2rem;
        right: 2rem;
        padding: 1rem 1.5rem;
        background: rgba(0, 0, 0, 0.9);
        border: 1px solid ${colors[type]};
        border-radius: 8px;
        color: white;
        font-size: 0.9rem;
        box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
        z-index: 1000;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    // Auto remove after 3 seconds
    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 300);
    }, 3000);
}

// Add CSS for notification animations
const style = document.createElement('style');
style.textContent = `
    @keyframes slideIn {
        from {
            transform: translateX(400px);
            opacity: 0;
        }
        to {
            transform: translateX(0);
            opacity: 1;
        }
    }
    
    @keyframes slideOut {
        from {
            transform: translateX(0);
            opacity: 1;
        }
        to {
            transform: translateX(400px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// ============================================
// EVENT LISTENERS
// ============================================

auditBtn.addEventListener('click', executeAudit);

copyBtn.addEventListener('click', copyToClipboard);

downloadBtn.addEventListener('click', downloadReport);

// Allow Enter key to submit (with Shift+Enter for new line)
userInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        executeAudit();
    }
});

// Auto-resize textarea
userInput.addEventListener('input', () => {
    userInput.style.height = 'auto';
    userInput.style.height = Math.min(userInput.scrollHeight, 200) + 'px';
});

// ============================================
// INITIALIZATION
// ============================================

window.addEventListener('load', () => {
    // Initial gauge setup
    setConfidence(0, false);
    
    // Reinitialize icons after DOM manipulation
    lucide.createIcons();
    
    console.log('🌊 AuditTrail Ocean Theme Loaded');
    console.log('📡 API Endpoint:', API_ENDPOINT);
});

// ============================================
// KEYBOARD SHORTCUTS
// ============================================

document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to execute audit
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        executeAudit();
    }
    
    // Ctrl/Cmd + K to clear input
    if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
        e.preventDefault();
        userInput.value = '';
        userInput.focus();
    }
});

// ============================================
// EXAMPLE QUERIES (for demo)
// ============================================

const exampleQueries = [
    "I have pain in my toe with burning sensation and redness",
    "Explain the concept of recursion in programming",
    "What are the legal requirements for starting a business?",
    "Calculate the derivative of x^3 + 2x^2 - 5x + 7",
    "Is free will compatible with determinism?"
];

// Add example button (optional - uncomment if needed)
/*
const examplesBtn = document.createElement('button');
examplesBtn.textContent = 'Load Example';
examplesBtn.className = 'icon-button';
examplesBtn.onclick = () => {
    const randomQuery = exampleQueries[Math.floor(Math.random() * exampleQueries.length)];
    userInput.value = randomQuery;
    showNotification('Example query loaded!', 'info');
};
document.querySelector('.input-footer').prepend(examplesBtn);
*/