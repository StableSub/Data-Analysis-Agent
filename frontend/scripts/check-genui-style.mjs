import { promises as fs } from "node:fs";
import path from "node:path";

const TARGET_DIRS = ["src/components/workbench", "src/components/gen-ui"];
const ALLOWLIST_FILE = ".genui-style-allowlist.txt";
const FILE_EXTENSIONS = new Set([".ts", ".tsx"]);

const RULES = [
  { name: "bg-white", regex: /\bbg-white\b/ },
  { name: "text-zinc/slate", regex: /\btext-(zinc|slate)-/ },
  { name: "border-zinc/slate", regex: /\bborder-(zinc|slate)-/ },
  { name: "ring-zinc/slate", regex: /\bring-(zinc|slate)-/ },
];

const ALLOWED_SHADCN_CLASSES = new Set([
  "bg-background",
  "text-foreground",
  "border-border",
]);

function normalizeRelative(filePath) {
  return filePath.replaceAll(path.sep, "/");
}

async function pathExists(targetPath) {
  try {
    await fs.access(targetPath);
    return true;
  } catch {
    return false;
  }
}

async function collectFiles(baseDir, currentDir = baseDir, result = []) {
  const entries = await fs.readdir(currentDir, { withFileTypes: true });
  for (const entry of entries) {
    const absolutePath = path.join(currentDir, entry.name);
    if (entry.isDirectory()) {
      await collectFiles(baseDir, absolutePath, result);
      continue;
    }

    if (FILE_EXTENSIONS.has(path.extname(entry.name))) {
      result.push(absolutePath);
    }
  }
  return result;
}

async function readAllowlist(cwd) {
  const allowlistPath = path.join(cwd, ALLOWLIST_FILE);
  const allowFiles = new Set();
  const allowLines = new Map();

  if (!(await pathExists(allowlistPath))) {
    return { allowFiles, allowLines };
  }

  const content = await fs.readFile(allowlistPath, "utf8");
  for (const rawLine of content.split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#")) continue;

    const lineMatch = line.match(/^(.*):(\d+)$/);
    if (lineMatch) {
      const relativePath = normalizeRelative(lineMatch[1]);
      const lineNumber = Number(lineMatch[2]);
      if (!Number.isFinite(lineNumber)) continue;
      const existing = allowLines.get(relativePath) ?? new Set();
      existing.add(lineNumber);
      allowLines.set(relativePath, existing);
      continue;
    }

    allowFiles.add(normalizeRelative(line));
  }

  return { allowFiles, allowLines };
}

function containsAllowedShadcnClass(line) {
  for (const className of ALLOWED_SHADCN_CLASSES) {
    if (line.includes(className)) return true;
  }
  return false;
}

async function main() {
  const cwd = process.cwd();
  const { allowFiles, allowLines } = await readAllowlist(cwd);

  const findings = [];

  for (const targetDir of TARGET_DIRS) {
    const absoluteDir = path.join(cwd, targetDir);
    if (!(await pathExists(absoluteDir))) continue;

    const files = await collectFiles(absoluteDir);
    for (const filePath of files) {
      const relativePath = normalizeRelative(path.relative(cwd, filePath));
      if (allowFiles.has(relativePath)) continue;

      const source = await fs.readFile(filePath, "utf8");
      const lines = source.split(/\r?\n/);
      for (let i = 0; i < lines.length; i += 1) {
        const lineNumber = i + 1;
        const line = lines[i];

        if (allowLines.get(relativePath)?.has(lineNumber)) continue;
        if (containsAllowedShadcnClass(line)) continue;

        for (const rule of RULES) {
          if (!rule.regex.test(line)) continue;
          findings.push({
            file: relativePath,
            line: lineNumber,
            rule: rule.name,
            snippet: line.trim(),
          });
        }
      }
    }
  }

  if (findings.length === 0) {
    console.log("check:genui-style passed (no violations).");
    process.exit(0);
  }

  console.warn(`check:genui-style warning (${findings.length} findings)`);
  for (const finding of findings) {
    console.warn(
      `- ${finding.file}:${finding.line} [${finding.rule}] ${finding.snippet}`,
    );
  }

  const strictMode = process.env.GENUI_STYLE_STRICT === "1";
  if (strictMode) {
    process.exit(1);
  }
}

main().catch((error) => {
  console.error("check:genui-style failed to run:", error);
  process.exit(1);
});
