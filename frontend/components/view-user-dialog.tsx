"use client";

import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";

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
};

export default function ViewUserDialog({ user }: Props) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <Button size="sm">View Details</Button>
      </DialogTrigger>

      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle>User Details</DialogTitle>
        </DialogHeader>

        <div className="space-y-2 mt-2">
          <Row label="Full Name" value={user.fullName} />
          <Row label="Username" value={user.userName} />
          <Row label="Email" value={user.email} />
          <Row label="Role">
            <span className="capitalize text-xs font-medium border rounded px-2 py-0.5">
              {user.role}
            </span>
          </Row>
          <Row label="Division" value={user.division} />
          <Row label="Department" value={user.department} />
          <Row label="Active">
            <span
              className={`text-xs font-medium rounded px-2 py-0.5 ${
                user.isActive
                  ? "bg-green-100 text-green-700"
                  : "bg-red-100 text-red-600"
              }`}
            >
              {user.isActive ? "Active" : "Inactive"}
            </span>
          </Row>
          <Row label="Verified">
            <span
              className={`text-xs font-medium rounded px-2 py-0.5 ${
                user.isVerified
                  ? "bg-blue-100 text-blue-700"
                  : "bg-gray-100 text-gray-600"
              }`}
            >
              {user.isVerified ? "Verified" : "Unverified"}
            </span>
          </Row>
          {user.createdAt && (
            <Row
              label="Joined"
              value={new Date(user.createdAt).toLocaleDateString("en-GB", {
                day: "2-digit",
                month: "short",
                year: "numeric",
              })}
            />
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

function Row({
  label,
  value,
  children,
}: {
  label: string;
  value?: string;
  children?: React.ReactNode;
}) {
  return (
    <div className="flex items-center justify-between py-1.5 border-b last:border-0">
      <span className="text-sm text-muted-foreground w-28 shrink-0">{label}</span>
      <span className="text-sm font-medium text-right">
        {children ?? value}
      </span>
    </div>
  );
}
