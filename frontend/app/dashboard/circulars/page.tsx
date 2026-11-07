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
    <div className="mx-auto w-full max-w-4xl px-4 py-6">
      <Card>
        <CardHeader>
          <CardTitle>All Circulars</CardTitle>
          <p className="text-sm text-muted-foreground">
            {docs.length} document{docs.length !== 1 ? "s" : ""} uploaded
          </p>
        </CardHeader>

        <CardContent className="px-0 sm:px-6">
          {docs.length === 0 ? (
            <div className="py-20 text-center text-muted-foreground">
              No circulars found
            </div>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full min-w-[500px]">
                <thead>
                  <tr className="border-b text-left text-xs uppercase tracking-wide text-muted-foreground">
                    <th className="p-4">Circular</th>
                    <th className="p-4 w-32">Published</th>
                    <th className="p-4 w-32">Uploaded</th>
                    <th className="p-4 w-10" />
                  </tr>
                </thead>
                <tbody>
                  {docs.map((doc) => (
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
                        {doc.published_date ? (
                          fmtDate(doc.published_date)
                        ) : (
                          <span className="text-muted-foreground">Not set</span>
                        )}
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
