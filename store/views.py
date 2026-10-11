from django.shortcuts import render, redirect, get_object_or_404
from .models import Book, Category, Coupon, OrderItem, BookReview, DeliveryMethod, PaymentMethod, StoreReview, Order, \
    ReviewSettings
from .forms import OrderCreateForm
from django.core.mail import send_mail
from django.conf import settings
# 1. استيراد مكتبة Decimal لمنع تعارض الحسابات
from decimal import Decimal
from .models import HomePageBanner, HomePageSection, QuickCategory
from django.db.models import Q, Sum, Count, Case, When
from django.utils import timezone
from datetime import timedelta
from django.contrib import messages
import json
from django.db.models import Q
from .models import DynamicPageBlock, Book


def get_all_related_category_ids(category, include_self=True):
    """
    تجمع جميع معرفات الأقسام المرتبطة بشكل متكرر (BFS).
    """
    visited = set()
    queue = []

    # نبدأ بإضافة القسم نفسه إذا طُلب ذلك
    if include_self:
        visited.add(category.id)
        queue.append(category.id)

    # نضيف الأقسام المرتبطة مباشرة
    direct_related = category.related_categories.filter(is_active=True).values_list('id', flat=True)
    for cid in direct_related:
        if cid not in visited:
            visited.add(cid)
            queue.append(cid)

    # نبحث بشكل متكرر في الأقسام المرتبطة بكل قسم
    while queue:
        current_id = queue.pop()
        # جلب الأقسام المرتبطة بهذا القسم
        child_ids = Category.objects.filter(
            id=current_id,
            is_active=True
        ).values_list('related_categories__id', flat=True).distinct()

        for cid in child_ids:
            if cid not in visited:
                visited.add(cid)
                queue.append(cid)

    return list(visited)
# ==========================================
# دالة مساعدة لجلب الكتب بناءً على نوع القسم (ذكية / يدوية)
# ==========================================
def get_books_for_category(category):
    books = Book.objects.filter(is_visible=True)
    if category.category_type == 'latest':
        return books.order_by('-created_at')
    elif category.category_type == 'best_selling':
        now = timezone.now()
        start_date = None
        if category.time_range == 'custom_days':
            start_date = now - timedelta(days=category.custom_days)
        elif category.time_range == 'this_week':
            start_date = now - timedelta(days=7)
        elif category.time_range == 'this_month':
            start_date = now - timedelta(days=30)

        items = OrderItem.objects.all()
        if start_date: items = items.filter(order__created_at__gte=start_date)
        best_selling_data = items.values('book').annotate(total_sold=Sum('quantity')).order_by('-total_sold')
        best_selling_ids = [item['book'] for item in best_selling_data]
        if best_selling_ids:
            preserved_order = Case(*[When(pk=pk, then=pos) for pos, pk in enumerate(best_selling_ids)])
            return Book.objects.filter(pk__in=best_selling_ids, is_visible=True).order_by(preserved_order)
        return Book.objects.none()
    else:  # قسم عادي (يدوي)
        base_query = Q(categories=category)

        # 🆕 الأولوية للـ deep إذا كان مفعلاً
        if category.include_related_deep:
            # جمع جميع الأقسام المرتبطة بجميع المستويات (بما فيها القسم نفسه)
            all_related_ids = get_all_related_category_ids(category, include_self=True)
            if all_related_ids:
                base_query = Q(categories__in=all_related_ids)
        # وإلا استخدم المنطق القديم (المستوى الأول فقط) إذا كان مفعلاً
        elif category.include_related_books:
            related_ids = category.related_categories.filter(is_active=True).values_list('id', flat=True)
            if related_ids.exists():
                base_query |= Q(categories__in=related_ids)

        return books.filter(base_query).distinct().order_by('-created_at')

# دالة البحث الشامل (تستدعى عندما يختار المستخدم "بحث شامل في المتجر")
def global_search(request):
    all_categories = Category.objects.filter(is_active=True)
    query = request.GET.get('q', '').strip()

    books = Book.objects.filter(is_visible=True)
    if query:
        books = books.filter(
            Q(title__icontains=query) |
            Q(description__icontains=query) |
            Q(categories__name__icontains=query)
        ).distinct()

    return render(request, 'store/search_results.html', {
        'all_categories': all_categories,
        'books': books,
        'query': query
    })




#اضافات جديده للتحكم بمضهر الصفحة  الرئيسية


def get_dynamic_layout(page_name, current_category=None, query=None):
    filters = Q(page_name=page_name, is_active=True)

    if page_name in ['category_detail', 'book_detail'] and current_category:
        filters &= (Q(specific_category_page=current_category) | Q(specific_category_page__isnull=True))

    blocks = DynamicPageBlock.objects.filter(filters).order_by('order')
    dynamic_layout = []

    for block in blocks:
        if block.block_type == 'quick_cats':
            categories = block.group_categories.filter(is_active=True)
            if categories.exists():
                dynamic_layout.append({
                    'type': 'quick_cats',
                    'title': block.title,
                    'icon_class': block.icon_class,  # <-- تمرير الأيقونة هنا
                    'icon_color': block.icon_color,  # <-- تمرير اللون هنا
                    'categories': categories
                })

        elif block.block_type == 'book_slider':
            if block.source_category_for_books:
                books = Book.objects.filter(categories=block.source_category_for_books, is_visible=True)
                if query:
                    books = books.filter(Q(title__icontains=query) | Q(description__icontains=query))
                else:
                    books = books[:12]

                if books.exists():
                    if block.title and block.title.strip():
                        slider_title = block.title.strip()
                    else:
                        slider_title = block.source_category_for_books.name

                    dynamic_layout.append({
                        'type': 'book_slider',
                        'title': slider_title,
                        'icon_class': block.icon_class,  # <-- تمرير الأيقونة هنا
                        'icon_color': block.icon_color,  # <-- تمرير اللون هنا
                        'category_id': block.source_category_for_books.id,
                        'category_icon': block.source_category_for_books.icon_class,
                        # 👈 [تعديل] إضافة هذا السطر لتمرير الأيقونة
                        'books': books
                    })

    return dynamic_layout


def home(request):
    # جلب كافة الأقسام النشطة ليعرضها الـ Sidebar في ملف base.html بشكل مستمر
    all_categories = Category.objects.filter(is_active=True)

    # جلب الأقسام المميزة والمحددة للصفحة الرئيسية فقط
    featured_categories = Category.objects.filter(is_active=True, show_on_homepage=True)

    # قراءة حقل البحث إذا قام المستخدم بالتصفية داخل الصفحة الحالية (home)
    query = request.GET.get('q', '').strip()

    # جلب أحدث الكتب المضافة مع إمكانية تصفيتها بالبحث الفوري
    latest_books = Book.objects.filter(is_visible=True)
    if query:
        latest_books = latest_books.filter(Q(title__icontains=query) | Q(description__icontains=query))
    else:
        latest_books = latest_books.order_by('-created_at')

    dynamic_layout = get_dynamic_layout('home')

    return render(request, 'store/home.html', {
        'all_categories': all_categories,
        'featured_categories': featured_categories,
        'latest_books': latest_books,
        'current_category': None,
        'search_query': query, # إرسال نص البحث ليحفظ في الحقل إن لزم الأمر
        'dynamic_layout': dynamic_layout,  # تم الإضافة هنا
    })


def add_to_cart(request, book_id):
    book = get_object_or_404(Book, id=book_id)
    cart = request.session.get('cart', {})
    book_id_str = str(book.id)

    # استخدام السعر الحالي الذي يراعي وجود خصم من عدمه
    price = float(book.current_price)

    if book_id_str in cart:
        cart[book_id_str]['quantity'] += 1
        # تحديث السعر في السلة لضمان دقة السعر إذا تم تغيير الخصم لاحقاً
        cart[book_id_str]['price'] = price
    else:
        cart[book_id_str] = {
            'price': price,
            'quantity': 1,
            'title': book.title
        }

    request.session['cart'] = cart
    referer = request.META.get('HTTP_REFERER', 'home')
    return redirect(referer)


# ==========================================
# 4. تفاصيل القسم (المطور)
# ==========================================
def category_detail(request, category_id):
    all_categories = Category.objects.filter(is_active=True)
    current_category = get_object_or_404(Category, id=category_id)
    assigned_categories = current_category.related_categories.filter(is_active=True)
    books = get_books_for_category(current_category)

    suggested_books = None
    if current_category.recommendation_source == 'auto':
        suggested_books = Book.objects.filter(categories=current_category, is_visible=True)[:10]
    elif current_category.recommendation_source == 'custom' and current_category.custom_recommendation_category:
        suggested_books = Book.objects.filter(categories=current_category.custom_recommendation_category,
                                              is_visible=True)[:10]

    detail_categories = []
    custom_categories = Category.objects.filter(is_active=True, show_on_detail=True).exclude(id=current_category.id)
    for cat in custom_categories:
        cat_books = get_books_for_category(cat)[:10]
        if cat_books.exists():
            detail_categories.append({'category_id': cat.id, 'category_name': cat.name,
                                      'category': cat,  # 👈 [تعديل] نمرر كائن القسم بالكامل للوصول لجميع بياناته بما فيها الأيقونة والاسم والمعرف
                                      'books': cat_books})

        # إضافة السطر أدناه فقط للتعرف على قوالب هذا القسم بترتيبها المخصص
    dynamic_layout = get_dynamic_layout('category_detail', current_category=current_category)

    return render(request, 'store/category_detail.html', {
        'all_categories': all_categories, 'current_category': current_category,
        'assigned_categories': assigned_categories,
        'books': books, 'suggested_books': suggested_books, 'detail_categories': detail_categories,

        'dynamic_layout': dynamic_layout,  # تم الإضافة هنا
    })


def cart_detail(request):
    if 'direct_buy' in request.session:
        del request.session['direct_buy']

    cart = request.session.get('cart', {})
    total_price = 0

    for book_id, item in cart.items():
        try:
            book = Book.objects.get(id=book_id)
            item['image_url'] = book.cover_image.url if book.cover_image else None
            # تحديث السعر في السلة ليعكس السعر الحالي (الخصم)
            item['price'] = float(book.current_price)
        except Book.DoesNotExist:
            item['image_url'] = None

        # حساب السعر الإجمالي بناءً على السعر المحدث
        total_price += item['price'] * item['quantity']

    return render(request, 'store/cart.html', {'cart': cart, 'total_price': total_price})



def remove_from_cart(request, book_id):
    cart = request.session.get('cart', {})
    if str(book_id) in cart:
        del cart[str(book_id)]
        request.session['cart'] = cart
    return redirect('cart_detail')


def update_cart(request, book_id, action):
    cart = request.session.get('cart', {})
    book_id_str = str(book_id)

    if book_id_str in cart:
        if action == 'plus':
            cart[book_id_str]['quantity'] += 1
        elif action == 'minus':
            if cart[book_id_str]['quantity'] > 1:
                cart[book_id_str]['quantity'] -= 1
            else:
                del cart[book_id_str]  # حذف إذا وصل للصفر

    request.session['cart'] = cart
    return redirect('cart_detail')


#منطق الطلب
# =================================================================
# دالة معالجة الطلب وإتمام الشراء المكتملة بعد تعديل زر العودة الذكي
# =================================================================
def checkout(request):
    # -----------------------------------------------------------------
    # خطوة ذكية: التقاط الواجهة السابقة الأصلية (مثل تفاصيل الكتاب أو السلة)
    # وحفظها في الـ session عند أول دخول للمستخدم لصفحة الشراء
    # -----------------------------------------------------------------
    if 'previous_page' not in request.session:
        referer = request.META.get('HTTP_REFERER', '/')
        # نتأكد أن الرابط ليس صفحة الدفع نفسها لضمان استقرار الجوال والكمبيوتر
        if 'checkout' not in referer:
            request.session['previous_page'] = referer

    # 1. التحقق أولاً هل العميل قادم عبر ميزة "اشترِ الآن" السريعة
    direct_buy_data = request.session.get('direct_buy')

    is_direct_buy = False
    direct_book = None
    direct_quantity = 1
    subtotal = Decimal('0.00')

    if direct_buy_data:
        # إذا وجدنا بيانات شراء مباشر، نقرأها فوراً
        is_direct_buy = True
        try:
            direct_book = Book.objects.get(id=direct_buy_data['book_id'])
            direct_quantity = int(direct_buy_data['quantity'])
            # حساب الإجمالي الفرعي بناءً على سعر هذا الكتاب وكميته المنفردة
            subtotal = Decimal(str(direct_book.current_price)) * Decimal(direct_quantity)
        except Book.DoesNotExist:
            # في حال حدوث خطأ أو حذف المنتج، نحذف الجلسة السريعة ونوجهه للرئيسية
            if 'direct_buy' in request.session:
                del request.session['direct_buy']
            return redirect('home')
    else:
        # إذا لم يكن شراء مباشر، نعتمد على نظام السلة التقليدي الطبيعي
        cart = request.session.get('cart', {})
        if not cart:
            return redirect('cart_detail')
        subtotal = Decimal(sum(item['price'] * item['quantity'] for item in cart.values()))

    # جلب طرق التوصيل والدفع النشطة
    delivery_methods = DeliveryMethod.objects.filter(is_active=True)
    payment_methods = PaymentMethod.objects.filter(is_active=True)

    if request.method == 'POST':
        form = OrderCreateForm(request.POST)

        if form.is_valid():
            order = form.save(commit=False)

            delivery = form.cleaned_data['delivery_method']
            shipping_cost = Decimal(delivery.cost)

            discount = Decimal('0.00')
            coupon_input = request.POST.get('coupon_code_applied')
            coupon_text_for_email = "لم يتم استخدام أي كود خصم"

            if coupon_input:
                try:
                    coupon = Coupon.objects.get(code=coupon_input, is_active=True)
                    discount = (subtotal * Decimal(coupon.discount_percentage)) / Decimal(100)
                    order.coupon = coupon
                    coupon_text_for_email = f"نعم، تم استخدام كود الخصم ({coupon.code})"
                except Coupon.DoesNotExist:
                    pass

            order.grand_total = (subtotal - discount) + shipping_cost

            # -----------------------------------------------------------------
            # التعديل الجديد: التقاط مصدر الإحالة ومفتاح الجلسة وحفظهما مع الطلب
            # -----------------------------------------------------------------
            current_referrer = request.session.get('initial_referrer', 'Direct / Unknown')
            order.referrer = current_referrer

            if not request.session.session_key:
                request.session.save()
            order.session_key = request.session.session_key
            # -----------------------------------------------------------------

            order.save()

            books_details_text = ""

            # 2. بناء تفاصيل المنتجات وحفظها بناءً على نوع العملية
            if is_direct_buy:
                # إذا كانت العملية شراء مباشر، نقوم بإنشاء عنصر الطلب للكتاب المنفرد فقط
                OrderItem.objects.create(order=order, book=direct_book, quantity=direct_quantity)
                books_details_text += f"- {direct_book.title} (الكمية: {direct_quantity}) [شراء مباشر سريع]\n"

                # تنظيف وتنظيف جلسة الشراء المباشر فور الانتهاء بنجاح لمنع تكرارها
                del request.session['direct_buy']
            else:
                # إذا كانت عملية شحن عادية للسلة، نلف على عناصر السلة المعتادة
                cart = request.session.get('cart', {})
                for book_id, item in cart.items():
                    book = Book.objects.get(id=book_id)
                    OrderItem.objects.create(order=order, book=book, quantity=item['quantity'])
                    books_details_text += f"- {book.title} (الكمية: {item['quantity']})\n"

                # تفريغ السلة الاعتيادية بعد الحفظ بنجاح
                request.session['cart'] = {}

            # ----------------- نص الإشعار البريدي المطور -----------------
            subject = f"طلب جديد في المتجر برقم {order.order_number}"
            message = f"""
            تفاصيل الطلب الجديد:
            -----------------------
            رقم الطلب: {order.order_number}
            نوع الطلب: {"شراء مباشر سريع ⚡" if is_direct_buy else "طلب من السلة العامة 🛒"}
            اسم العميل: {order.customer_name}
            رقم الهاتف: {order.customer_phone}
            البريد الإلكتروني: {order.customer_email}
            المدينة: {order.city}
            العنوان بالتفصيل: {order.address_details}
            مصدر الإحالة (المنصة): {order.referrer}

            الكتب المطلوبة:
            {books_details_text}

            طريقة التوصيل: {order.delivery_method.name}
            طريقة الدفع: {order.payment_method.name}

            استخدام كود خصم؟: {coupon_text_for_email}
            -----------------------
            الإجمالي الكلي للطلب: {order.grand_total} YER
            """

            try:
                send_mail(
                    subject,
                    message,
                    settings.DEFAULT_FROM_EMAIL,
                    [settings.ADMIN_EMAIL],
                    fail_silently=True,
                )
            except Exception:
                pass

            # -----------------------------------------------------------------
            # جلب رابط الواجهة السابقة الذي حفظناه وتمريره لصفحة النجاح
            # ثم مسحه من الجلسة لكي يصبح نظيفاً للعملية القادمة
            # -----------------------------------------------------------------
            previous_page = request.session.get('previous_page', '/')
            if 'previous_page' in request.session:
                del request.session['previous_page']

            return render(request, 'store/order_success.html', {
                'order': order,
                'previous_page': previous_page,  # إرسال الرابط المباشر إلى قالب HTML ليعود منه المستخدم
                'buyer_token': str(order.buyer_token)  # تحويل الـ UUID لنص وإرساله للمتصفح
            })
    else:
        form = OrderCreateForm()

    # 3. تمرير المتغيرات الإضافية ليتعرف عليها قالب الـ HTML ويظهر كروت المعاينة للمنتج
    return render(request, 'store/checkout.html', {
        'form': form,
        'delivery_methods': delivery_methods,
        'payment_methods': payment_methods,
        'subtotal': subtotal,
        'is_direct_buy': is_direct_buy,
        'direct_book': direct_book,
        'direct_quantity': direct_quantity
    })


# دالة برمجية صغيرة مخصصة للتحقق من كود الخصم عبر الجافا سكريبت بدون تحميل الصفحة
from django.http import JsonResponse


def validate_coupon(request):
    code = request.GET.get('code', '').strip()
    try:
        coupon = Coupon.objects.get(code=code, is_active=True)
        return JsonResponse({'valid': True, 'percentage': coupon.discount_percentage})
    except Coupon.DoesNotExist:
        return JsonResponse({'valid': False})

#عرض تفاصيل الكتاب
def book_detail(request, book_id):
    all_categories = Category.objects.filter(is_active=True)
    book = get_object_or_404(Book, id=book_id)
    book_reviews = book.reviews.filter(is_approved=True)

    # التعديل هنا: بما أن الكتاب له عدة أقسام، نأخذ القسم الأول المرتبط به
    # إذا لم يكن له أقسام، نضع القيمة None لتجنب الخطأ
    current_cat_setting = book.categories.first()

    suggested_books = None
    detail_categories = []
    assigned_categories = []

    if current_cat_setting:
        # جلب الأقسام المرتبطة بالقسم الحالي
        assigned_categories = current_cat_setting.related_categories.filter(is_active=True)

        # منطق الترشيحات (منتجات قد تعجبك)
        if current_cat_setting.recommendation_source == 'auto':
            # جلب كتب من نفس القسم الأول للكتاب
            suggested_books = Book.objects.filter(categories=current_cat_setting, is_visible=True).exclude(id=book.id)[
                              :10]
        elif current_cat_setting.recommendation_source == 'custom' and current_cat_setting.custom_recommendation_category:
            # جلب كتب من القسم المخصص المختار في لوحة التحكم
            suggested_books = Book.objects.filter(categories=current_cat_setting.custom_recommendation_category,
                                                  is_visible=True).exclude(id=book.id)[:10]

        # جلب الأقسام التي تظهر في صفحة التفاصيل (التمرير اللانهائي للأقسام)
        custom_categories = Category.objects.filter(is_active=True, show_on_detail=True).exclude(
            id=current_cat_setting.id)
        for cat in custom_categories:
            cat_books = get_books_for_category(cat)[:10]
            if cat_books.exists():
                detail_categories.append({
                    'category_id': cat.id,
                    'category_name': cat.name,
                    'category': cat,  # 👈 [تعديل] نمرر كائن القسم بالكامل هنا أيضاً
                    'books': cat_books
                })

        # إضافة السطر أدناه (نمرر قسم الكتاب الحالي ليعرض قوالب مخصصة بناء على قسمه إن وجدت)
    dynamic_layout = get_dynamic_layout('book_detail', current_category=book.categories.first())
    return render(request, 'store/book_detail.html', {
        'all_categories': all_categories,
        'book': book,
        'current_category': current_cat_setting,
        'assigned_categories': assigned_categories,
        'suggested_books': suggested_books,
        'detail_categories': detail_categories,
        'book_reviews': book_reviews,  # التقييمات الممررة لصفحة العرض
        'category_icon': cat.icon_class,  # 👈 [تعديل] إضافة هذا السطر لتمرير الأيقونة
        'dynamic_layout': dynamic_layout,  # تم الإضافة هنا
    })


#داله زر الدفع اشتري الان
def buy_now(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        quantity = int(request.POST.get('quantity', 1))

        # تخزين بيانات الشراء المباشر في الـ Session لتقرأها صفحة الدفع (Checkout)
        request.session['direct_buy'] = {
            'book_id': book.id,
            'quantity': quantity,
        }

        # التوجيه فوراً إلى صفحة الدفع وإتمام الطلب (استبدل 'checkout' باسم رابط صفحة الدفع لديك)
        return redirect('checkout')

    return redirect('book_detail', book_id=book_id)



#داله الةاجهه الرئيسيه
# تحديث دالة الواجهة الرئيسية لتدعم التصفية الفورية في نفس الصفحة
def new_home(request):
    banners = HomePageBanner.objects.filter(is_active=True).order_by('order')
    quick_cats = QuickCategory.objects.filter(is_active=True).order_by('order')
    home_sections = HomePageSection.objects.filter(is_active=True).order_by('order')
    query = request.GET.get('q', '').strip()
    sections_data = []
    for section in home_sections:
        section_books = get_books_for_category(section.category)
        if query: section_books = section_books.filter(Q(title__icontains=query) | Q(description__icontains=query))
        else: section_books = section_books[:8]
        sections_data.append({'name': section.name, 'category': section.category, 'books': section_books})

        # إضافة السطر أدناه فقط إلى الـ context قبل الـ render
    dynamic_layout = get_dynamic_layout('new_home', query=query)
    return render(request, 'store/new_home.html', {'banners': banners, 'quick_cats': quick_cats, 'sections_data': sections_data, 'search_query': query,'dynamic_layout': dynamic_layout, })

#واجهه من نحن
def about_us(request):
    # جلب كافة الأقسام النشطة ليعرضها الـ Sidebar في ملف base.html بشكل مستمر
    all_categories = Category.objects.filter(is_active=True)

    return render(request, 'store/about_us.html', {
        'all_categories': all_categories,
        'current_category': None
    })


def add_store_review(request):
    if request.method == 'POST':
        name = request.POST.get('name')
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')

        if name and rating and comment:
            StoreReview.objects.create(
                customer_name=name,
                rating=rating,
                comment=comment
            )
            messages.success(request, "شكراً لك! تم إرسال تقييمك بنجاح وسوف يظهر بعد المراجعة.")
        else:
            messages.error(request, "يرجى ملء جميع الحقول المطلوبة.")

    return redirect(request.META.get('HTTP_REFERER', 'home'))


def global_context(request):
    # دالة سياق عالمية (اختيارية) أو يمكن تمريرها في كل دالة
    return {
        'approved_reviews': StoreReview.objects.filter(is_approved=True)[:10]
    }


def store_reviews_context(request):
    from .models import StoreReview
    return {
        'approved_reviews': StoreReview.objects.filter(is_approved=True)[:6]
    }


# 1. جديد: دالة الفحص الذكي لكافة الرموز المحفوظة وحالة الاستلام قبل التقييم
def check_review_eligibility(request):
    book_id = request.GET.get('book_id')
    tokens_raw = request.GET.get('tokens', '[]')

    try:
        tokens_list = json.loads(tokens_raw)
    except Exception:
        tokens_list = []

    if not book_id:
        return JsonResponse({'eligible': False, 'message': 'كتاب غير محدد.'})

    # جلب الإعدادات العامة للمتجر
    settings_obj = ReviewSettings.get_settings()

    # --- الحالة الأولى: الإعدادات تسمح بالتعليق دون قيود أو طلبات ---
    if settings_obj.allow_without_order:
        return JsonResponse({
            'eligible': True,
            'customer_name': 'زائر المتجر',
            'is_edit_mode': False,
            'require_tokens': False
        })

    # إذا كان التعليق يشترط وجود طلبات ولم يرسل المتصفح رموزاً
    if not tokens_list:
        return JsonResponse({
            'eligible': False,
            'message': 'لا يمكنك تقييم هذا الكتاب إلا بعد طلب الكتاب.'
        })

    # --- نظام فحص وتنظيف الرموز الخاطئة ---
    valid_tokens = []
    invalid_tokens = []
    for token in tokens_list:
        if Order.objects.filter(buyer_token=token).exists():
            valid_tokens.append(token)
        else:
            invalid_tokens.append(token)

    if invalid_tokens:
        return JsonResponse({
            'eligible': False,
            'message': 'لا يمكنك تقييم هذا الكتاب إلا بعد طلبه واستلامه.',
            'clean_invalid_tokens': True,
            'invalid_tokens_to_remove': invalid_tokens
        })

    # البحث عن الكتاب داخل طلبات العميل
    matching_items = OrderItem.objects.filter(book_id=book_id, order__buyer_token__in=valid_tokens)

    if not matching_items.exists():
        return JsonResponse({
            'eligible': False,
            'message': 'لا يمكنك تقييم هذا الكتاب إلا بعد طلب الكتاب من المتجر.'
        })

    # --- الحالة الثانية: هل يشترط الاستلام أم يكفي مجرد الطلب؟ ---
    if not settings_obj.allow_on_order_only:
        # إذا كان لا يسمح بمجرد الطلب (أي يشترط الاستلام الشديد)
        delivered_items = matching_items.filter(order__status='delivered')
        if not delivered_items.exists():
            return JsonResponse({
                'eligible': False,
                'message': 'لم يتم استلام الطلب بعد، لا يمكنك التقييم إلا بعد الاستلام.'
            })
        target_items = delivered_items
    else:
        # يكفي وجود الطلب بأي حالة كانت
        target_items = matching_items

    # استخراج اسم العميل التلقائي من الطلب
    latest_customer_name = target_items.order_by('-order__created_at').first().order.customer_name

    # --- التحقق من وجود تعليق سابق لنفس العميل على هذا الكتاب ---
    existing_review = BookReview.objects.filter(book_id=book_id, customer_name=latest_customer_name).first()

    if existing_review:
        if existing_review.is_approved:
            return JsonResponse({
                'eligible': False,
                'message': 'لقد قمت بإضافة تعليق سابقاً وموافق عليه، شكراً لك!'
            })
        else:
            # التعليق موجود ولكن لم يتم تفعيل الموافقة عليه (تحت المراجعة) -> السماح بالتعديل
            return JsonResponse({
                'eligible': True,
                'customer_name': latest_customer_name,
                'is_edit_mode': True,
                'existing_comment': existing_review.comment,
                'existing_rating': existing_review.rating,
                'require_tokens': True,
                'message': 'لقد قمت بإضافة تعليق سابقاً، تعليقك تحت المراجعة شكراً لك. يمكنك تعديل تعليقك الحالي أدناه:'
            })

    return JsonResponse({
        'eligible': True,
        'customer_name': latest_customer_name,
        'is_edit_mode': False,
        'require_tokens': True
    })


def add_book_review(request, book_id):
    if request.method == 'POST':
        book = get_object_or_404(Book, id=book_id)
        rating = request.POST.get('rating')
        comment = request.POST.get('comment')
        tokens_raw = request.POST.get('buyer_tokens', '[]')
        custom_name = request.POST.get('custom_customer_name', '').strip()

        settings_obj = ReviewSettings.get_settings()
        approved_status = settings_obj.auto_approve_reviews

        try:
            tokens_list = json.loads(tokens_raw)
        except Exception:
            tokens_list = []

        # 1. المعالجة في حال كان المتجر يسمح بالتعليق دون طلب
        if settings_obj.allow_without_order:
            customer_name = custom_name if custom_name else "زائر مجهول"

            BookReview.objects.create(
                book=book,
                customer_name=customer_name,
                rating=int(rating),
                comment=comment,
                is_approved=approved_status
            )
            if approved_status:
                messages.success(request, "تم نشر تقييمك فوراً بنجاح! شكراً لك.")
            else:
                messages.success(request, "تم إرسال تقييمك بنجاح وهو تحت المراجعة الآن.")

        # 2. المعالجة الأمنية العادية القائمة على الرموز والطلبات
        else:
            if settings_obj.allow_on_order_only:
                matching_items = OrderItem.objects.filter(book_id=book_id, order__buyer_token__in=tokens_list)
            else:
                matching_items = OrderItem.objects.filter(book_id=book_id, order__buyer_token__in=tokens_list,
                                                          order__status='delivered')

            if matching_items.exists() and rating and comment:
                customer_name = matching_items.order_by('-order__created_at').first().order.customer_name

                existing_review = BookReview.objects.filter(book_id=book, customer_name=customer_name).first()

                if existing_review:
                    if not existing_review.is_approved:
                        existing_review.rating = int(rating)
                        existing_review.comment = comment
                        existing_review.is_approved = approved_status
                        existing_review.save()
                        messages.success(request, "تم تحديث مراجعتك بنجاح.")
                    else:
                        messages.error(request, "عذراً، لقد تمت الموافقة على تقييمك السابق بالفعل.")
                else:
                    BookReview.objects.create(
                        book=book,
                        customer_name=customer_name,
                        rating=int(rating),
                        comment=comment,
                        is_approved=approved_status
                    )
                    if approved_status:
                        messages.success(request, "تم نشر تقييمك فوراً بنجاح!")
                    else:
                        messages.success(request, "تم إرسال تقييمك بنجاح وهو تحت المراجعة.")
            else:
                messages.error(request, "عذراً، لم نتمكن من التحقق من صلاحية التقييم.")

    return redirect('book_detail', book_id=book_id)
