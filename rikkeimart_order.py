"""
RikkeiMart - Mo phong luong xu ly don hang khi het hang tai cua hang.

Nghiep vu:
- item_status: "available"  -> con hang, xu ly binh thuong
                "out_of_stock" -> het hang, tai xe de xuat san pham thay the

- customer_response (chi co y nghia khi item_status = "out_of_stock"):
    "accept"   -> khach hang dong y doi mon thay the
    "reject"   -> khach hang tu choi doi mon -> huy don (item nay)
    "timeout"  -> khach hang khong phan hoi trong 3 phut
                  -> He thong TU DONG xu ly an toan (khong cho Dev/Tester
                     phai doan) de giai phong tai xe, khong bao gio crash.

Bay du lieu can bat:
- item_status hoac customer_response khong hop le -> khong crash,
  tra ve ket qua loi ro rang de log/giam sat.
"""

from dataclasses import dataclass
from enum import Enum


class OrderResult(str, Enum):
    FULFILLED_AS_IS = "FULFILLED_AS_IS"                # Con hang, giao binh thuong
    SUBSTITUTED_CONFIRMED = "SUBSTITUTED_CONFIRMED"     # Khach dong y doi mon
    CANCELLED_BY_CUSTOMER = "CANCELLED_BY_CUSTOMER"     # Khach tu choi doi mon
    AUTO_SUBSTITUTED_TIMEOUT = "AUTO_SUBSTITUTED_TIMEOUT"  # Het 3 phut -> tu dong doi mon tuong duong
    AUTO_CANCELLED_TIMEOUT = "AUTO_CANCELLED_TIMEOUT"   # Het 3 phut -> khong co hang thay the an toan -> tu huy
    INVALID_INPUT = "INVALID_INPUT"                     # Du lieu dau vao khong hop le


@dataclass
class OrderOutcome:
    result: OrderResult
    message: str
    driver_released: bool  # Tai xe co duoc giai phong de chuyen don khac khong


# Chinh sach mac dinh khi Timeout 3 phut nhung khong the hoi khach:
# Neu san pham thay the la loai "an toan" (cung gia, cung nhom hang, VD Tao do -> Tao xanh)
# thi he thong TU DONG chap nhan thay the (Auto-substitute) de khong lam gian doan don hang.
# Neu KHONG co san pham thay the an toan/tuong duong ro rang, he thong TU DONG HUY (Auto-cancel)
# de giai phong tai xe thay vi de tai xe cho vo thoi han.
AUTO_SAFE_SUBSTITUTE_AVAILABLE_DEFAULT = True


def process_rikkeimart_order(
    item_status: str,
    customer_response: str = None,
    has_safe_substitute: bool = AUTO_SAFE_SUBSTITUTE_AVAILABLE_DEFAULT,
) -> OrderOutcome:
    """
    Mo phong xu ly 1 dong hang (item) trong don RikkeiMart.

    :param item_status: "available" | "out_of_stock"
    :param customer_response: None | "accept" | "reject" | "timeout"
        (chi bat buoc khi item_status == "out_of_stock")
    :param has_safe_substitute: co san pham thay the tuong duong (cung gia,
        cung nhom) de he thong tu dong ap dung khi timeout hay khong.
    :return: OrderOutcome - khong bao gio nem exception ra ngoai.
    """
    try:
        item_status_norm = (item_status or "").strip().lower()

        # ---- Truong hop 1: Con hang -> xu ly binh thuong ----
        if item_status_norm == "available":
            return OrderOutcome(
                result=OrderResult.FULFILLED_AS_IS,
                message="San pham con hang, tai xe tiep tuc giao don binh thuong.",
                driver_released=False,
            )

        # ---- Truong hop 2: Het hang -> can customer_response ----
        if item_status_norm == "out_of_stock":
            response_norm = (customer_response or "").strip().lower()

            if response_norm == "accept":
                return OrderOutcome(
                    result=OrderResult.SUBSTITUTED_CONFIRMED,
                    message=(
                        "Khach hang da xac nhan dong y san pham thay the. "
                        "Gui thong bao xac nhan den App khach hang va tiep tuc giao."
                    ),
                    driver_released=False,
                )

            if response_norm == "reject":
                return OrderOutcome(
                    result=OrderResult.CANCELLED_BY_CUSTOMER,
                    message="Khach hang tu choi doi mon. Huy muc hang nay khoi don.",
                    driver_released=True,
                )

            if response_norm == "timeout":
                # BAY: Unreachable Customer Trap - khach tat may / khong bam
                # phan hoi trong 3 phut. He thong PHAI tu dong ngat mach,
                # tuyet doi khong de tai xe cho vo thoi han.
                if has_safe_substitute:
                    return OrderOutcome(
                        result=OrderResult.AUTO_SUBSTITUTED_TIMEOUT,
                        message=(
                            "Qua 3 phut khong nhan duoc phan hoi. He thong tu dong "
                            "ap dung san pham thay the tuong duong (cung gia) va "
                            "gui thong bao cho khach hang. Giai phong tai xe."
                        ),
                        driver_released=True,
                    )
                else:
                    return OrderOutcome(
                        result=OrderResult.AUTO_CANCELLED_TIMEOUT,
                        message=(
                            "Qua 3 phut khong nhan duoc phan hoi va khong co san pham "
                            "thay the an toan. He thong tu dong huy muc hang nay de "
                            "giai phong tai xe."
                        ),
                        driver_released=True,
                    )

            # customer_response khong nam trong tap gia tri hop le
            return OrderOutcome(
                result=OrderResult.INVALID_INPUT,
                message=(
                    f"customer_response '{customer_response}' khong hop le khi het hang. "
                    "Gia tri hop le: 'accept', 'reject', 'timeout'."
                ),
                driver_released=False,
            )

        # item_status khong nam trong tap gia tri hop le
        return OrderOutcome(
            result=OrderResult.INVALID_INPUT,
            message=(
                f"item_status '{item_status}' khong hop le. "
                "Gia tri hop le: 'available', 'out_of_stock'."
            ),
            driver_released=False,
        )

    except Exception as e:
        # Luoi an toan cuoi cung: du co loi khong luong truoc,
        # ham van khong bao gio crash he thong.
        return OrderOutcome(
            result=OrderResult.INVALID_INPUT,
            message=f"Loi khong xac dinh khi xu ly don hang: {e}",
            driver_released=False,
        )


if __name__ == "__main__":
    test_cases = [
        # (item_status, customer_response, has_safe_substitute, mo_ta)
        ("available", None, True, "Con hang -> giao binh thuong"),
        ("out_of_stock", "accept", True, "Het hang -> khach dong y doi mon"),
        ("out_of_stock", "reject", True, "Het hang -> khach tu choi doi mon"),
        ("out_of_stock", "timeout", True, "BAY: Het hang -> khach mat lien lac 3' -> co hang thay the an toan"),
        ("out_of_stock", "timeout", False, "BAY: Het hang -> khach mat lien lac 3' -> KHONG co hang thay the"),
        ("out_of_stock", "maybe_later", True, "Du lieu la -> phan hoi khong hop le"),
        ("shipped", None, True, "Du lieu la -> trang thai san pham khong hop le"),
    ]

    print("=" * 90)
    print("MO PHONG XU LY DON HANG RIKKEIMART")
    print("=" * 90)
    for item_status, response, safe_sub, desc in test_cases:
        outcome = process_rikkeimart_order(item_status, response, safe_sub)
        print(f"\n>> Kich ban: {desc}")
        print(f"   Input           : item_status='{item_status}', customer_response='{response}', has_safe_substitute={safe_sub}")
        print(f"   Ket qua         : {outcome.result.value}")
        print(f"   Thong bao       : {outcome.message}")
        print(f"   Giai phong TX?  : {'Co' if outcome.driver_released else 'Khong'}")
    print("\n" + "=" * 90)
    print("Chuong trinh chay xong - khong co truong hop nao gay crash.")
    print("=" * 90)
