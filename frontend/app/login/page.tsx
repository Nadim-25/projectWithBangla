"use client";

import { useAuth } from "@/context/AuthContext";
import { useState } from "react";
import { useRouter } from "next/navigation";
import { Mail, Lock } from "lucide-react";
import { BASE_URL } from "@/settings";
import { useFlash } from "@/context/FlashContext";

// ─── JWT decode helper ────────────────────────────────────────────────────────
function getRoleFromToken(token: string): string | null {
  try {
    const base64 = token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/");
    const payload = JSON.parse(atob(base64));
    return payload.role ?? null;
  } catch {
    return null;
  }
}

export default function LoginPage() {
  const { refreshUser } = useAuth();
  const { showFlash } = useFlash();
  const router = useRouter();

  const [email, setEmail] = useState<string>("");
  const [password, setPassword] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const handleLogin = async () => {
    try {
      setLoading(true);
      setError("");

      const controller = new AbortController();
      const timeoutId = setTimeout(() => controller.abort(), 10000);

      let res: Response;
      try {
        res = await fetch(`${BASE_URL}/user/login1`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ email, password }),
          signal: controller.signal,
        });
      } catch (fetchErr) {
        if (fetchErr instanceof DOMException && fetchErr.name === "AbortError") {
          throw new Error("Server is taking too long to respond. Please try again in a moment.");
        }
        throw fetchErr;
      } finally {
        clearTimeout(timeoutId);
      }

      const text = await res.text();
      let data: { detail?: string; access_token?: string; requiresPasswordChange?: boolean; userId?: number } = {};
      try {
        data = text ? JSON.parse(text) : {};
      } catch {
        throw new Error("Server returned an unexpected response. Please try again.");
      }

      if (!res.ok) {
        throw new Error(data.detail || "Login failed");
      }

      // ✅ Store token in cookie
      document.cookie = `token=${data.access_token}; path=/; SameSite=Lax`;

      // ✅ Refresh user context
      try {
        await refreshUser();
      } catch (err) {
        console.warn("refreshUser failed:", err);
      }

      // ✅ Force password change takes priority over everything
      if (data.requiresPasswordChange) {
        router.push("/force-change-password");
        return;
      }

      // ✅ Redirect based on role
      const role = getRoleFromToken(data.access_token ?? "");
      showFlash("Logged in successfully. Welcome back!", "success");
      if (role === "admin") {
        router.push("/admin-dashboard");
      } else {
        router.push("/dashboard");
      }
    } catch (err: unknown) {
      if (err instanceof Error) {
        setError(err.message);
        showFlash(err.message, "error");
      } else {
        setError("Something went wrong");
        showFlash("Something went wrong. Please try again.", "error");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950 px-4">
      <div className="w-full max-w-sm bg-neutral-900 border border-neutral-800 rounded-2xl p-6 shadow-xl">
        {/* Header */}
        <div className="text-center mb-6">
          <h1 className="text-2xl font-semibold text-white">
            Welcome to IDLC ChatBot
          </h1>
          <p className="text-sm text-neutral-400 mt-1">Sign in to continue</p>
        </div>

        {/* Form */}
        <form
          className="space-y-4"
          onSubmit={(e) => {
            e.preventDefault();
            handleLogin();
          }}
        >
          {/* Email */}
          <div>
            {/* <label className="text-sm text-neutral-300">Email</label> */}

            <div className="relative mt-1">
              <Mail
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
              />
              <input
                type="email"
                required
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-white/20"
                placeholder="Enter Email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
          </div>

          {/* Password */}
          <div>
            {/* <label className="text-sm text-neutral-300">Password</label> */}
            <div className="relative mt-1">
              <Lock
                size={16}
                className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
              />
              <input
                type="password"
                required
                className="w-full pl-9 pr-3 py-2 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-white/20"
                placeholder="•••"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
              />
            </div>
          </div>
          {/* Error */}
          {error && <p className="text-red-400 text-sm text-center">{error}</p>}
          {/* Button */}
          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg bg-white text-black font-medium hover:bg-neutral-200 transition disabled:opacity-50"
          >
            {loading ? "Signing in..." : "Sign in"}
          </button>
        </form>

        {/* Divider */}
        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-800" />
          <span className="text-xs text-neutral-500">OR</span>
          <div className="h-px flex-1 bg-neutral-800" />
        </div>

        {/* Footer */}
        <p className="text-center text-xs text-neutral-500">
          Don&apos;t have an account?{" "}
          <a href="/register" className="text-white hover:underline">
            Sign up
          </a>
        </p>
      </div>
    </div>
  );
}
