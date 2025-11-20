/**
 * 피그마 디자인 참고용 화면 컴포넌트 모음
 * 
 * 각 컴포넌트를 App.tsx에서 임포트하여 개별적으로 확인할 수 있습니다.
 * 
 * 사용 예시:
 * ```tsx
 * import { NotebookLMGallery } from './components/figma-screens';
 * 
 * function App() {
 *   return <NotebookLMGallery />;
 * }
 * ```
 */

// 🔥 NotebookLM 스타일 (v3.0 - 최신!)
export { NotebookLMEmpty } from './NotebookLMEmpty';
export { NotebookLMWithSources } from './NotebookLMWithSources';
export { NotebookLMGallery } from './NotebookLMGallery';

// v2.0 단순화된 레이아웃
export { SimplifiedChatEmpty } from './SimplifiedChatEmpty';
export { SimplifiedChatWithMessages } from './SimplifiedChatWithMessages';
export { SimplifiedFileUpload } from './SimplifiedFileUpload';
export { SimplifiedVisualization } from './SimplifiedVisualization';

// 기존 화면들 (참고용)
export { ChatEmptyState } from './ChatEmptyState';
export { ChatWithMessages } from './ChatWithMessages';
export { ChatStreaming } from './ChatStreaming';
export { ChatWithAgent } from './ChatWithAgent';

export { UploadDefault } from './UploadDefault';
export { UploadDragOver } from './UploadDragOver';
export { UploadSuccess } from './UploadSuccess';

export {
  ComingSoonSnapshot,
  ComingSoonFilter,
  ComingSoonVisualization,
  ComingSoonEdit,
  ComingSoonSimulation,
  ComingSoonAudit,
} from './ComingSoonPages';
