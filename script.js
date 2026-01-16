lucide.createIcons();

const auditBtn = document.getElementById('auditBtn');
const userInput = document.getElementById('userInput');
const outputContent = document.getElementById('outputContent');
const gaugeCircle = document.getElementById('gaugeCircle');
const percentValue = document.getElementById('percentValue');
const loader = document.getElementById('loader');
const btnText = document.getElementById('btnText');

function updateGauge(percent) {
    const circumference = 282.7;
    const offset = circumference - (percent / 100 * circumference);
    gaugeCircle.style.strokeDashoffset = offset;
    
    // Counter animation for the text
    let current = 0;
    const duration = 2000;
    const startTime = performance.now();

    function animate(time) {
        const elapsed = time - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const value = Math.floor(progress * percent);
        percentValue.innerText = `${value}%`;
        if (progress < 1) requestAnimationFrame(animate);
    }
    requestAnimationFrame(animate);
}

auditBtn.addEventListener('click', async () => {
    const question = userInput.value.trim();
    if (!question) return;

    // UI Reset
    btnText.style.display = 'none';
    loader.style.display = 'block';
    outputContent.innerText = ">> PINGING CORES...\n>> ANALYZING SUBMERGED DATA...";
    updateGauge(0);

    try {
        const response = await fetch('http://127.0.0.1:8000/audit', {
            method: 'POST',
            headers: { 'Content-Type': 'text/plain' },
            body: question
        });

        const data = await response.text();
        outputContent.innerText = data;

        // Extract confidence from your backend response
        const match = data.match(/Combined Consensus Confidence:\s*(\d+)%/);
        if (match) {
            updateGauge(parseInt(match[1]));
        }

    } catch (error) {
        outputContent.innerText = "CRITICAL: SONAR FAILURE. Backend unreachable.";
    } finally {
        btnText.style.display = 'block';
        loader.style.display = 'none';
    }
});