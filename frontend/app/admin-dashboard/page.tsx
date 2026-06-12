"use client";

import { useEffect, useState } from "react";
import { getAdminSummary } from "@/helper/users";
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

type StatCardProps = {
  label: string;
  value: number;
  icon: React.ReactNode;
  color: string;
};

function StatCard({ label, value, icon, color }: StatCardProps) {
  return (
    <div className="flex items-center gap-4 rounded-xl border bg-background p-5 shadow-sm">
      <div className={`rounded-lg p-3 ${color}`}>{icon}</div>
      <div>
        <p className="text-sm text-muted-foreground">{label}</p>
        <p className="text-2xl font-bold">{value}</p>
      </div>
    </div>
  );
}

export default function DashboardPage() {
  const [summary, setSummary] = useState<Summary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getAdminSummary()
      .then(setSummary)
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

  const userCards: StatCardProps[] = [
    {
      label: "Total Users",
      value: summary.users.total,
      icon: <Users className="h-5 w-5 text-blue-600" />,
      color: "bg-blue-100 dark:bg-blue-900/30",
    },
    {
      label: "Active",
      value: summary.users.active,
      icon: <UserCheck className="h-5 w-5 text-green-600" />,
      color: "bg-green-100 dark:bg-green-900/30",
    },
    {
      label: "Inactive",
      value: summary.users.inactive,
      icon: <UserX className="h-5 w-5 text-red-500" />,
      color: "bg-red-100 dark:bg-red-900/30",
    },
    {
      label: "Verified",
      value: summary.users.verified,
      icon: <UserCheck className="h-5 w-5 text-emerald-600" />,
      color: "bg-emerald-100 dark:bg-emerald-900/30",
    },
    {
      label: "Unverified",
      value: summary.users.unverified,
      icon: <UserX className="h-5 w-5 text-orange-500" />,
      color: "bg-orange-100 dark:bg-orange-900/30",
    },
    {
      label: "Admins",
      value: summary.users.admins,
      icon: <ShieldCheck className="h-5 w-5 text-purple-600" />,
      color: "bg-purple-100 dark:bg-purple-900/30",
    },
    {
      label: "Regular Users",
      value: summary.users.regular,
      icon: <User className="h-5 w-5 text-slate-600" />,
      color: "bg-slate-100 dark:bg-slate-800",
    },
  ];

  const docCards: StatCardProps[] = [
    {
      label: "Total Documents",
      value: summary.documents.total,
      icon: <FileText className="h-5 w-5 text-blue-600" />,
      color: "bg-blue-100 dark:bg-blue-900/30",
    },
    {
      label: "Processed",
      value: summary.documents.processed,
      icon: <CheckCircle className="h-5 w-5 text-green-600" />,
      color: "bg-green-100 dark:bg-green-900/30",
    },
    {
      label: "Unprocessed",
      value: summary.documents.unprocessed,
      icon: <Clock className="h-5 w-5 text-yellow-600" />,
      color: "bg-yellow-100 dark:bg-yellow-900/30",
    },
  ];

  return (
    <div className="space-y-8">
      <div>
        <h2 className="mb-1 text-2xl font-bold">Dashboard</h2>
        <p className="text-sm text-muted-foreground">
          Overview of users and documents
        </p>
      </div>

      {/* Users Section */}
      <section>
        <h3 className="mb-4 text-lg font-semibold">Users</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-4">
          {userCards.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      </section>

      {/* Documents Section */}
      <section>
        <h3 className="mb-4 text-lg font-semibold">Documents</h3>
        <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
          {docCards.map((card) => (
            <StatCard key={card.label} {...card} />
          ))}
        </div>
      </section>
    </div>
  );
}
