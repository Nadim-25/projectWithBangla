"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";

import { registerUser } from "@/helper/auth";

import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

export default function RegisterPage() {
  const router = useRouter();

  const [form, setForm] = useState({
    fullName: "",
    userName: "",
    email: "",
    hashedPassword: "",
    confirmHashedPassword: "",
  });

  const [loading, setLoading] = useState(false);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setForm({
      ...form,
      [e.target.name]: e.target.value,
    });
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);

      const res = await registerUser(form);

      alert(res.message);

      router.push("/login");
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto mt-20 max-w-md">
      <div className="rounded-2xl border p-6 shadow-sm">
        {/* TITLE */}
        <div className="mb-6 space-y-1">
          <h1 className="text-2xl font-bold">Create Account</h1>

          <p className="text-sm text-muted-foreground">Register your account</p>
        </div>

        {/* FORM */}
        <div className="space-y-4">
          {/* FULL NAME */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Full Name</label>

            <Input
              name="fullName"
              value={form.fullName}
              onChange={handleChange}
              placeholder="John Doe"
            />
          </div>

          {/* USERNAME */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Username</label>

            <Input
              name="userName"
              value={form.userName}
              onChange={handleChange}
              placeholder="johndoe"
            />
          </div>

          {/* EMAIL */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Email</label>

            <Input
              type="email"
              name="email"
              value={form.email}
              onChange={handleChange}
              placeholder="john@example.com"
            />
          </div>

          {/* PASSWORD */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Password</label>

            <Input
              type="password"
              name="hashedPassword"
              value={form.hashedPassword}
              onChange={handleChange}
              placeholder="********"
            />
          </div>

          {/* CONFIRM PASSWORD */}
          <div className="space-y-2">
            <label className="text-sm font-medium">Confirm Password</label>

            <Input
              type="password"
              name="confirmHashedPassword"
              value={form.confirmHashedPassword}
              onChange={handleChange}
              placeholder="********"
            />
          </div>

          {/* BUTTON */}
          <Button onClick={handleSubmit} disabled={loading} className="w-full">
            {loading ? "Creating Account..." : "Register"}
          </Button>
        </div>
      </div>
    </div>
  );
}
