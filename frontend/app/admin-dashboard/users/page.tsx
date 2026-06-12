"use client";

import { useEffect, useState } from "react";

import {
  getAllUsers,
  toggleUserActive,
  toggleUserVerified,
} from "@/helper/users";

import { Button } from "@/components/ui/button";
import { Switch } from "@/components/ui/switch";
import AdminResetPasswordDialog from "@/components/admin-reset-password-dialog";

type User = {
  id: number;
  fullName: string;
  email: string;
  isActive: boolean;
  isVerified: boolean;
};

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [loading, setLoading] = useState(true);

  // ===================================
  // FETCH USERS
  // ===================================
  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await getAllUsers();

        if (Array.isArray(data)) {
          setUsers(data);
        } else {
          setUsers([]);
        }
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchUsers();
  }, []);

  // ===================================
  // TOGGLE ACTIVE
  // ===================================
  const handleToggleActive = async (id: number) => {
    try {
      // backend update
      const res = await toggleUserActive(id);

      // update UI
      setUsers((prev) =>
        prev.map((user) =>
          user.id === id
            ? {
                ...user,
                isActive: res.isActive,
              }
            : user,
        ),
      );
    } catch (err: any) {
      alert(err.message);
    }
  };

  // ===================================
  // TOGGLE VERIFIED
  // ===================================
  const handleToggleVerified = async (id: number) => {
    try {
      // backend update
      const res = await toggleUserVerified(id);

      // update UI
      setUsers((prev) =>
        prev.map((user) =>
          user.id === id
            ? {
                ...user,
                isVerified: res.isVerified,
              }
            : user,
        ),
      );
    } catch (err: any) {
      alert(err.message);
    }
  };

  if (loading) {
    return <div>Loading users...</div>;
  }

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div>
        <h1 className="text-2xl font-bold">Users Management</h1>

        <p className="text-muted-foreground text-sm">
          Manage all registered users
        </p>
      </div>

      {/* TABLE */}
      <div className="rounded-xl border overflow-x-auto">
        <table className="w-full min-w-[700px]">
          <thead className="bg-muted/50">
            <tr>
              <th className="text-left p-4">Full Name</th>

              <th className="text-left p-4">Email</th>

              <th className="text-left p-4">Active</th>

              <th className="text-left p-4">Verified</th>

              <th className="text-left p-4">Reset Password</th>

              <th className="text-left p-4">View</th>
              <th className="text-left p-4">Edit</th>
            </tr>
          </thead>

          <tbody>
            {users.map((user) => (
              <tr key={user.id} className="border-t">
                {/* FULL NAME */}
                <td className="p-4">{user.fullName}</td>

                {/* EMAIL */}
                <td className="p-4">{user.email}</td>

                {/* ACTIVE */}
                <td className="p-4">
                  <Switch
                    checked={user.isActive}
                    onCheckedChange={() => handleToggleActive(user.id)}
                  />
                </td>

                {/* VERIFIED */}
                <td className="p-4">
                  <Switch
                    checked={user.isVerified}
                    onCheckedChange={() => handleToggleVerified(user.id)}
                  />
                </td>

                {/* RESET PASSWORD */}
                <td className="p-4">
                  <AdminResetPasswordDialog userId={user.id} />
                </td>

                {/* EDIT */}
                <td className="p-4">
                  <Button>View details</Button>
                </td>
                <td className="p-4">
                  <Button variant="secondary">Edit User</Button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
