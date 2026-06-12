"use client";

import { AppSidebarFront } from "@/components/apps-sidebar-front";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { useAuth } from "@/context/AuthContext";
import { ChevronDown, Menu } from "lucide-react";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

import { useRouter } from "next/navigation";
import LogoutButton from "@/components/LogoutButtons";

export default function DashboardLayoutFront({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user } = useAuth();
  const router = useRouter();

  return (
    <SidebarProvider defaultOpen={true}>
      <div className="relative flex h-screen w-full overflow-hidden bg-background">
        {/* SIDEBAR */}
        <AppSidebarFront />

        {/* FLOATING TRIGGER */}
        <div className="absolute left-3 top-3 z-50">
          <SidebarTrigger>
            <Menu className="h-5 w-5" />
          </SidebarTrigger>
        </div>

        {/* MAIN AREA */}
        <div className="flex flex-1 flex-col">
          {/* TOPBAR */}
          <header className="flex h-14 items-center justify-between border-b px-4 sm:px-16">
            {/* LEFT */}
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-lg font-semibold truncate max-w-[140px] sm:max-w-none">IDLC Finance PLC</h1>
            </div>

            {/* RIGHT */}
            <div className="flex items-center gap-4">
              {/* USER DROPDOWN */}
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-1 text-sm font-medium hover:text-primary outline-none max-w-[100px] sm:max-w-none">
                    <span className="truncate">{user?.fullName}</span>

                    <ChevronDown className="h-4 w-4" />
                  </button>
                </DropdownMenuTrigger>

                <DropdownMenuContent align="end" className="w-52">
                  <DropdownMenuItem
                    onClick={() => router.push("/dashboard/profile")}
                  >
                    Profile
                  </DropdownMenuItem>

                  <DropdownMenuItem
                    onClick={() => router.push("/dashboard/change-password")}
                  >
                    Change Password
                  </DropdownMenuItem>

                  <DropdownMenuSeparator />

                  <DropdownMenuItem className="text-red-500 focus:text-red-500">
                    <LogoutButton />
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
              <LogoutButton />
            </div>
          </header>

          {/* CONTENT */}
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
}
