from django.db import models


# PAYMENT PROVIDERS

class PersonalAccount(models.Model):
    accountNumber = models.IntegerField(primary_key=True)
    paymentDetails = models.ForeignKey('PaymentDetails', on_delete=models.CASCADE)
    bankDetails = models.OneToOneField("BankDetails", on_delete=models.CASCADE)
    email = models.TextField(max_length=60)
    password = models.TextField(max_length=256)
    phoneNumber = models.TextField(max_length=13)
    fullName = models.TextField(max_length=80)


class BusinessAccount(models.Model):
    accountNumber = models.IntegerField(primary_key=True)
    paymentDetails = models.ForeignKey('PaymentDetails', on_delete=models.CASCADE)
    bankDetails = models.OneToOneField("BankDetails", on_delete=models.CASCADE)
    businessNumber = models.IntegerField()
    businessName = models.TextField(max_length=40)
    businessEmail = models.TextField(max_length=50)
    businessPhoneNumber = models.TextField(max_length=13)


class Transaction(models.Model):
    id = models.IntegerField(primary_key=True)
    payer = models.ForeignKey('PersonalAccount', on_delete=models.CASCADE)
    payee = models.ForeignKey('BusinessAccount', on_delete=models.CASCADE)
    amount = models.FloatField()
    currency = models.TextField()
    date = models.DateTimeField()
    transactionStatus = models.TextField()  # initiated, completed, refunded, cancelled


class PaymentDetails(models.Model):
    paymentId = models.IntegerField(primary_key=True)
    cardNumber = models.TextField()
    securityCode = models.TextField()
    expiryDate = models.DateTimeField()


class BankDetails(models.Model):
    accountNumber = models.IntegerField(primary_key=True)
    sortCode = models.TextField()
    accountName = models.TextField()
