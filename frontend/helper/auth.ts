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
  let result: { message?: string; detail?: string } = {};
  try {
    result = text ? JSON.parse(text) : {};
  } catch {
    throw new Error("Server returned an unexpected response. Please try again.");
  }

  if (!res.ok) {
    throw new Error(result.detail || "Registration failed");
  }

  return result;
}
