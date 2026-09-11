export type ChatStreamEvent =
  | { type: "delta"; content: string }
  | { type: "done" }
  | { type: "error" };

export interface MockChatRequest {
  content: string;
  attempt: number;
  signal: AbortSignal;
  onEvent: (event: ChatStreamEvent) => void;
}

// [error] fails the first attempt; retry succeeds. [slow] takes 5 seconds.
export function requestMockReply({ content, attempt, signal, onEvent }: MockChatRequest): Promise<string> {
  return new Promise((resolve, reject) => {
    if (signal.aborted) {
      reject(new DOMException("Aborted", "AbortError"));
      return;
    }
    const abort = () => {
      clearTimeout(timer);
      reject(new DOMException("Aborted", "AbortError"));
    };
    const answer = "Đã nhận câu hỏi của bạn. Đây là **câu trả lời mô phỏng**, chưa phân tích tài liệu.\n\nBạn có thể:\n- Gửi một câu hỏi khác.\n- Nhập nhiều dòng bằng Shift+Enter.\n\nVí dụ mã:\n```js\nconsole.log('Xin chào!');\n```";
    let offset = 0;
    const fail = () => {
      signal.removeEventListener("abort", abort);
      onEvent({ type: "error" });
      reject(new Error("Mock failure"));
    };
    const tick = () => {
      if (signal.aborted) return;
      if (content.includes("[stream-error]") && attempt === 1 && offset >= 60) {
        fail();
        return;
      }
      const chunk = answer.slice(offset, offset + 12);
      offset += chunk.length;
      onEvent({ type: "delta", content: chunk });
      if (signal.aborted) return;
      if (offset >= answer.length) {
        signal.removeEventListener("abort", abort);
        onEvent({ type: "done" });
        resolve(answer);
      } else {
        timer = setTimeout(tick, content.includes("[fast]") ? 1 : 80);
      }
    };
    let timer = setTimeout(() => {
      if (content.includes("[error]") && attempt === 1) {
        fail();
      } else {
        tick();
      }
    }, content.includes("[slow]") ? 5000 : 1200);
    signal.addEventListener("abort", abort, { once: true });
  });
}
