from django.contrib import admin
from .models import Category, Book, DeliveryMethod, PaymentMethod, Order, OrderItem, Coupon, HomePageBanner, \
    QuickCategory, HomePageSection, StoreReview, BookReview, ReviewSettings
from django.core.exceptions import ValidationError
from django.contrib import messages
from .models import DynamicPageBlock
from .models import Visitor, GlobalStats
from django.template.response import TemplateResponse
from django.db.models import Count
import json
from django.urls import path
from .models import SocialMediaLink
from .models import AnnouncementSetting, Announcement


# 1. تخصيص عرض الكتب مع ميزات الخصم
@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    # التعديل هنا: استخدام filter_horizontal لتسهيل اختيار عدة أقسام
    list_display = ['title', 'price', 'discount_price', 'is_discount_active', 'is_visible']
    list_editable = ['discount_price', 'is_discount_active', 'is_visible']
    list_filter = ['categories', 'is_discount_active', 'is_visible']
    search_fields = ['title', 'description']
    filter_horizontal = ['categories']

# 2. تخصيص عرض الأقسام مع ميزات الأقسام الذكية والأيام المخصصة
@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    # الحقول المعروضة في الجدول
    list_display = ['position', 'name', 'badge_text', 'category_type', 'show_on_sidebar', 'is_active', 'include_related_books','include_related_deep']

    # [الحل الذكي هنا] جعل حقل الاسم هو الرابط القابل للضغط بدلاً من الترتيب
    list_display_links = ['name']

    # الحقول القابلة للتعديل السريع مباشرة من الجدول
    list_editable = ['position', 'show_on_sidebar', 'is_active', 'include_related_books','include_related_deep']

    list_filter = ['category_type', 'show_on_sidebar', 'is_active', 'include_related_books','include_related_deep']
    search_fields = ['name']
    filter_horizontal = ['related_categories']

    fieldsets = (
        ('المعلومات الأساسية والترتيب', {
            'fields': ('name', 'position', 'image', 'icon_class', 'is_active', 'icon_color')
        }),
        ('نظام العلامات (Badges)', {
            'description': 'النص الذي سيظهر فوق بطاقة الكتاب المرتبط بهذا القسم',
            'fields': ('badge_text', 'badge_color')
        }),
        ('إعدادات الأقسام الذكية', {'fields': ('category_type', 'time_range', 'custom_days')}),
        ('إعدادات العرض والظهور', {
            'fields': ('show_on_sidebar', 'show_on_homepage', 'show_on_detail', 'related_categories','include_related_books','include_related_deep'),
        }),
        ('الترشيحات', {'fields': ('recommendation_source', 'custom_recommendation_category')}),
    )


# 3. إدارة الطلبات
class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    raw_id_fields = ['book']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_number', 'customer_name', 'customer_phone', 'city', 'grand_total', 'status', 'created_at']
    list_editable = ['status']
    list_filter = ['status', 'created_at', 'city']
    search_fields = ['order_number', 'customer_name', 'customer_phone']
    inlines = [OrderItemInline]

# 4. إدارة الكوبونات
@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ['code', 'discount_percentage', 'is_active']
    list_filter = ['is_active']
    search_fields = ['code']

# 5. إدارة الواجهة الرئيسية
@admin.register(HomePageBanner, QuickCategory, HomePageSection)
class HomeAdmin(admin.ModelAdmin):
    list_display = ('name_or_title', 'is_active', 'order')
    list_editable = ('is_active', 'order')

    def name_or_title(self, obj):
        return getattr(obj, 'name', getattr(obj, 'title', ''))



@admin.register(StoreReview)
class StoreReviewAdmin(admin.ModelAdmin):
    list_display = ['customer_name', 'rating', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'rating']
    search_fields = ['customer_name', 'comment']
    list_editable = ['is_approved']
    actions = ['approve_reviews']

    def approve_reviews(self, request, queryset):
        queryset.update(is_approved=True)
    approve_reviews.short_description = "الموافقة على التقييمات المختارة"


@admin.register(BookReview)
class BookReviewAdmin(admin.ModelAdmin):
    list_display = ['book', 'customer_name', 'rating', 'is_approved', 'created_at']
    list_editable = ['is_approved']  # التفعيل الفوري والمباشر من الواجهة الخارجية
    list_filter = ['is_approved', 'rating', 'book']
    search_fields = ['customer_name', 'comment', 'book__title']


@admin.register(ReviewSettings)
class ReviewSettingsAdmin(admin.ModelAdmin):
    list_display = ['__str__', 'allow_without_order', 'allow_on_order_only', 'auto_approve_reviews']

    def has_add_permission(self, request):
        # منع إضافة أكثر من سجل واحد للإعدادات
        if ReviewSettings.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        # منع حذف السجل الرئيسي للإعدادات
        return False


from django import forms
from django.forms.widgets import TextInput
from .models import StoreConfiguration


# 1. واجهة مخصصة لتحويل الحقل النصي إلى لوحة ألوان HTML5
class ColorPickerWidget(TextInput):
    input_type = 'color'


# 2. نموذج مخصص لربط لوحة الألوان بالحقل
class StoreConfigurationForm(forms.ModelForm):
    class Meta:
        model = StoreConfiguration
        fields = '__all__'
        widgets = {
            'text_color': ColorPickerWidget(),
            'whatsapp_banner_right_title_color': ColorPickerWidget(),
            'whatsapp_banner_right_text_color': ColorPickerWidget(),
            'whatsapp_banner_title_color': ColorPickerWidget(),
            'whatsapp_banner_subtitle_color': ColorPickerWidget(),
        }


# 3. تسجيل الموديل في لوحة التحكم بشكل احترافي لمنع التكرار
@admin.register(StoreConfiguration)
class StoreConfigurationAdmin(admin.ModelAdmin):
    form = StoreConfigurationForm

    # هذه الدالة تمنع الأدمن من إنشاء أكثر من سجل إعدادات واحد
    def has_add_permission(self, request):
        if StoreConfiguration.objects.exists():
            return False
        return True


# 6. تسجيل بقية الجداول
admin.site.register(DeliveryMethod)
admin.site.register(PaymentMethod)

#اضافات جديده للتحكم بمضهر الصفحة  الرئيسية

@admin.register(DynamicPageBlock)
class DynamicPageBlockAdmin(admin.ModelAdmin):
    # الأعمدة التي تظهر في جدول الاستعراض الرئيسي للوحة التحكم
    list_display = ['get_custom_title', 'page_name', 'specific_category_page', 'block_type', 'order', 'is_active']

    # خيارات الفلترة السريعة في الجانب الأيسر
    list_filter = ['page_name', 'block_type', 'is_active', 'specific_category_page']

    # تمكين البحث بواسطة العنوان أو اسم القسم المرتبط
    search_fields = ['title', 'specific_category_page__name', 'source_category_for_books__name']

    # ميزة سحرية: تتيح لك تعديل الترتيب وحالة النشاط مباشرة من الجدول دون الدخول لصفحة التعديل
    list_editable = ['order', 'is_active']

    # يمنحك صندوقين رائعين في لوحة التحكم لنقل واختيار "مجموعة الأقسام" بضغطة زر واحدة
    filter_horizontal = ['group_categories']

    # تقسيم الحقول داخل صفحة الإضافة/التعديل بشكل منسق واحترافي
    fieldsets = (
        ('إعدادات المكان والترتيب للواجهة', {
            'fields': ('page_name', 'specific_category_page', 'order', 'is_active'),
            'description': "حدد الصفحة المطلوبة. ملاحظة: إذا اخترت (صفحة قسم محدد) أو (صفحة تفاصيل الكتاب)، يمكنك تحديد قسم معين لربط القوالب به، أو اترك حقل القسم فارغاً ليتم تطبيق الترتيب كقالب عام يظهر في كل الأقسام/الكتب بشكل موحد."
        }),
        ('نوع وتصميم القالب المختار', {
            'fields': ('block_type', 'title', 'icon_class', 'icon_color'),
            'description': "اختر نوع القالب. حقل العنوان اختياري ويظهر كعنوان رئيسي فوق سلايدر الكتب (مثال: كتب مميزة، الأكثر مبيعاً)."
            
        }),
        ('محتوى القالب (يُعبأ بدقة حسب النوع المختار أعلاه)', {
            'fields': ('source_category_for_books', 'group_categories'),
            'description': "هام: إذا كان نوع القالب 'سلايدر كتب' يجب اختيار (القسم المصدري). أما إذا كان النوع 'مجموعة أقسام' فيجب اختيار الأقسام من الصندوق أدناه."
        }),
    )

    def get_custom_title(self, obj):
        """تظهر للمسؤول في الجدول الاسم الفعلي المعروض في المتجر بناءً على الوضعين"""
        if obj.block_type == 'book_slider' and obj.source_category_for_books:
            # إذا تم تحديد اسم مخصص (الوضع الثاني)
            if obj.title and obj.title.strip():
                return f"اسم مخصص: {obj.title} (يجلب من: {obj.source_category_for_books.name})"
            # إذا تُرِك فارغاً (الوضع الأول الافتراضي)
            return f"اسم افتراضي: {obj.source_category_for_books.name}"

        return obj.get_block_type_display()

    get_custom_title.short_description = "العنوان الفعلي المعروض في المتجر"

    def save_model(self, request, obj, form, change):
        """التحقق من القيود والشروط البرمجية قبل حفظ البيانات وإظهار تنبيهات ذكية في لوحة التحكم"""
        try:
            # تشغيل دالة clean المكتوبة داخل الموديل للتحقق من سلامة البيانات
            obj.full_clean()
            super().save_model(request, obj, form, change)
        except ValidationError as e:
            # في حال وجود خطأ في منطق الإدخال، يتم إلغاء الحفظ وإظهار رسالة خطأ حمراء للمسؤول
            form.add_error(None, e)
            messages.error(request, f"فشل الحفظ بسبب خطأ في الإدخال: {e}")


#تبع الزوار


@admin.register(Visitor)
class VisitorAdmin(admin.ModelAdmin):
    change_list_template = "admin/visitor_change_list.html"
    list_display = (
        'ip_address', 'session_key', 'path', 'referrer', 'country', 'region', 'city', 'timestamp'
    )
    list_filter = ('country', 'referrer', 'timestamp')
    search_fields = ('ip_address', 'city', 'path', 'referrer', 'user_agent')

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path(
                'analytics/',
                self.admin_site.admin_view(self.analytics_view),
                name='visitor_analytics'
            ),
        ]
        return custom_urls + urls

    def analytics_view(self, request):
        from django.db.models import Subquery, OuterRef # استيراد الأدوات المتقدمة للربط الدقيق

        platform_filter = request.GET.get('platform', '')
        country_filter = request.GET.get('country', '')
        region_filter = request.GET.get('region', '')
        city_filter = request.GET.get('city', '')
        date_from = request.GET.get('date_from', '')
        date_to = request.GET.get('date_to', '')

        visitors_queryset = Visitor.objects.all()

        if platform_filter:
            if platform_filter == "Facebook":
                visitors_queryset = visitors_queryset.filter(referrer__icontains='facebook')
            elif platform_filter == "Direct / Unknown":
                visitors_queryset = visitors_queryset.filter(referrer="Direct / Unknown")
            elif platform_filter == "Internal":
                visitors_queryset = visitors_queryset.filter(referrer="Internal")
            else:
                visitors_queryset = visitors_queryset.filter(referrer__icontains=platform_filter)

        if country_filter:
            visitors_queryset = visitors_queryset.filter(country=country_filter)
        if region_filter:
            visitors_queryset = visitors_queryset.filter(region=region_filter)
        if city_filter:
            visitors_queryset = visitors_queryset.filter(city=city_filter)
        if date_from:
            visitors_queryset = visitors_queryset.filter(timestamp__date__gte=date_from)
        if date_to:
            visitors_queryset = visitors_queryset.filter(timestamp__date__lte=date_to)

        # حساب المجاميع للزوار (بناءً على الفلترة الحالية)
        unique_visitors = visitors_queryset.values('session_key').distinct().count()
        sessions = visitors_queryset.values('session_key', 'timestamp__date').distinct().count()
        page_views = visitors_queryset.count()

        visitors_by_platform = list(visitors_queryset.values('referrer').annotate(count=Count('id')).order_by('-count'))
        visitors_by_country = list(visitors_queryset.values('country').annotate(count=Count('id')).order_by('-count'))
        visitors_by_city = list(
            visitors_queryset.values('city', 'region', 'country').annotate(count=Count('id')).order_by('-count'))

        # --- الربط الاحترافي والدقيق للطلبات والتحليلات المتقاطعة ---
        # استعلام فرعي لمعرفة البيانات النشطة للزائر في لحظة إنشاء الطلب بالضبط (أحدث سجل زيارة يسبق أو يساوي وقت الطلب)
        exact_visitor_subquery = Visitor.objects.filter(
            session_key=OuterRef('session_key'),
            timestamp__lte=OuterRef('created_at')
        ).order_by('-timestamp')

        # دمج البيانات الديناميكية مع جدول الطلبات قبل الفلترة لمنع أي تداخل بين المنصات
        orders_queryset = Order.objects.annotate(
            attributed_referrer=Subquery(exact_visitor_subquery.values('referrer')[:1]),
            attributed_country=Subquery(exact_visitor_subquery.values('country')[:1]),
            attributed_region=Subquery(exact_visitor_subquery.values('region')[:1]),
            attributed_city=Subquery(exact_visitor_subquery.values('city')[:1]),
        )

        # تطبيق فلاتر المنصة والموقع مباشرة على الطلبات المؤرشفة زمنياً
        if platform_filter:
            if platform_filter == "Facebook":
                orders_queryset = orders_queryset.filter(attributed_referrer__icontains='facebook')
            elif platform_filter == "Direct / Unknown":
                orders_queryset = orders_queryset.filter(attributed_referrer="Direct / Unknown")
            elif platform_filter == "Internal":
                orders_queryset = orders_queryset.filter(attributed_referrer="Internal")
            else:
                orders_queryset = orders_queryset.filter(attributed_referrer__icontains=platform_filter)

        if country_filter:
            orders_queryset = orders_queryset.filter(attributed_country=country_filter)
        if region_filter:
            orders_queryset = orders_queryset.filter(attributed_region=region_filter)
        if city_filter:
            orders_queryset = orders_queryset.filter(attributed_city=city_filter)

        if date_from:
            orders_queryset = orders_queryset.filter(created_at__date__gte=date_from)
        if date_to:
            orders_queryset = orders_queryset.filter(created_at__date__lte=date_to)

        total_orders = orders_queryset.count()
        completed_orders = orders_queryset.filter(status__in=['delivered', 'completed']).count()

        # حساب معدل التحويل بدقة
        conversion_rate = 0
        if unique_visitors > 0:
            conversion_rate = round((total_orders / unique_visitors) * 100, 2)

        # جلب القوائم لتغذية صناديق الاختيار (Dropdowns) كما هي
        platforms_list = Visitor.objects.values_list('referrer', flat=True).distinct()
        cleaned_platforms = []
        for p in platforms_list:
            if p and p != "Internal":
                if "facebook" in p.lower():
                    if "Facebook" not in cleaned_platforms:
                        cleaned_platforms.append("Facebook")
                else:
                    cleaned_platforms.append(p)
        if "Direct / Unknown" not in cleaned_platforms:
            cleaned_platforms.append("Direct / Unknown")
        cleaned_platforms.sort()

        countries_list = Visitor.objects.values_list('country', flat=True).distinct()
        cleaned_countries = [c for c in countries_list if c and c not in ["Unknown (IP not found)", "Unknown (GeoLite2-City.mmdb not found)", "Unknown (No IP Address)"]]
        cleaned_countries.sort()

        cities_list = Visitor.objects.values_list('city', flat=True).distinct()
        cleaned_cities = [city for city in cities_list if city and city != "Unknown"]
        cleaned_cities.sort()

        context = self.admin_site.each_context(request)
        context.update({
            'title': 'لوحة التحليل الشامل للمتجر',
            'unique_visitors': unique_visitors,
            'sessions': sessions,
            'page_views': page_views,
            'total_orders': total_orders,
            'completed_orders': completed_orders,
            'conversion_rate': conversion_rate,

            'chart_platforms': json.dumps([v['referrer'] or 'Direct / Unknown' for v in visitors_by_platform]),
            'chart_platforms_data': json.dumps([v['count'] for v in visitors_by_platform]),
            'chart_countries': json.dumps([v['country'] or 'Unknown' for v in visitors_by_country]),
            'chart_countries_data': json.dumps([v['count'] for v in visitors_by_country]),

            'visitors_by_city': visitors_by_city,
            'visitors_by_platform': visitors_by_platform,

            'filters': {
                'platform': platform_filter,
                'country': country_filter,
                'region': region_filter,
                'city': city_filter,
                'date_from': date_from,
                'date_to': date_to,
            },
            'dropdowns': {
                'platforms': cleaned_platforms,
                'countries': cleaned_countries,
                'cities': cleaned_cities,
            }
        })

        return TemplateResponse(request, 'admin/analytics_dashboard.html', context)


#وسائل التواصل الاجتماعي

@admin.register(SocialMediaLink)
class SocialMediaLinkAdmin(admin.ModelAdmin):
    list_display = ('get_platform_display', 'url', 'show_in_sidebar', 'show_in_footer', 'is_active')
    list_filter = ('is_active', 'show_in_sidebar', 'show_in_footer')

    # تحسين طريقة العرض في لوحة التحكم
    def get_platform_display(self, obj):
        return obj.get_platform_display()

    get_platform_display.short_description = 'المنصة المضافة'




###############
#شريط الاعلانات المتحرك
###############
# 🎨 إنشاء كود الـ Widget الخاص بمنقي الألوان
class AnnouncementSettingForm(forms.ModelForm):
    class Meta:
        model = AnnouncementSetting
        fields = '__all__'
        widgets = {
            'background_color': forms.widgets.Input(attrs={'type': 'color', 'style': 'width: 80px; height: 40px; cursor: pointer;'}),
            'text_color': forms.widgets.Input(attrs={'type': 'color', 'style': 'width: 80px; height: 40px; cursor: pointer;'}),
        }

@admin.register(AnnouncementSetting)
class AnnouncementSettingAdmin(admin.ModelAdmin):
    form = AnnouncementSettingForm  # تشغيل منقي الألوان الذكي هنا
    def has_add_permission(self, request):
        if AnnouncementSetting.objects.exists():
            return False
        return True

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ['text', 'order', 'is_active', 'show_on_all']
    list_editable = ['order', 'is_active']
    search_fields = ['text']

    # تقسيم الحقول في صفحة التعديل لتسهيل الاختيار المتعدد للواجهات
    fieldsets = [
        ("بيانات الإعلان الأساسية", {
            'fields': ['text', 'is_active', 'order']
        }),
        ("🎯 أماكن وعرض الإعلان (يمكنك تحديد أكثر من واجهة معاً)", {
            'fields': [
                'show_on_all',
                'show_on_home',
                'show_on_new_home',
                'show_on_category',
                'show_on_book',
                'show_on_cart',
                'show_on_checkout'
            ]
        }),
    ]
