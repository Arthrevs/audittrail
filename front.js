async function scanCode() {
    const reportDiv = document.getElementById('report-output');
    const question = document.getElementById('user-input').value;
    
    reportDiv.textContent = "Analyzing across multi-model consensus...";

    try {
        const response = await fetch('https://audittrail.onrender.com/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: question
        });

        // CRITICAL: Get response as text, NOT as json
        const result = await response.text(); 
        
        // Display the professional report
        reportDiv.textContent = result; 
    } catch (error) {
        reportDiv.textContent = "Error connecting to AuditTrail Core: " + error.message;
    }
}