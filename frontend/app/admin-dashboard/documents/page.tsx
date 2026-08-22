"use client";

import { useEffect, useState, Fragment } from "react";

import { getAllDocs, processDoc, deleteDoc, updateDocStrategy } from "@/helper/docs";

import { FileText, Trash2, Loader2, RefreshCw, Check, X } from "lucide-react";

import { Button } from "@/components/ui/button";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

const STRATEGY_OPTIONS = [
  { value: "auto", label: "Auto-detect" },
  { value: "circular_bn", label: "BB Circular (Bangla)" },
  { value: "circular_en", label: "BB Circular (English)" },
  { value: "chapter_doc", label: "Policy / Chapter Document" },
  { value: "industry_analysis", label: "Industry Analysis" },
] as const;

function strategyLabel(raw: string | null | undefined) {
  if (!raw) return "Auto-detect";
  return STRATEGY_OPTIONS.find((o) => o.value === raw)?.label ?? raw;
}

type Doc = {
  id: number;
  displayName: string;
  division: string;
  department: string;
  fileName: string;
  fileExt: string;
  processed: boolean;
  chunk_strategy: string | null;
};

export default function DocumentsPage() {
  const [docs, setDocs] = useState<Doc[]>([]);

  const [loading, setLoading] = useState(true);

  const [processingId, setProcessingId] = useState<number | null>(null);

  const [deletingId, setDeletingId] = useState<number | null>(null);

  // Inline reprocess panel: which doc is open + selected strategy
  const [reprocessId, setReprocessId] = useState<number | null>(null);
  const [selectedStrategy, setSelectedStrategy] = useState("auto");
  const [reprocessing, setReprocessing] = useState(false);

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
  // PROCESS (first time)
  // ======================================
  const handleProcess = async (id: number) => {
    try {
      setProcessingId(id);
      await processDoc(id);
      setDocs((prev) =>
        prev.map((doc) => (doc.id === id ? { ...doc, processed: true } : doc)),
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setProcessingId(null);
    }
  };

  // ======================================
  // OPEN REPROCESS PANEL
  // ======================================
  const openReprocess = (doc: Doc) => {
    setReprocessId(doc.id);
    setSelectedStrategy(doc.chunk_strategy ?? "auto");
  };

  const closeReprocess = () => {
    setReprocessId(null);
    setSelectedStrategy("auto");
  };

  // ======================================
  // CONFIRM REPROCESS (with optional strategy change)
  // ======================================
  const confirmReprocess = async (doc: Doc) => {
    try {
      setReprocessing(true);

      const newStrategy = selectedStrategy;
      const currentStrategy = doc.chunk_strategy ?? "auto";

      if (newStrategy !== currentStrategy) {
        await updateDocStrategy(doc.id, newStrategy);
        setDocs((prev) =>
          prev.map((d) =>
            d.id === doc.id
              ? { ...d, chunk_strategy: newStrategy === "auto" ? null : newStrategy }
              : d,
          ),
        );
      }

      await processDoc(doc.id, true);

      setDocs((prev) =>
        prev.map((d) => (d.id === doc.id ? { ...d, processed: true } : d)),
      );

      closeReprocess();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setReprocessing(false);
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
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
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
    <div>
      <Card>
        <CardHeader>
          <CardTitle>Documents</CardTitle>
        </CardHeader>

        <CardContent className="px-0 sm:px-6">
          <div className="overflow-x-auto">
            <table className="w-full min-w-[680px]">
              <thead>
                <tr className="border-b text-left">
                  <th className="p-4">Document</th>
                  <th className="p-4">Division</th>
                  <th className="p-4">Department</th>
                  <th className="p-4">Type</th>
                  <th className="p-4">Strategy</th>
                  <th className="p-4">Status</th>
                  <th className="p-4">Actions</th>
                </tr>
              </thead>

              <tbody>
                {docs.map((doc) => (
                  <Fragment key={doc.id}>
                    <tr className="border-b hover:bg-muted/40">
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

                      {/* STRATEGY */}
                      <td className="p-4">
                        <span className="rounded-full bg-blue-500/10 px-2 py-0.5 text-xs text-blue-700 dark:text-blue-400">
                          {strategyLabel(doc.chunk_strategy)}
                        </span>
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
                          {/* PROCESS (first time) */}
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

                          {/* REPROCESS (toggle panel) */}
                          {doc.processed && (
                            <Button
                              size="sm"
                              variant="outline"
                              disabled={reprocessing && reprocessId === doc.id}
                              onClick={() =>
                                reprocessId === doc.id
                                  ? closeReprocess()
                                  : openReprocess(doc)
                              }
                              title="Re-process with a (optionally different) strategy"
                            >
                              <RefreshCw className="h-4 w-4" />
                            </Button>
                          )}

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

                    {/* INLINE REPROCESS PANEL */}
                    {reprocessId === doc.id && (
                      <tr className="bg-muted/30">
                        <td colSpan={7} className="px-6 py-4">
                          <div className="flex flex-wrap items-center gap-4">
                            <span className="text-sm font-medium">
                              Re-process as:
                            </span>
                            <select
                              value={selectedStrategy}
                              onChange={(e) =>
                                setSelectedStrategy(e.target.value)
                              }
                              className="rounded-md border border-input bg-background px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-ring"
                            >
                              {STRATEGY_OPTIONS.map((opt) => (
                                <option key={opt.value} value={opt.value}>
                                  {opt.label}
                                </option>
                              ))}
                            </select>
                            <Button
                              size="sm"
                              disabled={reprocessing}
                              onClick={() => confirmReprocess(doc)}
                            >
                              {reprocessing ? (
                                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                              ) : (
                                <Check className="mr-1 h-4 w-4" />
                              )}
                              Confirm
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={reprocessing}
                              onClick={closeReprocess}
                            >
                              <X className="mr-1 h-4 w-4" />
                              Cancel
                            </Button>
                          </div>
                          {selectedStrategy !== (doc.chunk_strategy ?? "auto") && (
                            <p className="mt-2 text-xs text-amber-600 dark:text-amber-400">
                              Strategy will change from{" "}
                              <strong>{strategyLabel(doc.chunk_strategy)}</strong> →{" "}
                              <strong>
                                {strategyLabel(
                                  selectedStrategy === "auto"
                                    ? null
                                    : selectedStrategy,
                                )}
                              </strong>
                              . All existing embeddings will be deleted and regenerated.
                            </p>
                          )}
                          {selectedStrategy === (doc.chunk_strategy ?? "auto") && (
                            <p className="mt-2 text-xs text-muted-foreground">
                              All existing embeddings will be deleted and regenerated with the same strategy.
                            </p>
                          )}
                        </td>
                      </tr>
                    )}
                  </Fragment>
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
