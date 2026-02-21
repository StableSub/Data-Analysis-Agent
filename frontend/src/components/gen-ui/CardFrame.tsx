import {
  AlertCircle,
  CheckCircle2,
  Clock3,
  PauseCircle,
  Pin,
  PlayCircle,
  XCircle,
} from "lucide-react";

import { Button } from "../ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "../ui/card";
import { cn } from "../ui/utils";
import { BaseCardProps, CardAction } from "./types";

interface CardFrameProps {
  card: BaseCardProps;
  onAction?: (card: BaseCardProps, action: CardAction) => void;
  children: React.ReactNode;
}

function statusLabel(status: BaseCardProps["status"]): string {
  if (status === "queued") return "Queued";
  if (status === "running") return "Running";
  if (status === "success") return "Success";
  if (status === "failed") return "Failed";
  if (status === "canceled") return "Canceled";
  if (status === "needs_user") return "Need Input";
  return "Idle";
}

function statusClass(status: BaseCardProps["status"]): string {
  if (status === "success") return "genui-status-success";
  if (status === "failed") return "genui-status-error";
  if (status === "running") return "genui-status-running";
  if (status === "queued") return "genui-status-warning";
  if (status === "needs_user") return "genui-status-needs-user";
  return "genui-chip";
}

function statusIcon(status: BaseCardProps["status"]) {
  if (status === "running") return <PlayCircle className="h-3.5 w-3.5" />;
  if (status === "queued") return <Clock3 className="h-3.5 w-3.5" />;
  if (status === "success") return <CheckCircle2 className="h-3.5 w-3.5" />;
  if (status === "failed") return <XCircle className="h-3.5 w-3.5" />;
  if (status === "canceled") return <PauseCircle className="h-3.5 w-3.5" />;
  if (status === "needs_user") return <AlertCircle className="h-3.5 w-3.5" />;
  return <Clock3 className="h-3.5 w-3.5" />;
}

function actionLabel(action: CardAction): string {
  if (action.label) return action.label;
  switch (action.type) {
    case "add_to_report":
      return "Add to Report";
    case "view_log":
      return "View Log";
    case "open_artifact":
      return "Open Artifact";
    case "retry":
      return "Retry";
    case "cancel":
      return "Cancel";
    case "apply":
      return "Apply";
    case "edit":
      return "Edit";
    case "dismiss":
      return "Dismiss";
    case "pin":
      return "Pin";
    case "unpin":
      return "Unpin";
  }
}

function actionVariant(
  action: CardAction,
): "outline" | "default" | "secondary" | "destructive" {
  if (action.type === "apply") return "default";
  if (action.type === "cancel") return "destructive";
  if (action.type === "retry") return "secondary";
  return "outline";
}

export function CardFrame({ card, onAction, children }: CardFrameProps) {
  return (
    <Card className="genui-card genui-border genui-shadow-sm rounded-2xl border transition-shadow duration-150 ease-out hover:shadow-[var(--genui-shadow-md)]">
      <CardHeader className="genui-border space-y-2.5 border-b pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 flex-1">
            <CardTitle className="genui-text text-sm font-semibold">
              {card.title}
            </CardTitle>
            {card.subtitle ? (
              <CardDescription className="genui-muted mt-0.5 text-xs">
                {card.subtitle}
              </CardDescription>
            ) : null}
          </div>

          <div className="flex items-center gap-1.5">
            <span
              className={cn(
                "inline-flex items-center gap-1 rounded-full border px-2.5 py-0.5 text-[11px] font-medium",
                statusClass(card.status),
              )}
            >
              {statusIcon(card.status)}
              {statusLabel(card.status)}
            </span>
            {card.source.runId ? (
              <span className="genui-chip inline-flex items-center rounded-full border px-2 py-0.5 text-[11px]">
                run:{card.source.runId}
              </span>
            ) : null}
          </div>
        </div>

        {card.badges?.length ? (
          <div className="flex flex-wrap items-center gap-1.5">
            {card.badges.map((badge) => (
              <span
                key={badge.label}
                className="genui-chip inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-[11px]"
              >
                {badge.tone === "success" ? (
                  <CheckCircle2 className="h-3 w-3 text-genui-success" />
                ) : null}
                {badge.label}
              </span>
            ))}
          </div>
        ) : null}
      </CardHeader>

      <CardContent className="space-y-3.5 pt-4">
        {card.summary ? (
          <p className="genui-muted text-sm leading-relaxed">{card.summary}</p>
        ) : null}

        {children}

        {card.details?.length ? (
          <div className="space-y-1.5">
            {card.details.map((detail) => (
              <details
                key={detail.label}
                open={detail.defaultOpen}
                className="genui-border rounded-xl border px-3 py-2.5 text-xs"
              >
                <summary className="genui-muted cursor-pointer hover:text-[var(--genui-text)]">
                  {detail.label}
                </summary>
                <pre className="genui-panel genui-text mt-2 max-h-56 overflow-auto whitespace-pre-wrap rounded-lg p-2.5 text-[11px]">
                  {typeof detail.content === "string"
                    ? detail.content
                    : JSON.stringify(detail.content, null, 2)}
                </pre>
              </details>
            ))}
          </div>
        ) : null}

        {card.actions?.length ? (
          <div className="genui-border flex flex-wrap items-center gap-2 border-t pt-3.5">
            {card.actions.map((action, index) => (
              <Button
                key={`${action.type}-${index}`}
                size="sm"
                variant={actionVariant(action)}
                className={
                  actionVariant(action) === "default"
                    ? "bg-genui-running text-white hover:opacity-90"
                    : actionVariant(action) === "destructive"
                      ? "genui-status-error border"
                      : "genui-border genui-card genui-text border hover:opacity-90"
                }
                onClick={() => onAction?.(card, action)}
              >
                {action.type === "pin" || action.type === "unpin" ? (
                  <Pin className="mr-1.5 h-3.5 w-3.5" />
                ) : null}
                {actionLabel(action)}
              </Button>
            ))}
          </div>
        ) : null}
      </CardContent>
    </Card>
  );
}
