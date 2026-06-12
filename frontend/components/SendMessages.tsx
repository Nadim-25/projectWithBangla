"use client";

import { sendMessage } from "@/helper/tokenHelper";
import { useState } from "react";

interface UserCardProps {
  chatId: number;
  onNewMessage: (msg: { question: string; answer: string }) => void;
}

export default function SendMessages({ chatId, onNewMessage }: UserCardProps) {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSend = async () => {
    if (!question) return;

    try {
      setLoading(true);

      const res = await sendMessage(question, chatId);

      // ✅ IMPORTANT: update UI instantly
      onNewMessage({
        question,
        answer: res.answer, // make sure backend returns this
      });

      setQuestion("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div>
      <h2 className="mb-5">Ask Me</h2>

      <input
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        placeholder="Ask something..."
      />

      <button onClick={handleSend} disabled={loading}>
        {loading ? "Thinking..." : "Send"}
      </button>
    </div>
  );
}
