export type CSVParseError = {
  code:
  | 'empty_file'
  | 'missing_header'
  | 'too_many_columns'
  | 'parse_error'
  | 'inconsistent_columns'
  | 'schema_mismatch'
  | 'datatype_mismatch'
  | 'excessive_missing';
  message: string;
  detail?: any;
};

export type ColumnType = 'number' | 'string' | 'date' | 'boolean' | 'unknown';

export interface CSVOptions {
  delimiter?: ',' | ';' | '\t' | '|';
  maxColumns?: number; // hard cap
  requireHeader?: boolean; // header must exist and be non-empty
  expectedSchema?: {
    // optional schema for mismatch checks
    columns?: string[]; // required column names (order-insensitive)
    types?: Record<string, ColumnType>; // expected type by column name
  };
  missingThreshold?: number; // ratio [0,1] considered excessive
  sampleRowsForTypes?: number; // number of rows to infer types
}

export interface CSVResult {
  columns: string[];
  rows: Record<string, string>[];
  errors: CSVParseError[];
  warnings: CSVParseError[];
  columnTypes: Record<string, ColumnType>;
  missingRatioByColumn: Record<string, number>;
}

// Simple CSV parser supporting quoted fields and basic delimiters.
export function parseCSV(text: string, opts: CSVOptions = {}): CSVResult {
  const options: Required<Pick<CSVOptions, 'delimiter' | 'maxColumns' | 'requireHeader' | 'missingThreshold' | 'sampleRowsForTypes'>> & CSVOptions = {
    delimiter: ',',
    maxColumns: 100,
    requireHeader: true,
    missingThreshold: 0.5,
    sampleRowsForTypes: 100,
    ...opts,
  } as any;

  const errors: CSVParseError[] = [];
  const warnings: CSVParseError[] = [];

  const trimmed = text.replace(/\uFEFF/g, '').trim(); // strip BOM and trim
  if (!trimmed) {
    errors.push({ code: 'empty_file', message: '빈 파일입니다.' });
    return {
      columns: [],
      rows: [],
      errors,
      warnings,
      columnTypes: {},
      missingRatioByColumn: {},
    };
  }

  // Split into lines (preserve quoted newlines by parsing char-by-char)
  const records: string[][] = [];
  try {
    let field = '';
    const row: string[] = [];
    let inQuotes = false;
    const pushField = () => {
      row.push(field);
      field = '';
    };
    const pushRow = () => {
      records.push([...row]);
      row.length = 0;
    };
    const dlm = options.delimiter as string;
    for (let i = 0; i < text.length; i++) {
      const ch = text[i];
      if (ch === '"') {
        if (inQuotes && text[i + 1] === '"') {
          field += '"';
          i++; // escaped quote
        } else {
          inQuotes = !inQuotes;
        }
      } else if (!inQuotes && ch === dlm) {
        pushField();
      } else if (!inQuotes && (ch === '\n' || ch === '\r')) {
        // handle CRLF and LF
        if (ch === '\r' && text[i + 1] === '\n') i++;
        pushField();
        pushRow();
      } else {
        field += ch;
      }
    }
    // last field/row
    pushField();
    pushRow();
  } catch (e) {
    errors.push({ code: 'parse_error', message: 'CSV 파싱 중 오류가 발생했습니다.' });
  }

  if (records.length === 0 || (records[0] && records[0].length === 1 && !records[0][0])) {
    errors.push({ code: 'empty_file', message: '빈 파일입니다.' });
    return { columns: [], rows: [], errors, warnings, columnTypes: {}, missingRatioByColumn: {} };
  }

  const header = (records[0] || []).map((h) => h?.trim());
  const headerHasContent = header.some((h) => h && h.length > 0);
  const uniqueHeader = new Set(header.filter(Boolean));
  const hasDuplicates = uniqueHeader.size !== header.filter(Boolean).length;
  const columnCount = header.length;

  if (options.requireHeader && (!headerHasContent || hasDuplicates)) {
    errors.push({ code: 'missing_header', message: hasDuplicates ? '헤더에 중복된 컬럼명이 있습니다.' : '헤더가 없거나 비어있습니다.' });
  }

  if (options.maxColumns && columnCount > options.maxColumns) {
    errors.push({ code: 'too_many_columns', message: `컬럼 수가 제한(${options.maxColumns})을 초과했습니다.`, detail: { columnCount } });
  }

  // Validate each row has consistent number of columns
  for (let r = 1; r < records.length; r++) {
    const record = records[r];
    if (record && record.length !== columnCount) {
      errors.push({ code: 'inconsistent_columns', message: `${r + 1}행의 컬럼 수가 헤더와 일치하지 않습니다.`, detail: { row: r + 1 } });
      break; // one example is enough
    }
  }

  const rows: Record<string, string>[] = [];
  for (let r = 1; r < records.length; r++) {
    const record = records[r];
    if (!record) continue;
    const obj: Record<string, string> = {};
    for (let c = 0; c < columnCount; c++) {
      obj[header[c] || `column_${c + 1}`] = record[c] ?? '';
    }
    rows.push(obj);
  }

  // Infer types
  const sampleN = Math.min(rows.length, options.sampleRowsForTypes || 100);
  const types: Record<string, ColumnType> = {};
  const keys = header.map((h, i) => h || `column_${i + 1}`);
  const isNumber = (v: string) => v !== '' && !isNaN(Number(v.replace(/,/g, '')));
  const isBool = (v: string) => ['true', 'false', '0', '1', 'yes', 'no'].includes(v.toLowerCase());
  const isDate = (v: string) => {
    if (!v || typeof v !== 'string') return false;
    const t = Date.parse(v);
    return !isNaN(t);
  };

  for (const key of keys) {
    let num = 0, bool = 0, date = 0, str = 0;
    for (let i = 0; i < sampleN; i++) {
      const val = (rows[i]?.[key] ?? '').trim();
      if (val === '') continue;
      if (isNumber(val)) num++;
      else if (isBool(val)) bool++;
      else if (isDate(val)) date++;
      else str++;
    }
    const counts: [ColumnType, number][] = [
      ['number', num],
      ['boolean', bool],
      ['date', date],
      ['string', str],
    ];
    counts.sort((a, b) => b[1] - a[1]);
    const firstCount = counts[0];
    types[key] = !firstCount || firstCount[1] === 0 ? 'unknown' : firstCount[0];
  }

  // Missing ratios
  const missingRatio: Record<string, number> = {};
  for (const key of keys) {
    let missing = 0;
    for (const row of rows) {
      const v = (row[key] ?? '').trim();
      if (v === '' || v.toLowerCase() === 'na' || v.toLowerCase() === 'null') missing++;
    }
    missingRatio[key] = rows.length ? missing / rows.length : 0;
    if (missingRatio[key] >= (options.missingThreshold || 0.5)) {
      warnings.push({ code: 'excessive_missing', message: `컬럼 "${key}"의 결측치 비율이 높습니다 (${Math.round(missingRatio[key] * 100)}%).`, detail: { column: key, ratio: missingRatio[key] } });
    }
  }

  // Schema checks
  if (options.expectedSchema?.columns && options.expectedSchema.columns.length) {
    const expected = new Set(options.expectedSchema.columns);
    const present = new Set(keys);
    const missing = options.expectedSchema.columns.filter((c) => !present.has(c));
    const extra = keys.filter((k) => !expected.has(k));
    if (missing.length > 0 || extra.length > 0) {
      errors.push({ code: 'schema_mismatch', message: '스키마가 일치하지 않습니다 (컬럼 구성 불일치).', detail: { missing, extra } });
    }
  }

  if (options.expectedSchema?.types) {
    const mismatches: { column: string; expected: ColumnType; actual: ColumnType }[] = [];
    for (const [col, expectedType] of Object.entries(options.expectedSchema.types)) {
      const actual = types[col] || 'unknown';
      if (actual !== 'unknown' && expectedType !== actual) {
        mismatches.push({ column: col, expected: expectedType, actual });
      }
    }
    if (mismatches.length) {
      warnings.push({ code: 'datatype_mismatch', message: '일부 컬럼의 데이터 타입이 예상과 다릅니다.', detail: mismatches });
    }
  }

  // Row-level datatype mismatch check against inferred types
  // If more than 5% values in a column violate the inferred type, raise a warning.
  const mismatchColumns: { column: string; mismatchRatio: number }[] = [];
  for (const key of keys) {
    const inferred = types[key];
    if (inferred === 'unknown') continue;
    let mismatches = 0;
    for (const row of rows) {
      const raw = (row[key] ?? '').trim();
      if (raw === '') continue; // missing handled separately
      const ok =
        (inferred === 'number' && isNumber(raw)) ||
        (inferred === 'boolean' && isBool(raw)) ||
        (inferred === 'date' && isDate(raw)) ||
        (inferred === 'string');
      if (!ok) mismatches++;
    }
    const ratio = rows.length ? mismatches / rows.length : 0;
    if (ratio > 0.05) {
      mismatchColumns.push({ column: key, mismatchRatio: ratio });
    }
  }
  if (mismatchColumns.length) {
    warnings.push({
      code: 'datatype_mismatch',
      message: '일부 행에서 데이터 타입 불일치가 감지되었습니다.',
      detail: mismatchColumns,
    });
  }

  return {
    columns: keys,
    rows,
    errors,
    warnings,
    columnTypes: types,
    missingRatioByColumn: missingRatio,
  };
}
