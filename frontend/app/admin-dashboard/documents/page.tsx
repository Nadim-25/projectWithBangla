"use client";

import { useEffect, useState } from "react";

import { getAllDocs, processDoc, deleteDoc } from "@/helper/docs";

import { FileText, Trash2, Loader2 } from "lucide-react";

import { Button } from "@/components/ui/button";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

type Doc = {
  id: number;
  displayName: string;
  division: string;
  department: string;
  fileName: string;
  fileExt: string;
  processed: boolean;
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);

  const [loading, setLoading] = useState(true);

  const [processingId, setProcessingId] = useState<number | null>(null);

  const [deletingId, setDeletingId] = useState<number | null>(null);

  // ======================================
  // LOAD DOCS
  // ======================================
  useEffect(() => {
    const fetchDocs = async () => {
      try {
        const data = await getAllDocs();

        setDocs(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoading(false);
      }
    };

    fetchDocs();
  }, []);

  // ======================================
  // PROCESS
  // ======================================
  const handleProcess = async (id: number) => {
    try {
      setProcessingId(id);

      await processDoc(id);

      setDocs((prev) =>
        prev.map((doc) =>
          doc.id === id
            ? {
                ...doc,
                processed: true,
              }
            : doc,
        ),
      );
    } catch (err: any) {
      alert(err.message);
    } finally {
      setProcessingId(null);
    }
  };

  // ======================================
  // DELETE
  // ======================================
  const handleDelete = async (id: number) => {
    try {
      setDeletingId(id);

      await deleteDoc(id);

      setDocs((prev) => prev.filter((doc) => doc.id !== id));
    } catch (err: any) {
      alert(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  // ======================================
  // LOADING
  // ======================================
  if (loading) {
    return (
      <div className="flex h-[300px] items-center justify-center">
        <Loader2 className="h-8 w-8 animate-spin" />
      </div>
    );
  }

  return (
    <div className="p-6">
      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>

        <CardContent>
          <div className="overflow-x-auto">
            <table className="w-full">
              <thead>
                <tr className="border-b text-left">
                  <th className="p-4">Document</th>

                  <th className="p-4">Division</th>

                  <th className="p-4">Department</th>

                  <th className="p-4">Type</th>

                  <th className="p-4">Status</th>

                  <th className="p-4">Actions</th>
                </tr>
              </thead>

              <tbody>
                {docs.map((doc) => (
                  <tr key={doc.id} className="border-b hover:bg-muted/40">
                    {/* DOC */}
                    <td className="p-4">
                      <div className="flex items-center gap-3">
                        <div className="rounded-lg bg-muted p-2">
                          <FileText className="h-5 w-5" />
                        </div>

                        <div>
                          <p className="font-medium">{doc.displayName}</p>

                          <p className="text-xs text-muted-foreground">
                            {doc.fileName}
                          </p>
                        </div>
                      </div>
                    </td>

                    {/* DIVISION */}
                    <td className="p-4">{doc.division}</td>

                    {/* DEPARTMENT */}
                    <td className="p-4">{doc.department}</td>

                    {/* TYPE */}
                    <td className="p-4 uppercase">
                      {doc.fileExt.replace(".", "")}
                    </td>

                    {/* STATUS */}
                    <td className="p-4">
                      {doc.processed ? (
                        <span className="rounded-full bg-green-500/10 px-3 py-1 text-xs text-green-600">
                          Processed
                        </span>
                      ) : (
                        <span className="rounded-full bg-yellow-500/10 px-3 py-1 text-xs text-yellow-600">
                          Pending
                        </span>
                      )}
                    </td>

                    {/* ACTIONS */}
                    <td className="p-4">
                      <div className="flex gap-2">
                        {/* PROCESS */}
                        <Button
                          size="sm"
                          disabled={doc.processed || processingId === doc.id}
                          onClick={() => handleProcess(doc.id)}
                        >
                          {processingId === doc.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : doc.processed ? (
                            "Processed"
                          ) : (
                            "Process"
                          )}
                        </Button>

                        {/* DELETE */}
                        <Button
                          variant="destructive"
                          size="sm"
                          disabled={deletingId === doc.id}
                          onClick={() => handleDelete(doc.id)}
                        >
                          {deletingId === doc.id ? (
                            <Loader2 className="h-4 w-4 animate-spin" />
                          ) : (
                            <Trash2 className="h-4 w-4" />
                          )}
                        </Button>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            {/* EMPTY */}
            {docs.length === 0 && (
              <div className="py-20 text-center text-muted-foreground">
                No documents found
              </div>
            )}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
