import { Fragment } from "react";
import type React from "react";

export function renderInlineContent(text: string, keyPrefix: string): React.ReactNode[] {
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

export function renderMarkdownLines(text: string, keyPrefix: string) {
  return text.split("\n").map((line, index, lines) => (
    <Fragment key={`${keyPrefix}-line-${index}`}>
      {renderInlineContent(line, `${keyPrefix}-${index}`)}
      {index < lines.length - 1 ? <br /> : null}
    </Fragment>
  ));
}
