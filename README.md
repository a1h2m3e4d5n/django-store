# PythonProject17 — Docker وPostgreSQL

مشروع متجر مبني على Django، جُهّز في هذه النسخة للتشغيل مع PostgreSQL باستخدام Docker Compose. لا يحتوي هذا الأرشيف على ملف `.env` الحقيقي؛ أنشئ ملفًا محليًا من النموذج ولا ترفع القيم السرية إلى Git.

## تشغيل محلي

المتطلبات هي Docker Engine وملحق Docker Compose. من مجلد المشروع:

```bash
cp .env.example .env
```

عدّل `DB_PASSWORD` و`DJANGO_SECRET_KEY` في `.env` إلى قيم محلية خاصة بك، ثم شغّل:

```bash
docker compose up --build
```

بعد اكتمال التشغيل، افتح `http://localhost:8000`. ينفّذ مدخل الحاوية ترحيلات Django ويجمع الملفات الثابتة قبل تشغيل Gunicorn. تحفظ PostgreSQL والوسائط والنسخ الاحتياطية في Docker volumes. لإيقاف الخدمات مع الإبقاء على البيانات استخدم `docker compose down`؛ لا تستخدم `docker compose down -v` إلا إذا أردت حذف بيانات volumes نهائيًا.

لإنشاء حساب إدارة:

```bash
docker compose exec web python manage.py createsuperuser
```

## النشر على خادم Docker

يتطلب مسار النشر خادم Linux متصلًا بالإنترنت عليه Docker وملحق Compose، مع فتح المنفذين 80 و443 في الجدار الناري. وجّه سجلات DNS للنطاق إلى عنوان الخادم. يشغّل `docker-compose.production.yml` التطبيق وقاعدة PostgreSQL وCaddy؛ يتولى Caddy إصدار HTTPS وتجديده تلقائيًا عند صحة DNS وإمكانية الوصول إلى الخادم على المنافذ اللازمة.

أنشئ على الخادم مجلدًا للنشر، مثل `/opt/pythonproject17`، وانسخ إليه `docker-compose.production.yml` و`Caddyfile`. أنشئ ملف `/opt/pythonproject17/.env` يدويًا. لا تنسخ ملف `.env` المحلي من جهاز المطور. أضف على الأقل القيم التالية مع استبدال كل قيمة بمعلومة حقيقية:

```dotenv
DJANGO_ENV=production
DJANGO_DEBUG=false
DJANGO_SECRET_KEY=ضع_قيمة_عشوائية_قوية_وفريدة
DJANGO_ALLOWED_HOSTS=shop.example.com,www.shop.example.com
DJANGO_CSRF_TRUSTED_ORIGINS=https://shop.example.com,https://www.shop.example.com
DJANGO_TIME_ZONE=Asia/Aden
DB_NAME=store_db
DB_USER=store_user
DB_PASSWORD=ضع_كلمة_مرور_قوية_وفريدة
APP_PORT=8000
DOMAIN=shop.example.com
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=true
EMAIL_HOST_USER=
EMAIL_HOST_PASSWORD=
ADMIN_EMAIL=
DEFAULT_FROM_EMAIL=
```

يمكن توليد مفتاح Django عشوائي من جهاز موثوق باستخدام:

```bash
python -c 'from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())'
```

تأكد أن النطاقات في `DJANGO_ALLOWED_HOSTS` بلا `https://`، وأن `DJANGO_CSRF_TRUSTED_ORIGINS` تتضمن البروتوكول. اجعل `.env` مقروءًا من حساب النشر فقط، مثلًا `chmod 600 /opt/pythonproject17/.env`.

## إعداد النشر التلقائي

سير العمل الموجود في `.github/workflows/deploy.yml` يشغّل فحوص Django والاختبارات على PostgreSQL لكل طلب دمج، ثم يبني صورة Docker ويدفعها إلى GitHub Container Registry عند التحديث إلى `main`. إذا ضُبطت أسرار SSH المطلوبة، ينقل ملف Compose الإنتاجي إلى الخادم ويحدّث الخدمة تلقائيًا بعد نجاح الاختبارات.

أضف الأسرار التالية من إعدادات مستودع GitHub ضمن **Settings → Secrets and variables → Actions**:

| السر | القيمة |
|---|---|
| `DEPLOY_HOST` | اسم نطاق الخادم أو عنوانه العام |
| `DEPLOY_USER` | مستخدم SSH مخصص للنشر ومخوّل بتشغيل Docker Compose |
| `DEPLOY_SSH_KEY` | المفتاح الخاص الذي يقابله مفتاح عام مثبت في `authorized_keys` لذلك المستخدم |
| `DEPLOY_KNOWN_HOSTS` | سطر/أسطر بصمة SSH للخادم التي تحققت منها مسبقًا عبر قناة موثوقة |
| `DEPLOY_PATH` | مجلد النشر على الخادم، مثل `/opt/pythonproject17` |
| `DEPLOY_PORT` | اختياري؛ منفذ SSH، والافتراضي 22 |

اجعل حزمة GHCR **عامة** إذا كان الخادم سيسحب الصورة دون تسجيل دخول. إذا كانت خاصة، سجّل دخول Docker على الخادم إلى `ghcr.io` باستخدام حساب أو رمز وصول محدود الصلاحية بقراءة الحزم فقط، واختبر السحب يدويًا قبل أول نشر. لا تحفظ رمز GHCR في ملف المشروع أو في سجل الأوامر. يلزم أن يكون الفرع الافتراضي في إعدادات المستودع هو `main` أو تعديل اسم الفرع في workflow.

لأول تشغيل يدوي على الخادم، وبعد تسجيل الدخول إلى GHCR عند الحاجة، نفّذ من مجلد النشر:

```bash
# أضف اسم صورة GHCR وإصدارها إلى ملف .env قبل التشغيل:
# DOCKER_IMAGE=ghcr.io/owner/repository:latest

docker compose --env-file .env -f docker-compose.production.yml pull
docker compose --env-file .env -f docker-compose.production.yml up -d
```

أنشئ مستخدم الإدارة بعد أول تشغيل:

```bash
docker compose --env-file .env -f docker-compose.production.yml exec web python manage.py createsuperuser
```

## ملاحظات البيانات والأمان

تشغيل migrations ينشئ أو يحدّث مخطط PostgreSQL انطلاقًا من ملفات Django؛ ولا ينقل سجلات قاعدة SQL Server القديمة. إذا أردت الاحتفاظ ببيانات موجودة، يجب تنفيذ تصدير وتحويل واستيراد منفصل واختبار علاقات البيانات قبل توجيه الموقع للإنتاج.

تحتفظ volumes المحلية والإنتاجية ببيانات قاعدة PostgreSQL والوسائط وملفات النسخ الاحتياطية عند إعادة إنشاء الحاويات، لكنها ليست بديلًا عن نسخ احتياطي خارج الخادم واختبار الاستعادة. كما أن نسخة JSON التي ينشئها التطبيق ليست نسخة مطابقة لملفات الوسائط ولا تغني عن نسخ PostgreSQL الأصلية.

لا تستخدم Docker Compose الإنتاجي على الإنترنت قبل ضبط قيم الأسرار والنطاق وDNS. إذا سبق أن شاركت ملف `.env` يحتوي أسرارًا حقيقية، غيّر كلمات المرور ومفاتيح البريد وأي مفاتيح أخرى قبل تشغيل النسخة الإنتاجية.
