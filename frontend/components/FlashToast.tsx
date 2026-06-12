"use client";

import { useFlash } from "@/context/FlashContext";
import { X, CheckCircle, AlertCircle, Info } from "lucide-react";

const styles = {
  success: {
    container: "bg-emerald-50 border-emerald-400 text-emerald-800",
    icon: <CheckCircle className="h-4 w-4 text-emerald-500 shrink-0" />,
  },
  error: {
    container: "bg-red-50 border-red-400 text-red-800",
    icon: <AlertCircle className="h-4 w-4 text-red-500 shrink-0" />,
  },
  info: {
    container: "bg-blue-50 border-blue-400 text-blue-800",
    icon: <Info className="h-4 w-4 text-blue-500 shrink-0" />,
  },
};

export default function FlashToast() {
  const { flashes, dismiss } = useFlash();

  if (flashes.length === 0) return null;

  return (
    <div className="fixed top-4 right-4 z-[9999] flex flex-col gap-2 w-full max-w-sm">
      {flashes.map((flash) => {
        const s = styles[flash.type];
        return (
          <div
            key={flash.id}
            className={`flex items-start gap-3 rounded-lg border px-4 py-3 shadow-lg text-sm animate-in slide-in-from-top-2 fade-in duration-300 ${s.container}`}
          >
            {s.icon}
            <span className="flex-1">{flash.message}</span>
            <button
              onClick={() => dismiss(flash.id)}
              className="opacity-60 hover:opacity-100 transition-opacity"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          </div>
        );
      })}
    </div>
  );
}
