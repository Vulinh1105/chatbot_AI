import { useId, useLayoutEffect, useRef } from "react";
import "./ChatInput.css";

export interface ChatInputProps {
  value: string;
  onChange: (value: string) => void;
  onSend: (content: string) => boolean;
  disabled?: boolean;
  sendDisabled?: boolean;
}

function ChatInput({ value, onChange, onSend, disabled = false, sendDisabled = false }: ChatInputProps) {
  const inputId = useId();
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const composingRef = useRef(false);
  const restoreFocusRef = useRef(false);
  useLayoutEffect(() => {
    if (!disabled && restoreFocusRef.current) {
      restoreFocusRef.current = false;
      if (document.activeElement === document.body) textareaRef.current?.focus();
    }
  }, [disabled]);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (textarea && !textarea.disabled) textarea.focus();
  }, []);

  useLayoutEffect(() => {
    const textarea = textareaRef.current;
    if (!textarea) return;

    const resize = () => {
      const style = getComputedStyle(textarea);
      const lineHeight = parseFloat(style.lineHeight);
      const padding = parseFloat(style.paddingTop) + parseFloat(style.paddingBottom);
      const border = parseFloat(style.borderTopWidth) + parseFloat(style.borderBottomWidth);
      const minimum = lineHeight * 3 + padding + border;
      const maximum = lineHeight * 6 + padding + border;

      textarea.style.height = "auto";
      const height = Math.max(minimum, textarea.scrollHeight + border);
      textarea.style.height = `${Math.min(height, maximum)}px`;
      textarea.style.overflowY = height > maximum ? "auto" : "hidden";
    };

    resize();
    // Observe width only: our own height updates must not trigger a resize loop.
    let previousWidth = textarea.getBoundingClientRect().width;
    const observer = new ResizeObserver(() => {
      const width = textarea.getBoundingClientRect().width;
      if (width !== previousWidth) {
        previousWidth = width;
        resize();
      }
    });
    observer.observe(textarea);
    return () => observer.disconnect();
  }, [value]);

  const send = () => {
    const content = value.trim();
    if (disabled || sendDisabled || composingRef.current || !content) return;
    if (onSend(content)) {
      restoreFocusRef.current = true;
      onChange("");
      textareaRef.current?.focus();
    }
  };

  return (
    <form
      className="chat-composer"
      aria-label="Vùng nhập tin nhắn"
      onSubmit={(event) => {
        event.preventDefault();
        send();
      }}
    >
      <label htmlFor={inputId}>Tin nhắn</label>
      <textarea
        ref={textareaRef}
        id={inputId}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        onCompositionStart={() => { composingRef.current = true; }}
        onCompositionEnd={() => { composingRef.current = false; }}
        onBlur={() => { composingRef.current = false; }}
        onKeyDown={(event) => {
          if (event.key !== "Enter" || event.shiftKey) return;
          if (composingRef.current || event.nativeEvent.isComposing || event.nativeEvent.keyCode === 229) return;
          event.preventDefault();
          if (!event.repeat) send();
        }}
        rows={3}
        placeholder="Nhập câu hỏi của bạn…"
        aria-describedby={`${inputId}-hint`}
        disabled={disabled}
      />
      <div className="chat-composer-footer">
        <p id={`${inputId}-hint`}>Enter để gửi, Shift+Enter để xuống dòng</p>
        <button type="submit" disabled={disabled || sendDisabled || !value.trim()}>Gửi</button>
      </div>
    </form>
  );
}

export default ChatInput;
