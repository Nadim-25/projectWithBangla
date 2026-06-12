"use client";

import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import { getChatById } from "@/helper/tokenHelper";
import SendMessages from "@/components/SendMessages";

type Message = {
  question: string;
  answer: string;
};

export default function ChatPage() {
  const params = useParams();
  const chatId = Number(params?.id);

  const [messages, setMessages] = useState<Message[]>([]);

  useEffect(() => {
    window.scrollTo(0, document.body.scrollHeight);
  }, [messages]);

  useEffect(() => {
    if (!chatId) return;

    const load = async () => {
      const res = await getChatById(chatId);

      setMessages(Array.isArray(res.messages) ? res.messages : []);
    };

    load();
  }, [chatId]);

  // ✅ ADD THIS
  const addMessage = (msg: Message) => {
    setMessages((prev) => [...prev, msg]);
  };

  return (
    <div>
      {messages.map((m, i) => (
        <div key={i}>
          <p className="ml-6 bg-amber-100">{m.question}</p>
          <p>{m.answer}</p>
        </div>
      ))}

      <div className="mt-5 border-4 border-amber-300">
        {/* ✅ PASS CALLBACK */}
        <SendMessages chatId={chatId} onNewMessage={addMessage} />
      </div>
    </div>
  );
}
