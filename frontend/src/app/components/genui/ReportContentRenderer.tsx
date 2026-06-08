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

interface MarkdownTable {
  headers: string[];
  rows: string[][];
}

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
  const pattern = /(\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)|`([^`]+)`|\*\*([^*]+)\*\*|\*([^*]+)\*|(https?:\/\/[^\s<]+))/g;
  let lastIndex = 0;
  let tokenIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = pattern.exec(text)) !== null) {
    if (match.index > lastIndex) {
      nodes.push(text.slice(lastIndex, match.index));
    }

    const [, , linkText, linkUrl, codeText, strongText, emphasisText, rawUrl] = match;
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
    } else if (strongText) {
      nodes.push(
        <strong key={key} className="font-semibold text-[var(--genui-text)]">
          {strongText}
        </strong>,
      );
    } else if (emphasisText) {
      nodes.push(
        <em key={key} className="text-[var(--genui-text)]">
          {emphasisText}
        </em>,
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

function splitMarkdownTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

function parseMarkdownTable(lines: string[]): MarkdownTable | null {
  if (lines.length < 2) {
    return null;
  }

  const headers = splitMarkdownTableRow(lines[0]);
  const separator = splitMarkdownTableRow(lines[1]);
  if (headers.length < 2 || separator.length !== headers.length) {
    return null;
  }
  if (!separator.every((cell) => /^:?-{3,}:?$/.test(cell))) {
    return null;
  }

  const rows = lines.slice(2).map(splitMarkdownTableRow);
  if (rows.length === 0 || rows.some((row) => row.length !== headers.length)) {
    return null;
  }

  return { headers, rows };
}

function renderMarkdownTable(table: MarkdownTable, keyPrefix: string): React.ReactNode {
  return (
    <div key={keyPrefix} className="my-3 overflow-x-auto rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)]">
      <table className="min-w-full border-collapse text-left text-xs text-[var(--genui-text)]">
        <thead className="bg-[var(--genui-panel)]">
          <tr>
            {table.headers.map((header, index) => (
              <th
                key={`${keyPrefix}-head-${index}`}
                className="border-b border-[var(--genui-border)] px-3 py-2 font-semibold [overflow-wrap:anywhere]"
              >
                {renderInlineContent(header, `${keyPrefix}-head-${index}`)}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {table.rows.map((row, rowIndex) => (
            <tr key={`${keyPrefix}-row-${rowIndex}`} className="border-t border-[var(--genui-border)]/70">
              {row.map((cell, cellIndex) => (
                <td
                  key={`${keyPrefix}-cell-${rowIndex}-${cellIndex}`}
                  className="px-3 py-2 align-top leading-relaxed [overflow-wrap:anywhere]"
                >
                  {renderInlineContent(cell, `${keyPrefix}-cell-${rowIndex}-${cellIndex}`)}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function renderMarkdownBlockquote(lines: string[], keyPrefix: string): React.ReactNode {
  const quote = lines
    .map((line) => line.replace(/^>\s?/, "").trim())
    .filter(Boolean)
    .join("\n");

  return (
    <blockquote
      key={keyPrefix}
      className="my-3 border-l-2 border-[var(--genui-running)]/50 bg-[var(--genui-running)]/8 px-3 py-2 text-sm leading-relaxed text-[var(--genui-text)] [overflow-wrap:anywhere]"
    >
      {renderParagraphLines(quote, `${keyPrefix}-quote`)}
    </blockquote>
  );
}

function renderParagraphLines(text: string, keyPrefix: string) {
  return text.split("\n").map((line, index, lines) => (
    <Fragment key={`${keyPrefix}-line-${index}`}>
      {renderInlineContent(line, `${keyPrefix}-${index}`)}
      {index < lines.length - 1 ? <br /> : null}
    </Fragment>
  ));
}

function renderMarkdownParagraph(paragraph: string, keyPrefix: string): React.ReactNode {
  const lines = paragraph
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);

  const table = parseMarkdownTable(lines);
  if (table) {
    return renderMarkdownTable(table, keyPrefix);
  }

  const quoteItems = lines.map((line) => line.match(/^>\s?(.+)$/)?.[1]?.trim() ?? null);
  if (quoteItems.length > 0 && quoteItems.every((item): item is string => Boolean(item))) {
    return renderMarkdownBlockquote(lines, keyPrefix);
  }

  const headingMatch = lines.length === 1 ? lines[0].match(/^(#{1,3})\s+(.+)$/) : null;
  if (headingMatch) {
    const level = headingMatch[1].length;
    const text = headingMatch[2].trim();

    if (level === 1) {
      return (
        <h2 key={keyPrefix} className="break-words text-lg font-semibold leading-snug text-[var(--genui-text)] [overflow-wrap:anywhere]">
          {renderInlineContent(text, `${keyPrefix}-h1`)}
        </h2>
      );
    }

    if (level === 2) {
      return (
        <h3 key={keyPrefix} className="mt-3 border-b border-[var(--genui-border)] pb-1 text-sm font-semibold leading-snug text-[var(--genui-text)] [overflow-wrap:anywhere]">
          {renderInlineContent(text, `${keyPrefix}-h2`)}
        </h3>
      );
    }

    return (
      <h4 key={keyPrefix} className="mt-2 text-xs font-semibold uppercase tracking-wide text-[var(--genui-muted)] [overflow-wrap:anywhere]">
        {renderInlineContent(text, `${keyPrefix}-h3`)}
      </h4>
    );
  }

  const bulletItems = lines.map((line) => line.match(/^[-*]\s+(.+)$/)?.[1]?.trim() ?? null);
  if (bulletItems.length > 0 && bulletItems.every((item): item is string => Boolean(item))) {
    return (
      <ul key={keyPrefix} className="my-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-[var(--genui-text)]">
        {bulletItems.map((item, index) => (
          <li key={`${keyPrefix}-bullet-${index}`} className="break-words [overflow-wrap:anywhere]">
            {renderInlineContent(item, `${keyPrefix}-bullet-${index}`)}
          </li>
        ))}
      </ul>
    );
  }

  const numberedItems = lines.map((line) => line.match(/^\d+[.)]\s+(.+)$/)?.[1]?.trim() ?? null);
  if (numberedItems.length > 0 && numberedItems.every((item): item is string => Boolean(item))) {
    return (
      <ol key={keyPrefix} className="my-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-[var(--genui-text)]">
        {numberedItems.map((item, index) => (
          <li key={`${keyPrefix}-numbered-${index}`} className="break-words [overflow-wrap:anywhere]">
            {renderInlineContent(item, `${keyPrefix}-numbered-${index}`)}
          </li>
        ))}
      </ol>
    );
  }

  return (
    <p
      key={keyPrefix}
      className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--genui-text)] [overflow-wrap:anywhere]"
    >
      {renderParagraphLines(paragraph, keyPrefix)}
    </p>
  );
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
            {paragraphs.map((paragraph, paragraphIndex) =>
              renderMarkdownParagraph(paragraph, `paragraph-${blockIndex}-${paragraphIndex}`),
            )}
          </div>
        );
      })}
      {isStreaming && isLast && (
        <span className="inline-block h-[14px] w-[7px] animate-pulse rounded-[1px] bg-[var(--genui-text)] align-middle" />
      )}
    </div>
  );
}
