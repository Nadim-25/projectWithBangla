import { BASE_URL } from "../settings";

export async function forgotPassword(email: string) {
  const res = await fetch(`${BASE_URL}/user/forgot-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ email }),
  });

  const data = await res.json();

  if (!res.ok) {
    throw new Error(data.detail);
  }

  return data;
}

export async function resetPassword(data: {
  token: string;
  password: string;
  confirmPassword: string;
}) {
  const res = await fetch(`${BASE_URL}/user/reset-password`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(data),
  });

  const result = await res.json();

  if (!res.ok) {
    throw new Error(result.detail);
  }

  return result;
}
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
