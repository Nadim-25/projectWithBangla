"use client";

import { Suspense } from "react";
import { redirect, useSearchParams } from "next/navigation";
import { useState } from "react";
import { resetPassword } from "@/helper/auth";

function ResetPasswordForm() {
  const params = useSearchParams();
  const token = params.get("token") || "";

  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const res = await resetPassword({ token, password, confirmPassword });
      alert(res.message);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
      redirect("/login");
    }
  };

  return (
    <div className="mx-auto mt-20 max-w-md space-y-4">
      <h1 className="text-2xl font-bold">Reset Password</h1>

      <input
        type="password"
        placeholder="New password"
        value={password}
        onChange={(e) => setPassword(e.target.value)}
        className="w-full rounded border p-2"
      />

      <input
        type="password"
        placeholder="Confirm password"
        value={confirmPassword}
        onChange={(e) => setConfirmPassword(e.target.value)}
        className="w-full rounded border p-2"
      />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full rounded bg-black p-2 text-white"
      >
        {loading ? "Resetting..." : "Reset Password"}
      </button>
    </div>
  );
}

export default function ResetPasswordPage() {
  return (
    <Suspense fallback={<div className="mx-auto mt-20 max-w-md">Loading...</div>}>
      <ResetPasswordForm />
    </Suspense>
  );
}
