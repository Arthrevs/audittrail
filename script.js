lucide.createIcons();

const auditBtn = document.getElementById('auditBtn');
const userInput = document.getElementById('userInput');
const outputContent = document.getElementById('outputContent');
const gaugeFill = document.getElementById('gaugeFill');
const gaugeValue = document.getElementById('gaugeValue');
const loader = document.getElementById('loader');
const btnText = document.getElementById('btnText');

// Function to update the circle meter
function setConfidence(percent) {
    const circumference = 2 * Math.PI * 45; // 282.7
    const offset = circumference - (percent / 100 * circumference);
    gaugeFill.style.strokeDashoffset = offset;
    gaugeValue.innerText = `${percent}%`;

    // Visual feedback based on score
    if (percent < 50) gaugeFill.style.stroke = "#ef4444"; // Red
    else if (percent < 80) gaugeFill.style.stroke = "#f59e0b"; // Amber
    else gaugeFill.style.stroke = "#3b82f6"; // Blue
}

auditBtn.addEventListener('click', async () => {
    const question = userInput.value.trim();
    if (!question) return;

    // Reset UI state
    setConfidence(0);
    outputContent.innerText = ">> INITIALIZING SECURE HANDSHAKE...\n>> ACCESSING MULTI-MODEL CORE...";
    btnText.style.display = "none";
    loader.style.display = "block";
    auditBtn.disabled = true;

    try {
        const response = await fetch('http://127.0.0.1:8000/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: question
        });

        const textReport = await response.text();
        outputContent.innerText = textReport;

        // Extract confidence using Regex from your backend's format:
        // "Combined Consensus Confidence: 85%"
        const match = textReport.match(/Combined Consensus Confidence:\s*(\d+)%/);
        if (match && match[1]) {
            setConfidence(parseInt(match[1]));
        }

    } catch (error) {
        outputContent.innerText = "CRITICAL ERROR: Could not connect to AuditTrail Core.";
    } finally {
        btnText.style.display = "block";
        loader.style.display = "none";
        auditBtn.disabled = false;
    }
});

// Copy Report Function
document.getElementById('copyBtn').addEventListener('click', () => {
    navigator.clipboard.writeText(outputContent.innerText);
    alert("Report copied to clipboard.");
});