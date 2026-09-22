from typing import List, Dict, Optional
from datetime import datetime

class Product:
    """مدیریت اطلاعات هر لباس"""
    def __init__(self, product_id: int, name: str, size: str, color: str, price: float, stock: int):
        self.product_id = product_id
        self.name = name
        self.size = size
        self.color = color
        self.price = price
        self.stock = stock

    def update_stock(self, quantity: int) -> bool:
        """به‌روزرسانی موجودی انبار"""
        if self.stock + quantity < 0:
            return False
        self.stock += quantity
        return True

    def __str__(self):
        return f"{self.name} ({self.color} - {self.size}) | قیمت: {self.price:,} تومان | موجودی: {self.stock}"


class CartItem:
    """آیتم‌های موجود در سبد خرید"""
    def __init__(self, product: Product, quantity: int):
        self.product = product
        self.quantity = quantity

    @property
    def total_price(self) -> float:
        return self.product.price * self.quantity


class ShoppingCart:
    """مدیریت سبد خرید کاربر"""
    def __init__(self):
        self.items: Dict[int, CartItem] = {}

    def add_item(self, product: Product, quantity: int = 1) -> str:
        if quantity <= 0:
            return "تعداد درخواستی باید بیشتر از صفر باشد."
        
        if product.stock < quantity:
            return f"موجودی کافی نیست! موجودی فعلی: {product.stock}"

        if product.product_id in self.items:
            if product.stock < (self.items[product.product_id].quantity + quantity):
                return "مجموع تعداد درخواستی از موجودی انبار بیشتر است."
            self.items[product.product_id].quantity += quantity
        else:
            self.items[product.product_id] = CartItem(product, quantity)
        
        return f"{product.name} به سبد خرید اضافه شد."

    def remove_item(self, product_id: int) -> str:
        if product_id in self.items:
            removed_item = self.items.pop(product_id)
            return f"{removed_item.product.name} از سبد خرید حذف شد."
        return "آیتم مورد نظر در سبد خرید یافت نشد."

    @property
    def calculate_total(self) -> float:
        return sum(item.total_price for item in self.items.values())

    def clear_cart(self):
        self.items.clear()


class Order:
    """ثبت و صدور فاکتور نهایی"""
    def __init__(self, order_id: int, cart: ShoppingCart, discount_code: Optional[str] = None):
        self.order_id = order_id
        self.items = list(cart.items.values())
        self.raw_total = cart.calculate_total
        self.discount_amount = 0.0
        self.date = datetime.now()
        
        if discount_code == "WELCOME10":  # نمونه کد تخفیف ۱۰ درصدی
            self.discount_amount = self.raw_total * 0.10

    @property
    def final_total(self) -> float:
        return self.raw_total - self.discount_amount

    def checkout(self) -> bool:
        """کم کردن قطعی از انبار پس از پرداخت موفق"""
        # در دنیای واقعی اینجا بررسی می‌شود که آیا موجودی در این لحظه هنوز موجود است یا خیر
        for item in self.items:
            if item.product.stock < item.quantity:
                return False
        
        for item in self.items:
            item.product.update_stock(-item.quantity)
        return True

    def show_invoice(self):
        print(f"\n--- فاکتور سفارش شماره {self.order_id} ---")
        print(f"تاریخ: {self.date.strftime('%Y-%m-%d %H:%M')}")
        for item in self.items:
            print(f"- {item.product.name} ({item.product.size}) x{item.quantity}: {item.total_price:,} تومان")
        print(f"جمع کل بدون تخفیف: {self.raw_total:,} تومان")
        if self.discount_amount > 0:
            print(f"تخفیف: {self.discount_amount:,} تومان")
        print(f"مبلغ قابل پرداخت: {self.final_total:,} تومان")
        print("-" * 30)


# ==========================================
# تست عملی سیستم (شبیه‌سازی خرید)
# ==========================================

# ۱. تعریف محصولات انبار لباس
shirt = Product(product_id=101, name="پیراهن نخی مردانه", size="L", color="آبی", price=450000, stock=5)
jeans = Product(product_id=102, name="شلوار جین اسکینی", size="32", color="ذغالی", price=780000, stock=2)

print("--- موجودی اولیه انبار ---")
print(shirt)
print(jeans)

# ۲. ایجاد سبد خرید برای مشتری
my_cart = ShoppingCart()
print("\n" + my_cart.add_item(shirt, quantity=2))
print(my_cart.add_item(jeans, quantity=3))  # خطا می‌دهد چون موجودی شلوار ۲ عدد است
print(my_cart.add_item(jeans, quantity=1))

# ۳. ثبت سفارش و اعمال کد تخفیف
final_order = Order(order_id=5001, cart=my_cart, discount_code="WELCOME10")

# ۴. پرداخت و نهایی کردن خرید
if final_order.checkout():
    final_order.show_invoice()
    my_cart.clear_cart()
else:
    print("خطا در نهایی‌سازی سفارش. موجودی انبار تغییر کرد.")

print("\n--- موجودی انبار پس از خرید ---")
print(shirt)
print(jeans)
