# Phân tích vai trò UML và danh mục sơ đồ — RikkeiMart

## Bối cảnh

Dự án phát triển dịch vụ đi chợ mua hộ thực phẩm sạch **RikkeiMart** (thuộc RikkeiExpress) đang bị chậm tiến độ nghiêm trọng do Lập trình viên hiểu nhầm ý của BA về luồng xử lý khi tài xế đến cửa hàng mà thực phẩm bị hết hàng.

**Ràng buộc kỹ thuật:** Không yêu cầu nông dân/chủ cửa hàng nhỏ phải cập nhật tồn kho real-time trên phần mềm phức tạp.

**Quy tắc nghiệp vụ:** Khi hết hàng tại cửa hàng, ứng dụng tài xế phải cho phép chọn "Đề xuất sản phẩm thay thế tương đương" (ví dụ: đổi từ Táo đỏ sang Táo xanh cùng giá) và gửi thông báo xác nhận đến App khách hàng.

**Bẫy edge case — Unreachable Customer Trap:** Khi tài xế đề xuất đổi món, khách hàng lại tắt máy không nghe điện thoại hoặc không bấm phản hồi trong 3 phút. Hệ thống phải tự động ngắt mạch **Timeout 3 phút** (Auto-substitute hoặc Auto-cancel đơn an toàn) để giải phóng tài xế.

---

## Phần 1: Vai trò UML & Bảng định hướng sơ đồ

### 1. Vai trò của UML — 2 lý do giúp Dev/BA/Tester không hiểu nhầm

**Lý do 1 — UML là "ngôn ngữ hình ảnh" trung lập, không phụ thuộc cách diễn đạt của từng người.**
Khi BA mô tả bằng lời "nếu hết hàng thì tài xế đề xuất đổi món, khách không trả lời thì hệ thống tự xử lý", mỗi người đọc có thể hình dung một luồng khác nhau (Dev có thể hiểu là chờ vô hạn, Tester có thể không biết test case timeout). Một **Activity Diagram** thể hiện rõ ràng các nhánh rẽ (decision node), điều kiện hết hàng, và đường timeout bằng ký hiệu chuẩn quốc tế — không còn chỗ cho suy diễn khác nhau.

**Lý do 2 — UML buộc phải làm rõ mọi nhánh rẽ và trạng thái biên (edge case) trước khi code, thay vì phát hiện lúc chạy thử.**
Khi vẽ Activity/Sequence Diagram, người thiết kế bắt buộc phải trả lời câu hỏi "vậy nếu khách hàng không phản hồi thì sao?" ngay trên sơ đồ — nếu không có nhánh đó, sơ đồ sẽ "hở mạch" và dễ bị Tester/Dev phát hiện ngay khi review. Đây chính là cách UML "ép" đội ngũ phát hiện case Timeout 3 phút *trước khi* code sai như đã xảy ra ở RikkeiMart.

### 2. Bảng định hướng danh mục sơ đồ UML cần vẽ

| Sơ đồ | Nhóm | Mục đích cụ thể cho luồng xử lý hết hàng RikkeiMart |
|---|---|---|
| **Use Case Diagram** | Hành vi (Behavioral) | Xác định các actor (Khách hàng, Tài xế, Bưu cục, Hệ thống) và các use case chính: "Xác nhận đơn hàng", "Đề xuất sản phẩm thay thế", "Phản hồi đổi món", "Tự động hủy/thay thế khi timeout" — giúp BA và Dev thống nhất **phạm vi chức năng** cần xây trước khi đi vào chi tiết luồng. |
| **Activity Diagram** | Hành vi (Behavioral) | Mô tả chi tiết luồng xử lý từng bước khi tài xế phát hiện hết hàng: nhánh rẽ "còn hàng thay thế / hết hoàn toàn", nhánh chờ phản hồi khách hàng, và đặc biệt là **nhánh Timeout 3 phút** (Auto-substitute hoặc Auto-cancel) — đây là sơ đồ quan trọng nhất để Dev không code sai logic như sự cố đã xảy ra. |
| **Class Diagram** | Cấu trúc (Structural) | Mô hình hóa các đối tượng nghiệp vụ: `Order`, `Item`, `SubstituteProposal`, `Customer`, `Driver` và mối quan hệ giữa chúng (thuộc tính `status`, `timeout_timestamp`, `substitute_item`...) — giúp Dev thiết kế đúng cấu trúc dữ liệu để lưu trạng thái đơn hàng và đếm ngược timeout. |

---

## Phần 2: Mã nguồn mô phỏng (`rikkeimart_order.py`)

File `rikkeimart_order.py` triển khai hàm `process_rikkeimart_order(item_status, customer_response, has_safe_substitute)` mô phỏng luồng xử lý đơn hàng RikkeiMart.

### Điểm mấu chốt của thiết kế

- Hàm **không bao giờ ném exception ra ngoài** — mọi input lạ (`item_status`/`customer_response` sai) đều trả về `INVALID_INPUT` kèm thông báo rõ ràng thay vì crash.
- Bẫy **Timeout 3 phút** được xử lý bằng tham số `has_safe_substitute`:
  - Nếu có sản phẩm thay thế tương đương (cùng giá, cùng nhóm) → `AUTO_SUBSTITUTED_TIMEOUT`.
  - Nếu không có → `AUTO_CANCELLED_TIMEOUT`.
  - Cả hai nhánh đều trả về `driver_released=True` để **giải phóng tài xế ngay**, không để tài xế chờ vô thời hạn — đúng yêu cầu nghiệp vụ chống "đóng băng" đơn hàng.
- Kết quả trả về là `OrderOutcome` (dataclass) thay vì string tùy tiện, giúp Dev/Tester dễ viết unit test và giúp BA đối chiếu trực tiếp với các nhánh trên Activity Diagram.

### Các trạng thái kết quả (`OrderResult`)

| Trạng thái | Ý nghĩa |
|---|---|
| `FULFILLED_AS_IS` | Còn hàng, giao bình thường |
| `SUBSTITUTED_CONFIRMED` | Khách đồng ý đổi món thay thế |
| `CANCELLED_BY_CUSTOMER` | Khách từ chối đổi món → hủy mục hàng |
| `AUTO_SUBSTITUTED_TIMEOUT` | Hết 3 phút, không phản hồi → tự động đổi món tương đương |
| `AUTO_CANCELLED_TIMEOUT` | Hết 3 phút, không phản hồi, không có hàng thay thế an toàn → tự động hủy |
| `INVALID_INPUT` | Dữ liệu đầu vào không hợp lệ (không crash) |



Chương trình sẽ tự chạy 7 kịch bản mẫu (bao gồm cả bẫy Timeout 3 phút và dữ liệu đầu vào không hợp lệ) và in kết quả ra màn hình, minh chứng luồng xử lý chạy mượt mà, không crash trong mọi trường hợp.
