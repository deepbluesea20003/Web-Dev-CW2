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
    transactionStatus = models.TextField()


class PaymentDetails(models.Model):
    paymentId = models.IntegerField(primary_key=True)
    cardNumber = models.TextField()
    securityCode = models.TextField()
    expiryDate = models.DateTimeField()


class BankDetails(models.Model):
    accountNumber = models.IntegerField(primary_key=True)
    sortCode = models.TextField()
    accountName = models.TextField()


# PAYMENT NETWORK SERVICE

class Merchant(models.Model):
    id = models.IntegerField(primary_key=True)
    acqBankId = models.ForeignKey('Bank', on_delete=models.CASCADE)


class PNSTransaction(models.Model):
    id = models.IntegerField(primary_key=True)
    merchantId = models.ForeignKey('Merchant', on_delete=models.CASCADE)
    cardId = models.ForeignKey('Card', on_delete=models.CASCADE)
    auth = models.BooleanField()
    fraudLikelihood = models.IntegerField()


class Bank(models.Model):
    id = models.IntegerField(primary_key=True)
    bankName = models.TextField()
    authPt = models.TextField()


class Address(models.Model):
    id = models.IntegerField(primary_key=True)
    lineOne = models.TextField()
    lineTwo = models.TextField()
    city = models.TextField()
    area = models.TextField()
    postcode = models.TextField(max_length=8)


class Card(models.Model):
    id = models.IntegerField(primary_key=True)
    issueBankId = models.ForeignKey('Bank', on_delete=models.CASCADE)
    addressId = models.ForeignKey("Address", on_delete=models.CASCADE)
    cardNumber = models.IntegerField()
    expiryDate = models.DateField()
    holderName = models.TextField()
    serviceCode = models.IntegerField
