"use client";

import { useEffect, useRef, useState } from "react";
import { useParams } from "next/navigation";
import { getChatById, getToken } from "@/helper/tokenHelper";
import { sendMessage } from "@/helper/message";
import { useAuth } from "@/context/AuthContext";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import {
  ArrowUp,
  Sparkles,
  Copy,
  Check,
  Loader2,
  FileText,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  X,
  BookOpen,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";

type Source = {
  name: string;
  subject?: string | null;
  circular_ref?: string | null;
  circular_date?: string | null;
  document_id?: number | null;
  page?: number | null;
};

type Message = {
  question: string;
  answer: string;
  sources?: Source[];
};

function TypingDots() {
  return (
    <div className="flex items-center gap-1 py-1">
      <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:0ms]" />
      <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:150ms]" />
      <span className="h-2 w-2 rounded-full bg-muted-foreground/50 animate-bounce [animation-delay:300ms]" />
    </div>
  );
}

function PageImageModal({
  docId,
  page,
  onClose,
}: {
  docId: number;
  page: number;
  onClose: () => void;
}) {
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [err, setErr] = useState(false);
  const [zoom, setZoom] = useState(1);

  useEffect(() => {
    setZoom(1);
    const token = getToken();
    const url = `${process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}/document/${docId}/page/${page}`;
    let objectUrl: string | null = null;
    fetch(url, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setImgSrc(objectUrl);
      })
      .catch(() => setErr(true));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId, page]);

  const zoomOut = () => setZoom((z) => Math.max(0.5, parseFloat((z - 0.25).toFixed(2))));
  const zoomIn  = () => setZoom((z) => Math.min(4,   parseFloat((z + 0.25).toFixed(2))));
  const reset   = () => setZoom(1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex flex-col rounded-xl bg-background shadow-2xl overflow-hidden"
        style={{ maxHeight: "92vh", maxWidth: "92vw", minWidth: "18rem" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* ── toolbar ── */}
        <div className="flex shrink-0 items-center justify-between gap-3 border-b px-4 py-2">
          <span className="text-sm font-medium text-muted-foreground">
            Page {page}
          </span>

          <div className="flex items-center gap-1">
            <button
              onClick={zoomOut}
              disabled={zoom <= 0.5}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
              title="Zoom out"
            >
              <ZoomOut className="h-4 w-4" />
            </button>

            <button
              onClick={reset}
              className="min-w-[3.5rem] rounded-md px-2 py-0.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
              title="Reset zoom"
            >
              <span className="flex items-center gap-1">
                <RotateCcw className="h-3 w-3" />
                {Math.round(zoom * 100)}%
              </span>
            </button>

            <button
              onClick={zoomIn}
              disabled={zoom >= 4}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
              title="Zoom in"
            >
              <ZoomIn className="h-4 w-4" />
            </button>
          </div>

          <button
            onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground hover:bg-muted transition-colors"
            title="Close"
          >
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* ── image area ── */}
        <div className="overflow-auto flex-1" style={{ minHeight: 0 }}>
          {err ? (
            <p className="px-8 py-12 text-sm text-destructive">
              Could not load page image.
            </p>
          ) : imgSrc ? (
            <div className="p-4" style={{ width: `${zoom * 100}%`, minWidth: `${zoom * 100}%` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img
                src={imgSrc}
                alt={`Page ${page}`}
                style={{ display: "block", width: "100%", height: "auto" }}
              />
            </div>
          ) : (
            <div className="flex h-64 w-64 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

function FullCircularModal({
  docId,
  initialPage,
  onClose,
}: {
  docId: number;
  initialPage: number;
  onClose: () => void;
}) {
  const [pageCount, setPageCount] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(initialPage);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [err, setErr] = useState(false);
  const [zoom, setZoom] = useState(1);

  // Fetch total page count once
  useEffect(() => {
    const token = getToken();
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    fetch(`${base}/document/${docId}/pages`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((d) => setPageCount(d.page_count ?? null))
      .catch(() => {});
  }, [docId]);

  // Load page image whenever currentPage changes
  useEffect(() => {
    setImgSrc(null);
    setErr(false);
    setZoom(1);
    const token = getToken();
    const base = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";
    let objectUrl: string | null = null;
    fetch(`${base}/document/${docId}/page/${currentPage}`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => {
        if (!r.ok) throw new Error("not ok");
        return r.blob();
      })
      .then((blob) => {
        objectUrl = URL.createObjectURL(blob);
        setImgSrc(objectUrl);
      })
      .catch(() => setErr(true));
    return () => {
      if (objectUrl) URL.revokeObjectURL(objectUrl);
    };
  }, [docId, currentPage]);

  const prev = () => setCurrentPage((p) => Math.max(1, p - 1));
  const next = () => setCurrentPage((p) => (pageCount ? Math.min(pageCount, p + 1) : p + 1));
  const zoomOut = () => setZoom((z) => Math.max(0.5, parseFloat((z - 0.25).toFixed(2))));
  const zoomIn  = () => setZoom((z) => Math.min(4,   parseFloat((z + 0.25).toFixed(2))));
  const reset   = () => setZoom(1);

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 backdrop-blur-sm"
      onClick={onClose}
    >
      <div
        className="flex flex-col rounded-xl bg-background shadow-2xl overflow-hidden"
        style={{ maxHeight: "92vh", maxWidth: "92vw", minWidth: "18rem" }}
        onClick={(e) => e.stopPropagation()}
      >
        {/* toolbar */}
        <div className="flex shrink-0 items-center justify-between gap-2 border-b px-4 py-2">
          {/* page navigation */}
          <div className="flex items-center gap-1">
            <button
              onClick={prev}
              disabled={currentPage <= 1}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
              title="Previous page"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="min-w-[5rem] text-center text-sm font-medium text-muted-foreground">
              {pageCount ? `${currentPage} / ${pageCount}` : `Page ${currentPage}`}
            </span>
            <button
              onClick={next}
              disabled={pageCount !== null && currentPage >= pageCount}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
              title="Next page"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* zoom controls */}
          <div className="flex items-center gap-1">
            <button onClick={zoomOut} disabled={zoom <= 0.5}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors">
              <ZoomOut className="h-4 w-4" />
            </button>
            <button onClick={reset}
              className="min-w-[3.5rem] rounded-md px-2 py-0.5 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors">
              <span className="flex items-center gap-1">
                <RotateCcw className="h-3 w-3" />
                {Math.round(zoom * 100)}%
              </span>
            </button>
            <button onClick={zoomIn} disabled={zoom >= 4}
              className="flex h-7 w-7 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors">
              <ZoomIn className="h-4 w-4" />
            </button>
          </div>

          <button onClick={onClose}
            className="flex h-7 w-7 items-center justify-center rounded-full text-muted-foreground hover:bg-muted transition-colors">
            <X className="h-4 w-4" />
          </button>
        </div>

        {/* image area */}
        <div className="overflow-auto flex-1" style={{ minHeight: 0 }}>
          {err ? (
            <p className="px-8 py-12 text-sm text-destructive">Could not load page image.</p>
          ) : imgSrc ? (
            <div className="p-4" style={{ width: `${zoom * 100}%`, minWidth: `${zoom * 100}%` }}>
              {/* eslint-disable-next-line @next/next/no-img-element */}
              <img src={imgSrc} alt={`Page ${currentPage}`}
                style={{ display: "block", width: "100%", height: "auto" }} />
            </div>
          ) : (
            <div className="flex h-64 w-64 items-center justify-center">
              <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}


function SourceCard({ sources }: { sources: Source[] }) {
  const [modal, setModal] = useState<{ docId: number; page: number } | null>(null);
  const [fullModal, setFullModal] = useState<{ docId: number; page: number } | null>(null);

  if (!sources || sources.length === 0) return null;

  // All sources come from the same document — pick the first non-null value.
  const name          = sources[0].name;
  const subject       = sources.find((s) => s.subject)?.subject       ?? null;
  const circular_ref  = sources.find((s) => s.circular_ref)?.circular_ref  ?? null;
  const circular_date = sources.find((s) => s.circular_date)?.circular_date ?? null;
  const doc_id        = sources.find((s) => s.document_id)?.document_id    ?? null;

  // Deduplicate and sort pages.
  const seen = new Set<number>();
  const pages = sources
    .filter((s) => s.page != null && !seen.has(s.page!) && seen.add(s.page!))
    .sort((a, b) => (a.page ?? 0) - (b.page ?? 0));

  return (
    <>
      <div className="mt-4 w-fit max-w-sm rounded-xl border bg-muted/30 px-4 py-3 text-sm shadow-sm">
        {/* document name + full circular button */}
        <div className="mb-2 flex items-center justify-between gap-3">
          <div className="flex items-center gap-2 min-w-0">
            <FileText className="h-4 w-4 shrink-0 text-primary" />
            <span className="font-semibold text-foreground truncate">{name}</span>
          </div>
          {doc_id != null && (
            <button
              onClick={() => setFullModal({ docId: doc_id, page: 1 })}
              className="flex shrink-0 items-center gap-1 rounded-md border border-primary/30 bg-primary/5 px-2 py-1 text-xs font-medium text-primary hover:bg-primary/15 transition-colors"
              title="View full circular"
            >
              <BookOpen className="h-3.5 w-3.5" />
              Full Circular
            </button>
          )}
        </div>

        {/* subject */}
        {subject && (
          <p className="mb-1 text-xs font-medium text-foreground/80 leading-snug">
            {subject}
          </p>
        )}

        {/* circular reference */}
        {circular_ref && (
          <p className="mb-0.5 text-xs text-muted-foreground leading-snug">
            {circular_ref}
          </p>
        )}

        {/* issue date */}
        {circular_date && (
          <p className="mb-3 text-xs text-muted-foreground">{circular_date}</p>
        )}

        {/* relevant pages */}
        {pages.length > 0 && (
          <div className="flex flex-wrap items-center gap-1.5">
            <span className="text-xs text-muted-foreground">Relevant pages:</span>
            {pages.map((src, i) =>
              src.document_id != null ? (
                <button
                  key={i}
                  onClick={() => setModal({ docId: src.document_id!, page: src.page! })}
                  className="rounded-md bg-primary/10 px-2 py-0.5 text-xs font-semibold text-primary hover:bg-primary/20 transition-colors"
                  title={`View page ${src.page}`}
                >
                  p.{src.page}
                </button>
              ) : (
                <span key={i} className="rounded-md bg-muted px-2 py-0.5 text-xs font-medium text-muted-foreground">
                  p.{src.page}
                </span>
              ),
            )}
          </div>
        )}
      </div>

      {modal && (
        <PageImageModal
          docId={modal.docId}
          page={modal.page}
          onClose={() => setModal(null)}
        />
      )}

      {fullModal && (
        <FullCircularModal
          docId={fullModal.docId}
          initialPage={fullModal.page}
          onClose={() => setFullModal(null)}
        />
      )}
    </>
  );
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    await navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <button
      onClick={handleCopy}
      className="mt-2 flex items-center gap-1 text-xs text-muted-foreground opacity-0 group-hover:opacity-100 transition-opacity hover:text-foreground"
    >
      {copied ? (
        <>
          <Check className="h-3 w-3" />
          Copied
        </>
      ) : (
        <>
          <Copy className="h-3 w-3" />
          Copy
        </>
      )}
    </button>
  );
}

export default function ChatPage() {
  const params = useParams();
  const { user } = useAuth();
  const chatId = Number(params?.id);

  const [messages, setMessages] = useState<Message[]>([]);
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);
  const [pageLoading, setPageLoading] = useState(true);

  const bottomRef = useRef<HTMLDivElement | null>(null);
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);

  const initials =
    user?.fullName
      ?.split(" ")
      .map((n: string) => n[0])
      .join("")
      .slice(0, 2)
      .toUpperCase() ?? "U";

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  useEffect(() => {
    if (!chatId) return;
    const load = async () => {
      try {
        const res = await getChatById(chatId);
        setMessages(Array.isArray(res.messages) ? res.messages : []);
      } catch (err) {
        console.error(err);
      } finally {
        setPageLoading(false);
      }
    };
    load();
  }, [chatId]);

  const handleSend = async () => {
    if (!question.trim() || loading) return;
    const currentQuestion = question;
    setQuestion("");
    if (textareaRef.current) textareaRef.current.style.height = "auto";

    try {
      setLoading(true);
      setMessages((prev) => [
        ...prev,
        { question: currentQuestion, answer: "" },
      ]);
      const res = await sendMessage(currentQuestion, chatId);
      setMessages((prev) =>
        prev.map((msg, i) =>
          i === prev.length - 1
            ? { ...msg, answer: res.answer, sources: res.sources ?? [] }
            : msg,
        ),
      );
    } catch (err: unknown) {
      alert(err instanceof Error ? err.message : "An error occurred");
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const handleTextareaChange = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setQuestion(e.target.value);
    e.target.style.height = "auto";
    e.target.style.height = Math.min(e.target.scrollHeight, 160) + "px";
  };

  if (pageLoading) {
    return (
      <div className="flex h-[calc(100vh-56px)] items-center justify-center">
        <Loader2 className="h-6 w-6 animate-spin text-muted-foreground" />
      </div>
    );
  }

  return (
    <div className="flex h-[calc(100vh-56px)] flex-col bg-background">
      {/* ── HEADER ── */}
      {/* <div className="flex items-center gap-3 border-b px-4 py-3 shrink-0">
        <button
          onClick={() => router.push("/dashboard/ask-question")}
          className="flex items-center justify-center rounded-lg p-1.5 text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
        </button>

        <div className="flex items-center gap-2">
          <div className="flex h-7 w-7 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-pink-500">
            <Sparkles className="h-3.5 w-3.5 text-white" />
          </div>
          <span className="text-sm font-semibold">IDLC AI Assistant</span>
        </div>

        <div className="ml-auto flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs text-muted-foreground">
          <span className="h-1.5 w-1.5 rounded-full bg-green-500" />
          Online
        </div>
      </div> */}

      {/* ── MESSAGES ── */}
      <div className="flex-1 overflow-y-auto">
        <div className="mx-auto w-full max-w-3xl px-4 py-8 space-y-10">
          {/* Empty state */}
          {messages.length === 0 && (
            <div className="flex flex-col items-center justify-center py-24 text-center">
              <div className="mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-orange-400 to-pink-500 shadow-lg">
                <Sparkles className="h-8 w-8 text-white" />
              </div>
              <h2 className="text-xl font-semibold">Start the conversation</h2>
              <p className="mt-2 max-w-sm text-sm text-muted-foreground">
                Ask anything about your documents, financial data, or reports.
              </p>
            </div>
          )}

          {messages.map((m, i) => (
            <div key={i} className="space-y-6">
              {/* USER MESSAGE */}
              <div className="flex justify-end">
                <div className="flex items-end gap-2.5 max-w-[80%]">
                  <div className="rounded-2xl rounded-br-sm bg-indigo-600 px-4 py-3 text-sm text-white shadow-sm leading-relaxed">
                    {m.question}
                  </div>
                  <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-indigo-500 to-blue-600 text-xs font-bold text-white shadow-sm">
                    {initials}
                  </div>
                </div>
              </div>

              {/* AI MESSAGE */}
              <div className="flex items-start gap-3 group">
                <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-gradient-to-br from-orange-400 to-pink-500 shadow-sm">
                  <Sparkles className="h-3.5 w-3.5 text-white" />
                </div>

                <div className="flex-1 min-w-0">
                  {m.answer ? (
                    <>
                      <div className="prose prose-sm dark:prose-invert max-w-none text-foreground
                        prose-table:border-collapse
                        prose-th:border prose-th:border-border prose-th:bg-muted prose-th:px-3 prose-th:py-2 prose-th:text-left prose-th:text-xs prose-th:font-semibold prose-th:uppercase prose-th:tracking-wide
                        prose-td:border prose-td:border-border prose-td:px-3 prose-td:py-2 prose-td:text-sm prose-td:align-top
                        prose-tr:even:bg-muted/30
                        prose-p:leading-7 prose-p:my-2
                        prose-ul:my-2 prose-li:my-0.5
                        prose-strong:font-semibold">
                        <ReactMarkdown remarkPlugins={[remarkGfm]}>
                          {m.answer}
                        </ReactMarkdown>
                      </div>
                      {m.sources && m.sources.length > 0 && (
                        <SourceCard sources={m.sources} />
                      )}
                      <CopyButton text={m.answer} />
                    </>
                  ) : (
                    <TypingDots />
                  )}
                </div>
              </div>
            </div>
          ))}

          <div ref={bottomRef} />
        </div>
      </div>

      {/* ── INPUT ── */}
      <div className="shrink-0 border-t bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60 px-4 py-4">
        <div className="mx-auto w-full max-w-3xl">
          <div className="relative flex items-end gap-2 rounded-2xl border bg-background shadow-sm ring-1 ring-transparent focus-within:ring-primary/30 transition-all px-4 py-3">
            <textarea
              ref={textareaRef}
              value={question}
              onChange={handleTextareaChange}
              onKeyDown={handleKeyDown}
              placeholder="Message IDLC AI..."
              rows={1}
              className="flex-1 resize-none bg-transparent text-sm outline-none placeholder:text-muted-foreground max-h-40 leading-6"
            />

            <button
              onClick={handleSend}
              disabled={loading || !question.trim()}
              className="flex h-8 w-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground transition-all hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-40"
            >
              {loading ? (
                <Loader2 className="h-4 w-4 animate-spin" />
              ) : (
                <ArrowUp className="h-4 w-4" />
              )}
            </button>
          </div>

          <p className="mt-2 text-center text-xs text-muted-foreground">
            IDLC AI can make mistakes. Always verify important information.
          </p>
        </div>
      </div>
    </div>
  );
}
