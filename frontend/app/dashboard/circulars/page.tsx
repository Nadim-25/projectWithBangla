"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { getAllDocs } from "@/helper/docs";
import { FileText, Loader2, ChevronRight } from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Doc = {
  id: number;
  displayName: string;
  fileName: string;
  subject: string | null;
  published_date: string | null;
  createdAt: string | null;
  processed: boolean;
};

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

export default function AllCircularsPage() {
  const router = useRouter();
  const [docs, setDocs] = useState<Doc[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getAllDocs()
      .then((data) => setDocs(data))
      .catch(console.error)
      .finally(() => setLoading(false));
  }, []);

  if (loading) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="w-full py-4">
      <Card>
        <CardHeader className="pb-3">
          <CardTitle>All Circulars</CardTitle>
          <p className="text-sm text-muted-foreground">
            {docs.length} document{docs.length !== 1 ? "s" : ""} uploaded
          </p>
        </CardHeader>

        <CardContent className="p-0 sm:px-2">
          {docs.length === 0 ? (
            <div className="py-20 text-center text-muted-foreground">
              No circulars found
            </div>
          ) : (
            <>
              {/* ── MOBILE: card list ── */}
              <ul className="divide-y sm:hidden">
                {docs.map((doc) => (
                  <li
                    key={doc.id}
                    className="flex items-start gap-3 px-4 py-3 cursor-pointer hover:bg-muted/40 active:bg-muted/60 transition-colors"
                    onClick={() => router.push(`/dashboard/circulars/${doc.id}`)}
                  >
                    <div className="mt-0.5 rounded-lg bg-muted p-2 shrink-0">
                      <FileText className="h-4 w-4" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <p className="font-medium leading-snug">{doc.displayName}</p>
                      {doc.subject && (
                        <p className="mt-0.5 text-xs text-primary/70 leading-snug line-clamp-2">
                          {doc.subject}
                        </p>
                      )}
                      <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-muted-foreground">
                        <span>
                          Published:{" "}
                          <span className={doc.published_date ? "text-foreground" : ""}>
                            {fmtDate(doc.published_date)}
                          </span>
                        </span>
                        <span>Uploaded: {fmtDate(doc.createdAt)}</span>
                      </div>
                    </div>
                    <ChevronRight className="h-4 w-4 text-muted-foreground shrink-0 mt-1" />
                  </li>
                ))}
              </ul>

              {/* ── DESKTOP: table ── */}
              <div className="hidden sm:block overflow-x-auto">
                <table className="w-full">
                  <thead>
                    <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                      <th className="px-4 py-3">Circular</th>
                      <th className="px-4 py-3 w-36">Published</th>
                      <th className="px-4 py-3 w-36">Uploaded</th>
                      <th className="px-4 py-3 w-10" />
                    </tr>
                  </thead>
                  <tbody>
                    {docs.map((doc) => (
                      <tr
                        key={doc.id}
                        className="border-b hover:bg-muted/40 cursor-pointer transition-colors"
                        onClick={() => router.push(`/dashboard/circulars/${doc.id}`)}
                      >
                        <td className="px-4 py-3">
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
                        <td className="px-4 py-3 text-sm whitespace-nowrap">
                          {doc.published_date ? (
                            fmtDate(doc.published_date)
                          ) : (
                            <span className="text-muted-foreground">Not set</span>
                          )}
                        </td>
                        <td className="px-4 py-3 text-sm text-muted-foreground whitespace-nowrap">
                          {fmtDate(doc.createdAt)}
                        </td>
                        <td className="px-4 py-3">
                          <ChevronRight className="h-4 w-4 text-muted-foreground" />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
