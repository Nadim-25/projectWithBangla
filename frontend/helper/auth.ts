import { BASE_URL } from "../settings";

export async function registerUser(data: {
  fullName: string;
  userName: string;
  email: string;
  hashedPassword: string;
  confirmHashedPassword: string;
}) {
  const res = await fetch(`${BASE_URL}/user/register`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  const text = await res.text();

  // Parse — handle both string and array detail (FastAPI 422 uses array)
  let detail: string | undefined;
  try {
    const json = text ? JSON.parse(text) : {};
    if (typeof json.detail === "string") {
      detail = json.detail;
    } else if (Array.isArray(json.detail) && json.detail.length > 0) {
      detail = json.detail.map((e: { msg?: string }) => e.msg).join(", ");
    } else if (json.message) {
      // success path — just return
      if (res.ok) return json;
    }
  } catch {
    throw new Error(`Server error (${res.status}): ${text.slice(0, 120) || "empty response"}`);
  }

  if (!res.ok) {
    throw new Error(detail || `Request failed (${res.status})`);
  }

  return text ? JSON.parse(text) : {};
}
