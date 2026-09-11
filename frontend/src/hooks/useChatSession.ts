import { useEffect } from "react";
import { useChatStore } from "../stores/chatStore";

export function useChatSession() {
  const cancel = useChatStore((state) => state.cancelRequest);
  useEffect(() => () => cancel(), [cancel]);
}
