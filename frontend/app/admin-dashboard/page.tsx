"use client";

import { useEffect, useState } from "react";
import { getAdminSummary, getAllUsers } from "@/helper/users";
import { getAllDocs } from "@/helper/docs";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import {
  Users,
  UserCheck,
  UserX,
  ShieldCheck,
  User,
  FileText,
  CheckCircle,
  Clock,
} from "lucide-react";

// ─── Types ────────────────────────────────────────────────────────────────────

type Summary = {
  users: {
    total: number;
    active: number;
    inactive: number;
    verified: number;
    unverified: number;
    admins: number;
    regular: number;
  };
  documents: {
    total: number;
    processed: number;
    unprocessed: number;
  };
};

type UserRow = {
  id: number;
  fullName: string;
  userName: string;
  email: string;
  role: string;
  isActive: boolean;
  isVerified: boolean;
};

type DocRow = {
  id: number;
  displayName: string;
  division: string;
  department: string;
  fileExt: string;
  processed: boolean;
};

type FilterState =
  | { kind: "users"; label: string; filter: (u: UserRow) => boolean }
  | { kind: "docs"; label: string; filter: (d: DocRow) => boolean }
  | null;

// ─── StatCard ─────────────────────────────────────────────────────────────────

type StatCardProps = {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
  onClick: () => void;
};

function StatCard({ label, value, icon, color, onClick }: StatCardProps) {
  return (
    <button
      onClick={onClick}
      className="flex w-full items-center gap-4 rounded-xl border bg-background p-5 shadow-sm text-left transition-all hover:shadow-md hover:border-primary/40 cursor-pointer"
    >
      <div className={`rounded-lg p-3 ${color}`}>{icon}</div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </button>
  );
}

// ─── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [users, setUsers] = useState<UserRow[]>([]);
  const [docs, setDocs] = useState<DocRow[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeFilter, setActiveFilter] = useState<FilterState>(null);

  useEffect(() => {
    Promise.all([getAdminSummary(), getAllUsers(), getAllDocs()])
      .then(([summaryData, usersData, docsData]) => {
        setSummary(summaryData);
        setUsers(Array.isArray(usersData) ? usersData : []);
        setDocs(Array.isArray(docsData) ? docsData : []);
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-full items-center justify-center text-muted-foreground">
        Loading summary...
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex h-full items-center justify-center text-destructive">
        {error}
      </div>
    );
  }

  if (!summary) return null;

  // ── User card definitions ──────────────────────────────────────────────────
  const userCards: (Omit<StatCardProps, "onClick"> & {
    filterFn: (u: UserRow) => boolean;
  })[] = [
    {
      label: "Total Users",
      value: summary.users.total,
      icon: <Users className="h-5 w-5 text-blue-600" />,
      color: "bg-blue-100 dark:bg-blue-900/30",
      filterFn: () => true,
    },
    {
      label: "Active",
      value: summary.users.active,
      icon: <UserCheck className="h-5 w-5 text-green-600" />,
      color: "bg-green-100 dark:bg-green-900/30",
      filterFn: (u) => u.isActive,
    },
    {
      label: "Inactive",
      value: summary.users.inactive,
      icon: <UserX className="h-5 w-5 text-red-500" />,
      color: "bg-red-100 dark:bg-red-900/30",
      filterFn: (u) => !u.isActive,
    },
    {
      label: "Verified",
      value: summary.users.verified,
      icon: <UserCheck className="h-5 w-5 text-emerald-600" />,
      color: "bg-emerald-100 dark:bg-emerald-900/30",
      filterFn: (u) => u.isVerified,
    },
    {
      label: "Unverified",
      value: summary.users.unverified,
      icon: <UserX className="h-5 w-5 text-orange-500" />,
      color: "bg-orange-100 dark:bg-orange-900/30",
      filterFn: (u) => !u.isVerified,
    },
    {
      label: "Admins",
      value: summary.users.admins,
      icon: <ShieldCheck className="h-5 w-5 text-purple-600" />,
      color: "bg-purple-100 dark:bg-purple-900/30",
      filterFn: (u) => u.role === "admin",
    },
    {
      label: "Regular Users",
      value: summary.users.regular,
      icon: <User className="h-5 w-5 text-slate-600" />,
      color: "bg-slate-100 dark:bg-slate-800",
      filterFn: (u) => u.role !== "admin",
    },
  ];

  // ── Doc card definitions ───────────────────────────────────────────────────
  const docCards: (Omit<StatCardProps, "onClick"> & {
    filterFn: (d: DocRow) => boolean;
  })[] = [
    {
      label: "Total Documents",
      value: summary.documents.total,
      icon: <FileText className="h-5 w-5 text-blue-600" />,
      color: "bg-blue-100 dark:bg-blue-900/30",
      filterFn: () => true,
    },
    {
      label: "Processed",
      value: summary.documents.processed,
      icon: <CheckCircle className="h-5 w-5 text-green-600" />,
      color: "bg-green-100 dark:bg-green-900/30",
      filterFn: (d) => d.processed,
    },
    {
      label: "Unprocessed",
      value: summary.documents.unprocessed,
      icon: <Clock className="h-5 w-5 text-yellow-600" />,
      color: "bg-yellow-100 dark:bg-yellow-900/30",
      filterFn: (d) => !d.processed,
    },
  ];

  // ── Filtered rows ──────────────────────────────────────────────────────────
  const filteredUsers =
    activeFilter?.kind === "users" ? users.filter(activeFilter.filter) : [];
  const filteredDocs =
    activeFilter?.kind === "docs" ? docs.filter(activeFilter.filter) : [];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="mb-1 text-2xl font-bold">Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Overview of users and documents — click any card to see details
        </p>
      </div>

      {/* Users Section */}
      <section>
        <h3 className="mb-4 text-lg font-semibold">Users</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {userCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              icon={card.icon}
              color={card.color}
              onClick={() =>
                setActiveFilter({
                  kind: "users",
                  label: card.label,
                  filter: card.filterFn,
                })
              }
            />
          ))}
        </div>
      </section>

      {/* Documents Section */}
      <section>
        <h3 className="mb-4 text-lg font-semibold">Documents</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {docCards.map((card) => (
            <StatCard
              key={card.label}
              label={card.label}
              value={card.value}
              icon={card.icon}
              color={card.color}
              onClick={() =>
                setActiveFilter({
                  kind: "docs",
                  label: card.label,
                  filter: card.filterFn,
                })
              }
            />
          ))}
        </div>
      </section>

      {/* ── Detail Dialog ──────────────────────────────────────────────────── */}
      <Dialog
        open={activeFilter !== null}
        onOpenChange={(open) => !open && setActiveFilter(null)}
      >
        <DialogContent className="max-w-3xl max-h-[80vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{activeFilter?.label}</DialogTitle>
          </DialogHeader>

          {/* Users table */}
          {activeFilter?.kind === "users" && (
            filteredUsers.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No users found
              </p>
            ) : (
              <div className="overflow-x-auto mt-2">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="p-3">Name</th>
                      <th className="p-3">Username</th>
                      <th className="p-3">Email</th>
                      <th className="p-3">Role</th>
                      <th className="p-3">Active</th>
                      <th className="p-3">Verified</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredUsers.map((u) => (
                      <tr key={u.id} className="border-b hover:bg-muted/40">
                        <td className="p-3 font-medium">{u.fullName}</td>
                        <td className="p-3 text-muted-foreground">{u.userName}</td>
                        <td className="p-3">{u.email}</td>
                        <td className="p-3 capitalize">{u.role}</td>
                        <td className="p-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              u.isActive
                                ? "bg-green-100 text-green-700"
                                : "bg-red-100 text-red-600"
                            }`}
                          >
                            {u.isActive ? "Active" : "Inactive"}
                          </span>
                        </td>
                        <td className="p-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              u.isVerified
                                ? "bg-blue-100 text-blue-700"
                                : "bg-gray-100 text-gray-500"
                            }`}
                          >
                            {u.isVerified ? "Verified" : "Unverified"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}

          {/* Docs table */}
          {activeFilter?.kind === "docs" && (
            filteredDocs.length === 0 ? (
              <p className="py-8 text-center text-sm text-muted-foreground">
                No documents found
              </p>
            ) : (
              <div className="overflow-x-auto mt-2">
                <table className="w-full text-sm">
                  <thead>
                    <tr className="border-b text-left">
                      <th className="p-3">Name</th>
                      <th className="p-3">Division</th>
                      <th className="p-3">Department</th>
                      <th className="p-3">Type</th>
                      <th className="p-3">Status</th>
                    </tr>
                  </thead>
                  <tbody>
                    {filteredDocs.map((d) => (
                      <tr key={d.id} className="border-b hover:bg-muted/40">
                        <td className="p-3 font-medium">{d.displayName}</td>
                        <td className="p-3">{d.division}</td>
                        <td className="p-3">{d.department}</td>
                        <td className="p-3 uppercase">
                          {d.fileExt.replace(".", "")}
                        </td>
                        <td className="p-3">
                          <span
                            className={`rounded-full px-2 py-0.5 text-xs font-medium ${
                              d.processed
                                ? "bg-green-100 text-green-700"
                                : "bg-yellow-100 text-yellow-700"
                            }`}
                          >
                            {d.processed ? "Processed" : "Pending"}
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
