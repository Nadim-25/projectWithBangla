"use client";

import { AppSidebar } from "@/components/AppSidebarBack";
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { Menu, ChevronDown } from "lucide-react";
import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";

import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
  DropdownMenuSeparator,
} from "@/components/ui/dropdown-menu";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { user, logout } = useAuth();
  const router = useRouter();
  return (
    <SidebarProvider defaultOpen={true}>
      <div className="relative flex h-screen w-full overflow-hidden bg-background">
        {/* SIDEBAR */}
        <AppSidebar />

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
            <div className="flex items-center gap-2">
              <h1 className="text-sm sm:text-lg font-semibold truncate max-w-[140px] sm:max-w-none">
                IDLC Finance PLC
              </h1>
            </div>

            <div className="flex items-center gap-4">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <button className="flex items-center gap-1 text-sm font-medium hover:text-primary outline-none">
                    <span className="max-w-[100px] sm:max-w-none truncate">{user?.fullName}</span>
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

                  <DropdownMenuItem
                    onClick={logout}
                    className="text-red-500 focus:text-red-500 cursor-pointer"
                  >
                    Logout
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </header>

          {/* CONTENT */}
          <main className="flex-1 overflow-auto p-6">{children}</main>
        </div>
      </div>
    </SidebarProvider>
  );
}
