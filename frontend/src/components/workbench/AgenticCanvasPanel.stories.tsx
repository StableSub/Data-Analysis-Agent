import type { Meta, StoryObj } from "@storybook/react-vite";

import type { WorkbenchCardProps } from "../gen-ui";
import { AgenticCanvasPanel } from "./AgenticCanvasPanel";

const activeSessionId = "session-story-1";

const baseSession = {
  id: activeSessionId,
  title: "품질 분석 세션",
  updatedAt: "2026-02-20T10:00:00.000Z",
  messageCount: 2,
};

const errorCard: WorkbenchCardProps = {
  cardId: "error-card-story",
  cardType: "error_card",
  title: "시각화 생성 실패",
  subtitle: "부분 실패가 발생했지만 대화는 계속됩니다.",
  sessionId: activeSessionId,
  source: {
    kind: "run",
    runId: "run-err-1",
  },
  status: "failed",
  summary: "차트 생성 도중 스키마 불일치가 발생했습니다.",
  error: {
    failedStep: "csv_visualization_workflow",
    reason: "필수 컬럼 defect_rate를 찾지 못했습니다.",
    retryAction: { type: "retry", label: "다시 시도" },
  },
  actions: [{ type: "retry", label: "다시 시도" }],
};

const meta = {
  title: "Workbench/AgenticCanvasPanel",
  component: AgenticCanvasPanel,
  parameters: {
    layout: "fullscreen",
  },
  tags: ["autodocs"],
  args: {
    sessions: [baseSession],
    activeSessionId,
    messages: [],
    files: [],
    onOpenUpload: () => {},
    onUploadFile: async () => {},
    onNewSession: () => {},
    onSelectSession: () => {},
    onDeleteSession: () => {},
    onRenameSession: () => {},
    onToggleFile: () => {},
    onRemoveFile: () => {},
    onAddMessage: () => {},
  },
} satisfies Meta<typeof AgenticCanvasPanel>;

export default meta;
type Story = StoryObj<typeof meta>;

export const Empty: Story = {};

export const Streaming: Story = {
  args: {
    messages: [
      {
        id: "msg-user-1",
        role: "user",
        content: "최근 결함률 추이를 요약해줘.",
        timestamp: "2026-02-20T10:00:10.000Z",
      },
      {
        id: "msg-assistant-1",
        role: "assistant",
        content: "데이터를 분석 중입니다. 잠시만 기다려주세요...",
        timestamp: "2026-02-20T10:00:11.000Z",
      },
    ],
    files: [
      {
        id: "dataset-story-1",
        name: "production_line_a.csv",
        type: "dataset",
        size: 212038,
        selected: true,
      },
    ],
    initialIsResponding: true,
  },
};

export const WithErrorCard: Story = {
  args: {
    messages: [
      {
        id: "msg-user-2",
        role: "user",
        content: "결함률을 라인 차트로 그려줘.",
        timestamp: "2026-02-20T10:01:00.000Z",
      },
      {
        id: "msg-assistant-2",
        role: "assistant",
        content: "시각화 도구 실행 결과를 정리했습니다.",
        timestamp: "2026-02-20T10:01:03.000Z",
      },
    ],
    files: [
      {
        id: "dataset-story-2",
        name: "production_line_b.csv",
        type: "dataset",
        size: 431128,
        selected: true,
      },
    ],
    initialArtifacts: {
      [activeSessionId]: [
        {
          id: "artifact-error-1",
          createdAt: "2026-02-20T10:01:04.000Z",
          type: "card",
          card: errorCard,
        },
      ],
    },
  },
};
