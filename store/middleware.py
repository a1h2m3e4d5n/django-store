import os  # تمت الإضافة: ضروري لعمل os.path.join بشكل صحيح
from datetime import timedelta  # تمت الإضافة: للتحكم بالنطاق الزمني (الساعات/الأيام)
from django.utils.deprecation import MiddlewareMixin
from ipware import get_client_ip
import geoip2.database
from .models import Visitor, GlobalStats, Order  # إضافة Order هنا
from django.db.models import F
from urllib.parse import urlparse
from django.conf import settings
from django.utils import timezone  # لإضافة timezone.now()


class AdvancedTrackerMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 1. تحديث إجمالي الطلبات (Total Requests)
        stats, created = GlobalStats.objects.get_or_create(id=1)
        GlobalStats.objects.filter(id=1).update(total_requests=F("total_requests") + 1)

        # استثناء صفحات الإدارة والملفات الثابتة من تتبع الزوار التفصيلي
        if request.path.startswith("/admin/") or \
                request.path.startswith("/static/") or \
                request.path.startswith("/media/") or \
                request.path == "/favicon.ico":
            return None

        # 2. الحصول على مفتاح الجلسة (Session Key)
        if not request.session.session_key:
            request.session.save()  # حفظ الجلسة لإنشاء مفتاح لها
        session_key = request.session.session_key

        # 3. الحصول على IP العميل الحقيقي
        client_ip, is_routable = get_client_ip(request)
        country, region, city = "Unknown", "Unknown", "Unknown"

        # 4. تحديد الموقع الجغرافي باستخدام GeoIP2
        if client_ip:
            db_path = os.path.join(settings.BASE_DIR, 'geoip', 'GeoLite2-City.mmdb')
            if os.path.exists(db_path):
                try:
                    with geoip2.database.Reader(db_path) as reader:
                        response = reader.city(client_ip)
                        country = response.country.names.get('ar', response.country.name) or "Unknown"
                        region = response.subdivisions.most_specific.name or "Unknown"
                        city = response.city.name or "Unknown"
                except geoip2.errors.AddressNotFoundError:
                    country = "Unknown (IP not found)"
                except Exception as e:
                    country = f"Error: {e}"
            else:
                country = "Unknown (GeoLite2-City.mmdb not found)"
        else:
            country = "Unknown (No IP Address)"

        # 5. تحديد مصدر الإحالة (Referrer) وتصنيفه وتخزينه في الجلسة
        # إذا لم يكن هناك مصدر أولي مخزن في الجلسة، قم بتحديده وحفظه
        utm_source = request.GET.get('utm_source')
        if utm_source:
            fake_referrer_url = f"https://{utm_source.lower()}.com"
            current_referrer = self._process_referrer(fake_referrer_url, request.get_host())
        else:
            raw_referrer = request.META.get("HTTP_REFERER")
            current_referrer = self._process_referrer(raw_referrer, request.get_host())

        # منطق تحديث المنصة الذكي:
        # إذا جاء العميل من منصة خارجية حقيقية جديدة (ليست تنقلاً داخلياً وليست دخولاً مباشراً غير معروف)
        # نقوم بتحديث المنصة النشطة في الجلسة فوراً لتتحول إلى المنصة الجديدة
        if current_referrer not in ["Internal", "Direct / Unknown"]:
            request.session['active_referrer'] = current_referrer

        # إذا لم تكن هناك أي منصة مسجلة في الجلسة مسبقاً، نضع القيمة الحالية كإجراء احتياطي
        elif 'active_referrer' not in request.session:
            request.session['active_referrer'] = current_referrer

        # الاعتماد على المنصة النشطة الحالية لتسجيل الزيارة
        active_referrer = request.session['active_referrer']

        # 6. الحصول على User Agent
        user_agent = request.META.get("HTTP_USER_AGENT", None)

        # 7. حفظ معلومات الزيارة في قاعدة البيانات
        time_threshold = timezone.now() - timedelta(minutes=2)

        # نتحقق مما إذا كان الزائر قد سجل زيارة لنفس المسار ونفس المنصة النشطة مؤخراً
        if not Visitor.objects.filter(session_key=session_key, path=request.path,
                                      referrer=active_referrer,
                                      timestamp__gte=time_threshold).exists():
            Visitor.objects.create(
                ip_address=client_ip,
                session_key=session_key,
                path=request.path,
                referrer=active_referrer,  # حفظ المنصة النشطة الحالية
                country=country,
                region=region,
                city=city,
                user_agent=user_agent
            )

        return None

    def process_response(self, request, response):
        # 8. تحديث الطلبات الناجحة (التي عادت بكود 200)
        if response.status_code == 200:
            GlobalStats.objects.filter(id=1).update(successful_requests=F("successful_requests") + 1)
        return response

    def _process_referrer(self, referrer_url, current_host):
        if not referrer_url:
            return "Direct / Unknown"

        try:
            parsed_url = urlparse(referrer_url)
            domain = parsed_url.netloc

            if domain == current_host:
                return "Internal"

            social_media_map = {
                "facebook.com": "Facebook",
                "m.facebook.com": "Facebook (Mobile)",
                "l.facebook.com": "Facebook (Link)",
                "instagram.com": "Instagram",
                "t.co": "Twitter",
                "twitter.com": "Twitter",
                "linkedin.com": "LinkedIn",
                "youtube.com": "YouTube",
                "google.com": "Google Search",
                "bing.com": "Bing Search",
                "yahoo.com": "Yahoo Search",
                "whatsapp.com": "WhatsApp",
                "web.whatsapp.com": "WhatsApp Web",
                "reddit.com": "Reddit",
                "pinterest.com": "Pinterest",
                "tiktok.com": "TikTok",
            }

            for key, value in social_media_map.items():
                if key in domain:
                    return value

            return domain

        except Exception:
            return referrer_url

