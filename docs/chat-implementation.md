# Tiến độ triển khai Chat

## Quy tắc cho mỗi phiên

- Chỉ triển khai một bước, kiểm tra và cập nhật tài liệu này rồi dừng.
- Đọc tài liệu này và code liên quan trước khi sửa. Không refactor ngoài phạm vi.
- Dùng mock trước, giao diện tiếng Việt, giữ navigation và phong cách hiện tại.
- Chat lưu trong RAM, reload mất lịch sử. API thật là đợt riêng khi có hợp đồng backend.
- Chưa làm upload trong chat, citation UI, feedback, tìm kiếm hoặc đổi tên hội thoại.
- Xóa hội thoại được người dùng bổ sung sau bước 4 và đã triển khai bên dưới.

## Trạng thái ngày 2026-09-08

- [x] Bước 0: code nền tảng, build và lint.
- [ ] Bước 0: xác nhận trực tiếp đăng nhập demo và giao diện desktop/mobile.
- [x] Bước 1: Chat input — code, build và lint.
- [ ] Bước 1: kiểm chứng tương tác và responsive trong trình duyệt.
- [x] Bước 2: Message list và gửi mock tức thời — code, build/lint, kiểm tra store.
- [ ] Bước 2: kiểm chứng Markdown, cuộn và responsive trong trình duyệt.
- [x] Bước 3: Conversation list — code, build/lint, kiểm tra store.
- [ ] Bước 3: kiểm chứng sidebar/mobile và chuyển hội thoại trong trình duyệt.
- [x] Bước 4: Loading, lỗi và thử lại — code, build/lint và 7 test Vitest.
- [ ] Bước 4: kiểm thử tương tác trên trình duyệt.
- [x] Bước 5: Streaming UX — code, build/lint, 16 tests Vitest.
- [ ] Bước 5: kiểm chứng streaming/cuộn/Dừng trên trình duyệt.

## Bước 0 đã triển khai

- Sửa dòng mô tả sai cú pháp trong `frontend/src/types/chat.ts`.
- Bỏ `Message.sender`, bắt buộc `Message.role`: `user | assistant | system`.
  Không có consumer sử dụng sender trước thay đổi. Giữ các type citation còn lại.
- Xóa ký tự `q` trong login; đổi FormEvent và hai import Citation thành type-only
  theo cấu hình verbatimModuleSyntax.
- Thêm khung chat: tiêu đề, vùng danh sách tin nhắn trống, vùng nhập và nút gửi disabled.
  Chưa có state, service, gửi tin hoặc streaming. CSS riêng cho trang chat.
- Giữ route `/chat` và ProtectedRoute. Login demo vẫn dùng
  `demo@docbot.local` / `123456`.

### File đã thay đổi (đường dẫn từ gốc repository chatbot_AI)

- `frontend/src/types/chat.ts`
- `frontend/src/pages/Login/LoginPage.tsx`
- `frontend/src/components/citations/CitationBadge.tsx`
- `frontend/src/components/citations/SourcecCard.tsx`
- `frontend/src/pages/Chat/ChatPage.tsx`
- `frontend/src/pages/Chat/ChatPage.css`
- `docs/chat-implementation.md`

### Kết quả kiểm tra

- Ban đầu: build lỗi cú pháp chat.ts; lint lỗi chat.ts và ký tự q.
- Sau sửa cú pháp: build phát hiện thêm hai import Citation cần type-only; đã sửa.
- `npm.cmd run build`: PASS (TypeScript và Vite).
- `npm.cmd run lint`: PASS.
- Vite dev khởi động được tại http://127.0.0.1:5173/.
- Chưa kiểm chứng tương tác/hiển thị bằng trình duyệt: công cụ báo không có browser.
  Không coi build là bằng chứng đăng nhập hoặc responsive đã được kiểm thử.
- Kiểm tra thủ công còn lại: đăng nhập demo chuyển đến /chat, thấy khung và controls
  disabled; thử chiều rộng 375px và desktop, không tràn ngang; navigation tài liệu
  và đăng xuất vẫn hoạt động.

## Quyết định kiến trúc cho các bước tiếp theo

- Component hiển thị/tương tác; Zustand giữ dữ liệu; hook điều phối request/stream/hủy.
- Message.role là nguồn duy nhất xác định người gửi. Giữ ID ổn định.
- Khi tạo store ở bước 2, dùng messages theo conversation ID làm nguồn chính;
  không sao chép vào Conversation.messages. Trường optional hiện tại chưa được dùng.
- Bước 3 thêm activeConversationId, metadata hội thoại và draft theo ID.
- Từ bước 4 chỉ có một request toàn ứng dụng; cho chuyển hội thoại nhưng khóa gửi.
- Request gắn conversation ID và message ID; bỏ qua kết quả đến muộn sau hủy.

## Bước 1 — đã triển khai

- Thêm `frontend/src/components/chat/ChatInput.tsx` và `ChatInput.css`.
- Interface: value: string, onChange: (value: string) => void,
  onSend: (content: string) => boolean, disabled?: boolean (mặc định false).
- Component controlled, không sao chép draft; onSend nhận nội dung đã trim.
  Callback trả true thì xóa draft/giữ focus; false thì giữ nguyên draft.
- Dùng form và chung hàm gửi cho nút/Enter; Shift+Enter xuống dòng,
  chặn IME composition và key repeat; chặn rỗng/whitespace và disabled ở hàm gửi.
- Textarea 3–6 dòng, đo scrollHeight khi value thay đổi, theo dõi chiều rộng bằng
  ResizeObserver (có disconnect khi cleanup), vượt 6 dòng cuộn bên trong.
- Có label, hướng dẫn bàn phím, focus-visible và trạng thái disabled.
- `ChatPage.tsx` giữ draft và lastSubmittedContent bằng useState;
  callback mock lưu lần gửi gần nhất và trả true. Gửi mới thay thế nội dung cũ.
- `ChatPage.css` chỉ giữ bố cục/vùng kết quả; nội dung là text giữ xuống dòng và
  ngắt chuỗi dài. Không có API, lịch sử, assistant, store hoặc loading/streaming.
- Reload hoặc rời trang rồi quay lại sẽ mất draft và nội dung mock của bước này.

### Kiểm tra bước 1

- `npm.cmd run build`: PASS (TypeScript + Vite).
- `npm.cmd run lint`: PASS.
- Kiểm tra tĩnh các nhánh gửi, từ chối, disabled và cleanup observer.
- Công cụ UI trả apps=[] và browsers=[]; chưa xác nhận tương tác thực tế,
  IME, chiều cao/focus hay responsive. Không bổ sung thư viện test ở bước này.
- Khi có browser: thử nút Gửi/Enter (một lần, trim, xóa, focus), Shift+Enter,
  rỗng/whitespace, IME tiếng Việt, giữ Enter, nhập/xóa trên 6 dòng, đổi chiều rộng,
  chuỗi dài, desktop/375px và reload. Trong harness tạm, thử disabled=true
  và onSend trả false để xác nhận không gửi/không mất draft.
- Kiểm tra login/navigation còn thiếu của bước 0 vẫn cần làm; composer hiện tại
  đã được bật thay cho trạng thái disabled ở bước 0.

### Bước 2 — đã triển khai

- Thêm `frontend/src/stores/chatStore.ts`: messagesByConversation là nguồn duy nhất,
  khởi tạo một hội thoại `local-conversation`; sendMessage(content): boolean chặn rỗng,
  trim và thêm nguyên tử cặp user/assistant có UUID, created_at và status=done.
- Mock cố định có đoạn văn, chữ đậm, danh sách, code block; nêu rõ chưa phân tích tài liệu.
  Không có request hoặc trạng thái chờ. Không sao chép messages vào Conversation.
- Thêm `frontend/src/components/chat/MessageItem.tsx`: memo theo message,
  nhãn Bạn/DocBot/Hệ thống, user/system là text giữ xuống dòng;
  assistant dùng react-markdown skipHtml, giữ bộ lọc URL mặc định, không bật HTML thô.
- Thêm `MessageList.tsx` và `MessageList.css` cùng thư mục: empty state,
  danh sách có thứ tự và key ID, vùng log cuộn bằng bàn phím, code block cuộn ngang.
- Cuộn: ngưỡng gần cuối 80px; user mới luôn kéo xuống; nội dung mới chỉ theo cuối
  khi người dùng đang gần cuối. Nút Xuống cuối hiện khi ở xa cuối.
  ResizeObserver theo dõi viewport/content (gồm thay đổi kích thước nội dung), cleanup
  khi unmount. Tắt overflow-anchor để tránh trình duyệt tự đổi vị trí khi đang đọc.
- ChatPage dùng selector riêng cho messages và sendMessage, giữ draft local;
  xóa lastSubmittedContent và CSS preview. Giữ contract ChatInput bước 1.
- Lịch sử giữ trong RAM khi rời chat rồi quay lại; reload mất lịch sử.
  Draft vẫn mất khi rời trang. Reset store khi logout thuộc bước 4 đã chốt,
  hiện chưa triển khai; dữ liệu ở bước này chỉ là mock local.

### Kiểm tra bước 2

- `npm.cmd run build`: PASS.
- `npm.cmd run lint`: PASS, không còn warning dependency hook cuộn.
- Chạy smoke check store bằng Node TypeScript stripping: PASS cho input rỗng,
  trim/giữ xuống dòng, thứ tự user-assistant, giữ lịch sử, không mutate mảng trước,
  giữ reference message cũ, ID không trùng và status done.
- Không thêm dependency hoặc bộ test vào repository ở bước này.
- Công cụ UI vẫn trả apps=[] và browsers=[]: chưa kiểm thử trình duyệt.
- Cần kiểm tra trực tiếp: login và input bước 0–1; nhiều lượt; text dài/Markdown/code;
  desktop/375px không tràn ngang; cuộn lên rồi gửi phải xuống cuối; nút Xuống cuối;
  nội dung assistant cập nhật khi đang ở trên không kéo xuống (harness tạm vì mock
  hiện trả tức thời); đổi chiều rộng; rời trang/quay lại giữ lịch sử; reload xóa lịch sử.

### Điểm bàn giao tiếp theo

- Hoàn tất kiểm tra UI còn thiếu của bước 0–5. Tích hợp API thật cần hợp đồng backend,
  là đợt riêng; không tự chọn endpoint hoặc giao thức streaming.
- Hoàn tất kiểm tra UI còn thiếu khi có browser; ghi rõ hạn chế nếu chưa kiểm tra được.

### Bước 3 — đã triển khai

- `frontend/src/stores/chatStore.ts`: thêm conversations (metadata, dùng
  Omit<Conversation, "messages">), activeConversationId, draftsByConversation.
  Messages vẫn chỉ lưu tại messagesByConversation.
- createConversation(): string tái sử dụng active nếu chưa có message, giữ draft;
  nếu đã có message thì tạo UUID, metadata/draft/messages mới và đưa lên đầu.
- selectConversation(id): void chỉ chọn ID hợp lệ, không đổi timestamp/thứ tự.
  setDraft(id, value): void chỉ ghi đúng hội thoại hợp lệ.
- sendMessage(content): boolean gửi vào active, xóa draft của hội thoại đó,
  thêm cặp mock, cập nhật updated_at và đưa hội thoại lên đầu kể cả khi timestamp trùng.
  Tiêu đề chỉ lấy ở lần gửi đầu, gộp whitespace và cắt tối đa 40 Unicode code point.
- `frontend/src/components/chat/ConversationList.tsx` và CSS: nút tạo mới,
  danh sách giới hạn chiều cao có cuộn, active aria-current, focus-visible và title tooltip.
- Sidebar chỉ hiện danh sách ở /chat, ẩn ở chiều rộng <=768px.
  ChatPage có mục Hội thoại mở/đóng bằng details/summary trên mobile;
  tạo/chọn sẽ đóng danh sách, trả focus về summary. Không dùng overlay hoặc modal.
- ChatPage đọc title/messages/draft theo active ID, không còn draft local.
  MessageList và ChatInput key theo active ID để reset scroll/composition khi chuyển;
  mở hội thoại hiển thị cuối lịch sử. Draft và lịch sử giữ khi đổi route, reload mất.
- File sửa: chatStore.ts, Sidebar.tsx, ChatPage.tsx, ChatPage.css và tài liệu này;
  thêm ConversationList.tsx/ConversationList.css. Không thêm dependency.

### Kiểm tra bước 3

- `npm.cmd run build`: PASS; `npm.cmd run lint`: PASS không warning.
- Node smoke check store: PASS cho tái sử dụng hội thoại trống (kể cả có draft),
  tạo mới sau gửi, input rỗng, xóa draft khi gửi, hai draft/lịch sử độc lập,
  chọn không đổi thứ tự, ID không hợp lệ, gửi đưa lên đầu, tiêu đề đầu giữ nguyên
  và giới hạn 40 ký tự, immutable message cũ, UUID duy nhất và metadata không chứa messages.
- `git diff --check`: PASS (chỉ cảnh báo chuyển đổi LF/CRLF của Git).
- UI tool vẫn trả apps=[] và browsers=[]; chưa xác nhận trực tiếp desktop/mobile.
- Cần kiểm tra browser: hai hội thoại với draft khác nhau, tạo/chọn và active,
  gửi đổi thứ tự, tiêu đề dài, danh sách dài, /documents ẩn danh sách,
  <=768px mở/đóng bằng bàn phím và focus sau chọn, 375px không tràn ngang,
  quay lại hội thoại reset về cuối và input hiện đúng draft, reload khởi tạo lại một hội thoại.
- Kiểm tra UI bước 0–2 vẫn còn thiếu. Reset chat khi logout vẫn dành cho bước 4.

## Các bước sau — phạm vi đã chốt

### Đợt hoàn thiện UI sau bước 5

- Rà code và sửa header wrap/gap ở màn hình hẹp; bổ sung nhãn/title cho navigation
  chỉ hiện emoji trên mobile, focus-visible cho navigation/logout.
- ChatInput phục hồi focus sau gửi khi hết disabled nếu focus đang ở body;
  không giành focus từ điều khiển khác. Blur reset composition để tránh trạng thái IME treo.
- Xóa hội thoại đưa focus về nút tạo mới; mobile tiếp tục đưa về summary Hội thoại.
- Tăng vùng bấm Gửi/Xóa/Xuống cuối lên 44px, thanh streaming có wrap;
  dùng scrollbar-gutter ổn định và overscroll containment cho vùng danh sách.
- Files: ChatInput.tsx/CSS, ConversationList.tsx/CSS, Sidebar.tsx, index.css,
  MessageList.css, tài liệu này và chat-ui-checklist.md.
- Build/lint PASS, 16/16 test logic cũ PASS. Không thêm test chỉ phản chiếu CSS.
- Chưa hoàn thành QA trực quan: tool vẫn apps=[]/browsers=[]. Checklist cụ thể ở
  `docs/chat-ui-checklist.md`; mọi ca browser vẫn ghi Chưa chạy. Cần browser hoặc
  phản hồi/ảnh từ người dùng để xác nhận layout thực tế, IME, focus và cuộn.

### Bước 5 — đã triển khai và bàn giao

- mockChat.ts thêm ChatStreamEvent delta/content, done, error và onEvent vào request.
  Promise vẫn trả chuỗi đầy đủ khi hoàn thành để chốt nội dung cuối; reject khi lỗi/hủy.
  Đây là hợp đồng nội bộ của mock, chưa phải giao thức backend.
- Sau chờ đầu tiên 1200ms, mock phát 12 ký tự mỗi 80ms. [slow] chờ phần đầu 5000ms;
  [fast] khoảng cách phần 1ms; [error] lỗi trước phần đầu ở lần 1;
  [stream-error] lỗi sau 60 ký tự ở lần 1. Retry thành công. Có thể kết hợp marker.
- chatStore gom delta vào buffer theo request, tối đa một cập nhật mỗi frame qua
  requestAnimationFrame. Flush khi done/error/cancel/stop để không mất phần cuối.
  Chỉ sửa cùng message assistant; waiting → streaming → done/error/stopped.
- stopRequest() gọi cancelRequest("stop"): giữ toàn bộ phần đã nhận, đánh dấu stopped,
  giải phóng khóa gửi. Dừng trước phần đầu giữ message rỗng với nhãn Đã dừng.
- cancelRequest() mặc định vẫn dành cho rời trang: giữ nội dung và error để retry.
  Retry xóa phần cũ, dùng lại message/user ID và phát lại từ đầu; stopped không có retry,
  người dùng có thể gửi tin mới. Lỗi giữa stream giữ nguyên phần nhận được.
- Hủy frame đã lên lịch, abort timer và bỏ qua delta/done/reject đến muộn theo request ID.
  Logout/xóa vẫn cleanup qua cancelRequest. Request cũ không được xóa controller mới.
- ChatPage hiện nút Dừng trong khi waiting/streaming, kể cả khi xem hội thoại khác;
  thông báo chỉ rõ đang trả lời ở hội thoại khác. MessageItem có Đang viết… / Đã dừng.
- Giữ quy tắc cuộn của MessageList: nội dung tăng chỉ theo cuối nếu người dùng gần cuối;
  nếu đang đọc phía trên thì giữ vị trí, dùng nút Xuống cuối.
- Files sửa: mockChat.ts, chatStore.ts, types/chat.ts, ChatPage.tsx,
  MessageItem.tsx, MessageList.css, tests/chat.test.ts, tài liệu này. Không thêm dependency.

### Kiểm tra bước 5

- Build PASS; lint PASS không warning; Vitest 16/16 PASS.
- Giữ 10 test cũ với thời gian bao gồm cả stream; thêm 6 test: tăng nội dung trong cùng ID,
  dừng trước phần đầu/gửi tiếp, flush giữa frame và chặn delta muộn, lỗi giữa stream/retry,
  gom nhiều delta một frame/flush cuối, rời trang/xóa khi còn frame chờ.
- Tests frame dùng fake RAF 16ms; cleanup route kiểm tra action hook sử dụng, chưa DOM unmount.
- UI tool vẫn trả apps=[]/browsers=[]: chưa kiểm chứng trực tiếp Markdown đang dở,
  tự cuộn/đọc phía trên, Dừng/focus và responsive. Không coi unit tests là xác nhận UI.
- Test local: câu thường hiện dần; [slow] rồi Dừng trước phần đầu; câu thường rồi Dừng
  giữa chừng; [stream-error] giữ phần trả lời và Thử lại; [fast] không mất ký tự cuối;
  chuyển hội thoại khi đang stream, xóa hội thoại đó, rời /chat và đăng xuất khi đang stream.
- Điểm dừng: hoàn thành code 5 bước bằng mock. Chưa API thật; kiểm tra UI còn tồn đọng.

### Bổ sung sau bước 4: khoảng cách UI và xóa hội thoại

- Theo phản hồi người dùng về ô chat bị dính, đổi danh sách hội thoại thành flex column
  gap 10px, mỗi hàng có border, min-height và flex-shrink=0. Nút chọn co giãn có
  min-width=0/ellipsis; nút xóa riêng luôn hiển thị, không lồng button.
- Vùng message không bị flex co chiều cao; message không co, empty state có padding.
  Đây là điều chỉnh dựa trên CSS; chưa quan sát được lỗi người dùng trong browser.
- Thêm icon thùng rác có nhãn Xóa hội thoại trên desktop/mobile. Xóa ngay dữ liệu RAM.
- deleteConversation(id): xóa metadata/messages/draft, ID lạ bỏ qua. Xóa active chọn
  hội thoại đầu còn lại; xóa cuối cùng khởi tạo một hội thoại trống.
- Chỉ hủy pending thuộc hội thoại bị xóa; reply muộn không khôi phục dữ liệu đã xóa.
- Sửa ConversationList.tsx/CSS, MessageList.css, chatStore.ts, tests/chat.test.ts.
- Build/lint PASS; 10/10 Vitest PASS, gồm 3 test mới cho xóa dữ liệu/fallback,
  abort/late result và giữ request thuộc hội thoại khác.
- UI tool vẫn không có browser. Cần kiểm chứng khoảng cách, tiêu đề dài, icon xóa
  trên desktop/mobile và đối chiếu đúng vị trí lỗi “dính lên nhau” người dùng báo.

### Bước 4 — đã triển khai và bàn giao

- Service `frontend/src/services/mockChat.ts`: requestMockReply({ content, attempt,
  signal }) trả Promise<string>. Mặc định chờ 1200ms; nội dung có [slow] chờ 5000ms;
  [error] lỗi lần đầu, retry thành công. Có thể kết hợp hai marker. Không có API thật.
  Abort xóa timer, kết thúc bình thường gỡ listener.
- Store quản lý pendingRequest duy nhất với request ID, conversationId, messageId.
  sendMessage trả boolean ngay khi chấp nhận, thêm user done và assistant waiting,
  xóa draft và khóa send/retry toàn ứng dụng ở cấp store. Promise xử lý nội bộ.
- Phản hồi chỉ được cập nhật khi ID request còn khớp; kết quả về conversation ban đầu
  dù active đã đổi. finally của request cũ không xóa controller của request mới.
- retryMessage(conversationId, messageId): boolean chỉ retry assistant error ở cuối
  hội thoại, dùng lại user/message ID, tăng attempt; không thêm user hoặc đổi thứ tự hội thoại.
- cancelRequest(): void vô hiệu hóa request trước abort, giữ user, đánh dấu reply error
  với thông báo đã hủy để cho retry khi quay lại. resetChat(): void hủy và tạo lại state trống.
- Hook `frontend/src/hooks/useChatSession.ts` chỉ quản lý cleanup khi ChatPage unmount;
  chuyển hội thoại không unmount trang nên không hủy request. Điều phối async dùng chung
  đặt trong chatStore để giữ khóa toàn ứng dụng; controller ở module, không lưu trong state UI.
- authStore.logout gọi resetChat trước xóa token/auth; không giữ lịch sử/draft sau logout.
- Message thêm status waiting, error?: string, attempt?: number. MessageList thêm busy
  và onRetry; MessageItem hiện Đang trả lời… / lỗi / Thử lại. Retry chỉ hiện ở lượt cuối,
  disabled khi ứng dụng bận. ChatInput disabled khi có pending; trang hiện lời nhắc chờ.
- File sửa: chatStore.ts, authStore.ts, types/chat.ts, ChatPage.tsx,
  MessageList.tsx, MessageItem.tsx, MessageList.css, package.json/package-lock.json;
  thêm service, hook, `frontend/tests/chat.test.ts` và cập nhật tài liệu này.

### Kiểm tra bước 4

- `npm.cmd run build`: PASS. `npm.cmd run lint`: PASS không warning.
- Thêm Vitest dev dependency và script `npm.cmd test`; 7/7 tests PASS.
- Tests dùng fake timers: input rỗng/gửi trùng; placeholder/thành công;
  đổi hội thoại trong khi chờ và giữ draft khác; retry đúng ID không nhân đôi;
  chặn retry lượt lỗi cũ/ID không hợp lệ; cancel xóa timer/retry;
  late success không sửa lượt cũ hoặc mở khóa request mới; logout abort/reset và late rejection.
- Test cancel gọi action mà cleanup hook sử dụng; chưa mô phỏng React unmount bằng DOM test.
- UI tool vẫn trả apps=[]/browsers=[]; chưa kiểm chứng giao diện, focus, cuộn hoặc thao tác thật.
- Test local: gửi bình thường thấy chờ ~1.2s; gửi [error] thấy lỗi rồi retry thành công;
  [slow] chờ 5s để tạo/chọn hội thoại khác, xác nhận input khóa và phản hồi ở hội thoại gốc;
  chuyển /documents khi chờ rồi quay lại thấy thông báo hủy; retry; logout/login lịch sử trống.
- Điểm dừng: đã có waiting/done/error và retry, chưa streaming hoặc nút Dừng.

### Bước 2: Message list

- MessageList/MessageItem, empty state; user dùng text giữ xuống dòng,
  assistant dùng react-markdown, không HTML thô.
- Store bắt đầu với một hội thoại. Gửi thêm user, mock trả assistant đầy đủ ngay.
- Xóa vùng kiểm tra tạm bước 1. Gửi tự cuộn xuống; nội dung mới chỉ tự cuộn nếu
  gần cuối, còn lại có nút Xuống cuối.
- Kiểm tra nhiều lượt, thứ tự/ID, nội dung dài/Markdown/code và cuộn.

### Bước 3: Conversation list

- Danh sách trong sidebar khi ở chat; mobile mở bằng nút Hội thoại.
- Tạo/chọn/đánh dấu active; giữ route /chat. Draft và messages riêng theo ID.
- Tiêu đề từ tin đầu tối đa 40 ký tự, trống là Cuộc trò chuyện mới.
- Sắp theo lần gửi mới nhất; chọn không đổi thứ tự; không tạo thêm khi active trống.
- Kiểm tra hai hội thoại/draft không lẫn, tạo mới, mobile và reload mất dữ liệu.

### Bước 4: Loading và lỗi

- Tách mock service có delay và lỗi tái hiện được. Hiện user ngay và placeholder chờ.
- Chống gửi trùng ở lớp điều phối, không chỉ disabled nút.
- Lỗi giữ user; chỉ retry lượt lỗi cuối, thay lượt trả lời và không nhân đôi user.
- Hủy khi rời chat/đăng xuất; đăng xuất xóa store.
- Thêm Vitest kiểm tra request trùng, kết quả đúng hội thoại, retry/hủy, sự kiện muộn.

### Bước 5: Streaming

- Mock phát delta/done/error nội bộ, chưa định nghĩa giao thức backend.
- Trạng thái waiting → streaming → done/error/stopped; cập nhật cùng message,
  gom tối đa một lần/frame và flush khi kết thúc.
- Phần đầu thay loading; nút Dừng hủy, giữ nội dung, đánh dấu đã dừng, cho gửi tiếp.
- Lỗi giữ phần đã nhận; retry thay thế phần trả lời lỗi.
- Cleanup timer/request/frame callback; giữ quy tắc cuộn bước 2.
- Kiểm tra chậm phần đầu, stream nhanh, lỗi/dừng trước và sau phần đầu,
  chuyển hội thoại, rời trang/quay lại và sự kiện muộn. Mở rộng test bước 4.

## Mẫu bàn giao cuối mỗi bước

- Đã làm và hành vi hiện tại.
- Interface/state mới hoặc thay đổi.
- File đã sửa và kết quả từng kiểm tra.
- Lỗi còn tồn tại và kiểm tra chưa chạy (nêu lý do).
- Bước kế tiếp và phạm vi phải dừng.

## Sửa nút “Cuộc trò chuyện mới”

- Nút trước đây gọi `createConversation()`, action này tái sử dụng hội thoại đang trống.
  Khi cần một khung mới, active ID có thể không đổi nên MessageList/Input không reset.
- `ConversationList` nay gọi `startNewConversation()`: luôn tạo ID mới, đặt active ID,
  khởi tạo messages/draft rỗng và đưa hội thoại mới lên đầu. Hội thoại cũ giữ lịch sử;
  response đang stream vẫn gắn với conversation ID cũ.
- `createConversation()` vẫn giữ semantics tái sử dụng hội thoại trống cho code nội bộ;
  nút người dùng không gọi action đó nữa.
- Regression test xác nhận ID mới, messages/draft rỗng, hội thoại cũ còn đủ tin và
  hội thoại mới active. Build/lint PASS; Vitest hiện 17/17 PASS.

## Sửa focus và thao tác ở hội thoại mới khi hội thoại cũ đang chờ

- Trước đây `ChatPage` truyền `disabled={pending !== null}` nên request của một hội
  thoại khóa luôn input ở mọi hội thoại. Khung mới vì vậy không gõ được.
- `ChatInput` thêm `sendDisabled`: khi request thuộc hội thoại khác, textarea của
  khung hiện tại vẫn hoạt động và tự focus sau khi remount; nút/Enter gửi vẫn bị khóa
  ở tầng UI cho đến khi request toàn ứng dụng kết thúc. Khi request thuộc active ID,
  cả input và gửi đều khóa.
- Không thay đổi invariant store: `sendMessage` vẫn chặn mọi request thứ hai. Draft
  ở khung mới được giữ theo conversation ID và có thể tiếp tục sau khi request cũ xong.
- Build/lint PASS; Vitest 17/17 PASS.
