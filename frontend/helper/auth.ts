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

  const result = await res.json();

  if (!res.ok) {
    throw new Error(result.detail || "Registration failed");
  }

  return result;
}
