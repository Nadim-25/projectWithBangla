"use client";

import { MessageSquare, LogOut } from "lucide-react";

import Link from "next/link";

import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarHeader,
} from "@/components/ui/sidebar";

import { Button } from "./ui/button";

import { ScrollArea } from "./ui/scroll-area";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import GetAllChats from "./GetAllChats";
import { useAuth } from "@/context/AuthContext";

export function AppSidebarFront() {
  const { user, logout } = useAuth();

  const initials =
    user?.fullName
      ?.split(" ")
      .map((n: string) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() ?? "U";
  return (
    <Sidebar collapsible="offcanvas" className="border-r">
      {/* HEADER */}
      <SidebarHeader />
      <div className="flex justify-center 2xl">ChatBot</div>
      {/* CONTENT */}
      <SidebarContent>
        {user?.role == "admin" && (
          <Link href="/admin-dashboard" className="ml-4 mt-3">
            Go to Admin Dashboard
          </Link>
        )}
        <ScrollArea className="h-[calc(100vh-120px)] px-2 mt-5">
          {/* NEW CHAT */}
          <Link
            href="/dashboard/ask-question"
            className="mb-4 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <MessageSquare className="h-4 w-4" />
            New Chat
          </Link>
          <div className="mb-1 font-bold">Recent Chat</div>
          {/* CHAT LIST */}
          <GetAllChats />
        </ScrollArea>
      </SidebarContent>

      {/* FOOTER */}
      <SidebarFooter className="border-t p-3">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2 min-w-0">
            <Avatar>
              <AvatarFallback>{initials}</AvatarFallback>
            </Avatar>

            <div className="min-w-0">
              <p className="text-sm font-medium truncate">
                {user?.fullName ?? "User"}
              </p>
              <p className="text-xs text-muted-foreground capitalize">
                {user?.role ?? ""}
              </p>
            </div>
          </div>

          <Button
            variant="ghost"
            size="icon"
            onClick={logout}
            className="cursor-pointer shrink-0 hover:bg-red-100 hover:text-red-600 transition-colors"
          >
            <LogOut className="h-4 w-4" />
          </Button>
        </div>
      </SidebarFooter>
    </Sidebar>
  );
}
