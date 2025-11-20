import { FeatureNav } from '../layout/FeatureNav';
import { Database, Filter, BarChart3, FileEdit, Activity, Shield } from 'lucide-react';
import { Card } from '../ui/card';

/**
 * Coming Soon 페이지 템플릿
 */
function ComingSoonTemplate({ 
  icon: Icon, 
  title, 
  description, 
  features,
  featureId
}: { 
  icon: any; 
  title: string; 
  description: string; 
  features: string[];
  featureId: any;
}) {
  return (
    <div className="flex h-screen bg-gray-50 dark:bg-[#1c1c1e]">
      {/* 좌측 네비게이션 */}
      <FeatureNav 
        activeFeature={featureId}
        onFeatureChange={() => {}}
      />

      {/* 메인 컨텐츠 */}
      <div className="flex-1 h-full flex flex-col bg-white dark:bg-[#1c1c1e]">
        {/* Header */}
        <div className="p-6 border-b border-gray-200 dark:border-white/10">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 rounded-lg bg-blue-100 dark:bg-blue-900/30 flex items-center justify-center">
              <Icon className="w-5 h-5 text-blue-600 dark:text-[#0a84ff]" />
            </div>
            <div>
              <h2 className="text-gray-900 dark:text-white text-xl">{title}</h2>
              <p className="text-sm text-gray-500 dark:text-[#98989d]">{description}</p>
            </div>
          </div>
        </div>

        {/* Content */}
        <div className="flex-1 overflow-auto p-6">
          <div className="max-w-3xl mx-auto">
            <Card className="p-12 text-center">
              <div className="w-20 h-20 rounded-full bg-gradient-to-br from-blue-100 to-purple-100 dark:from-blue-900/30 dark:to-purple-900/30 flex items-center justify-center mx-auto mb-6">
                <Icon className="w-10 h-10 text-blue-600 dark:text-[#0a84ff]" />
              </div>
              
              <h3 className="text-2xl text-gray-900 dark:text-white mb-3">
                곧 출시 예정
              </h3>
              
              <p className="text-gray-600 dark:text-gray-400 mb-8 max-w-md mx-auto">
                {description}
              </p>

              {features.length > 0 && (
                <div className="inline-block text-left">
                  <h4 className="text-sm font-medium text-gray-900 dark:text-white mb-3">
                    예정된 기능:
                  </h4>
                  <ul className="space-y-2">
                    {features.map((feature, idx) => (
                      <li key={idx} className="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
                        <div className="w-1.5 h-1.5 rounded-full bg-blue-500" />
                        {feature}
                      </li>
                    ))}
                  </ul>
                </div>
              )}

              <div className="mt-8 pt-8 border-t border-gray-200 dark:border-white/10">
                <p className="text-xs text-gray-500 dark:text-[#98989d]">
                  이 기능은 현재 개발 중입니다
                </p>
              </div>
            </Card>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 데이터 스냅샷
 */
export function ComingSoonSnapshot() {
  return (
    <ComingSoonTemplate
      icon={Database}
      title="데이터 스냅샷"
      description="데이터 버전 관리 및 스냅샷 기능"
      featureId="data-snapshot"
      features={[
        '데이터 버전 저장 및 관리',
        '특정 시점으로 복원',
        '버전 간 비교 분석',
        '자동 스냅샷 스케줄링'
      ]}
    />
  );
}

/**
 * 데이터 필터링
 */
export function ComingSoonFilter() {
  return (
    <ComingSoonTemplate
      icon={Filter}
      title="데이터 필터링"
      description="조건별 데이터 추출 및 필터링"
      featureId="data-filter"
      features={[
        '다중 조건 필터링',
        '고급 쿼리 빌더',
        '필터 템플릿 저장',
        '실시간 결과 미리보기'
      ]}
    />
  );
}

/**
 * 데이터 시각화
 */
export function ComingSoonVisualization() {
  return (
    <ComingSoonTemplate
      icon={BarChart3}
      title="데이터 시각화"
      description="다양한 차트와 그래프로 데이터 시각화"
      featureId="visualization"
      features={[
        '차트 타입: 선, 막대, 원형, 산점도 등',
        '인터랙티브 차트',
        '대시보드 구성',
        '차트 내보내기 (PNG, PDF)'
      ]}
    />
  );
}

/**
 * 데이터 편집
 */
export function ComingSoonEdit() {
  return (
    <ComingSoonTemplate
      icon={FileEdit}
      title="데이터 편집"
      description="AI 기반 데이터 수정 및 보정"
      featureId="data-edit"
      features={[
        'AI 추천 데이터 보정',
        '일괄 편집 기능',
        '데이터 유효성 검사',
        '변경 이력 추적'
      ]}
    />
  );
}

/**
 * 시뮬레이션
 */
export function ComingSoonSimulation() {
  return (
    <ComingSoonTemplate
      icon={Activity}
      title="시뮬레이션"
      description="제조 공정 시뮬레이션 및 예측"
      featureId="simulation"
      features={[
        '공정 시뮬레이션',
        '예측 분석',
        '시나리오 비교',
        '최적화 제안'
      ]}
    />
  );
}

/**
 * 감사 로그
 */
export function ComingSoonAudit() {
  return (
    <ComingSoonTemplate
      icon={Shield}
      title="감사 로그"
      description="사용자 활동 추적 및 보안 모니터링"
      featureId="audit-log"
      features={[
        '사용자 활동 로그',
        '데이터 접근 기록',
        '보안 이벤트 모니터링',
        '로그 검색 및 필터링'
      ]}
    />
  );
}
