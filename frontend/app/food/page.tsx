// Server-side base URL for the backend API. Set this to your deployed
// backend's HTTPS URL in production (see the root README for details).
const API_URL = process.env.API_URL || "http://localhost:8000";

async function getBackendHealth() {
  try {
    const res = await fetch(`${API_URL}/health`, { cache: "no-store" });
    if (!res.ok) {
      throw new Error(`Backend responded with status ${res.status}`);
    }
    return { ok: true as const, data: await res.json() };
  } catch (error) {
    return {
      ok: false as const,
      message: error instanceof Error ? error.message : "Unknown error",
    };
  }
}

export default async function FoodPage() {
  const health = await getBackendHealth();

  return (
    <main>
      <h1>Food</h1>
      <p>This page confirms the frontend can reach the backend API.</p>

      {health.ok ? (
        <p>
          Backend says: <code>{JSON.stringify(health.data)}</code>
        </p>
      ) : (
        <p>
          Could not reach the backend at <code>{API_URL}/health</code>.
          <br />
          Error: {health.message}
        </p>
      )}
    </main>
  );
}
