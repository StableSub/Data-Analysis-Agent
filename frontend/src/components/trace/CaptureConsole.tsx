import { useState } from 'react';
import { Card } from '../ui/card';
import { Button } from '../ui/button';
import { Badge } from '../ui/badge';
import { Input } from '../ui/input';
import { Label } from '../ui/label';
import { ScrollArea } from '../ui/scroll-area';
import { Play, Square, Download, Terminal } from 'lucide-react';
import { toast } from 'sonner';
import { useStore } from '../../store/useStore';

export function CaptureConsole() {
  const [isCapturing, setIsCapturing] = useState(false);
  const [duration, setDuration] = useState(30);
  const [captureEvents, setCaptureEvents] = useState<any[]>([]);
  const { addAuditLog, user } = useStore();

  const handleStartCapture = () => {
    if (!user) return;
    
    setIsCapturing(true);
    setCaptureEvents([]);
    
    // Add audit log
    addAuditLog({
      user: user.email,
      action: 'TRACE:CAPTURE',
      target: 'collector',
      result: 'success',
    });

    toast.success(`${duration}초 동안 이벤트 캡처를 시작합니다`);

    // Mock capture - in production, this would call the API
    const mockEvents = [
      { time: '00:01', type: 'exec', process: 'python3', cmd: '/usr/bin/python3 app.py' },
      { time: '00:03', type: 'open', process: 'python3', path: '/etc/passwd', suspicious: true },
      { time: '00:05', type: 'tcp_connect', process: 'curl', dest: '192.168.1.100:8080' },
      { time: '00:08', type: 'exec', process: 'bash', cmd: '/bin/bash -c ls' },
      { time: '00:12', type: 'open', process: 'vim', path: '/home/user/data.csv' },
    ];

    let index = 0;
    const interval = setInterval(() => {
      if (index < mockEvents.length) {
        setCaptureEvents((prev) => [...prev, mockEvents[index]]);
        index++;
      } else {
        clearInterval(interval);
        setIsCapturing(false);
        toast.success('캡처가 완료되었습니다');
      }
    }, 2000);

    // Auto-stop after duration
    setTimeout(() => {
      clearInterval(interval);
      setIsCapturing(false);
    }, duration * 1000);
  };

  const handleStopCapture = () => {
    setIsCapturing(false);
    toast.info('캡처를 중단했습니다');
  };

  const handleDownload = () => {
    const data = JSON.stringify(captureEvents, null, 2);
    const blob = new Blob([data], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `capture-${new Date().toISOString()}.json`;
    a.click();
    toast.success('캡처 데이터를 다운로드했습니다');
  };

  return (
    <Card className="p-6">
      <div className="flex items-center justify-between mb-4">
        <div className="flex items-center gap-2">
          <Terminal className="w-5 h-5 text-blue-600" />
          <h3 className="text-gray-900">온디맨드 캡처 (On-demand Capture)</h3>
        </div>
        {isCapturing && (
          <Badge variant="default" className="animate-pulse">
            캡처 중...
          </Badge>
        )}
      </div>

      <div className="space-y-4">
        {/* Controls */}
        <div className="flex items-end gap-3">
          <div className="flex-1">
            <Label htmlFor="duration">캡처 시간 (초)</Label>
            <Input
              id="duration"
              type="number"
              min={10}
              max={300}
              value={duration}
              onChange={(e) => setDuration(parseInt(e.target.value) || 30)}
              disabled={isCapturing}
              className="mt-1"
            />
          </div>
          
          {isCapturing ? (
            <Button onClick={handleStopCapture} variant="destructive" className="gap-2">
              <Square className="w-4 h-4" />
              중단
            </Button>
          ) : (
            <Button onClick={handleStartCapture} className="gap-2">
              <Play className="w-4 h-4" />
              시작
            </Button>
          )}

          <Button
            onClick={handleDownload}
            variant="outline"
            disabled={captureEvents.length === 0}
            className="gap-2"
          >
            <Download className="w-4 h-4" />
            다운로드
          </Button>
        </div>

        {/* Event Stream */}
        <div className="border border-gray-200 rounded-lg bg-gray-900 overflow-hidden">
          <div className="bg-gray-800 px-4 py-2 border-b border-gray-700">
            <span className="text-xs text-gray-400">
              이벤트 스트림 ({captureEvents.length}개)
            </span>
          </div>
          <ScrollArea className="h-[400px]">
            <div className="p-4 font-mono text-xs space-y-2">
              {captureEvents.length === 0 ? (
                <p className="text-gray-500">캡처를 시작하려면 '시작' 버튼을 클릭하세요</p>
              ) : (
                captureEvents.map((event, index) => (
                  <div
                    key={index}
                    className={`p-2 rounded ${
                      event.suspicious ? 'bg-orange-900/30 border border-orange-700' : 'bg-gray-800'
                    }`}
                  >
                    <span className="text-blue-400">[{event.time}]</span>{' '}
                    <span className="text-purple-400">{event.type}</span>{' '}
                    <span className="text-gray-300">{event.process}</span>
                    {event.cmd && <span className="text-gray-400"> → {event.cmd}</span>}
                    {event.path && (
                      <span className="text-yellow-400"> → {event.path}</span>
                    )}
                    {event.dest && <span className="text-green-400"> → {event.dest}</span>}
                  </div>
                ))
              )}
            </div>
          </ScrollArea>
        </div>
      </div>
    </Card>
  );
}
