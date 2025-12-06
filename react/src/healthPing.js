export async function pingHealth(apiUrl) {
  if (!apiUrl) return;

  try {
    const response = await fetch(`${apiUrl}/health`);
    if (!response.ok) throw new Error(`Health check failed: ${response.status}`);
    console.log("Backend is alive!");
  } catch (err) {
    console.error("Health ping error:", err);
  }
}
