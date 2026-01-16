// Initialize Lucide icons
lucide.createIcons(); 

// DOM Element References
const auditBtn = document.getElementById('auditBtn');
const userInput = document.getElementById('userInput');
const outputContent = document.getElementById('outputContent');
const gaugeFill = document.getElementById('gaugeFill');
const gaugeValue = document.getElementById('gaugeValue');
const loader = document.getElementById('loader');
const btnText = document.getElementById('btnText');

/**
 * Updates the SVG circular meter based on the consensus score
 * @param {number} percent - The confidence percentage (0-100)
 */
function setConfidence(percent) {
    const circumference = 2 * Math.PI * 45; // Approx 282.7 based on r=45
    const offset = circumference - (percent / 100 * circumference);
    
    // Apply stroke-dashoffset for the animation effect
    gaugeFill.style.strokeDashoffset = offset;
    gaugeValue.innerText = `${percent}%`;

    // Visual feedback color-coding
    if (percent < 50) {
        gaugeFill.style.stroke = "#ef4444"; // High Risk (Red)
    } else if (percent < 80) {
        gaugeFill.style.stroke = "#f59e0b"; // Medium Certainty (Amber)
    } else {
        gaugeFill.style.stroke = "#3b82f6"; // High Consensus (Blue)
    }
}

/**
 * Executes the cross-model audit via the FastAPI backend
 */
auditBtn.addEventListener('click', async () => {
    const question = userInput.value.trim();
    if (!question) return;

    // Reset UI state to processing mode
    setConfidence(0);
    outputContent.innerText = ">> INITIALIZING SECURE HANDSHAKE...\n>> ACCESSING MULTI-MODEL CORE...\n>> COMPARING GPT-4 & CEREBRAS PERSPECTIVES...";
    btnText.style.display = "none";
    loader.style.display = "block";
    auditBtn.disabled = true;

    try {
        // PRODUCTION FIX: Send raw text/plain string to prevent 422 errors
        const response = await fetch('https://audittrail.onrender.com/audit', {
            method: 'POST',
            headers: { 
                'Content-Type': 'text/plain' 
            },
            body: question // DO NOT use JSON.stringify here
        });

        if (!response.ok) {
            throw new Error(`Server returned status ${response.status}`);
        }

        const textReport = await response.text();
        
        // Render the report in the terminal container
        outputContent.innerText = textReport;

        // Improved Regex to extract score from formatted text:
        // "Combined Consensus Confidence: 85%"
        const match = textReport.match(/Combined Consensus Confidence:\s*(\d+)/); 
        if (match && match[1]) {
            setConfidence(parseInt(match[1]));
        }

    } catch (error) {
        console.error("AuditTrail Connection Error:", error);
        outputContent.innerText = "CRITICAL ERROR: Connection to AuditTrail Core failed. Verify Render service status.";
    } finally {
        // Restore UI state
        btnText.style.display = "block";
        loader.style.display = "none";
        auditBtn.disabled = false;
    }
});

/**
 * Copy Functionality for Audit Reports
 */
document.getElementById('copyBtn').addEventListener('click', () => {
    if (!outputContent.innerText || outputContent.innerText.includes("INITIALIZING")) return;
    
    navigator.clipboard.writeText(outputContent.innerText).then(() => {
        alert("Unified Audit Report copied to clipboard.");
    }).catch(err => {
        console.error("Copy failed:", err);
    });
});