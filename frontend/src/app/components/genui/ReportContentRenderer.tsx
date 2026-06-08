import { useState } from "react";
import { Check, Copy } from "lucide-react";
import { renderMarkdownLines, renderMarkdownReportContent } from "./MarkdownReportRenderer";

interface CodeBlockProps {
  code: string;
  language?: string;
}

interface LabelValueTextProps {
  text: string;
}

interface ReportTextContentProps {
  content: string;
  isStreaming?: boolean;
  isLast?: boolean;
}

type TextBlock =
  | { type: "text"; content: string }
  | { type: "code"; content: string; language?: string };

function splitLabelAndBody(text: string): { label: string; body: string } | null {
  const match = text.match(/^\s*([^:\n]{1,80}?)\s*[:：]\s+(.+)$/);
  if (!match) {
    return null;
  }

  const label = match[1].trim();
  const body = match[2].trim();
  if (!label || !body) {
    return null;
  }

  return { label, body };
}

function parseTextBlocks(content: string): TextBlock[] {
  const normalized = content.replace(/\r\n?/g, "\n");
  const lines = normalized.split("\n");
  const blocks: TextBlock[] = [];
  let textBuffer: string[] = [];
  let lineIndex = 0;

  const flushText = () => {
    const text = textBuffer.join("\n").trim();
    if (text) {
      blocks.push({ type: "text", content: text });
    }
    textBuffer = [];
  };

  while (lineIndex < lines.length) {
    const line = lines[lineIndex];
    const fenceMatch = line.trim().match(/^```([\w-]+)?$/);

    if (!fenceMatch) {
      textBuffer.push(line);
      lineIndex += 1;
      continue;
    }

    flushText();
    const language = fenceMatch[1];
    lineIndex += 1;

    const codeLines: string[] = [];
    while (lineIndex < lines.length && !lines[lineIndex].trim().match(/^```$/)) {
      codeLines.push(lines[lineIndex]);
      lineIndex += 1;
    }

    if (lineIndex < lines.length) {
      lineIndex += 1;
    }

    blocks.push({
      type: "code",
      content: codeLines.join("\n"),
      language,
    });
  }

  flushText();
  return blocks;
}

export function CodeBlock({ code, language }: CodeBlockProps) {
  const [copied, setCopied] = useState(false);

  const handleCopy = () => {
    navigator.clipboard.writeText(code).catch(() => {});
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  };

  return (
    <div className="relative my-1 overflow-hidden rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)]">
      <div className="flex items-center justify-between border-b border-[var(--genui-border)] bg-[var(--genui-panel)] px-3 py-1.5">
        <span className="text-[10px] font-mono font-semibold uppercase tracking-wider text-[var(--genui-muted)]">
          {language ?? "code"}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 text-[10px] text-[var(--genui-muted)] transition-colors hover:text-[var(--genui-text)]"
          title="Copy"
        >
          {copied ? (
            <Check className="h-3 w-3 text-[var(--genui-success)]" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
          {copied ? "Copied!" : "Copy"}
        </button>
      </div>
      <pre className="overflow-x-auto whitespace-pre px-4 py-3 text-[11px] leading-relaxed text-[var(--genui-text)]">
        <code>{code}</code>
      </pre>
    </div>
  );
}

export function LabelValueText({ text }: LabelValueTextProps) {
  const split = splitLabelAndBody(text);

  if (!split) {
    return (
      <span className="whitespace-pre-wrap break-words [overflow-wrap:anywhere]">
        {renderMarkdownLines(text, "label-value")}
      </span>
    );
  }

  return (
    <span className="block text-left">
      <span className="block whitespace-pre-wrap break-words font-medium [overflow-wrap:anywhere]">
        {renderMarkdownLines(`${split.label}:`, "label")}
      </span>
      <span className="mt-0.5 block whitespace-pre-wrap break-words text-[var(--genui-text)] [overflow-wrap:anywhere]">
        {renderMarkdownLines(split.body, "body")}
      </span>
    </span>
  );
}

export function ReportTextContent({
  content,
  isStreaming = false,
  isLast = false,
}: ReportTextContentProps) {
  const blocks = parseTextBlocks(content);

  return (
    <div className="space-y-2.5 text-left">
      {blocks.map((block, blockIndex) => {
        if (block.type === "code") {
          return (
            <CodeBlock
              key={`code-${blockIndex}`}
              code={block.content}
              language={block.language}
            />
          );
        }

        return (
          <div key={`text-${blockIndex}`} className="space-y-2.5">
            {renderMarkdownReportContent(block.content, `text-${blockIndex}`)}
          </div>
        );
      })}
      {isStreaming && isLast && (
        <span className="inline-block h-[14px] w-[7px] animate-pulse rounded-[1px] bg-[var(--genui-text)] align-middle" />
      )}
    </div>
  );
}
