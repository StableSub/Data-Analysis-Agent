import { useState } from 'react';
import { Button } from '../ui/button';
import { Check, Copy } from 'lucide-react';
import { toast } from 'sonner';

interface MarkdownRendererProps {
  content: string;
}

export function MarkdownRenderer({ content }: MarkdownRendererProps) {
  // Simple markdown rendering - in production, use react-markdown or similar
  const renderContent = (text: string) => {
    const lines = text.split('\n');
    const elements: JSX.Element[] = [];
    let i = 0;

    while (i < lines.length) {
      const line = lines[i];

      // Code block
      if (line.startsWith('```')) {
        const language = line.slice(3).trim();
        const codeLines: string[] = [];
        i++;
        while (i < lines.length && !lines[i].startsWith('```')) {
          codeLines.push(lines[i]);
          i++;
        }
        elements.push(
          <CodeBlock key={i} code={codeLines.join('\n')} language={language} />
        );
        i++;
        continue;
      }

      // Heading
      if (line.startsWith('##')) {
        const level = line.match(/^#+/)?.[0].length || 2;
        const text = line.replace(/^#+\s*/, '');
        elements.push(
          <div key={i} className={`text-gray-900 mt-4 mb-2 ${level === 1 ? '' : level === 2 ? '' : ''}`}>
            {text}
          </div>
        );
      }
      // List item
      else if (line.match(/^(\d+\.|-|\*)\s/)) {
        const text = line.replace(/^(\d+\.|-|\*)\s*/, '');
        elements.push(
          <li key={i} className="ml-6 text-gray-700 mb-1">
            {formatInline(text)}
          </li>
        );
      }
      // Regular paragraph
      else if (line.trim()) {
        elements.push(
          <p key={i} className="text-gray-700 mb-2">
            {formatInline(line)}
          </p>
        );
      }
      // Empty line
      else {
        elements.push(<div key={i} className="h-2" />);
      }

      i++;
    }

    return elements;
  };

  const formatInline = (text: string) => {
    // Bold **text**
    let formatted = text.replace(/\*\*(.+?)\*\*/g, '<strong class="text-gray-900">$1</strong>');
    // Italic *text*
    formatted = formatted.replace(/\*(.+?)\*/g, '<em>$1</em>');
    // Inline code `code`
    formatted = formatted.replace(/`(.+?)`/g, '<code class="bg-gray-100 px-1 py-0.5 rounded text-sm text-blue-600">$1</code>');

    return <span dangerouslySetInnerHTML={{ __html: formatted }} />;
  };

  return <div className="space-y-1">{renderContent(content)}</div>;
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      toast.success('코드가 복사되었습니다');
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      toast.error('복사에 실패했습니다');
    }
  };

  return (
    <div className="my-4 rounded-lg bg-gray-900 overflow-hidden">
      <div className="flex items-center justify-between px-4 py-2 bg-gray-800 border-b border-gray-700">
        <span className="text-xs text-gray-400">{language || 'code'}</span>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleCopy}
          className="h-6 text-gray-400 hover:text-white"
        >
          {copied ? (
            <>
              <Check className="w-3 h-3 mr-1" />
              복사됨
            </>
          ) : (
            <>
              <Copy className="w-3 h-3 mr-1" />
              복사
            </>
          )}
        </Button>
      </div>
      <pre className="p-4 overflow-x-auto">
        <code className="text-sm text-gray-100">{code}</code>
      </pre>
    </div>
  );
}
