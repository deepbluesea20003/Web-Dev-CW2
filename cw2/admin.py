from django.contrib import admin
from cw2.models import Transaction, PersonalAccount, BusinessAccount, PaymentDetails, BankDetails

admin.site.register(Transaction)
admin.site.register(PersonalAccount)
admin.site.register(BusinessAccount)
admin.site.register(PaymentDetails)
admin.site.register(BankDetails)

