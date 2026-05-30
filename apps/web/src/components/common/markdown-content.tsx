import { Loader2 } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import { cn } from "@/lib/utils";

interface MarkdownContentProps {
  className?: string;
  content: string;
  isStreaming?: boolean;
}

export function MarkdownContent({
  className,
  content,
  isStreaming = false,
}: MarkdownContentProps) {
  return (
    <div className={cn("break-words", className)} data-testid="markdown-content">
      <ReactMarkdown
        components={{
          a: ({ children, href }) => (
            <a
              className="font-medium underline underline-offset-2 hover:opacity-80"
              href={href}
              rel="noreferrer"
              target="_blank"
            >
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 pl-3 italic opacity-90">
              {children}
            </blockquote>
          ),
          code: ({ children, className }) => (
            <code className={cn(className, "rounded bg-black/10 px-1 py-0.5 font-mono text-[0.85em]")}>
              {children}
            </code>
          ),
          li: ({ children }) => <li className="pl-1">{children}</li>,
          ol: ({ children }) => <ol className="my-2 list-decimal space-y-1 pl-5">{children}</ol>,
          p: ({ children }) => <p className="mb-3 whitespace-pre-wrap last:mb-0">{children}</p>,
          pre: ({ children }) => (
            <pre className="my-2 overflow-x-auto rounded-md bg-black/10 p-3 text-xs leading-5">
              {children}
            </pre>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto">
              <table className="min-w-full border-collapse text-left text-xs">
                {children}
              </table>
            </div>
          ),
          td: ({ children }) => <td className="border px-2 py-1">{children}</td>,
          th: ({ children }) => <th className="border px-2 py-1 font-semibold">{children}</th>,
          ul: ({ children }) => <ul className="my-2 list-disc space-y-1 pl-5">{children}</ul>,
        }}
        remarkPlugins={[remarkGfm]}
      >
        {content}
      </ReactMarkdown>
      {isStreaming ? (
        <Loader2 className="ml-2 inline-block h-3 w-3 animate-spin" aria-label="Streaming" />
      ) : null}
    </div>
  );
}
