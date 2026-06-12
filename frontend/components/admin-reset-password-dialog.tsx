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

import { resetPasswordByAdmin } from "@/helper/users";

type Props = {
  userId: number;
};

export default function AdminResetPasswordDialog({ userId }: Props) {
  const [open, setOpen] = useState(false);

  const [password, setPassword] = useState("");

  const [confirmPassword, setConfirmPassword] = useState("");

  const [loading, setLoading] = useState(false);

  const handleSubmit = async () => {
    try {
      setLoading(true);

      const res = await resetPasswordByAdmin(userId, password, confirmPassword);

      alert(res.message);

      // reset fields
      setPassword("");
      setConfirmPassword("");

      // close dialog
      setOpen(false);
    } catch (err: any) {
      alert(err.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={setOpen}>
      {/* BUTTON */}
      <DialogTrigger asChild>
        <Button variant="outline">Reset Password</Button>
      </DialogTrigger>

      {/* MODAL */}
      <DialogContent>
        <DialogHeader>
          <DialogTitle>Reset User Password</DialogTitle>
        </DialogHeader>

        <div className="space-y-4 mt-4">
          {/* PASSWORD */}
          <div className="space-y-2">
            <label className="text-sm">New Password</label>

            <Input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
            />
          </div>

          {/* CONFIRM */}
          <div className="space-y-2">
            <label className="text-sm">Confirm Password</label>

            <Input
              type="password"
              value={confirmPassword}
              onChange={(e) => setConfirmPassword(e.target.value)}
            />
          </div>

          {/* BUTTON */}
          <Button className="w-full" onClick={handleSubmit} disabled={loading}>
            {loading ? "Updating..." : "Change Password"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
