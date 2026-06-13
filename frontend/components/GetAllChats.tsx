"use client";

import { useEffect, useState } from "react";
import { usePathname } from "next/navigation";
import Link from "next/link";
import { getToken } from "@/helper/tokenHelper";
import { BASE_URL } from "@/settings";

type Chat = {
  chatId: number;
  title: string;
};

export default function GetAllChats() {
  const [chats, setChats] = useState<Chat[]>([]);
  const pathname = usePathname();
  const token = getToken();

  useEffect(() => {
    if (!token) return;

    const loadChats = async () => {
      try {
        const res = await fetch(`${BASE_URL}/history`, {
          headers: {
            Authorization: `Bearer ${token}`,
          },
        });

        const data = await res.json();

        console.log("API response:", data);

        // ✅ FIX HERE
        setChats(Array.isArray(data.chats) ? data.chats : []);
      } catch (err) {
        console.error("Failed to fetch chats", err);
      }
    };

    loadChats();
  }, [pathname, token]);

  return (
    <>
      {chats.map((chat) => {
        const isActive = pathname === `/dashboard/chat/${chat.chatId}`;

        return (
          <Link
            key={chat.chatId}
            href={`/dashboard/chat/${chat.chatId}`}
            className={`block px-2 py-1 rounded hover:bg-muted ${
              isActive ? "bg-muted font-medium" : ""
            }`}
          >
            {chat.title || `Chat ${chat.chatId}`}
          </Link>
        );
      })}
    </>
  );
}
