from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('add/<int:book_id>/', views.add_to_cart, name='add_to_cart'),
#    path('category/<int:category_id>/', views.category_books, name='category_books'),
    path('category/<int:category_id>/', views.category_detail, name='category_detail'),
    path('cart/', views.cart_detail, name='cart_detail'),
    path('remove/<int:book_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('update/<int:book_id>/<str:action>/', views.update_cart, name='update_cart'),
    path('checkout/', views.checkout, name='checkout'),
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    path('book/<int:book_id>/', views.book_detail, name='book_detail'),
    path('buy-now/<int:book_id>/', views.buy_now, name='buy_now'),
    path('new-home/', views.new_home, name='new_home'),
    path('about-us/', views.about_us, name='about_us'),

    # الرابط الجديد المخصص للبحث العام الشامل
    path('search/', views.global_search, name='global_search'),
    path('add-review/', views.add_store_review, name='add_store_review'),

    # مسارات منظومة فحص وتقييمات الكتب المستقلة
    path('api/check-review-eligibility/', views.check_review_eligibility, name='check_review_eligibility'),
    path('book/<int:book_id>/add-review/', views.add_book_review, name='add_book_review'),
]
