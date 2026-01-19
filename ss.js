async function logAudit(event, context = {}) {
    await fetch("/api/audit", {
        method: "POST",
        headers: {
            "Content-Type": "application/json"
        },
        body: JSON.stringify({
            actor: "anonymous",
            event,
            context
        })
    });
}

// Example call
logAudit("PAGE_LOADED", {
    page: "home"
});