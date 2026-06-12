"use client";

import { useState } from "react";

import { changePassword } from "@/helper/tokenHelper";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { useAuth } from "@/context/AuthContext";

export default function ChangePasswordPage() {
  const { logout } = useAuth();

  const [form, setForm] = useState({
    oldPassword: "",
    newPassword: "",
    confirmNewPassword: "",
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

      const res = await changePassword(form);

      alert(res.message);

      setForm({
        oldPassword: "",
        newPassword: "",
        confirmNewPassword: "",
      });

      logout();
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="mx-auto max-w-md space-y-5">
      <div>
        <h1 className="text-2xl font-bold">Change Password</h1>

        <p className="text-sm text-muted-foreground">
          Update your account password
        </p>
      </div>

      <div className="space-y-4 rounded-xl border p-6">
        {/* OLD PASSWORD */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Old Password</label>

          <Input
            type="password"
            name="oldPassword"
            value={form.oldPassword}
            onChange={handleChange}
          />
        </div>

        {/* NEW PASSWORD */}
        <div className="space-y-2">
          <label className="text-sm font-medium">New Password</label>

          <Input
            type="password"
            name="newPassword"
            value={form.newPassword}
            onChange={handleChange}
          />
        </div>

        {/* CONFIRM PASSWORD */}
        <div className="space-y-2">
          <label className="text-sm font-medium">Confirm Password</label>

          <Input
            type="password"
            name="confirmNewPassword"
            value={form.confirmNewPassword}
            onChange={handleChange}
          />
        </div>

        {/* BUTTON */}
        <Button onClick={handleSubmit} disabled={loading} className="w-full">
          {loading ? "Updating..." : "Change Password"}
        </Button>
      </div>
    </div>
  );
}
