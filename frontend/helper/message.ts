import { BASE_URL } from "@/settings";
import { getToken } from "./tokenHelper";

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
    throw new Error("Failed to send message");
  }

  return res.json(); // ✅ MUST RETURN
}
