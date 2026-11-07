"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getRecentCirculars } from "@/helper/docs";
import {
  FileText,
  Loader2,
  ChevronRight,
  ArrowUpDown,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Doc = {
  id: number;
  displayName: string;
  fileName: string;
  subject: string | null;
  published_date: string | null;
  createdAt: string | null;
};

type SortKey = "published_date" | "createdAt";
type SortDir = "asc" | "desc";

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "2-digit",
      month: "short",
      year: "numeric",
    });
  } catch {
    return iso;
  }
}

function sortDocs(docs: Doc[], key: SortKey, dir: SortDir): Doc[] {
  return [...docs].sort((a, b) => {
    const av = a[key] ?? "";
    const bv = b[key] ?? "";
    const cmp = av < bv ? -1 : av > bv ? 1 : 0;
    return dir === "asc" ? cmp : -cmp;
  });
}

export default function NewCircularsPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);
  const [sortKey, setSortKey] = useState<SortKey>("published_date");
  const [sortDir, setSortDir] = useState<SortDir>("desc");

  useEffect(() => {
    getRecentCirculars(30)
      .then((data) => setDocs(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir("desc");
    }
  };

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ArrowUpDown className="ml-1 h-3 w-3 opacity-40" />;
    return sortDir === "desc" ? (
      <ArrowDown className="ml-1 h-3 w-3" />
    ) : (
      <ArrowUp className="ml-1 h-3 w-3" />
    );
  };

  const sorted = sortDocs(docs, sortKey, sortDir);

  if (loading) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            New Circulars
            <span className="rounded-full bg-amber-500/15 px-2 py-0.5 text-xs font-medium text-amber-600 dark:text-amber-400">
              Last 30 days
            </span>
          </CardTitle>
          <p className="text-sm text-muted-foreground">
            {sorted.length} circular{sorted.length !== 1 ? "s" : ""} published in the last 30 days
          </p>
        </CardHeader>

        <CardContent className="px-0 sm:px-6">
          {sorted.length === 0 ? (
            <div className="py-20 text-center text-muted-foreground">
              No circulars published in the last 30 days
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[500px]">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="p-4">Circular</th>
                    <th className="p-4 w-36">
                      <button
                        onClick={() => handleSort("published_date")}
                        className="flex items-center font-semibold hover:text-foreground transition-colors"
                      >
                        Published <SortIcon col="published_date" />
                      </button>
                    </th>
                    <th className="p-4 w-36">
                      <button
                        onClick={() => handleSort("createdAt")}
                        className="flex items-center font-semibold hover:text-foreground transition-colors"
                      >
                        Uploaded <SortIcon col="createdAt" />
                      </button>
                    </th>
                    <th className="p-4 w-10" />
                  </tr>
                </thead>
                <tbody>
                  {sorted.map((doc) => (
                    <tr
                      key={doc.id}
                      className="border-b hover:bg-muted/40 cursor-pointer transition-colors"
                      onClick={() => router.push(`/dashboard/circulars/${doc.id}`)}
                    >
                      <td className="p-4">
                        <div className="flex items-start gap-3">
                          <div className="mt-0.5 rounded-lg bg-muted p-2 shrink-0">
                            <FileText className="h-4 w-4" />
                          </div>
                          <div className="min-w-0">
                            <p className="font-medium leading-snug">{doc.displayName}</p>
                            {doc.subject && (
                              <p className="mt-0.5 text-xs text-primary/70 leading-snug line-clamp-2">
                                {doc.subject}
                              </p>
                            )}
                          </div>
                        </div>
                      </td>
                      <td className="p-4 text-sm whitespace-nowrap">
                        {fmtDate(doc.published_date)}
                      </td>
                      <td className="p-4 text-sm text-muted-foreground whitespace-nowrap">
                        {fmtDate(doc.createdAt)}
                      </td>
                      <td className="p-4">
                        <ChevronRight className="h-4 w-4 text-muted-foreground" />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
