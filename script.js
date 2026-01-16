// ============================================
// INITIALIZATION
// ============================================
// Initialize Lucide Icons
lucide.createIcons();

// DOM Element References
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
// CONFIGURATION (CRITICAL FIX)
// ============================================
// This logic selects the correct server URL.
// If you are on GitHub Pages, it forces the request to go to Render.
const API_ENDPOINT = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
    ? 'http://127.0.0.1:8000/audit'
    : 'https://audittrail.onrender.com/audit'; 

console.log(`🔌 AuditTrail API connected to: ${API_ENDPOINT}`);

// ============================================
// GAUGE ANIMATION LOGIC
// ============================================
function setConfidence(percent, animated = true) {
    // Circumference calculation for r=42 (2 * PI * 42 ≈ 264)
    // Matches the stroke-dasharray in your CSS
    const circumference = 264; 
    const offset = circumference - (percent / 100 * circumference);
    
    if (animated) {
        // Smooth transition
        gaugeFill.style.transition = 'stroke-dashoffset 1.5s cubic-bezier(0.4, 0, 0.2, 1), stroke 0.5s ease';
    } else {
        gaugeFill.style.transition = 'none';
    }
    
    // Apply the offset to animate the ring
    gaugeFill.style.strokeDashoffset = offset;
    
    // Animate the numeric counter
    animateValue(gaugeValue, parseInt(gaugeValue.textContent) || 0, percent, 1500);
    
    // Update text label and color
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
    
    // Logic for color coding
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
    
    // Apply updates safely
    if (confidenceLabel) {
        confidenceLabel.textContent = label;
        confidenceLabel.style.color = color;
    }
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
// MAIN AUDIT FUNCTION
// ============================================
async function executeAudit() {
    const question = userInput.value.trim();
    
    if (!question) {
        showNotification('Please enter a query first.', 'info');
        return;
    }

    // 1. Reset UI
    setConfidence(0, false);
    setLoadingState(true);
    outputContent.textContent = ">> INITIALIZING DEEP SCAN...\n>> CONNECTING TO RENDER SERVER...\n>> AGGREGATING MULTI-MODEL CONSENSUS...";

    try {
        // 2. Fetch Data (Sending JSON)
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',
                'Accept': 'application/json' 
            },
            body: JSON.stringify({ question: question }) // Matches Python request: dict
        });

        if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
        }

        // 3. Parse JSON Response
        const data = await response.json();

        // 4. Handle Success
        if (data.report) {
            outputContent.textContent = data.report;
            
            // Regex to find "Average Confidence: 85%" or similar patterns
            const match = data.report.match(/Average Confidence:\s*(\d+)/) || 
                          data.report.match(/Combined Consensus Confidence:\s*(\d+)/);
            
            if (match && match[1]) {
                setConfidence(parseInt(match[1]));
            }
            
            showNotification('Audit Completed Successfully', 'success');
        } else {
            throw new Error('Invalid response format received from backend.');
        }

    } catch (error) {
        console.error("Audit Error:", error);
        outputContent.textContent = `CRITICAL CONNECTION ERROR.\n\nDetails: ${error.message}\n\nEndpoint: ${API_ENDPOINT}\n\nPlease ensure the Render server is waking up (it may take 50 seconds on free tier).`;
        showNotification('Connection Failed', 'error');
    } finally {
        setLoadingState(false);
    }
}

// ============================================
// TOOLS: COPY & DOWNLOAD
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
    URL.revokeObjectURL(url);
});

// ============================================
// TOAST NOTIFICATIONS
// ============================================
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    const colors = { success: '#10b981', error: '#ef4444', info: '#3b82f6' };
    
    notification.style.cssText = `
        position: fixed; bottom: 20px; right: 20px;
        background: rgba(15, 23, 42, 0.95); border-left: 4px solid ${colors[type]};
        color: white; padding: 12px 24px; border-radius: 4px;
        box-shadow: 0 4px 12px rgba(0,0,0,0.5); z-index: 9999;
        font-family: 'Inter', sans-serif; font-size: 0.9rem;
        backdrop-filter: blur(5px); animation: slideIn 0.3s ease-out;
    `;
    notification.textContent = message;
    document.body.appendChild(notification);

    setTimeout(() => {
        notification.style.animation = 'slideOut 0.3s ease-in';
        setTimeout(() => notification.remove(), 280);
    }, 3000);
}

// Inject Animation Styles for Toasts
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

// Enable "Ctrl + Enter" to submit
userInput.addEventListener('keydown', (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        executeAudit();
    }
});