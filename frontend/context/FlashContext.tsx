"use client";

import {
  createContext,
  useContext,
  useState,
  useCallback,
  useRef,
} from "react";

type FlashType = "success" | "error" | "info";

type Flash = {
  id: number;
  message: string;
  type: FlashType;
};

type FlashContextType = {
  showFlash: (message: string, type?: FlashType) => void;
  flashes: Flash[];
  dismiss: (id: number) => void;
};

const FlashContext = createContext<FlashContextType | null>(null);

export function FlashProvider({ children }: { children: React.ReactNode }) {
  const [flashes, setFlashes] = useState<Flash[]>([]);
  const counter = useRef(0);

  const dismiss = useCallback((id: number) => {
    setFlashes((prev) => prev.filter((f) => f.id !== id));
  }, []);

  const showFlash = useCallback(
    (message: string, type: FlashType = "info") => {
      const id = ++counter.current;
      setFlashes((prev) => [...prev, { id, message, type }]);
      setTimeout(() => dismiss(id), 3500);
    },
    [dismiss],
  );

  return (
    <FlashContext.Provider value={{ showFlash, flashes, dismiss }}>
      {children}
    </FlashContext.Provider>
  );
}

export function useFlash() {
  const ctx = useContext(FlashContext);
  if (!ctx) throw new Error("useFlash must be used inside FlashProvider");
  return ctx;
}
