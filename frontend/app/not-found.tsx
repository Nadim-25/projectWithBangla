"use client";

import { useAuth } from "@/context/AuthContext";
import { useRouter } from "next/navigation";
import { ArrowLeft, Home, LogIn } from "lucide-react";

export default function NotFound() {
  const { user, loading } = useAuth();
  const router = useRouter();

  const primaryHref =
    user?.role === "admin" ? "/admin-dashboard" : user ? "/dashboard" : "/login";

  const primaryLabel = user ? "Back to Dashboard" : "Back to Login";
  const PrimaryIcon = user ? Home : LogIn;

  return (
    <div className="min-h-screen flex flex-col items-center justify-center bg-background px-4 text-center">

      {/* 404 number */}
      <h1 className="text-[120px] sm:text-[160px] font-extrabold leading-none bg-gradient-to-br from-orange-400 to-pink-500 bg-clip-text text-transparent select-none">
        404
      </h1>

      {/* Heading */}
      <h2 className="mt-2 text-2xl sm:text-3xl font-bold">Page not found</h2>

      {/* Description */}
      <p className="mt-3 max-w-sm text-sm text-muted-foreground">
        The page you are looking for doesn&apos;t exist or has been moved.
      </p>

      {/* Buttons */}
      {!loading && (
        <div className="mt-8 flex flex-col sm:flex-row items-center gap-3">
          {/* Go back */}
          <button
            onClick={() => router.back()}
            className="flex items-center gap-2 rounded-lg border px-5 py-2.5 text-sm font-medium transition-colors hover:bg-muted"
          >
            <ArrowLeft className="h-4 w-4" />
            Go Back
          </button>

          {/* Primary action */}
          <button
            onClick={() => router.push(primaryHref)}
            className="flex items-center gap-2 rounded-lg bg-gradient-to-br from-orange-400 to-pink-500 px-5 py-2.5 text-sm font-medium text-white shadow-sm transition-opacity hover:opacity-90"
          >
            <PrimaryIcon className="h-4 w-4" />
            {primaryLabel}
          </button>
        </div>
      )}
    </div>
  );
}
