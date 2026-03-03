import React from "react";
import { cn } from "../../../lib/utils";

export function StreamingText({ text, speed = 50, className }: { text: string; speed?: number; className?: string }) {
  const [displayedText, setDisplayedText] = React.useState("");

  React.useEffect(() => {
    let index = 0;
    const interval = setInterval(() => {
      setDisplayedText((prev) => {
        if (index < text.length) {
          index++;
          return text.substring(0, index);
        }
        return prev;
      });
    }, speed);

    return () => clearInterval(interval);
  }, [text, speed]);

  return (
    <span className={cn("inline-block", className)}>
      {displayedText}
      <span className="inline-block w-1.5 h-4 ml-0.5 bg-[var(--genui-running)] animate-pulse align-middle" />
    </span>
  );
}
