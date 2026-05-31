import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { DashboardWorkspace } from "@/components/dashboard/dashboard-workspace";

export default function DashboardPage() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-background"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}>
      <DashboardWorkspace />
    </Suspense>
  );
}
