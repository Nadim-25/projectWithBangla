"use client";

import {
  LogOut,
  Upload,
  UserPlus,
  LayoutDashboard,
  FileText,
  User2Icon,
} from "lucide-react";

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
import { useAuth } from "@/context/AuthContext";

export function AppSidebar() {
  const { user, logout } = useAuth();

  const initials = user?.fullName
    ?.split(" ")
    .map((n: string) => n[0])
    .join("")
    .slice(0, 2)
    .toUpperCase() ?? "U";
  return (
    <Sidebar collapsible="offcanvas" className="border-r">
      {/* HEADER */}
      <SidebarHeader className="flex items-center px-3 py-3">
        {/* <Button variant="ghost" className="flex items-center gap-2">
          <Folder className="h-5 w-5" />
          <span className="font-medium">IDLC</span>
        </Button> */}
      </SidebarHeader>

      {/* CONTENT */}
      <SidebarContent>
        <ScrollArea className="h-[calc(100vh-120px)] px-2 mt-5">
          {/* NEW CHAT */}
          <Link
            href="/admin-dashboard/upload"
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <Upload className="h-4 w-4" />
            Upload File
          </Link>
          <Link
            href="/dashboard"
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <UserPlus className="h-4 w-4" />
            Add User
          </Link>

          <Link
            href="/dashboard"
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <LayoutDashboard className="h-4 w-4" />
            Uer Dashboard
          </Link>
          <Link
            href="/admin-dashboard/users"
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            {/* <LayoutDashboard className="h-4 w-4" /> */}
            <User2Icon />
            All User
          </Link>
          <Link
            href="/admin-dashboard/documents"
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            {/* <LayoutDashboard className="h-4 w-4" /> */}
            <FileText />
            Documents
          </Link>
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
              <p className="text-sm font-medium truncate">{user?.fullName ?? "User"}</p>
              <p className="text-xs text-muted-foreground capitalize">{user?.role ?? ""}</p>
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
