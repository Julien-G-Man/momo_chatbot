export async function pingHealth() {
  try {
    const response = await fetch(`${import.meta.env.VITE_BASE_API_URL}/health`);
    if (!response.ok) throw new Error("Health check failed");
    console.log("Flask Backend is live");
  } catch (err) {
    console.error("Health ping error:", err);
  }
}
