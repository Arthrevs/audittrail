async function scanCode() {
    const reportDiv = document.getElementById('report-output');
    const bar = document.getElementById('confidence-bar');
    const question = document.getElementById('user-input').value;

    try {
        const response = await fetch('https://audittrail.onrender.com/audit', {
            method: 'POST',
            body: question
        });

        const resultText = await response.text();
        
        // Use Regex to find the "Consensus Confidence: XX.X%" in the text
        const match = resultText.match(/Consensus Confidence: ([\d.]+)%/);
        if (match) {
            const score = match[1];
            bar.style.width = score + "%";
            bar.textContent = "Consensus Confidence: " + score + "%";
            
            // Optional: Change color based on score
            bar.style.backgroundColor = score < 50 ? "#dc3545" : "#28a745"; 
        }

        reportDiv.textContent = resultText;
    } catch (error) {
        reportDiv.textContent = "Error: " + error.message;
    }
}