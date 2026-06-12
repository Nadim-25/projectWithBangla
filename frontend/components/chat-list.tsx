"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const chats = [
  {
    id: 1,
    title: "FastAPI Authentication",
  },
];

export default function ChatList() {
  const pathname = usePathname();

  return (
    <div className="space-y-1">
      {chats.map((chat) => {
        const isActive = pathname === `/dashboard/chat/${chat.id}`;

        return (
          <Link
            key={chat.id}
            href={`/dashboard/chat/${chat.id}`}
            className={`block rounded-lg px-3 py-2 text-sm transition-colors hover:bg-muted ${
              isActive ? "bg-muted font-medium" : ""
            }`}
          >
            {chat.title}
          </Link>
        );
      })}
    </div>
  );
}
