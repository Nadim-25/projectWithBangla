"use client";

import { sendMessage } from "@/helper/message";
import { useRouter } from "next/navigation";
import { useState } from "react";

import {
  ArrowUp,
  Sparkles,
  FileText,
  BrainCircuit,
  Loader2,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";

export default function AskQuestionPage() {
  const [question, setQuestion] = useState("");
  const [loading, setLoading] = useState(false);

  const router = useRouter();

  // =========================
  // SEND MESSAGE
  // =========================
  const handleSend = async () => {
    if (!question.trim()) return;

    try {
      setLoading(true);

      // create new chat
      const res = await sendMessage(question);

      // redirect to generated chat
      router.push(`/dashboard/chat/${res.chatId}`);
    } catch (err: any) {
      alert(err.message || "Failed to create chat");
    } finally {
      setLoading(false);
    }
  };

  // =========================
  // ENTER TO SEND
  // =========================
  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <div className="flex h-full flex-col items-center justify-center px-4">
      {/* HERO */}
      <div className="mb-10 text-center">
        <div className="mb-5 flex justify-center">
          <div className="rounded-2xl border bg-background p-4 shadow-sm">
            <BrainCircuit className="h-10 w-10" />
          </div>
        </div>

        <h1 className="text-2xl sm:text-4xl font-bold tracking-tight">
          How can I help today?
        </h1>
      </div>

      {/* INPUT CARD */}
      <Card className="w-full max-w-3xl rounded-3xl border bg-background/80 p-4 shadow-xl backdrop-blur">
        {/* TEXTAREA */}
        <div className="relative">
          <Textarea
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Message AI assistant..."
            className="min-h-[120px] resize-none border-0 bg-transparent pr-14 pt-4 text-base shadow-none focus-visible:ring-0"
          />

          {/* SEND BUTTON */}
          <Button
            size="icon"
            disabled={loading || !question.trim()}
            onClick={handleSend}
            className="absolute bottom-3 right-3 h-10 w-10 rounded-xl"
          >
            {loading ? (
              <Loader2 className="h-4 w-4 animate-spin" />
            ) : (
              <ArrowUp className="h-4 w-4" />
            )}
          </Button>
        </div>

        {/* FOOTER */}
        <div className="mt-4 flex flex-wrap items-center gap-2 border-t pt-4">
          <div className="flex items-center gap-2 rounded-full border px-3 py-1 text-sm text-muted-foreground">
            <Sparkles className="h-4 w-4" />
            AI Powered
          </div>

          <div className="flex items-center gap-2 rounded-full border px-3 py-1 text-sm text-muted-foreground">
            <FileText className="h-4 w-4" />
            PDF / DOC / DOCX
          </div>
        </div>
      </Card>
    </div>
  );
}
