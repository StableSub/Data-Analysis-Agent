import type React from "react";
import { renderInlineContent, renderMarkdownLines } from "./MarkdownInlineRenderer";
import type { MarkdownFlowBlock, MarkdownTable } from "./markdownReportParser";
import { splitMarkdownFlowBlocks } from "./markdownReportParser";

export { renderMarkdownLines } from "./MarkdownInlineRenderer";

function renderMarkdownTable(table: MarkdownTable, keyPrefix: string): React.ReactNode {
  return (
    <div key={keyPrefix} className="my-3 overflow-x-auto rounded-md border border-[var(--genui-border)] bg-[var(--genui-surface)]">
      <table className="min-w-full border-collapse text-left text-xs text-[var(--genui-text)]">
        <thead className="bg-[var(--genui-panel)]">
          <tr>
            {table.headers.map((header, index) => (
              <th
                key={`${keyPrefix}-head-${index}`}
                scope="col"
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

function renderMarkdownBlockquote(block: Extract<MarkdownFlowBlock, { kind: "blockquote" }>, keyPrefix: string): React.ReactNode {
  const quote = block.lines
    .map((line) => line.replace(/^>\s?/, "").trim())
    .filter(Boolean)
    .join("\n");

  return (
    <blockquote
      key={keyPrefix}
      className="my-3 border-l-2 border-[var(--genui-running)]/50 bg-[var(--genui-running)]/8 px-3 py-2 text-sm leading-relaxed text-[var(--genui-text)] [overflow-wrap:anywhere]"
    >
      {renderMarkdownLines(quote, `${keyPrefix}-quote`)}
    </blockquote>
  );
}

function renderMarkdownHeading(block: Extract<MarkdownFlowBlock, { kind: "heading" }>, keyPrefix: string): React.ReactNode {
  const content = renderInlineContent(block.text, `${keyPrefix}-heading`);

  if (block.level === 1) {
    return (
      <h2
        key={keyPrefix}
        data-markdown-heading-level={block.level}
        className="break-words text-lg font-semibold leading-snug text-[var(--genui-text)] [overflow-wrap:anywhere]"
      >
        {content}
      </h2>
    );
  }

  if (block.level === 2) {
    return (
      <h3
        key={keyPrefix}
        data-markdown-heading-level={block.level}
        className="mt-3 border-b border-[var(--genui-border)] pb-1 text-sm font-semibold leading-snug text-[var(--genui-text)] [overflow-wrap:anywhere]"
      >
        {content}
      </h3>
    );
  }

  return (
    <h4
      key={keyPrefix}
      data-markdown-heading-level={block.level}
      className="mt-2 text-xs font-semibold uppercase text-[var(--genui-muted)] [overflow-wrap:anywhere]"
    >
      {content}
    </h4>
  );
}

function renderMarkdownList(block: Extract<MarkdownFlowBlock, { kind: "list" }>, keyPrefix: string): React.ReactNode {
  if (block.ordered) {
    return (
      <ol key={keyPrefix} className="my-2 list-decimal space-y-1 pl-5 text-sm leading-relaxed text-[var(--genui-text)]">
        {block.items.map((item, index) => (
          <li key={`${keyPrefix}-item-${index}`} className="break-words [overflow-wrap:anywhere]">
            {renderInlineContent(item, `${keyPrefix}-item-${index}`)}
          </li>
        ))}
      </ol>
    );
  }

  return (
    <ul key={keyPrefix} className="my-2 list-disc space-y-1 pl-5 text-sm leading-relaxed text-[var(--genui-text)]">
      {block.items.map((item, index) => (
        <li key={`${keyPrefix}-item-${index}`} className="break-words [overflow-wrap:anywhere]">
          {renderInlineContent(item, `${keyPrefix}-item-${index}`)}
        </li>
      ))}
    </ul>
  );
}

function renderMarkdownBlock(block: MarkdownFlowBlock, keyPrefix: string): React.ReactNode {
  if (block.kind === "heading") {
    return renderMarkdownHeading(block, keyPrefix);
  }
  if (block.kind === "table") {
    return renderMarkdownTable(block.table, keyPrefix);
  }
  if (block.kind === "blockquote") {
    return renderMarkdownBlockquote(block, keyPrefix);
  }
  if (block.kind === "list") {
    return renderMarkdownList(block, keyPrefix);
  }

  return (
    <p
      key={keyPrefix}
      className="whitespace-pre-wrap break-words text-sm leading-relaxed text-[var(--genui-text)] [overflow-wrap:anywhere]"
    >
      {renderMarkdownLines(block.lines.join("\n"), keyPrefix)}
    </p>
  );
}

export function renderMarkdownReportContent(content: string, keyPrefix = "markdown"): React.ReactNode[] {
  return splitMarkdownFlowBlocks(content).map((block, index) => renderMarkdownBlock(block, `${keyPrefix}-${index}`));
}
