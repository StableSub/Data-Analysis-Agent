import { useCopilotReadable } from '@copilotkit/react-core';
import { useStore } from '../../store/useStore';
import { Card } from '../ui/card';
import { Database, FileSpreadsheet } from 'lucide-react';

interface WorkspaceCanvasProps {
    isDark?: boolean;
}

/**
 * 메인 작업 영역 (캔버스)
 * AI가 데이터와 상호작용하는 중심 공간
 */
export function WorkspaceCanvas({ isDark = false }: WorkspaceCanvasProps) {
    const { sessions, activeSessionId } = useStore();
    const activeSession = sessions.find(s => s.id === activeSessionId);

    // AI가 현재 작업 중인 파일 정보를 읽을 수 있도록 제공
    useCopilotReadable({
        description: '현재 업로드된 데이터 파일 목록',
        value: activeSession?.files || [],
    });

    // AI가 세션 컨텍스트를 이해할 수 있도록 제공
    useCopilotReadable({
        description: '현재 활성화된 분석 세션 정보',
        value: {
            sessionId: activeSessionId,
            sessionTitle: activeSession?.title || '새 세션',
            messageCount: activeSession?.messages.length || 0,
            fileCount: activeSession?.files.length || 0,
        },
    });

    return (
        <div className="flex-1 flex flex-col bg-white dark:bg-[#212121] overflow-auto">
            {/* 빈 상태: 파일 업로드 대기 */}
            {(!activeSession?.files || activeSession.files.length === 0) ? (
                <div className="flex-1 flex items-center justify-center p-8">
                    <Card className="max-w-2xl w-full p-12 text-center">
                        <div className="inline-flex items-center justify-center w-20 h-20 rounded-3xl bg-gradient-to-br from-blue-500 to-purple-600 text-white mb-6">
                            <Database className="w-10 h-10" />
                        </div>
                        <h2 className="text-2xl font-semibold text-gray-900 dark:text-white mb-4">
                            데이터 분석 워크스페이스
                        </h2>
                        <p className="text-gray-600 dark:text-gray-400 mb-6">
                            좌측 사이드바에서 파일을 업로드하거나, AI 코파일럿에게 데이터 분석을 요청하세요.
                        </p>
                        <div className="grid grid-cols-2 gap-4 text-left">
                            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                <FileSpreadsheet className="w-6 h-6 text-blue-500 mb-2" />
                                <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                                    데이터 업로드
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    CSV, Excel 파일을 분석하세요
                                </p>
                            </div>
                            <div className="p-4 bg-gray-50 dark:bg-gray-800/50 rounded-lg">
                                <div className="w-6 h-6 bg-gradient-to-br from-purple-500 to-pink-500 rounded mb-2" />
                                <p className="text-sm font-medium text-gray-900 dark:text-white mb-1">
                                    AI 코파일럿
                                </p>
                                <p className="text-xs text-gray-500 dark:text-gray-400">
                                    우측 사이드바에서 질문하세요
                                </p>
                            </div>
                        </div>
                    </Card>
                </div>
            ) : (
                /* 파일이 있을 때: 데이터 요약 표시 */
                <div className="flex-1 p-6 space-y-4">
                    <h3 className="text-lg font-semibold text-gray-900 dark:text-white">
                        업로드된 파일
                    </h3>
                    <div className="grid gap-4">
                        {activeSession.files.map((file) => (
                            <Card key={file.id} className="p-4">
                                <div className="flex items-start justify-between">
                                    <div className="flex items-center gap-3">
                                        <div className="p-2 bg-blue-100 dark:bg-blue-900/30 rounded-lg">
                                            <FileSpreadsheet className="w-5 h-5 text-blue-600 dark:text-blue-400" />
                                        </div>
                                        <div>
                                            <h4 className="text-sm font-medium text-gray-900 dark:text-white">
                                                {file.name}
                                            </h4>
                                            <p className="text-xs text-gray-500 dark:text-gray-400">
                                                {(file.size / 1024).toFixed(1)} KB
                                            </p>
                                        </div>
                                    </div>
                                    <span className={`px-2 py-1 rounded text-xs ${file.selected
                                            ? 'bg-green-100 text-green-700 dark:bg-green-900/30 dark:text-green-400'
                                            : 'bg-gray-100 text-gray-600 dark:bg-gray-800 dark:text-gray-400'
                                        }`}>
                                        {file.selected ? '선택됨' : '대기중'}
                                    </span>
                                </div>
                            </Card>
                        ))}
                    </div>

                    <div className="mt-8 p-6 bg-blue-50 dark:bg-blue-900/20 rounded-lg border border-blue-200 dark:border-blue-800">
                        <p className="text-sm text-blue-900 dark:text-blue-200">
                            💡 <strong>Tip:</strong> 우측 AI 코파일럿에게 "이 데이터를 분석해줘" 또는 "차트를 그려줘"와 같이 요청해보세요.
                        </p>
                    </div>
                </div>
            )}
        </div>
    );
}
