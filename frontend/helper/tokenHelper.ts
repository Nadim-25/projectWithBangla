// /lib/chat.ts

import { BASE_URL } from "@/settings";

// const BASE_URL = "http://localhost:8000"; // change if needed

// 🔹 helper to get token
export function getToken() {
  if (typeof document === "undefined") return null;

  const value = `; ${document.cookie}`;
  const parts = value.split(`; token=`);
  if (parts.length === 2) {
    return parts.pop()?.split(";").shift() || null;
  }
  return null;
}

// =========================
// 1. CHAT (send question)
// =========================

export async function sendMessage(question: string, chatId?: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/chat`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify({
      question,
      chatId: chatId || null,
    }),
  });

  if (!res.ok) {
    throw new Error("Failed to send message>>");
  }

  return res.json(); // ✅ MUST RETURN
}

export async function changePassword(data: {
  oldPassword: string;
  newPassword: string;
  confirmNewPassword: string;
}) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/user/change-password`, {
    method: "PUT",
    headers: {
      "Content-Type": "application/json",
      Authorization: `Bearer ${token}`,
    },
    body: JSON.stringify(data),
  });

  const text = await res.text();
  let result: { detail?: string; success?: boolean; message?: string } = {};
  try {
    result = text ? JSON.parse(text) : {};
  } catch {
    throw new Error("Server returned an unexpected response. Please try again.");
  }

  if (!res.ok) {
    throw new Error(result.detail || "Failed to change password");
  }

  return result;
}

export async function getChatById(chatId: number) {
  const res = await fetch(`${BASE_URL}/history/${chatId}`, {
    headers: {
      Authorization: `Bearer ${getToken()}`,
    },
  });

  const data = await res.json();

  console.log("RAW API:", data); // 🔥 DEBUG

  if (!res.ok) {
    throw new Error("Failed to load chat");
  }

  return data;
}
export async function deleteDocument(documentId: number) {
  const token = getToken();

  const res = await fetch(`${BASE_URL}/upload/${documentId}`, {
    method: "DELETE",
    headers: {
      Authorization: `Bearer ${token}`,
    },
  });

  if (!res.ok) {
    const errorData = await res.json();

    throw new Error(errorData.detail || "Failed to delete document");
  }

  return await res.json();
}
