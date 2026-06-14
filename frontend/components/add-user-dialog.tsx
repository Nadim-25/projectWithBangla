"use client";

import { useState } from "react";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { UserPlus } from "lucide-react";

import { registerUser } from "@/helper/users";

const emptyForm = {
  fullName: "",
  userName: "",
  email: "",
  hashedPassword: "",
  confirmHashedPassword: "",
};

export default function AddUserDialog() {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState(emptyForm);

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    if (!form.fullName.trim() || !form.userName.trim() || !form.email.trim()) {
      alert("Please fill in all fields");
      return;
    }

    if (form.hashedPassword !== form.confirmHashedPassword) {
      alert("Passwords do not match");
      return;
    }

    try {
      setLoading(true);
      const res = await registerUser(form);
      alert(res.message || "User created successfully");
      setForm(emptyForm);
      setOpen(false);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Failed to create user");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <button className="mb-2 flex w-full items-center gap-2 rounded-lg px-3 py-2 hover:bg-muted text-sm text-left">
          <UserPlus className="h-4 w-4 shrink-0" />
          Add User
        </button>
      </DialogTrigger>

      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Add New User</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 mt-2">
          <Field label="Full Name">
            <Input
              placeholder="John Doe"
              value={form.fullName}
              onChange={(e) => handleChange("fullName", e.target.value)}
            />
          </Field>

          <Field label="Username">
            <Input
              placeholder="johndoe"
              value={form.userName}
              onChange={(e) => handleChange("userName", e.target.value)}
            />
          </Field>

          <Field label="Email">
            <Input
              type="email"
              placeholder="john@example.com"
              value={form.email}
              onChange={(e) => handleChange("email", e.target.value)}
            />
          </Field>

          <Field label="Password">
            <Input
              type="password"
              placeholder="••••••••"
              value={form.hashedPassword}
              onChange={(e) => handleChange("hashedPassword", e.target.value)}
            />
          </Field>

          <Field label="Confirm Password">
            <Input
              type="password"
              placeholder="••••••••"
              value={form.confirmHashedPassword}
              onChange={(e) =>
                handleChange("confirmHashedPassword", e.target.value)
              }
            />
          </Field>

          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? "Creating..." : "Create User"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <div className="space-y-1">
      <label className="text-sm font-medium">{label}</label>
      {children}
    </div>
  );
}
