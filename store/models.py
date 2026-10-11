import os
import uuid
from io import BytesIO
from datetime import timedelta
from PIL import Image

from django.db import models
from django.utils.text import slugify
from django.core.validators import MinValueValidator, MaxValueValidator
from django.utils import timezone
from django.core.files.base import ContentFile


# ==========================================
# دالة مساعدة لضغط وتحويل الصور إلى WebP
# ==========================================
def optimize_image_to_webp(image_field, quality=75):
    """
    تستقبل هذه الدالة حقل الصورة، وتتحقق مما إذا كانت تحتاج إلى تحويل،
    ثم تقوم بضغطها وإعادتها بصيغة WebP.
    """
    if not image_field or not hasattr(image_field, 'file'):
        return image_field

    # منع تكرار الضغط إذا كانت الصورة محولة مسبقاً (مهم جداً عند تحديث البيانات)
    if image_field.name.lower().endswith('.webp'):
        return image_field

    # فتح الصورة
    img = Image.open(image_field)

    # تحويل نظام الألوان إذا لزم الأمر
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')

    output = BytesIO()
    img.save(output, format='WebP', quality=quality)
    output.seek(0)

    current_name = os.path.splitext(image_field.name)[0]
    new_name = f"{current_name}.webp"

    return ContentFile(output.read(), name=new_name)



ICON_CHOICES = [
    ('', 'بدون أيقونة'),
    ('bi bi-star-fill', '⭐ نجمة ممتلئة (Star)'),
    ('bi bi-star', '☆ نجمة فارغة (Star Outline)'),
    ('bi bi-heart-fill', '❤️ قلب (Heart)'),
    ('bi bi-book', '📖 كتاب (Book)'),
    ('bi bi-book-half', '📖 كتاب مفتوح (Book Half)'),
    ('bi bi-journals', '📚 مجموعة كتب/مجلات (Journals)'),
    ('bi bi-journal-bookmark-fill', '📔 كتاب بعلامة مرجعية (Journal Bookmark)'),
    ('bi bi-award-fill', '🏅 وسام التميز (Award)'),
    ('bi bi-fire', '🔥 نار/شائع (Fire)'),
    ('bi bi-lightning-fill', '⚡ صاعقة/سريع (Lightning)'),
    ('bi bi-info-circle-fill', 'ℹ️ معلومات (Info)'),
    ('bi bi-check-circle-fill', '✅ علامة صح (Check)'),
    ('bi bi-bag-fill', '🛍️ حقيبة تسوق (Bag)'),
    ('bi bi-cart-fill', '🛒 عربة تسوق (Cart)'),
    ('bi bi-person-fill', '👤 مستخدم (Person)'),
    ('bi bi-people-fill', '👥 مجموعة مستخدمين (People)'),
    ('bi bi-tags-fill', '🏷️ تصنيفات/تاجات (Tags)'),
    ('bi bi-bookmark-fill', '🔖 إشارة مرجعية (Bookmark)'),
    ('bi bi-grid-fill', '🔲 شبكة أقسام (Grid)'),
    ('bi bi-list-ul', '📋 قائمة (List)'),
    ('bi bi-search', '🔍 بحث (Search)'),
    ('bi bi-bell-fill', '🔔 إشعار/تنبيه (Bell)'),
    ('bi bi-play-circle-fill', '▶️ تشغيل (Play)'),
    ('bi bi-gem', '💎 جوهرة/مميز (Gem)'),
    ('bi bi-globe', '🌐 عالم/لغات (Globe)'),
    ('bi bi-lightbulb-fill', '💡 فكرة (Lightbulb)'),
    ('bi bi-megaphone-fill', '📢 إعلان (Megaphone)'),
    ('bi bi-shield-check', '🛡️ حماية/موثوق (Shield)'),
    ('bi bi-trophy-fill', '🏆 كأس (Trophy)'),
    ('bi bi-pen-fill', '✏️ قلم/مؤلف (Pen)'),
    ('bi bi-sparkles', '✨ بريق / جديد ومميز (Sparkles)'),
    ('bi bi-box-seam-fill', '📦 وصول جديد / صندوق (Box)'),
    ('bi bi-clock-fill', '🕒 أضيف حديثاً / الوقت (Clock)'),
    ('bi bi-crown-fill', '👑 تاج / مميز جداً (Crown)'),
    ('bi bi-gift-fill', '🎁 هدية / عروض (Gift)'),
    ('bi bi-cup-hot-fill', '☕ كوب قهوة / استراحة (Coffee)'),
    ('bi bi-controller', '🎮 ألعاب (Controller)'),
    ('bi bi-palette-fill', '🎨 ألوان / فنون (Palette)'),
    ('bi bi-list', '\ ألوان / فنون (Palette)'),
]
COLOR_CHOICES = [
    ('', 'اللون الافتراضي الخاص بالأيقونة نفسها'),
    ('text-reset', 'بدون لون إضافي (يأخذ اللون الافتراضي للنص)'),
    ('text-primary', 'أزرق (Primary)'),
    ('text-secondary', 'رمادي (Secondary)'),
    ('text-success', 'أخضر (Success)'),
    ('text-danger', 'أحمر (Danger)'),
    ('text-warning', 'أصفر/ذهبي (Warning)'),
    ('text-info', 'سماوي (Info)'),
    ('text-dark', 'أسود (Dark)'),
    ('text-light', 'أبيض (Light)'),
    ('text-muted', 'باهت (Muted)'),

]


# 1. تصنيفات الكتب المحدثة بنظام المرونة الكاملة والأقسام الذكية
class Category(models.Model):
    DYNAMIC_CHOICES = [
        ('none', 'قسم عادي (يدوي)'),
        ('latest', 'أحدث الكتب المضافة'),
        ('best_selling', 'الكتب الأكثر مبيعاً'),
    ]

    TIME_RANGE_CHOICES = [
        ('all_time', 'كل الأوقات'),
        ('custom_days', 'عدد أيام محدد'),
        ('this_week', 'هذا الأسبوع'),
        ('this_month', 'هذا الشهر'),
        ('this_year', 'هذه السنة'),
    ]

    name = models.CharField(max_length=100, unique=True, verbose_name="اسم القسم")
    image = models.ImageField(upload_to="categories_images/", verbose_name="صورة القسم", blank=True, null=True)
    is_active = models.BooleanField(default=True, verbose_name="نشط / ظاهر")
    show_on_sidebar = models.BooleanField(default=False, verbose_name="إظهار في الواجهة الجانبية كقسم رئيسي")
    show_on_homepage = models.BooleanField(default=False, verbose_name="إظهار في الصفحة الرئيسية")
    show_on_detail = models.BooleanField(default=False, verbose_name="إظهار في صفحة التفاصيل")

    # [تحديث] إضافة حقل الأيقونة للقسم
    icon_class = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default='',
        blank=True,
        verbose_name="أيقونة القسم"
    )

    # 4. حقل اختيار اللون
    icon_color = models.CharField(
        max_length=50,
        choices=COLOR_CHOICES,
        default='',
        blank=True,
        verbose_name="لون الأيقونة (اختياري)"
    )
    badge_text = models.CharField(max_length=50, blank=True, null=True, verbose_name="نص العلامة (Badge)",
                                  help_text="مثلاً: جديد، عرض، نادر")
    badge_color = models.CharField(
        max_length=20,
        choices=[
            ('bg-success', 'أخضر'),
            ('bg-danger', 'أحمر'),
            ('bg-warning', 'أصفر'),
            ('bg-primary', 'أزرق'),
            ('bg-dark', 'أسود'),
            ('bg-info', 'سماوي'),
        ],
        default='bg-success',
        verbose_name="لون العلامة"
    )

    category_type = models.CharField(max_length=20, choices=DYNAMIC_CHOICES, default='none', verbose_name="نوع القسم")
    time_range = models.CharField(max_length=20, choices=TIME_RANGE_CHOICES, default='all_time',
                                  verbose_name="النطاق الزمني")
    custom_days = models.PositiveIntegerField(default=0, verbose_name="عدد الأيام المخصص")

    recommendation_source = models.CharField(
        max_length=10,
        choices=[('auto', 'تلقائي من نفس القسم'), ('custom', 'قسم مخصص')],
        default='auto',
        verbose_name="مصدر الترشيحات"
    )
    custom_recommendation_category = models.ForeignKey('self', on_delete=models.SET_NULL, blank=True, null=True,
                                                       related_name='custom_recommended_for')
    related_categories = models.ManyToManyField('self', blank=True, symmetrical=False, related_name='visible_under')

    # 🆕 الحقل الجديد: جلب كتب الأقسام المرتبطة
    include_related_books = models.BooleanField(
        default=False,
        verbose_name="جلب كتب الأقسام المرتبطة",
        help_text="عند التفعيل، سيتم عرض كتب هذا القسم مع كتب الأقسام المرتبطة به (related_categories)."
    )
    include_related_deep = models.BooleanField(
        default=False,
        verbose_name="جلب كتب جميع الأقسام المرتبطة (بجميع المستويات)",
        help_text="عند التفعيل، سيتم جلب كتب هذا القسم + كتب الأقسام المرتبطة به مباشرة، ثم كتب الأقسام المرتبطة بتلك الأقسام، وهكذا إلى أبعد مستوى.",
        db_index=True

    )

    # [إضافة جديدة] حقل للتحكم بالترتيب (كلما قل الرقم ظهر القسم أولاً، مثلاً 0 ثم 1 ثم 2)
    position = models.PositiveIntegerField(
        default=0,
        verbose_name="ترتيب العرض",
        help_text="الترتيب تصاعدي (الأرقام الأصغر تظهر أولاً)"
    )





    class Meta:
        verbose_name = "قسم"
        verbose_name_plural =  "أقسام المتجر" # تم تعديلها لتشمل أي نوع من الأقسام
        # [تحديث] جعل الترتيب الافتراضي مبنياً على حقل position ثم الاسم أبجدياً
        ordering = ['position', 'name']


    def save(self, *args, **kwargs):
        # تطبيق الضغط على صورة القسم
        if self.image:
            self.image = optimize_image_to_webp(self.image)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


# 2. الكتب
class Book(models.Model):
    title = models.CharField(max_length=255, verbose_name="عنوان الكتاب")
    categories = models.ManyToManyField(Category, related_name="books", verbose_name="الأقسام")
    description = models.TextField(verbose_name="نبذة عن الكتاب")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="السعر الأصلي")
    discount_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="سعر الخصم", blank=True,
                                         null=True)
    is_discount_active = models.BooleanField(default=False, verbose_name="تفعيل الخصم")
    cover_image = models.ImageField(upload_to="books_covers/", verbose_name="صورة الغلاف")
    is_visible = models.BooleanField(default=True, verbose_name="إظهار في المتجر")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "كتاب"
        verbose_name_plural = "الكتب"

    def save(self, *args, **kwargs):
        # تطبيق الضغط على غلاف الكتاب
        if self.cover_image:
            self.cover_image = optimize_image_to_webp(self.cover_image)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.title

    @property
    def current_price(self):
        if self.is_discount_active and self.discount_price:
            return self.discount_price
        return self.price

    @property
    def dynamic_badges(self):
        badges = []
        dynamic_cats = Category.objects.filter(
            is_active=True
        ).exclude(category_type='none').exclude(badge_text__isnull=True).exclude(badge_text='')

        for cat in dynamic_cats:
            if cat.category_type == 'latest':
                latest_ids = Book.objects.filter(is_visible=True).order_by('-created_at').values_list('id', flat=True)[
                             :20]
                if self.id in latest_ids:
                    badges.append({'text': cat.badge_text, 'color': cat.badge_color})

            elif cat.category_type == 'best_selling':
                from .views import get_books_for_category
                best_selling_books = get_books_for_category(cat)
                if best_selling_books and self in best_selling_books:
                    badges.append({'text': cat.badge_text, 'color': cat.badge_color})

        return badges

    @property
    def average_rating_emoji(self):
        reviews = self.reviews.filter(is_approved=True)
        if not reviews.exists():
            return "⭐⭐⭐⭐⭐"

        avg = sum(r.rating for r in reviews) / reviews.count()
        rounded_rating = round(avg)

        if rounded_rating == 5:
            return "⭐⭐⭐⭐⭐"
        elif rounded_rating == 4:
            return "⭐⭐⭐⭐"
        elif rounded_rating == 3:
            return "⭐⭐⭐"
        elif rounded_rating == 2:
            return "⭐⭐"
        else:
            return "⭐"

    @property
    def approved_reviews_count(self):
        return self.reviews.filter(is_approved=True).count()


# 3. طرق التوصيل
class DeliveryMethod(models.Model):
    name = models.CharField(max_length=150, verbose_name="طريقة التوصيل")
    description = models.TextField(verbose_name="تفاصيل التوصيل ومواعيده", blank=True, null=True)
    cost = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="التكلفة (YER)")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    def __str__(self):
        return f"{self.name} - {self.cost}"


# 4. طرق الدفع
class PaymentMethod(models.Model):
    name = models.CharField(max_length=150, verbose_name="طريقة الدفع")
    instructions = models.TextField(verbose_name="تعليمات الدفع للعميل")
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    def __str__(self):
        return self.name


# 5. نموذج كود الخصم
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="كود الخصم")
    discount_percentage = models.PositiveIntegerField(
        verbose_name="نسبة الخصم %",
        validators=[MinValueValidator(1), MaxValueValidator(100)]
    )
    is_active = models.BooleanField(default=True, verbose_name="نشط")

    def __str__(self):
        return f"{self.code} ({self.discount_percentage}%)"


# 5. الطلبات
class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'قيد الانتظار'),
        ('processing', 'قيد التجهيز'),
        ('delivered', 'تم التسليم'),
    ]
    order_number = models.CharField(max_length=50, unique=True, editable=False, verbose_name="رقم الطلب")
    buyer_token = models.UUIDField(default=uuid.uuid4, editable=False, unique=True, verbose_name="رمز المشتري السري")

    customer_name = models.CharField(max_length=255, verbose_name="اسم العميل")
    customer_phone = models.CharField(max_length=50, verbose_name="رقم الهاتف")
    customer_email = models.EmailField(verbose_name="البريد الإلكتروني", blank=True, null=True)
    city = models.CharField(max_length=100, verbose_name="المدينة", blank=True, null=True)
    address_details = models.TextField(verbose_name="العنوان بالتفصيل")

    # --- الحقل الجديد المطلوب للربط الدقيق بالتحليلات ---
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name="مفتاح الجلسة (للتحليلات)")
    # --------------------------------------------------

    delivery_method = models.ForeignKey(DeliveryMethod, on_delete=models.PROTECT, verbose_name="طريقة التوصيل")
    payment_method = models.ForeignKey(PaymentMethod, on_delete=models.PROTECT, verbose_name="طريقة الدفع")
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True,
                               verbose_name="كود الخصم المستخدم")
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="الإجمالي")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="حالة الطلب")
    created_at = models.DateTimeField(auto_now_add=True)

    def save(self, *args, **kwargs):
        if not self.order_number:
            self.order_number = f"ORD-{uuid.uuid4().hex[:8].upper()}"
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.order_number} - {self.customer_name}"


# 6. تفاصيل الطلب
class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name="الطلب")
    book = models.ForeignKey(Book, on_delete=models.PROTECT, verbose_name="الكتاب")
    quantity = models.PositiveIntegerField(default=1, verbose_name="الكمية")
    is_reviewed = models.BooleanField(default=False, verbose_name="تم التقييم")

    def __str__(self):
        return f"{self.book.title} ({self.quantity})"


# واجهه الرئيسيه
class HomePageBanner(models.Model):
    title = models.CharField(max_length=200, verbose_name="عنوان الإعلان")
    image = models.ImageField(upload_to="home_banners/", verbose_name="صورة الإعلان")
    is_active = models.BooleanField(default=True, verbose_name="إظهار في الواجهة")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتيب العرض")

    class Meta:
        ordering = ['order']
        verbose_name = "إعلان الواجهة الرئيسية"

    def save(self, *args, **kwargs):
        # تطبيق الضغط على صورة الإعلان
        if self.image:
            self.image = optimize_image_to_webp(self.image, quality=80)  # جودة أعلى قليلاً للبنرات
        super().save(*args, **kwargs)


class HomePageSection(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم القسم في الواجهة")
    category = models.ForeignKey('Category', on_delete=models.CASCADE, verbose_name="القسم المرتبط")
    is_active = models.BooleanField(default=True, verbose_name="إظهار القسم في الواجهة")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتيب القسم")

    class Meta:
        ordering = ['order']
        verbose_name = "قسم المنتجات في الواجهة"


class QuickCategory(models.Model):
    name = models.CharField(max_length=100, verbose_name="اسم القسم السريع")
    image = models.ImageField(upload_to="quick_categories/", verbose_name="أيقونة القسم")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="القسم المرتبط")
    is_active = models.BooleanField(default=True, verbose_name="إظهار في الشريط")
    order = models.PositiveIntegerField(default=0, verbose_name="الترتيب")

    class Meta:
        ordering = ['order']
        verbose_name = "أيقونة الوصول السريع"

    def save(self, *args, **kwargs):
        # تطبيق الضغط على أيقونة القسم
        if self.image:
            self.image = optimize_image_to_webp(self.image)
        super().save(*args, **kwargs)


# 7. تقييمات المتجر
class StoreReview(models.Model):
    RATING_CHOICES = [
        (1, '⭐'), (2, '⭐⭐'), (3, '⭐⭐⭐'), (4, '⭐⭐⭐⭐'), (5, '⭐⭐⭐⭐⭐'),
    ]
    customer_name = models.CharField(max_length=100, verbose_name="اسم العميل")
    rating = models.IntegerField(choices=RATING_CHOICES, default=5, verbose_name="التقييم")
    comment = models.TextField(verbose_name="التعليق")
    is_approved = models.BooleanField(default=False, verbose_name="تمت الموافقة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التقييم")

    class Meta:
        verbose_name = "تقييم المتجر"
        verbose_name_plural = "تقييمات المتجر"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.customer_name} - {self.rating} Stars"


# تقييمات الكتب
class BookReview(models.Model):
    RATING_CHOICES = [
        (1, '⭐'), (2, '⭐⭐'), (3, '⭐⭐⭐'), (4, '⭐⭐⭐⭐'), (5, '⭐⭐⭐⭐⭐'),
    ]
    book = models.ForeignKey(Book, on_delete=models.CASCADE, related_name="reviews", verbose_name="الكتاب")
    customer_name = models.CharField(max_length=100, verbose_name="اسم العميل")
    rating = models.IntegerField(choices=RATING_CHOICES, verbose_name="التقييم")
    comment = models.TextField(verbose_name="التعليق")
    is_approved = models.BooleanField(default=False, verbose_name="تمت الموافقة")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="تاريخ التقييم")

    class Meta:
        verbose_name = "تقييم الكتاب"
        verbose_name_plural = "تقييمات الكتب"
        ordering = ['-created_at']

    def __str__(self):
        return f"تقييم لـ {self.book.title} من {self.customer_name}"


# إعدادات تقييمات الكتب
class ReviewSettings(models.Model):
    allow_without_order = models.BooleanField(default=False, verbose_name="السماح بالتعليق دون طلب الكتاب (للجميع)")
    allow_on_order_only = models.BooleanField(default=False,
                                              verbose_name="السماح بالتعليق بمجرد الطلب (حتى لو لم يستلم بعد)")
    auto_approve_reviews = models.BooleanField(default=False,
                                               verbose_name="الموافقة التلقائية على التعليقات وعرضها فوراً")

    class Meta:
        verbose_name = "إعدادات تقييمات الكتب"
        verbose_name_plural = "إعدادات تقييمات الكتب"

    def __str__(self):
        return "الإعدادات العامة لنظام التقييمات"

    @classmethod
    def get_settings(cls):
        obj, created = cls.objects.get_or_create(id=1)
        return obj





class StoreConfiguration(models.Model):
    store_name = models.CharField(max_length=150, default="مكتبة السقاف", verbose_name="اسم المتجر")
    logo = models.ImageField(upload_to="store_logo/", verbose_name="صورة الشعار", blank=True, null=True)
    text_color = models.CharField(max_length=7, default="#ffffff", verbose_name="لون اسم المتجر")
    whatsapp_link = models.URLField(
        default="https://wa.me/967774835815",
        verbose_name="رابط واتساب للشريط السفلي المثبت"
    )

    # --- حقول بانر طلب الكتب الجديد قبل الفوتر ---
    show_whatsapp_banner = models.BooleanField(
        default=True,
        verbose_name="عرض بانر الواتساب قبل الفوتر"
    )
    whatsapp_banner_title = models.CharField(
        max_length=200,
        default="لم تجد الكتاب الذي تبحث عنه؟",
        verbose_name="عنوان البانر الرئيسي"
    )
    # --- ألوان نصوص الجهة اليسرى (الأساسية) ---
    whatsapp_banner_title_color = models.CharField(
        max_length=7,
        default="#D4AF37",  # اللون الذهبي الافتراضي للموقع
        verbose_name="لون عنوان البانر الأساسي"
    )
    whatsapp_banner_subtitle = models.CharField(
        max_length=300,
        default="تواصل معنا عبر واتساب وسنوفره لك بأسرع وقت",
        verbose_name="النص الفرعي للبانر"
    )
    whatsapp_banner_subtitle_color = models.CharField(max_length=7, default="#ffffff",
        verbose_name="لون وصف البانر الأساسي"
    )



    whatsapp_banner_bg = models.ImageField(
        upload_to='banners/',
        blank=True,
        null=True,
        verbose_name="صورة خلفية البانر (يفضل صورة مظلمة بدقة عالية)"
    )
    whatsapp_banner_btn_text = models.CharField(
        max_length=100,
        default="تواصل عبر واتساب",
        verbose_name="نص زر الواتساب"
    )
    whatsapp_banner_url = models.URLField(
        default="https://wa.me/967774835815",
        verbose_name="رابط الواتساب المخصص للبانر"
    )
    # --- [إضافة] حقول الجهة اليمنى الاختيارية للبانر ---
    whatsapp_banner_right_title = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        verbose_name="عنوان الجهة اليمنى للبانر (اختياري - يترك فارغاً للإخفاء)"
    )
    # --- ألوان نصوص الجهة اليمنى ---
    whatsapp_banner_right_title_color = models.CharField(
        max_length=7,
        default="#ffffff",
        verbose_name="لون عنوان الجهة اليمنى"
    )


    whatsapp_banner_right_text = models.TextField(
        blank=True,
        null=True,
        verbose_name="نص أو وصف الجهة اليمنى (اختياري - يترك فارغاً للإخفاء)"
    )


    whatsapp_banner_right_text_color = models.CharField(
        max_length=7,
        default="#b0b0b0",
        verbose_name="لون وصف الجهة اليمنى"
    )







    class Meta:
        verbose_name = "إعدادات المتجر العامة"
        verbose_name_plural = "إعدادات المتجر العامة"

    def __str__(self):
        return self.store_name



#اضافات جديده للتحكم بمضهر الصفحة  الرئيسية

class DynamicPageBlock(models.Model):
    BLOCK_TYPES = [
        ('quick_cats', 'مجموعة أقسام (دوائر متحركة)'),
        ('book_slider', 'سلايدر كتب (منتجات متحركة)'),
    ]

    # الصفحات الأربع المطلوبة
    PAGE_CHOICES = [
        ('home', 'الرئيسية القديمة (home)'),
        ('new_home', 'الرئيسية الجديدة (new_home)'),
        ('category_detail', 'صفحة تفاصيل القسم (category)'),
        ('book_detail', 'صفحة تفاصيل الكتاب (book)'),
    ]

    # 1. إضافة قائمة الأيقونات
    # 1. قائمة أيقونات Bootstrap فقط (موسعة)

    # 2. قائمة ألوان Bootstrap


    # 3. حقل اختيار الأيقونة
    icon_class = models.CharField(
        max_length=50,
        choices=ICON_CHOICES,
        default='',
        blank=True,
        verbose_name="أيقونة العنوان (اختياري)"
    )

    # 4. حقل اختيار اللون
    icon_color = models.CharField(
        max_length=50,
        choices=COLOR_CHOICES,
        default='',
        blank=True,
        verbose_name="لون الأيقونة (اختياري)"
    )


    title = models.CharField(
        max_length=150,
        verbose_name="عنوان القالب",
        blank=True,
        null=True,
        help_text="الوضع 1 (افتراضي): اترك الحقل فارغاً ليتم عرض اسم القسم الأصلي للكتب تلقائياً. الوضع 2: اكتب اسماً هنا ليتم عرضه كاسم جديد بدلاً من اسم القسم."
    )
    page_name = models.CharField(max_length=50, choices=PAGE_CHOICES, verbose_name="الصفحة المستهدفة")

    # يربط بالقسم سواء كانت صفحة القسم نفسه أو إذا كنا نريد تخصيص الصفحة لكتاب ينتمي لقسم معين
    specific_category_page = models.ForeignKey('Category', on_delete=models.CASCADE, null=True, blank=True,
                                               related_name='page_blocks',
                                               verbose_name="تحديد القسم (إذا كان القالب مخصص لصفحة قسم أو كتاب محدد)")

    block_type = models.CharField(max_length=50, choices=BLOCK_TYPES, verbose_name="نوع القالب")
    order = models.PositiveIntegerField(verbose_name="ترتيب العرض في هذه الصفحة")
    is_active = models.BooleanField(default=True, verbose_name="نشط/ظاهر")

    source_category_for_books = models.ForeignKey('Category', on_delete=models.SET_NULL, null=True, blank=True,
                                                  related_name='slider_blocks',
                                                  verbose_name="القسم المصدري (لسلايدر الكتب)")
    group_categories = models.ManyToManyField('Category', blank=True, related_name='group_blocks',
                                              verbose_name="مجموعة الأقسام (للقالب الدائري)")

    class Meta:
        ordering = ['order']
        verbose_name = "قالب ديناميكي بالصفحة"
        verbose_name_plural = "منشئ الصفحات الديناميكي"
        # يمنع تكرار نفس رقم الترتيب لنفس الصفحة ونفس القسم المخصص
        unique_together = [['page_name', 'specific_category_page', 'order']]

    def __str__(self):
        return f"{self.get_block_type_display()} - {self.get_page_name_display()} (ترتيب: {self.order})"



#نظام تتبع الزوار

class Visitor(models.Model):
    ip_address = models.GenericIPAddressField(null=True, blank=True, verbose_name="عنوان IP")
    session_key = models.CharField(max_length=40, null=True, blank=True, verbose_name="مفتاح الجلسة")
    path = models.CharField(max_length=255, verbose_name="الصفحة المزورة")
    referrer = models.URLField(max_length=500, null=True, blank=True, verbose_name="مصدر الزيارة")  # زيادة الطول
    country = models.CharField(max_length=100, default="Unknown", verbose_name="الدولة")
    region = models.CharField(max_length=100, default="Unknown", verbose_name="المنطقة/المحافظة")
    city = models.CharField(max_length=100, default="Unknown", verbose_name="المدينة")
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name="وقت الزيارة")
    user_agent = models.CharField(max_length=255, null=True, blank=True, verbose_name="وكيل المستخدم")

    def __str__(self):
        return f"{self.ip_address} - {self.path} ({self.timestamp.strftime('%Y-%m-%d %H:%M')})"

    class Meta:
        ordering = [

        ]
        verbose_name = "زائر"
        verbose_name_plural = "سجل الزوار"


class GlobalStats(models.Model):
    """نموذج لتخزين العدادات العامة للمتجر"""
    total_requests = models.PositiveBigIntegerField(default=0, verbose_name="إجمالي طلبات المتجر")
    successful_requests = models.PositiveBigIntegerField(default=0, verbose_name="طلبات استلام ناجحة")

    class Meta:
        verbose_name = "إحصائيات عامة"
        verbose_name_plural = "إحصائيات عامة"

    def __str__(self):
        return f"إحصائيات المتجر (طلبات: {self.total_requests})"



#########
# 1. موديل مخصص لإضافة أي شبكة تواصل بشكل ديناميكي
#########
class SocialMediaLink(models.Model):
    # تعريف المنصات وأيقونات بوتستراب وكلاسات الألوان الرسمية لكل خلفية
    PLATFORM_METADATA = {
        'facebook': {
            'name': 'فيسبوك (Facebook)',
            'icon': 'bi-facebook',
            'bs_color_sidebar': 'text-primary',  # لون أزرق رسمي للبوتستراب
            'bs_color_footer': 'text-primary'
        },
        'instagram': {
            'name': 'إنستغرام (Instagram)',
            'icon': 'bi-instagram',
            'bs_color_sidebar': 'text-danger',  # لون أحمر/وردي قريب من إنستغرام
            'bs_color_footer': 'text-danger'
        },
        'whatsapp': {
            'name': 'واتساب (WhatsApp)',
            'icon': 'bi-whatsapp',
            'bs_color_sidebar': 'text-success',  # لون أخضر بوتستراب
            'bs_color_footer': 'text-success'
        },
        'youtube': {
            'name': 'يوتيوب (YouTube)',
            'icon': 'bi-youtube',
            'bs_color_sidebar': 'text-danger',  # أحمر بوتستراب
            'bs_color_footer': 'text-danger'
        },
        'telegram': {
            'name': 'تلغرام (Telegram)',
            'icon': 'bi-telegram',
            'bs_color_sidebar': 'text-info',  # لون سماوي رسمي للبوتستراب
            'bs_color_footer': 'text-info'
        },
        'tiktok': {
            'name': 'تيك توك (TikTok)',
            'icon': 'bi-tiktok',
            'bs_color_sidebar': 'text-dark',  # يظهر أسود بالقائمة الجانبية
            'bs_color_footer': 'text-light'  # يظهر أبيض بالفوتر الداكن
        },
        'twitter_x': {
            'name': 'إكس / تويتر (X)',
            'icon': 'bi-twitter-x',
            'bs_color_sidebar': 'text-dark',
            'bs_color_footer': 'text-light'
        },
        'linkedin': {
            'name': 'لينكد إن (LinkedIn)',
            'icon': 'bi-linkedin',
            'bs_color_sidebar': 'text-primary',
            'bs_color_footer': 'text-primary'
        },
        'snapchat': {
            'name': 'سناب شات (Snapchat)',
            'icon': 'bi-snapchat',
            'bs_color_sidebar': 'text-warning',  # لون أصفر بوتستراب
            'bs_color_footer': 'text-warning'
        },
    }

    PLATFORM_CHOICES = [(key, val['name']) for key, val in PLATFORM_METADATA.items()]

    platform = models.CharField(
        max_length=50,
        choices=PLATFORM_CHOICES,
        unique=True,
        verbose_name="المنصة"
    )
    url = models.URLField(verbose_name="رابط الحساب الكامل")

    # التحكم بالظهور والإخفاء
    show_in_sidebar = models.BooleanField(default=True, verbose_name="عرض في تذييل القائمة الجانبية")
    show_in_footer = models.BooleanField(default=True, verbose_name="عرض في تذييل الصفحة الرئيسية")
    is_active = models.BooleanField(default=True, verbose_name="نشط (تفعيل/تعطيل)")

    class Meta:
        verbose_name = "رابط تواصل اجتماعي"
        verbose_name_plural = "روابط التواصل الاجتماعي"

    def __str__(self):
        return self.get_platform_display()

    # جلب كود الأيقونة تلقائياً
    @property
    def icon_class(self):
        return self.PLATFORM_METADATA.get(self.platform, {}).get('icon', 'bi-link-45deg')

    # جلب كلاس لون بوتستراب للقائمة الجانبية
    @property
    def bs_color_sidebar(self):
        return self.PLATFORM_METADATA.get(self.platform, {}).get('bs_color_sidebar', 'text-secondary')

    # جلب كلاس لون بوتستراب للفوتر
    @property
    def bs_color_footer(self):
        return self.PLATFORM_METADATA.get(self.platform, {}).get('bs_color_dark', 'text-light')

###############
#شريط الاعلانات المتحرك
###############
class AnnouncementSetting(models.Model):
    is_bar_enabled = models.BooleanField(default=True, verbose_name="تفعيل شريط الإعلانات بشكل كلي للموقع")
    # 🎨 الحقول الجديدة للتحكم في الألوان
    background_color = models.CharField(max_length=7, default="#3e2723", verbose_name="لون خلفية الشريط الإعلاني")
    text_color = models.CharField(max_length=7, default="#d4af37", verbose_name="لون خط نصوص الإعلانات")

    class Meta:
        verbose_name = "⚙️ مفتاح التشغيل والإخفاء الكلي للشريط"
        verbose_name_plural = "⚙️ مفتاح التشغيل والإخفاء الكلي للشريط"

    def __str__(self):
        return "إعدادات التشغيل العامة"


class Announcement(models.Model):
    text = models.CharField(max_length=255, verbose_name="النص الإعلاني")
    is_active = models.BooleanField(default=True, verbose_name="نشط (ظهور)")
    order = models.PositiveIntegerField(default=0, verbose_name="ترتيب الظهور")

    # حقول الاختيار المتعدد المستقلة - يمكنك تحديد أي عدد من الواجهات معاً للنص الواحد
    show_on_all = models.BooleanField(default=False, verbose_name="جميع واجهات الموقع بلا استثناء")
    show_on_home = models.BooleanField(default=False, verbose_name="الواجهة الرئيسية القديمة")
    show_on_new_home = models.BooleanField(default=False, verbose_name="الواجهة الرئيسية الجديدة")
    show_on_category = models.BooleanField(default=False, verbose_name="صفحة تفاصيل القسم")
    show_on_book = models.BooleanField(default=False, verbose_name="صفحة تفاصيل الكتاب")
    show_on_cart = models.BooleanField(default=False, verbose_name="صفحة سلة التسوق")
    show_on_checkout = models.BooleanField(default=False, verbose_name="صفحة الدفع والنهاية")

    class Meta:
        ordering = ['order']
        verbose_name = "📝 نص رسالة إعلانية"
        verbose_name_plural = "📝 إدارة النصوص والرسائل الإعلانية"

    def __str__(self):
        return self.text[:50]
