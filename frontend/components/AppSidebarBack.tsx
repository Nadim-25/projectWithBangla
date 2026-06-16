"use client";

import {
  LogOut,
  Upload,
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
  useSidebar,
} from "@/components/ui/sidebar";

import { Button } from "./ui/button";

import { ScrollArea } from "./ui/scroll-area";

import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { useAuth } from "@/context/AuthContext";
import AddUserDialog from "./add-user-dialog";

export function AppSidebar() {
  const { user, logout } = useAuth();
  const { setOpenMobile, isMobile } = useSidebar();

  const closeOnMobile = () => {
    if (isMobile) setOpenMobile(false);
  };

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
      <Link className="flex justify-center 2xl" href="/admin-dashboard">
        ChatBot
      </Link>
      {/* CONTENT */}
      <SidebarContent>
        <ScrollArea className="h-[calc(100vh-120px)] px-2 mt-5">
          <Link
            href="/admin-dashboard/upload"
            onClick={closeOnMobile}
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <Upload className="h-4 w-4" />
            Upload File
          </Link>
          <AddUserDialog />

          <Link
            href="/dashboard"
            onClick={closeOnMobile}
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <LayoutDashboard className="h-4 w-4" />
            User Dashboard
          </Link>
          <Link
            href="/admin-dashboard/users"
            onClick={closeOnMobile}
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <User2Icon className="h-4 w-4" />
            All Users
          </Link>
          <Link
            href="/admin-dashboard/documents"
            onClick={closeOnMobile}
            className="mb-2 flex items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted"
          >
            <FileText className="h-4 w-4" />
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
