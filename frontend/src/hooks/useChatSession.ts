import { useEffect } from "react";
import { useChatStore } from "../stores/chatStore";

export function useChatSession() {
  const cancel = useChatStore((state) => state.cancelRequest);
  const load = useChatStore((state) => state.loadConversations);
  useEffect(() => {
    if (!useChatStore.getState().initialized) void load();
    return () => cancel();
  }, [cancel, load]);
}
