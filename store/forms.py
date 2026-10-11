from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    # حقل كود الخصم (حقل نصي عادي مضاف للواجهة)
    coupon_code = forms.CharField(required=False, label="كود الخصم")

    class Meta:
        model = Order
        fields = ['customer_name', 'customer_phone', 'customer_email', 'city', 'address_details', 'delivery_method', 'payment_method']
