"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { User, AtSign, Mail, Lock } from "lucide-react";
import { registerUser } from "@/helper/auth";
import { useFlash } from "@/context/FlashContext";

export default function RegisterPage() {
  const router = useRouter();
  const { showFlash } = useFlash();

  const [form, setForm] = useState({
    fullName: "",
    userName: "",
    email: "",
    hashedPassword: "",
    confirmHashedPassword: "",
  });

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({ ...form, [e.target.name]: e.target.value });
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError("");
    try {
      setLoading(true);
      const res = await registerUser(form);
      showFlash(res.message || "Account created! Please wait for admin approval.", "success");
      router.push("/login");
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "An error occurred";
      setError(msg);
      showFlash(msg, "error");
    } finally {
      setLoading(false);
    }
  };

  const fields = [
    { label: "Full Name", name: "fullName", type: "text", placeholder: "John Doe", icon: User },
    { label: "Username", name: "userName", type: "text", placeholder: "johndoe", icon: AtSign },
    { label: "Email", name: "email", type: "email", placeholder: "john@example.com", icon: Mail },
    { label: "Password", name: "hashedPassword", type: "password", placeholder: "••••••••", icon: Lock },
    { label: "Confirm Password", name: "confirmHashedPassword", type: "password", placeholder: "••••••••", icon: Lock },
  ] as const;

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950 px-4 py-8">
      <div className="w-full max-w-sm bg-neutral-900 border border-neutral-800 rounded-2xl p-6 shadow-xl">
        <div className="text-center mb-6">
          <h1 className="text-2xl font-semibold text-white">Create Account</h1>
          <p className="text-sm text-neutral-400 mt-1">Register to get started</p>
        </div>

        <form className="space-y-4" onSubmit={handleSubmit}>
          {fields.map(({ label, name, type, placeholder, icon: Icon }) => (
            <div key={name}>
              <label className="text-xs text-neutral-400 mb-1 block">{label}</label>
              <div className="relative">
                <Icon
                  size={16}
                  className="absolute left-3 top-1/2 -translate-y-1/2 text-neutral-400"
                />
                <input
                  type={type}
                  name={name}
                  required
                  value={form[name]}
                  onChange={handleChange}
                  placeholder={placeholder}
                  className="w-full pl-9 pr-3 py-2 rounded-lg bg-neutral-800 text-white border border-neutral-700 focus:outline-none focus:ring-2 focus:ring-white/20 text-sm"
                />
              </div>
            </div>
          ))}

          {error && <p className="text-red-400 text-sm text-center">{error}</p>}

          <button
            type="submit"
            disabled={loading}
            className="w-full py-2 rounded-lg bg-white text-black font-medium hover:bg-neutral-200 transition disabled:opacity-50"
          >
            {loading ? "Creating Account..." : "Register"}
          </button>
        </form>

        <div className="my-5 flex items-center gap-3">
          <div className="h-px flex-1 bg-neutral-800" />
          <span className="text-xs text-neutral-500">OR</span>
          <div className="h-px flex-1 bg-neutral-800" />
        </div>

        <p className="text-center text-xs text-neutral-500">
          Already have an account?{" "}
          <a href="/login" className="text-white hover:underline">
            Sign in
          </a>
        </p>
      </div>
    </div>
  );
}
