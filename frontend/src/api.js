const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

export const getBuilds = async () => {
  const res = await fetch(`${API_URL}/builds`);
  if (!res.ok) throw new Error("Failed to fetch builds");
  return res.json();
};

export const getBuild = async (id) => {
  const res = await fetch(`${API_URL}/builds/${id}`);
  if (!res.ok) throw new Error("Failed to fetch build detail");
  return res.json();
};

export const submitBuild = async (payload) => {
  const res = await fetch(`${API_URL}/builds`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error("Failed to submit build");
  return res.json();
};
