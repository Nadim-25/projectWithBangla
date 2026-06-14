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

import { updateUser } from "@/helper/users";

type User = {
  id: number;
  fullName: string;
  userName: string;
  email: string;
  role: string;
  division: string;
  department: string;
  isActive: boolean;
  isVerified: boolean;
  createdAt?: string;
};

type Props = {
  user: User;
  onUpdated: (updated: User) => void;
};

export default function EditUserDialog({ user, onUpdated }: Props) {
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    fullName: user.fullName,
    userName: user.userName,
    email: user.email,
    role: user.role,
    division: user.division,
    department: user.department,
  });

  const handleChange = (field: keyof typeof form, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSubmit = async () => {
    try {
      setLoading(true);
      const updated = await updateUser(user.id, form);
      onUpdated({ ...user, ...updated });
      setOpen(false);
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Update failed");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      <DialogTrigger asChild>
        <Button variant="secondary" size="sm">Edit User</Button>
      </DialogTrigger>

      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>Edit User</DialogTitle>
        </DialogHeader>

        <div className="space-y-3 mt-2">
          <Field label="Full Name">
            <Input
              value={form.fullName}
              onChange={(e) => handleChange("fullName", e.target.value)}
            />
          </Field>

          <Field label="Username">
            <Input
              value={form.userName}
              onChange={(e) => handleChange("userName", e.target.value)}
            />
          </Field>

          <Field label="Email">
            <Input
              type="email"
              value={form.email}
              onChange={(e) => handleChange("email", e.target.value)}
            />
          </Field>

          <Field label="Role">
            <select
              value={form.role}
              onChange={(e) => handleChange("role", e.target.value)}
              className="w-full h-9 rounded-md border border-input bg-background px-3 py-1 text-sm shadow-sm focus-visible:outline-none focus-visible:ring-1 focus-visible:ring-ring"
            >
              <option value="user">User</option>
              <option value="admin">Admin</option>
            </select>
          </Field>

          <Field label="Division">
            <Input
              value={form.division}
              onChange={(e) => handleChange("division", e.target.value)}
            />
          </Field>

          <Field label="Department">
            <Input
              value={form.department}
              onChange={(e) => handleChange("department", e.target.value)}
            />
          </Field>

          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? "Saving..." : "Save Changes"}
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
