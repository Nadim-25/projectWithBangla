"use client";

import { useEffect, useRef, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { getChatById } from "@/helper/tokenHelper";
import { sendMessage } from "@/helper/message";
import { useAuth } from "@/context/AuthContext";

import {
  ArrowUp,
  ArrowLeft,
  Sparkles,
  User,
  Copy,
  Check,
  Loader2,
} from "lucide-react";

type Message = {
  question: string;
  answer: string;
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
  const router = useRouter();
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
          i === prev.length - 1 ? { ...msg, answer: res.answer } : msg,
        ),
      );
    } catch (err: any) {
      alert(err.message);
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
                      <div className="text-sm leading-7 text-foreground whitespace-pre-wrap">
                        {m.answer}
                      </div>
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
