"use client";

import { useEffect, useState } from "react";

import {
  getAllUsers,
  toggleUserActive,
  toggleUserVerified,
} from "@/helper/users";

import { Switch } from "@/components/ui/switch";
import { Input } from "@/components/ui/input";
import AdminResetPasswordDialog from "@/components/admin-reset-password-dialog";
import ViewUserDialog from "@/components/view-user-dialog";
import EditUserDialog from "@/components/edit-user-dialog";

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

export default function UsersPage() {
  const [users, setUsers] = useState<User[]>([]);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchUsers = async () => {
      try {
        const data = await getAllUsers();
        setUsers(Array.isArray(data) ? data : []);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };
    fetchUsers();
  }, []);

  const handleToggleActive = async (id: number) => {
    try {
      const res = await toggleUserActive(id);
      setUsers((prev) =>
        prev.map((user) =>
          user.id === id ? { ...user, isActive: res.isActive } : user,
        ),
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  const handleToggleVerified = async (id: number) => {
    try {
      const res = await toggleUserVerified(id);
      setUsers((prev) =>
        prev.map((user) =>
          user.id === id ? { ...user, isVerified: res.isVerified } : user,
        ),
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    }
  };

  const handleUserUpdated = (updated: User) => {
    setUsers((prev) =>
      prev.map((user) => (user.id === updated.id ? { ...user, ...updated } : user)),
    );
  };

  const filteredUsers = users.filter((u) =>
    u.email.toLowerCase().includes(search.toLowerCase()),
  );

  if (loading) {
    return <div>Loading users...</div>;
  }

  return (
    <div className="space-y-6">
      {/* HEADER */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <h1 className="text-xl font-bold sm:text-2xl">Users Management</h1>
          <p className="text-muted-foreground text-sm">
            Manage all registered users
          </p>
        </div>
        <Input
          placeholder="Search by email..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="w-full sm:w-64"
        />
      </div>

      {/* MOBILE CARDS — visible on small screens only */}
      <div className="flex flex-col gap-3 sm:hidden">
        {filteredUsers.length === 0 && (
          <p className="py-8 text-center text-sm text-muted-foreground">
            No users match your search
          </p>
        )}
        {filteredUsers.map((user) => (
          <div key={user.id} className="rounded-xl border bg-background p-4 shadow-sm space-y-3">
            {/* Name + role */}
            <div className="flex items-start justify-between gap-2">
              <div>
                <p className="font-semibold">{user.fullName}</p>
                <p className="text-xs text-muted-foreground">{user.email}</p>
              </div>
              <span className="shrink-0 rounded-full bg-muted px-2 py-0.5 text-xs capitalize">
                {user.role}
              </span>
            </div>

            {/* Toggles */}
            <div className="flex items-center gap-6">
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Active</span>
                <Switch
                  checked={user.isActive}
                  onCheckedChange={() => handleToggleActive(user.id)}
                />
              </div>
              <div className="flex items-center gap-2">
                <span className="text-sm text-muted-foreground">Verified</span>
                <Switch
                  checked={user.isVerified}
                  onCheckedChange={() => handleToggleVerified(user.id)}
                />
              </div>
            </div>

            {/* Actions */}
            <div className="flex items-center gap-2 flex-wrap">
              <AdminResetPasswordDialog userId={user.id} />
              <ViewUserDialog user={user} />
              <EditUserDialog user={user} onUpdated={handleUserUpdated} />
            </div>
          </div>
        ))}
      </div>

      {/* DESKTOP TABLE — hidden on small screens */}
      <div className="hidden sm:block rounded-xl border overflow-x-auto">
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
            {filteredUsers.length === 0 && (
              <tr>
                <td colSpan={7} className="p-6 text-center text-sm text-muted-foreground">
                  No users match your search
                </td>
              </tr>
            )}
            {filteredUsers.map((user) => (
              <tr key={user.id} className="border-t">
                <td className="p-4">{user.fullName}</td>
                <td className="p-4">{user.email}</td>
                <td className="p-4">
                  <Switch
                    checked={user.isActive}
                    onCheckedChange={() => handleToggleActive(user.id)}
                  />
                </td>
                <td className="p-4">
                  <Switch
                    checked={user.isVerified}
                    onCheckedChange={() => handleToggleVerified(user.id)}
                  />
                </td>
                <td className="p-4">
                  <AdminResetPasswordDialog userId={user.id} />
                </td>
                <td className="p-4">
                  <ViewUserDialog user={user} />
                </td>
                <td className="p-4">
                  <EditUserDialog user={user} onUpdated={handleUserUpdated} />
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
