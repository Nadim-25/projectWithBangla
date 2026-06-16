"use client";

import { useEffect, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import Link from "next/link";
import { Trash2 } from "lucide-react";
import { getToken } from "@/helper/tokenHelper";
import { BASE_URL } from "@/settings";

type Chat = {
  chatId: number;
  title: string;
};

export default function GetAllChats({ onLinkClick }: { onLinkClick?: () => void }) {
  const [chats, setChats] = useState<Chat[]>([]);
  const pathname = usePathname();
  const router = useRouter();
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
        setChats(Array.isArray(data.chats) ? data.chats : []);
      } catch (err) {
        console.error("Failed to fetch chats", err);
      }
    };

    loadChats();
  }, [pathname, token]);

  const handleDelete = async (e: React.MouseEvent, chatId: number) => {
    e.preventDefault();
    e.stopPropagation();

    try {
      const res = await fetch(`${BASE_URL}/chat/${chatId}`, {
        method: "DELETE",
        headers: {
          Authorization: `Bearer ${token}`,
        },
      });

      if (!res.ok) return;

      setChats((prev) => prev.filter((c) => c.chatId !== chatId));

      if (pathname === `/dashboard/chat/${chatId}`) {
        router.push("/dashboard/ask-question");
      }
    } catch (err) {
      console.error("Failed to delete chat", err);
    }
  };

  return (
    <>
      {chats.map((chat) => {
        const isActive = pathname === `/dashboard/chat/${chat.chatId}`;

        return (
          <div key={chat.chatId} className="group relative">
            <Link
              href={`/dashboard/chat/${chat.chatId}`}
              onClick={onLinkClick}
              className={`flex items-center px-2 py-1 rounded hover:bg-muted pr-8 ${
                isActive ? "bg-muted font-medium" : ""
              }`}
            >
              <span className="truncate">{chat.title || `Chat ${chat.chatId}`}</span>
            </Link>
            <button
              onClick={(e) => handleDelete(e, chat.chatId)}
              className="absolute right-[12px] top-1/2 -translate-y-1/2 opacity-0 group-hover:opacity-100 p-1 rounded hover:bg-red-100 text-red-500 hover:text-red-600 transition-opacity"
              aria-label="Delete chat"
            >
              <Trash2 className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </>
  );
}
