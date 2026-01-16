// ============================================
// INITIALIZATION
// ============================================
lucide.createIcons();

// DOM Elements
const auditBtn = document.getElementById('auditBtn');
const userInput = document.getElementById('userInput');
const outputContent = document.getElementById('outputContent');
const gaugeFill = document.getElementById('gaugeFill');
const gaugeValue = document.getElementById('gaugeValue');
const loader = document.getElementById('loader');
const btnText = document.getElementById('btnText');
const copyBtn = document.getElementById('copyBtn');

// ============================================
// CONFIGURATION
// ============================================
// CRITICAL FIX: Point to the live Render backend
const API_ENDPOINT = 'https://audittrail.onrender.com/audit';

// ============================================
// GAUGE ANIMATION
// ============================================
function setConfidence(percent) {
    const circumference = 2 * Math.PI * 45; // ~282.7
    const offset = circumference - (percent / 100 * circumference);
    
    gaugeFill.style.transition = 'stroke-dashoffset 1.0s ease-out, stroke 0.5s ease';
    gaugeFill.style.strokeDashoffset = offset;
    gaugeValue.innerText = `${percent}%`;

    // Visual feedback colors
    if (percent < 50) gaugeFill.style.stroke = "#ef4444"; // Red
    else if (percent < 80) gaugeFill.style.stroke = "#f59e0b"; // Amber
    else gaugeFill.style.stroke = "#3b82f6"; // Blue
}

// ============================================
// AUDIT LOGIC
// ============================================
auditBtn.addEventListener('click', async () => {
    const question = userInput.value.trim();
    if (!question) return;

    // 1. Reset UI State
    setConfidence(0);
    outputContent.innerText = ">> INITIALIZING SECURE HANDSHAKE...\n>> ACCESSING MULTI-MODEL CORE...";
    btnText.style.display = "none";
    loader.style.display = "block";
    auditBtn.disabled = true;

    try {
        // 2. Fetch from Render (FIX: Sending JSON)
        const response = await fetch(API_ENDPOINT, {
            method: 'POST',
            headers: { 
                'Content-Type': 'application/json',  // Fixed: JSON
                'Accept': 'application/json'
            },
            body: JSON.stringify({ question: question }) // Fixed: JSON Body
        });

        if (!response.ok) {
            throw new Error(`Server returned status: ${response.status}`);
        }

        // 3. Parse JSON Response (FIX: Handling JSON)
        const data = await response.json();
        
        // The backend returns { "report": "..." }
        if (data.report) {
            outputContent.innerText = data.report;

            // Extract confidence score from the report text
            const match = data.report.match(/Combined Consensus Confidence:\s*(\d+)%/) ||
                          data.report.match(/Average Confidence:\s*(\d+)%/);
            
            if (match && match[1]) {
                setConfidence(parseInt(match[1]));
            }
        } else {
            throw new Error("Invalid response format.");
        }

    } catch (error) {
        console.error(error);
        outputContent.innerText = `CRITICAL ERROR: Could not connect to AuditTrail Core.\n\nDetails: ${error.message}\n\nNote: The server might be waking up. Please try again in 30 seconds.`;
        setConfidence(0);
    } finally {
        // 4. Restore UI
        btnText.style.display = "block";
        loader.style.display = "none";
        auditBtn.disabled = false;
    }
});

// ============================================
// UTILITIES
// ============================================
if (copyBtn) {
    copyBtn.addEventListener('click', () => {
        navigator.clipboard.writeText(outputContent.innerText)
            .then(() => alert("Report copied to clipboard."))
            .catch(() => alert("Failed to copy."));
    });
}