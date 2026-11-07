"use client";

import { useEffect, useState, Fragment } from "react";

import { getAllDocs, processDoc, deleteDoc, updateDocStrategy, updateDoc } from "@/helper/docs";

import { FileText, Trash2, Loader2, RefreshCw, Check, X, Pencil } from "lucide-react";

import { Button } from "@/components/ui/button";

import { Input } from "@/components/ui/input";

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

function fmtDate(iso: string | null | undefined): string {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB", {
      day: "2-digit", month: "short", year: "numeric",
    });
  } catch {
    return iso;
  }
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
  subject: string | null;
  published_date: string | null;
  createdAt: string | null;
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

  // Inline edit panel
  const [editId, setEditId] = useState<number | null>(null);
  const [editFields, setEditFields] = useState({ displayName: "", subject: "", published_date: "" });
  const [saving, setSaving] = useState(false);

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
  // EDIT
  // ======================================
  const openEdit = (doc: Doc) => {
    setEditId(doc.id);
    setEditFields({
      displayName: doc.displayName,
      subject: doc.subject ?? "",
      published_date: doc.published_date ?? "",
    });
  };

  const closeEdit = () => {
    setEditId(null);
    setEditFields({ displayName: "", subject: "", published_date: "" });
  };

  const confirmEdit = async (docId: number) => {
    try {
      setSaving(true);
      await updateDoc(docId, editFields);
      setDocs((prev) =>
        prev.map((d) =>
          d.id === docId
            ? { ...d, displayName: editFields.displayName, subject: editFields.subject || null, published_date: editFields.published_date || null }
            : d,
        ),
      );
      closeEdit();
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
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
            <table className="w-full min-w-[700px]">
              <thead>
                <tr className="border-b text-left">
                  <th className="p-4">Document</th>
                  <th className="p-4">Published Date</th>
                  <th className="p-4">Upload Date</th>
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
                            {doc.subject && (
                              <p className="text-xs text-primary/70 max-w-[260px] truncate" title={doc.subject}>
                                {doc.subject}
                              </p>
                            )}
                            <p className="text-xs text-muted-foreground">
                              {doc.fileName}
                            </p>
                          </div>
                        </div>
                      </td>

                      {/* PUBLISHED DATE */}
                      <td className="p-4 text-sm">
                        {doc.published_date ? fmtDate(doc.published_date) : (
                          <span className="text-muted-foreground">Not set</span>
                        )}
                      </td>

                      {/* UPLOAD DATE */}
                      <td className="p-4 text-sm text-muted-foreground">
                        {fmtDate(doc.createdAt)}
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

                          {/* EDIT (toggle panel) */}
                          <Button
                            size="sm"
                            variant="outline"
                            onClick={() =>
                              editId === doc.id ? closeEdit() : openEdit(doc)
                            }
                            title="Edit document name, subject, published date"
                          >
                            <Pencil className="h-4 w-4" />
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
                        <td colSpan={6} className="px-6 py-4">
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

                    {/* INLINE EDIT PANEL */}
                    {editId === doc.id && (
                      <tr className="bg-muted/30">
                        <td colSpan={6} className="px-6 py-4">
                          <div className="flex flex-wrap items-end gap-4">
                            <div>
                              <label className="mb-1 block text-xs font-medium">
                                Display Name
                              </label>
                              <Input
                                value={editFields.displayName}
                                onChange={(e) =>
                                  setEditFields((f) => ({ ...f, displayName: e.target.value }))
                                }
                                className="h-8 w-56 text-sm"
                              />
                            </div>
                            <div>
                              <label className="mb-1 block text-xs font-medium">
                                Subject / Title
                              </label>
                              <Input
                                value={editFields.subject}
                                onChange={(e) =>
                                  setEditFields((f) => ({ ...f, subject: e.target.value }))
                                }
                                placeholder="Circular title shown in source box"
                                className="h-8 w-80 text-sm"
                              />
                            </div>
                            <div>
                              <label className="mb-1 block text-xs font-medium">
                                Published Date
                              </label>
                              <Input
                                type="date"
                                value={editFields.published_date}
                                onChange={(e) =>
                                  setEditFields((f) => ({ ...f, published_date: e.target.value }))
                                }
                                className="h-8 w-40 text-sm"
                              />
                            </div>
                            <Button
                              size="sm"
                              disabled={saving}
                              onClick={() => confirmEdit(doc.id)}
                            >
                              {saving ? (
                                <Loader2 className="mr-1 h-4 w-4 animate-spin" />
                              ) : (
                                <Check className="mr-1 h-4 w-4" />
                              )}
                              Save
                            </Button>
                            <Button
                              size="sm"
                              variant="ghost"
                              disabled={saving}
                              onClick={closeEdit}
                            >
                              <X className="mr-1 h-4 w-4" />
                              Cancel
                            </Button>
                          </div>
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
