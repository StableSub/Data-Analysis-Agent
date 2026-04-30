import React, { Fragment, useState } from "react";
import { Check, Copy } from "lucide-react";

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

function renderInlineContent(text: string, keyPrefix: string): React.ReactNode[] {
  const nodes: React.ReactNode[] = [];
  const pattern = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`|(https?:\/\/[^\s<]+))/g;
  let lastIndex = 0;
  let tokenIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const [, , linkText, linkUrl, codeText, rawUrl] = match;
    const key = `${keyPrefix}-${tokenIndex}`;

    if (linkText && linkUrl) {
      nodes.push(
        <a
          key={key}
          href={linkUrl}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[var(--genui-running)] underline underline-offset-2 hover:opacity-80"
        >
          {linkText}
        </a>,
      );
    } else if (codeText) {
      nodes.push(
        <code
          key={key}
          className="rounded bg-[var(--genui-surface)] px-1.5 py-0.5 font-mono text-[0.92em] text-[var(--genui-text)]"
        >
          {codeText}
        </code>,
      );
    } else if (rawUrl) {
      nodes.push(
        <a
          key={key}
          href={rawUrl}
          target="_blank"
          rel="noreferrer"
          className="font-medium text-[var(--genui-running)] underline underline-offset-2 hover:opacity-80"
        >
          {rawUrl}
        </a>,
      );
    }

    lastIndex = match.index + match[0].length;
    tokenIndex += 1;
  }

  if (lastIndex < text.length) {
    nodes.push(text.slice(lastIndex));
  }

  return nodes;
}

function renderParagraphLines(text: string, keyPrefix: string) {
  return text.split("\n").map((line, index, lines) => (
    <Fragment key={`${keyPrefix}-line-${index}`}>
      {renderInlineContent(line, `${keyPrefix}-${index}`)}
      {index < lines.length - 1 ? <br /> : null}
    </Fragment>
  ));
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
        {renderParagraphLines(text, "label-value")}
      </span>
    );
  }

  return (
    <span className="block text-left">
      <span className="block whitespace-pre-wrap break-words font-medium [overflow-wrap:anywhere]">
        {renderParagraphLines(`${split.label}:`, "label")}
      </span>
      <span className="mt-0.5 block whitespace-pre-wrap break-words text-[var(--genui-text)] [overflow-wrap:anywhere]">
        {renderParagraphLines(split.body, "body")}
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

        const paragraphs = block.content
          .split(/\n{2,}/)
          .map((item) => item.trim())
          .filter(Boolean);

        return (
          <div key={`text-${blockIndex}`} className="space-y-2.5">
            {paragraphs.map((paragraph, paragraphIndex) => (
              <p
                key={`paragraph-${blockIndex}-${paragraphIndex}`}
                className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--genui-text)] [overflow-wrap:anywhere]"
              >
                {renderParagraphLines(paragraph, `paragraph-${blockIndex}-${paragraphIndex}`)}
              </p>
            ))}
          </div>
        );
      })}
      {isStreaming && isLast && (
        <span className="inline-block h-[14px] w-[7px] animate-pulse rounded-[1px] bg-[var(--genui-text)] align-middle" />
      )}
    </div>
  );
}
