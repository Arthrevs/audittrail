async function scanCode() {
    const reportDiv = document.getElementById('report-output');
    const input = document.getElementById('user-input').value;
    
    reportDiv.textContent = "Synthesizing cross-model audit data...";

    try {
        const response = await fetch('https://audittrail.onrender.com/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: input
        });

        // Pull raw text to maintain formatting
        const result = await response.text();
        reportDiv.textContent = result;
    } catch (err) {
        reportDiv.textContent = "CRITICAL ERROR: " + err.message;
    }
}