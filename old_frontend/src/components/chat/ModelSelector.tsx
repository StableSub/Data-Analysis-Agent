import { useState } from 'react';
import { Check, ChevronDown, Sparkles } from 'lucide-react';
import { Button } from '../ui/button';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '../ui/dropdown-menu';
import { AI_MODELS, getModelById } from '../../lib/models';
import { cn } from '../ui/utils';

interface ModelSelectorProps {
  selectedModelId?: string;
  onSelectModel: (modelId: string) => void;
  variant?: 'default' | 'compact';
}

export function ModelSelector({ 
  selectedModelId, 
  onSelectModel,
  variant = 'default'
}: ModelSelectorProps) {
  const [open, setOpen] = useState(false);
  const selectedModel = selectedModelId ? getModelById(selectedModelId) : AI_MODELS[0];

  const handleSelect = (modelId: string) => {
    onSelectModel(modelId);
    setOpen(false);
  };

  if (variant === 'compact') {
    return (
      <div className="relative">
        <button
          type="button"
          onClick={() => {
            console.log('Button clicked! Current state:', open);
            setOpen(!open);
          }}
          className="inline-flex items-center justify-center gap-2 h-8 px-3 rounded-md text-sm font-medium transition-all border bg-white dark:bg-[#2c2c2e] text-gray-900 dark:text-white border-gray-300 dark:border-white/20 hover:bg-gray-50 dark:hover:bg-[#3a3a3c] outline-none"
        >
          <span className="text-base">{selectedModel?.icon}</span>
          <span className="hidden sm:inline">{selectedModel?.name}</span>
          <ChevronDown className="w-4 h-4 opacity-50" />
        </button>
        
        {open && (
          <div className="fixed inset-0 z-[90]" onClick={() => setOpen(false)} />
        )}
        
        {open && (
          <div className="absolute right-0 top-full mt-2 w-72 bg-white dark:bg-[#2c2c2e] border border-gray-200 dark:border-white/20 rounded-md shadow-lg z-[100] overflow-hidden">
            <div className="px-3 py-2 text-sm font-medium text-gray-900 dark:text-white">
              AI 모델 선택
            </div>
            <div className="h-px bg-gray-200 dark:bg-white/10" />
            <div className="max-h-[400px] overflow-y-auto">
              {AI_MODELS.map((model) => (
                <button
                  key={model.id}
                  type="button"
                  onClick={() => {
                    console.log('Selected model:', model.id);
                    handleSelect(model.id);
                  }}
                  className="w-full text-left px-3 py-2 hover:bg-gray-100 dark:hover:bg-[#3a3a3c] cursor-pointer transition-colors"
                >
                  <div className="flex items-center gap-3">
                    <span className="text-lg">{model.icon}</span>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="font-medium text-gray-900 dark:text-white">{model.name}</span>
                        <span className="text-xs text-gray-500 dark:text-gray-400">
                          {model.provider}
                        </span>
                      </div>
                      <p className="text-xs text-gray-600 dark:text-gray-400 truncate">
                        {model.description}
                      </p>
                    </div>
                    {selectedModelId === model.id && (
                      <Check className="w-4 h-4 text-blue-600 dark:text-[#0a84ff] flex-shrink-0" />
                    )}
                  </div>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    );
  }

  return (
    <DropdownMenu open={open} onOpenChange={setOpen}>
      <DropdownMenuTrigger asChild>
        <button className="group relative flex items-center gap-4 px-6 py-4 rounded-2xl border-2 border-gray-200 dark:border-white/20 hover:border-blue-500 dark:hover:border-[#0a84ff] bg-white dark:bg-[#2c2c2e] hover:bg-gray-50 dark:hover:bg-[#3a3a3c] transition-all duration-200 shadow-sm hover:shadow-md w-full max-w-2xl">
          <div className="flex items-center justify-center w-12 h-12 rounded-xl bg-gradient-to-br from-blue-500 to-purple-600 text-white text-2xl flex-shrink-0">
            {selectedModel?.icon}
          </div>
          <div className="flex-1 text-left min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="font-semibold text-gray-900 dark:text-white">
                {selectedModel?.name}
              </span>
              <span className="text-sm text-gray-500 dark:text-gray-400">
                by {selectedModel?.provider}
              </span>
            </div>
            <p className="text-sm text-gray-600 dark:text-gray-400">
              {selectedModel?.description}
            </p>
            <div className="flex items-center gap-2 mt-2">
              {selectedModel?.capabilities?.map((cap) => (
                <span
                  key={cap}
                  className="text-xs px-2 py-0.5 rounded-full bg-blue-100 dark:bg-blue-900/30 text-blue-700 dark:text-blue-300"
                >
                  {cap}
                </span>
              ))}
            </div>
          </div>
          <ChevronDown className="w-5 h-5 text-gray-400 dark:text-gray-500 group-hover:text-blue-600 dark:group-hover:text-[#0a84ff] transition-colors flex-shrink-0" />
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent 
        align="center" 
        className="w-[600px] bg-white dark:bg-[#2c2c2e] border-gray-200 dark:border-white/20 p-2"
      >
        <DropdownMenuLabel className="px-3 py-2 flex items-center gap-2 text-gray-900 dark:text-white">
          <Sparkles className="w-4 h-4" />
          AI 모델 선택
        </DropdownMenuLabel>
        <DropdownMenuSeparator className="bg-gray-200 dark:bg-white/10" />
        <div className="grid gap-1 max-h-[320px] overflow-y-auto">
          {AI_MODELS.map((model) => (
            <DropdownMenuItem
              key={model.id}
              onClick={() => handleSelect(model.id)}
              className={cn(
                "cursor-pointer rounded-lg p-3 focus:bg-gray-100 dark:focus:bg-[#3a3a3c]",
                selectedModelId === model.id && "bg-blue-50 dark:bg-blue-950/30"
              )}
            >
              <div className="flex items-start gap-3 w-full">
                <div className="flex items-center justify-center w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 text-white text-xl flex-shrink-0">
                  {model.icon}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2 mb-1">
                    <span className="font-medium text-gray-900 dark:text-white">
                      {model.name}
                    </span>
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {model.provider}
                    </span>
                  </div>
                  <p className="text-sm text-gray-600 dark:text-gray-400 mb-2">
                    {model.description}
                  </p>
                  <div className="flex items-center gap-2 flex-wrap">
                    {model.capabilities?.map((cap) => (
                      <span
                        key={cap}
                        className="text-xs px-2 py-0.5 rounded-full bg-gray-100 dark:bg-white/10 text-gray-700 dark:text-gray-300"
                      >
                        {cap}
                      </span>
                    ))}
                    <span className="text-xs text-gray-500 dark:text-gray-400">
                      {model.contextWindow.toLocaleString()} tokens
                    </span>
                  </div>
                </div>
                {selectedModelId === model.id && (
                  <Check className="w-5 h-5 text-blue-600 dark:text-[#0a84ff] flex-shrink-0 mt-1" />
                )}
              </div>
            </DropdownMenuItem>
          ))}
        </div>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}