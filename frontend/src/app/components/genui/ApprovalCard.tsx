import React from "react";
import { Check, Edit2, X, AlertTriangle, ShieldCheck } from "lucide-react";
import { cn } from "../../../lib/utils";
import { CardShell, CardHeader, CardBody, CardFooter } from "./CardShell";
import { ToolCallIndicator } from "./ToolCallIndicator";

interface ApprovalCardProps {
  title: string;
  description: string;
  changes: string[];
  status?: "pending" | "approved" | "rejected" | "editing";
  onApprove?: () => void;
  onReject?: () => void;
  onEdit?: () => void;
  hideActions?: boolean;
  className?: string;
}

export function ApprovalCard({
  title,
  description,
  changes,
  status = "pending",
  onApprove,
  onReject,
  onEdit,
  hideActions = false,
  className
}: ApprovalCardProps) {
  
  if (status === "approved") {
    return (
      <CardShell status="success" className={className}>
        <CardHeader 
          title={title} 
          meta="Approved" 
          statusLabel="Action Complete" 
          statusVariant="success" 
        />
        <CardBody>
           <div className="flex items-center gap-2 text-sm text-[var(--genui-success)] bg-[var(--genui-success)]/10 p-3 rounded-lg border border-[var(--genui-success)]/20">
              <Check className="w-4 h-4" />
              <span>Changes applied successfully.</span>
           </div>
        </CardBody>
      </CardShell>
    );
  }

  if (status === "rejected") {
    return (
      <CardShell status="error" className={className}>
        <CardHeader 
          title={title} 
          meta="Rejected" 
          statusLabel="Action Cancelled" 
          statusVariant="error" 
        />
        <CardBody>
           <div className="flex items-center gap-2 text-sm text-[var(--genui-error)] bg-[var(--genui-error)]/10 p-3 rounded-lg border border-[var(--genui-error)]/20">
              <X className="w-4 h-4" />
              <span>User rejected the proposed changes.</span>
           </div>
        </CardBody>
      </CardShell>
    );
  }

  // Pending (Needs User) State
  return (
    <CardShell status="needs-user" className={cn("border-[var(--genui-needs-user)] shadow-[0_0_0_1px_var(--genui-needs-user)]", className)}>
      <CardHeader 
        title={title} 
        meta="Action Required" 
        statusLabel="Approval Needed" 
        statusVariant="needs-user"
      >
        <ToolCallIndicator status="needs-user" label="Awaiting confirmation..." />
      </CardHeader>
      
      <CardBody className="space-y-4">
        <p className="text-sm text-[var(--genui-text)] leading-relaxed">
          {description}
        </p>
        
        {/* Diff / Change List */}
        <div className="bg-[var(--genui-surface)]/50 rounded-lg border border-[var(--genui-border)] p-3 space-y-2">
           <div className="flex items-center justify-between border-b border-[var(--genui-border)] pb-2 mb-2">
              <span className="text-xs font-medium text-[var(--genui-muted)] uppercase tracking-wider">Proposed Changes</span>
              <button 
                onClick={onEdit}
                className="flex items-center gap-1 text-[10px] text-[var(--genui-running)] hover:underline"
              >
                 <Edit2 className="w-3 h-3" />
                 Edit Parameters
              </button>
           </div>
           <ul className="space-y-2">
             {changes.map((change, i) => (
               <li key={i} className="flex items-start gap-2 text-sm text-[var(--genui-text)]">
                 <div className="mt-1 w-1.5 h-1.5 rounded-full bg-[var(--genui-needs-user)] flex-shrink-0" />
                 <span>{change}</span>
               </li>
             ))}
           </ul>
        </div>

        {/* Optional Toggle */}
        <label className="flex items-center gap-2 cursor-pointer group">
           <div className="w-4 h-4 rounded border border-[var(--genui-border)] bg-[var(--genui-panel)] group-hover:border-[var(--genui-text)] transition-colors flex items-center justify-center">
              {/* Checkbox state logic omitted for UI mock */}
           </div>
           <span className="text-xs text-[var(--genui-muted)] group-hover:text-[var(--genui-text)] transition-colors">
              Always approve similar actions in this session
           </span>
        </label>
      </CardBody>

      {!hideActions && (
      <CardFooter className="flex justify-end gap-3 pt-4 border-t border-[var(--genui-border)]/50">
         <button 
           onClick={onReject}
           className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--genui-error)] hover:bg-[var(--genui-error)]/5 transition-colors"
         >
           Reject
         </button>
         <button 
           onClick={onEdit}
           className="px-4 py-2 rounded-lg text-sm font-medium text-[var(--genui-text)] bg-[var(--genui-surface)] border border-[var(--genui-border)] hover:bg-[var(--genui-border)]/20 transition-colors"
         >
           Edit
         </button>
         <button 
           onClick={onApprove}
           className="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-[var(--genui-needs-user)] hover:bg-[var(--genui-needs-user)]/90 shadow-sm transition-all"
         >
           <ShieldCheck className="w-4 h-4" />
           Approve
         </button>
      </CardFooter>
      )}
    </CardShell>
  );
}
