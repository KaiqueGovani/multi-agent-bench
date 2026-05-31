import { Suspense } from "react";
import { Loader2 } from "lucide-react";
import { ChatWorkspace } from "@/components/chat/chat-workspace";

export default function Home() {
  return (
    <Suspense fallback={<div className="flex h-screen items-center justify-center bg-background"><Loader2 className="h-6 w-6 animate-spin text-muted-foreground" /></div>}>
      <ChatWorkspace />
    </Suspense>
  );
}
