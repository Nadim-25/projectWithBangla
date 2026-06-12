"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function LogoutButton() {
  const router = useRouter();

  useEffect(() => {
    const getCookie = (name: string) => {
      const value = `; ${document.cookie}`;
      const parts = value.split(`; ${name}=`);
      if (parts.length === 2) return parts.pop()?.split(";").shift();
    };

    const token = getCookie("token");
    console.log("Token:", token);
  }, []);

  const logout = () => {
    // ✅ Delete cookie (match attributes used when setting it)
    document.cookie =
      "token=; path=/; expires=Thu, 01 Jan 1970 00:00:00 GMT; SameSite=Lax";

    // Redirect and refresh server state
    router.push("/");
    router.refresh();
  };

  return <button onClick={logout} className="cursor-pointer rounded-md px-3 py-1.5 text-sm transition-colors hover:bg-red-100 hover:text-red-600">Logout</button>;
}
