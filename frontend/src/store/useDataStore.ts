import { create } from 'zustand';

export interface ColumnInfo {
  name: string;
  type: 'number' | 'string' | 'date' | 'boolean';
  missing: number;
  unique: number;
  mean?: number;
  median?: number;
  min?: number;
  max?: number;
  std?: number;
}

interface DataState {
  file: File | null;
  data: any[];
  columns: string[];
  columnInfo: ColumnInfo[];

  // 히스토리 관리
  history: {
    data: any[];
    columns: string[];
    columnInfo: ColumnInfo[];
  }[];
  historyIndex: number;

  // 액션들
  setFileData: (file: File, data: any[], columns: string[], columnInfo: ColumnInfo[]) => void;
  updateData: (data: any[], columns: string[], columnInfo: ColumnInfo[], addToHistory?: boolean) => void;
  clearData: () => void;

  // Undo/Redo
  undo: () => void;
  redo: () => void;
  canUndo: () => boolean;
  canRedo: () => boolean;
}

export const useDataStore = create<DataState>((set, get) => ({
  file: null,
  data: [],
  columns: [],
  columnInfo: [],
  history: [],
  historyIndex: -1,

  setFileData: (file, data, columns, columnInfo) => {
    set({
      file,
      data,
      columns,
      columnInfo,
      history: [{ data, columns, columnInfo }],
      historyIndex: 0,
    });
  },

  updateData: (data, columns, columnInfo, addToHistory = true) => {
    if (addToHistory) {
      const { history, historyIndex } = get();
      const newHistory = history.slice(0, historyIndex + 1);
      newHistory.push({ data, columns, columnInfo });

      set({
        data,
        columns,
        columnInfo,
        history: newHistory,
        historyIndex: newHistory.length - 1,
      });
    } else {
      set({ data, columns, columnInfo });
    }
  },

  clearData: () => {
    set({
      file: null,
      data: [],
      columns: [],
      columnInfo: [],
      history: [],
      historyIndex: -1,
    });
  },

  undo: () => {
    const { history, historyIndex } = get();
    if (historyIndex > 0) {
      const prevState = history[historyIndex - 1]!;
      set({
        data: prevState.data,
        columns: prevState.columns,
        columnInfo: prevState.columnInfo,
        historyIndex: historyIndex - 1,
      });
    }
  },

  redo: () => {
    const { history, historyIndex } = get();
    if (historyIndex < history.length - 1) {
      const nextState = history[historyIndex + 1]!;
      set({
        data: nextState.data,
        columns: nextState.columns,
        columnInfo: nextState.columnInfo,
        historyIndex: historyIndex + 1,
      });
    }
  },

  canUndo: () => {
    const { historyIndex } = get();
    return historyIndex > 0;
  },

  canRedo: () => {
    const { history, historyIndex } = get();
    return historyIndex < history.length - 1;
  },
}));
