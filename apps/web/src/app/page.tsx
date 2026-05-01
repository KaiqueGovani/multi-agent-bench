import { Suspense } from "react";
import { ChatWorkspace } from "@/components/chat/chat-workspace";

export default function Home() {
  return (
    <Suspense>
      <ChatWorkspace />
    </Suspense>
  );
}
