export default async function handler(req, res) {
    if (req.method !== "POST") {
        return res.status(405).json({
            error: "Only POST allowed"
        });
    }

    const {
        actor,
        event,
        context
    } = req.body;

    console.log("ANTIGRAVITY_AUDIT", {
        actor,
        event,
        context,
        time: new Date().toISOString()
    });

    res.status(200).json({
        success: true
    });
}