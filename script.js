// Initialize Lucide Icons
lucide.createIcons();

// ============================================
// DOM ELEMENTS
// ============================================
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

// ============================================
// Configuration
const API_ENDPOINT = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/audit'
    : 'https://audittrail.onrender.com/audit'; // Correct absolute URL for Render

// ============================================
// GAUGE ANIMATION LOGIC
// ============================================
function setConfidence(percent, animated = true) {
    // Circumference based on r=42 in HTML (2 * pi * 42 ≈ 264)
    const circumference = 264; 
    const offset = circumference - (percent / 100 * circumference);
    
    if (animated) {
        gaugeFill.style.transition = 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s ease';
    } else {
        gaugeFill.style.transition = 'none';
    }
    
    gaugeFill.style.strokeDashoffset = offset;
    
    // Animate the number counter
    animateValue(gaugeValue, parseInt(gaugeValue.textContent) || 0, percent, 1500);
    
    // Update color and label
    updateConfidenceVisuals(percent);
}

function animateValue(element, start, end, duration) {
    let startTimestamp = null;
    const step = (timestamp) => {
        if (!startTimestamp) startTimestamp = timestamp;
        const progress = Math.min((timestamp - startTimestamp) / duration, 1);
        element.textContent = Math.floor(progress * (end - start) + start);
        if (progress < 1) {
            window.requestAnimationFrame(step);
        }
    };
    window.requestAnimationFrame(step);
}

function updateConfidenceVisuals(percent) {
    let label = '';
    let color = '';
    
    if (percent >= 80) {
        label = 'High Confidence • Low Risk';
        color = '#10b981'; // Green
    } else if (percent >= 50) {
        label = 'Moderate Confidence • Verify';
        color = '#f59e0b'; // Amber
    } else {
        label = 'Low Confidence • High Risk';
        color = '#ef4444'; // Red
    }
    
    confidenceLabel.textContent = label;
    confidenceLabel.style.color = color;
    gaugeFill.style.stroke = color;
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

// ============================================
// API COMMUNICATION
// ============================================
async function executeAudit() {
    const question = userInput.value.trim();
    
    if (!question) {
        showNotification('Please enter a query first.', 'info');
        return;
    }

    // Reset UI
    setConfidence(0, false);
    setLoadingState(true);
    outputContent.textContent = ">> INITIALIZING SECURE HANDSHAKE...\n>> CONNECTING TO MULTI-MODEL CORE...\n>> ANALYZING RISK VECTORS...";

    try {
        // MATCHING YOUR PYTHON BACKEND: Sending JSON
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json'
            },
            body: JSON.stringify({ question: question }) 
        });

        if (!response.ok) {
            throw new Error(`Server Status: ${response.status}`);
        }

        const data = await response.json();

        // The Python backend returns { "report": "...", "success": true }
        if (data.report) {
            // 1. Display the Text Report
            outputContent.textContent = data.report;
            
            // 2. Extract Confidence Score using Regex
            // Matches "Average Confidence: 85%" from your Python formatter
            const match = data.report.match(/Average Confidence:\s*(\d+)/);
            if (match && match[1]) {
                setConfidence(parseInt(match[1]));
            }
            
            showNotification('Audit Completed Successfully', 'success');
        } else {
            throw new Error('Invalid response format');
        }

    } catch (error) {
        console.error("Audit Error:", error);
        outputContent.textContent = `CRITICAL ERROR: Connection Failed.\nDetails: ${error.message}\n\nEnsure Backend is running at: ${API_ENDPOINT}`;
        showNotification('Audit Failed. See terminal for details.', 'error');
    } finally {
        setLoadingState(false);
    }
}

// ============================================
// COPY & DOWNLOAD UTILITIES
// ============================================
copyBtn.addEventListener('click', () => {
    navigator.clipboard.writeText(outputContent.textContent)
        .then(() => showNotification('Report copied to clipboard', 'success'))
        .catch(() => showNotification('Failed to copy', 'error'));
});

downloadBtn.addEventListener('click', () => {
    const blob = new Blob([outputContent.textContent], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `AuditTrail_Report_${Date.now()}.txt`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
});

// ============================================
// TOAST NOTIFICATION SYSTEM
// ============================================
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const colors = { success: '#10b981', error: '#ef4444', info: '#3b82f6' };
    
    notification.style.cssText = `
        position: fixed; bottom: 20px; right: 20px;
        background: rgba(15, 23, 42, 0.9); border-left: 4px solid ${colors[type]};
        color: white; padding: 12px 24px; border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 1000;
        font-family: 'Inter', sans-serif; font-size: 0.9rem;
        animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 280);
    }, 3000);
}

// Add animation styles dynamically
const styleSheet = document.createElement("style");
styleSheet.innerText = `
@keyframes slideIn { from { transform: translateX(100%); opacity: 0; } to { transform: translateX(0); opacity: 1; } }
@keyframes slideOut { from { transform: translateX(0); opacity: 1; } to { transform: translateX(100%); opacity: 0; } }
`;
document.head.appendChild(styleSheet);

// ============================================
// EVENT LISTENERS
// ============================================
auditBtn.addEventListener('click', executeAudit);

// Allow "Ctrl + Enter" to submit
userInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        executeAudit();
    }
});