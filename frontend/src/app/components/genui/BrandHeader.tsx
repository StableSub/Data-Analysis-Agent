import React from "react";
import { cn } from "../../../lib/utils";

export type BrandHeaderVariant = "default" | "compact";

interface BrandHeaderProps {
  variant?: BrandHeaderVariant;
  className?: string;
}

/**
 * BrandHeader – HARU / Hanyang AI Research Union
 *
 * variant="default"  → logo icon + stacked text (brand title + subtitle)
 * variant="compact"  → icon + inline text only (for tight headers)
 */
export function BrandHeader({
  variant = "default",
  className,
}: BrandHeaderProps) {
  if (variant === "compact") {
    return (
      <div className={cn("flex items-center gap-1.5", className)}>
        {/* Logo mark */}
        <div
          className="w-5 h-5 rounded flex items-center justify-center flex-shrink-0"
          style={{ background: "var(--genui-running)" }}
        >
          <span
            className="text-white"
            style={{ fontSize: "10px", fontWeight: 800, lineHeight: 1 }}
          >
            H
          </span>
        </div>

        {/* Compact: single-line brand + subtitle */}
        <div className="flex items-baseline gap-1.5">
          <span
            className="text-[var(--genui-text)] uppercase tracking-widest"
            style={{ fontSize: "12px", fontWeight: 800, letterSpacing: "0.12em" }}
          >
            HARU
          </span>
          <span
            className="text-[var(--genui-muted)] hidden sm:inline"
            style={{ fontSize: "9px", fontWeight: 500, letterSpacing: "0.04em" }}
          >
            Hanyang AI Research Union
          </span>
        </div>
      </div>
    );
  }

  /* default variant – stacked layout */
  return (
    <div className={cn("flex items-center gap-2.5", className)}>
      {/* Logo mark */}
      <div
        className="w-7 h-7 rounded-md flex items-center justify-center flex-shrink-0 shadow-sm"
        style={{ background: "var(--genui-running)" }}
      >
        <span
          className="text-white"
          style={{ fontSize: "13px", fontWeight: 900, lineHeight: 1 }}
        >
          H
        </span>
      </div>

      {/* Stacked text */}
      <div className="flex flex-col justify-center gap-0" style={{ lineHeight: 1 }}>
        <span
          className="text-[var(--genui-text)] uppercase tracking-widest"
          style={{ fontSize: "14px", fontWeight: 800, letterSpacing: "0.14em", lineHeight: 1.15 }}
        >
          HARU
        </span>
        <span
          className="text-[var(--genui-muted)]"
          style={{ fontSize: "9px", fontWeight: 500, letterSpacing: "0.06em", lineHeight: 1.4 }}
        >
          Hanyang AI Research Union
        </span>
      </div>
    </div>
  );
}
