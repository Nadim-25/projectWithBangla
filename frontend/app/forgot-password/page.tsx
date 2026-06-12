"use client";

import { useState } from "react";

import { forgotPassword } from "@/helper/auth";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");

  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);

      const res = await forgotPassword(email);

      alert(res.message);

      setEmail("");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto mt-20 max-w-md space-y-4">
      <h1 className="text-2xl font-bold">Forgot Password</h1>

      <input
        type="email"
        placeholder="Enter email"
        value={email}
        onChange={(e) => setEmail(e.target.value)}
        className="w-full rounded border p-2"
      />

      <button
        onClick={handleSubmit}
        disabled={loading}
        className="w-full rounded bg-black p-2 text-white"
      >
        {loading ? "Sending..." : "Send Reset Link"}
      </button>
    </div>
  );
}
