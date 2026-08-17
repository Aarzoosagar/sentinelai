import clsx from "clsx";
import { ShieldCheck, User as UserIcon } from "lucide-react";
import type { ChatMessage } from "@/types";

export function ChatBubble({ message }: { message: ChatMessage }) {
  const isUser = message.role === "user";
  return (
    <div className={clsx("flex gap-3", isUser && "flex-row-reverse")}>
      <span
        className={clsx(
          "flex h-7 w-7 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-white/10 text-text-secondary" : "bg-accent-blue/15 text-accent-blue"
        )}
      >
        {isUser ? <UserIcon className="h-3.5 w-3.5" /> : <ShieldCheck className="h-3.5 w-3.5" />}
      </span>
      <div
        className={clsx(
          "max-w-[75%] whitespace-pre-line rounded-xl px-3.5 py-2.5 text-sm",
          isUser ? "bg-accent-blue text-white" : "sentinel-card text-text-primary"
        )}
      >
        {message.content}
      </div>
    </div>
  );
}
