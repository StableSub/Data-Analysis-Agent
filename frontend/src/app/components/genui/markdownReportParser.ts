type HeadingLevel = 1 | 2 | 3;

export interface MarkdownTable {
  headers: string[];
  rows: string[][];
}

export type MarkdownFlowBlock =
  | { kind: "heading"; level: HeadingLevel; text: string }
  | { kind: "table"; table: MarkdownTable }
  | { kind: "blockquote"; lines: string[] }
  | { kind: "list"; ordered: boolean; items: string[] }
  | { kind: "paragraph"; lines: string[] };

function splitMarkdownTableRow(line: string): string[] {
  return line
    .trim()
    .replace(/^\|/, "")
    .replace(/\|$/, "")
    .split("|")
    .map((cell) => cell.trim());
}

export function parseMarkdownTable(lines: string[]): MarkdownTable | null {
  if (lines.length < 3) {
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

function lineIsBlank(line: string): boolean {
  return line.trim().length === 0;
}

function getHeading(line: string): { level: HeadingLevel; text: string } | null {
  const headingMatch = line.match(/^(#{1,3})\s+(.+)$/);
  if (!headingMatch) {
    return null;
  }
  return {
    level: headingMatch[1].length as HeadingLevel,
    text: headingMatch[2].trim(),
  };
}

function isHeadingLine(line: string): boolean {
  return getHeading(line.trim()) !== null;
}

function isPipeRow(line: string): boolean {
  const trimmed = line.trim();
  return trimmed.startsWith("|") && trimmed.endsWith("|") && trimmed.includes("|");
}

function isMarkdownTableStart(lines: string[], index: number): boolean {
  if (!isPipeRow(lines[index] ?? "") || !isPipeRow(lines[index + 1] ?? "")) {
    return false;
  }
  const headers = splitMarkdownTableRow(lines[index]);
  const separator = splitMarkdownTableRow(lines[index + 1]);
  return headers.length >= 2 && separator.length === headers.length && separator.every((cell) => /^:?-{3,}:?$/.test(cell));
}

function isBlockquoteLine(line: string): boolean {
  return /^>\s?.+/.test(line.trim());
}

function isBulletLine(line: string): boolean {
  return /^[-*]\s+.+/.test(line.trim());
}

function isNumberedLine(line: string): boolean {
  return /^\d+[.)]\s+.+/.test(line.trim());
}

export function isMarkdownBlockStart(lines: string[], index: number): boolean {
  const line = lines[index]?.trim() ?? "";
  return (
    isHeadingLine(line) ||
    isMarkdownTableStart(lines, index) ||
    isBlockquoteLine(line) ||
    isBulletLine(line) ||
    isNumberedLine(line)
  );
}

function collectListItems(lines: string[], startIndex: number, ordered: boolean): { items: string[]; nextIndex: number } {
  const pattern = ordered ? /^\d+[.)]\s+(.+)$/ : /^[-*]\s+(.+)$/;
  const items: string[] = [];
  let index = startIndex;

  while (index < lines.length) {
    const match = lines[index].trim().match(pattern);
    if (!match) {
      break;
    }
    items.push(match[1].trim());
    index += 1;
  }

  return { items, nextIndex: index };
}

function collectTableBlock(lines: string[], startIndex: number): { block: MarkdownFlowBlock; nextIndex: number } {
  const tableLines: string[] = [];
  let index = startIndex;

  while (index < lines.length && isPipeRow(lines[index])) {
    tableLines.push(lines[index].trim());
    index += 1;
  }

  const table = parseMarkdownTable(tableLines);
  return {
    block: table ? { kind: "table", table } : { kind: "paragraph", lines: tableLines },
    nextIndex: index,
  };
}

function collectBlockquote(lines: string[], startIndex: number): { block: MarkdownFlowBlock; nextIndex: number } {
  const quoteLines: string[] = [];
  let index = startIndex;

  while (index < lines.length && isBlockquoteLine(lines[index])) {
    quoteLines.push(lines[index].trim());
    index += 1;
  }

  return { block: { kind: "blockquote", lines: quoteLines }, nextIndex: index };
}

function collectParagraph(lines: string[], startIndex: number, fallbackLine: string): { block: MarkdownFlowBlock; nextIndex: number } {
  const paragraphLines: string[] = [];
  let index = startIndex;

  while (index < lines.length && !lineIsBlank(lines[index]) && !isMarkdownBlockStart(lines, index)) {
    paragraphLines.push(lines[index].trim());
    index += 1;
  }

  if (paragraphLines.length > 0) {
    return { block: { kind: "paragraph", lines: paragraphLines }, nextIndex: index };
  }

  return { block: { kind: "paragraph", lines: [fallbackLine] }, nextIndex: startIndex + 1 };
}

export function splitMarkdownFlowBlocks(content: string): MarkdownFlowBlock[] {
  const lines = content.replace(/\r\n?/g, "\n").split("\n");
  const blocks: MarkdownFlowBlock[] = [];
  let index = 0;

  while (index < lines.length) {
    const currentLine = lines[index].trim();
    if (lineIsBlank(currentLine)) {
      index += 1;
      continue;
    }

    const heading = getHeading(currentLine);
    if (heading) {
      blocks.push({ kind: "heading", ...heading });
      index += 1;
      continue;
    }

    if (isMarkdownTableStart(lines, index)) {
      const result = collectTableBlock(lines, index);
      blocks.push(result.block);
      index = result.nextIndex;
      continue;
    }

    if (isBlockquoteLine(currentLine)) {
      const result = collectBlockquote(lines, index);
      blocks.push(result.block);
      index = result.nextIndex;
      continue;
    }

    const bulletItems = collectListItems(lines, index, false);
    if (bulletItems.items.length > 0) {
      blocks.push({ kind: "list", ordered: false, items: bulletItems.items });
      index = bulletItems.nextIndex;
      continue;
    }

    const numberedItems = collectListItems(lines, index, true);
    if (numberedItems.items.length > 0) {
      blocks.push({ kind: "list", ordered: true, items: numberedItems.items });
      index = numberedItems.nextIndex;
      continue;
    }

    const result = collectParagraph(lines, index, currentLine);
    blocks.push(result.block);
    index = result.nextIndex;
  }

  return blocks;
}
