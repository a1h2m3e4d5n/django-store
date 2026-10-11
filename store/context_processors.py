from .models import Category, StoreConfiguration
from .models import SocialMediaLink
from .models import AnnouncementSetting, Announcement
from django.db.models import Q


def cart_count(request):
    cart = request.session.get('cart', {})
    # جمع كل الكميات الموجودة في السلة
    total_items = sum(item['quantity'] for item in cart.values())
    return {'cart_count': total_items}

def categories_processor(request):
    # جلب فقط الأقسام النشطة والمحددة للظهور في الصفحة الرئيسية
    return {
        'all_categories': Category.objects.filter(is_active=True)
    }




def global_store_settings(request):
    config = StoreConfiguration.objects.first()
    # إذا لم يقم الأدمن بإدخال بيانات بعد، نرسل قيماً افتراضية لتجنب توقف الموقع
    if not config:
        return {
            'store_config': {
                'store_name': "مكتبة السقاف",
                'text_color': "#ffffff",
                'logo': None
            }
        }

    return {'store_config': config}


########
#وسائل التواصل الاجتماعي
#########


def global_context(request):
    return {
        'social_links': SocialMediaLink.objects.filter(is_active=True),

    }



###############
#شريط الاعلانات المتحرك
###############
def announcement_bar_processor(request):
    # 1. التحقق من مفتاح الإخفاء والتشغيل الكلي
    setting = AnnouncementSetting.objects.first()
    if not setting or not setting.is_bar_enabled:
        return {'announcements': [], 'show_announcement_bar': False}

    # 2. قراءة الواجهة النشطة الحالية
    current_url_name = request.resolver_match.url_name if request.resolver_match else ''

    # 3. بناء استعلام مرن لفحص شروط الاختيار المتعدد للواجهات
    q_filter = Q(show_on_all=True)  # يظهر إذا تم تفعيل خيار "كل الواجهات"

    if current_url_name == 'home':
        q_filter |= Q(show_on_home=True)
    elif current_url_name == 'new_home':
        q_filter |= Q(show_on_new_home=True)
    elif current_url_name == 'category_detail':
        q_filter |= Q(show_on_category=True)
    elif current_url_name == 'book_detail':
        q_filter |= Q(show_on_book=True)
    elif current_url_name == 'cart_detail':
        q_filter |= Q(show_on_cart=True)
    elif current_url_name == 'checkout':
        q_filter |= Q(show_on_checkout=True)

    # جلب الإعلانات المطابقة للشروط مرتبة تنازلياً أو تصاعدياً حسب رغبتك
    announcements = Announcement.objects.filter(is_active=True).filter(q_filter).order_by('order')

    return {
        'announcements': announcements,
        'show_announcement_bar': announcements.exists(),
        # 🎨 نمرر الألوان هنا لكي يقرأها ملف الـ HTML
        'bar_bg_color': setting.background_color,
        'bar_text_color': setting.text_color,
    }
