"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getToken } from "@/helper/tokenHelper";
import {
  Loader2,
  ZoomIn,
  ZoomOut,
  RotateCcw,
  ChevronLeft,
  ChevronRight,
  ArrowLeft,
} from "lucide-react";
import { BASE_URL } from "@/settings";

export default function CircularViewerPage() {
  const { id } = useParams<{ id: string }>();
  const router = useRouter();
  const docId = Number(id);

  const [pageCount, setPageCount] = useState<number | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [imgSrc, setImgSrc] = useState<string | null>(null);
  const [err, setErr] = useState(false);
  const [zoom, setZoom] = useState(1);

  // Fetch total page count
  useEffect(() => {
    if (!docId) return;
    const token = getToken();
    fetch(`${BASE_URL}/document/${docId}/pages`, {
      headers: token ? { Authorization: `Bearer ${token}` } : {},
    })
      .then((r) => r.json())
      .then((d) => setPageCount(d.page_count ?? null))
      .catch(() => {});
  }, [docId]);

  // Load page image
  useEffect(() => {
    if (!docId) return;
    setImgSrc(null);
    setErr(false);
    setZoom(1);
    const token = getToken();
    let objectUrl: string | null = null;
    fetch(`${BASE_URL}/document/${docId}/page/${currentPage}`, {
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
  const next = () =>
    setCurrentPage((p) => (pageCount ? Math.min(pageCount, p + 1) : p + 1));
  const zoomOut = () =>
    setZoom((z) => Math.max(0.5, parseFloat((z - 0.25).toFixed(2))));
  const zoomIn = () =>
    setZoom((z) => Math.min(4, parseFloat((z + 0.25).toFixed(2))));
  const reset = () => setZoom(1);

  return (
    <div className="flex h-[calc(100vh-56px)] flex-col bg-background">
      {/* TOOLBAR */}
      <div className="flex shrink-0 items-center justify-between gap-2 border-b bg-background px-4 py-2 shadow-sm">
        {/* back button */}
        <button
          onClick={() => router.back()}
          className="flex items-center gap-1.5 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted hover:text-foreground transition-colors"
          title="Back to circulars"
        >
          <ArrowLeft className="h-4 w-4" />
          <span className="hidden sm:inline">Back</span>
        </button>

        {/* page navigation */}
        <div className="flex items-center gap-1">
          <button
            onClick={prev}
            disabled={currentPage <= 1}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
            title="Previous page"
          >
            <ChevronLeft className="h-4 w-4" />
          </button>
          <span className="min-w-[5.5rem] text-center text-sm font-medium tabular-nums">
            {pageCount ? `${currentPage} / ${pageCount}` : `Page ${currentPage}`}
          </span>
          <button
            onClick={next}
            disabled={pageCount !== null && currentPage >= pageCount}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
            title="Next page"
          >
            <ChevronRight className="h-4 w-4" />
          </button>
        </div>

        {/* zoom controls */}
        <div className="flex items-center gap-1">
          <button
            onClick={zoomOut}
            disabled={zoom <= 0.5}
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
            title="Zoom out"
          >
            <ZoomOut className="h-4 w-4" />
          </button>
          <button
            onClick={reset}
            className="min-w-[3.5rem] rounded-md px-2 py-1 text-xs font-medium text-muted-foreground hover:bg-muted transition-colors"
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
            className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
            title="Zoom in"
          >
            <ZoomIn className="h-4 w-4" />
          </button>
        </div>
      </div>

      {/* PAGE IMAGE */}
      <div className="flex-1 overflow-auto bg-muted/20">
        {err ? (
          <div className="flex h-full items-center justify-center">
            <p className="text-sm text-destructive">Could not load page image.</p>
          </div>
        ) : imgSrc ? (
          <div
            className="mx-auto p-4 transition-all"
            style={{ width: `${zoom * 100}%`, minWidth: `${zoom * 100}%` }}
          >
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={imgSrc}
              alt={`Page ${currentPage}`}
              style={{ display: "block", width: "100%", height: "auto" }}
            />
          </div>
        ) : (
          <div className="flex h-full items-center justify-center">
            <Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
          </div>
        )}
      </div>

      {/* BOTTOM PAGE NAV (convenience repeat) */}
      <div className="flex shrink-0 items-center justify-center gap-2 border-t bg-background py-2">
        <button
          onClick={prev}
          disabled={currentPage <= 1}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
        >
          <ChevronLeft className="h-4 w-4" />
        </button>
        <span className="text-sm font-medium tabular-nums">
          {pageCount ? `${currentPage} / ${pageCount}` : `Page ${currentPage}`}
        </span>
        <button
          onClick={next}
          disabled={pageCount !== null && currentPage >= pageCount}
          className="flex h-8 w-8 items-center justify-center rounded-md text-muted-foreground hover:bg-muted disabled:opacity-30 transition-colors"
        >
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
}
