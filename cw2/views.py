import re
from datetime import date, datetime

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cw2.error_handling import errorHandling, checkBody, checkMethod
import requests
import luhn
from cw2.models import Transaction, PersonalAccount, BusinessAccount, PaymentDetails, BankDetails


# if it's a guest put the person id as 0 and process transaction as usual
#

@csrf_exempt
def InitiatePayment(request):
    # returns the data or error message and boolean indicating which that is
    data, methodStatus = checkMethod(request)
    print(data)
    # data contains error message if the body wasn't in the correct format
    if not methodStatus:
        return data

    correct_keys = {"CardNumber": str,
                    "CVV": str,
                    "Expiry": str,
                    "CardHolderName": str,
                    "CardHolderAddress": str,
                    "Email": str,
                    "PayeeBankAccNum": str,
                    "PayeeBankSortCode": str,
                    "RecipientName": str,
                    "Amount": float,
                    "PayerCurrencyCode": str,
                    "PayeeCurrencyCode": str
                    }

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # check all fields fit their specific criteria

    # in case of spaces in credit card number
    data["CardNumber"] = data["CardNumber"].strip()
    # check correct length and card number formatting
    if len(data["CardNumber"]) < 8 or len(data["CardNumber"]) > 16 or not luhn.verify(data["CardNumber"]):
        return errorHandling(104, "CardNumber")

    # check made up of only numbers and is 3-4 characters long
    if not data["CVV"].isdigit() or len(data["CVV"]) not in (3, 4):
        return errorHandling(104, "CVV")

    # check expiry is in date format
    try:
        data["Expiry"] = datetime.strptime(data["Expiry"], '%Y-%m-%d').date()
    except:
        return errorHandling(104, "Expiry")

    # Check card-holder name isn't too long
    if len(data["CardHolderName"]) > 80:
        return errorHandling(104, "CardHolderName")

    # Check email is valid syntactically
    emailRegex = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
    if not re.fullmatch(emailRegex, data["Email"]):
        return errorHandling(104, "Email")

    if not data["PayeeBankAccNum"].isdigit() or len(data["PayeeBankAccNum"]) > 8 or len(data["PayeeBankAccNum"]) < 1:
        return errorHandling(104, "PayeeBankAccNum")

    # remove any - separators and ensure length is 6
    data["PayeeBankSortCode"] = data["PayeeBankSortCode"].replace("-", "")
    if not data["PayeeBankSortCode"].isdigit() or len(data["PayeeBankSortCode"]) != 6:
        return errorHandling(104, "PayeeBankSortCode")

    # Check card-holder name isn't too long
    if len(data["RecipientName"]) > 80:
        return errorHandling(104, "RecipientName")

    # positive amounts only
    if data["Amount"] <= 0.00:
        return errorHandling(104, "Amount")

    # check that the payment account of the payer exists
    allPaymentData = PaymentDetails.objects.filter(cardNumber=data["CardNumber"],
                                                   securityCode=data["CVV"]).values()
    # incorrect card number of CVV
    if len(allPaymentData) != 1:
        return errorHandling(106)

    # queryset can be condensed
    paymentData = allPaymentData[0]

    # incorrect expiry date
    if paymentData["expiryDate"].date() != data["Expiry"]:
        return errorHandling(106)

    # check that the payee details provided match those linked to the bank account
    allPayerData = PersonalAccount.objects.filter(paymentDetails=paymentData["paymentId"]).all()

    # personal account does not exist
    if len(allPayerData) != 1:
        return errorHandling(108)

    # queryset can be condensed
    payerData = allPayerData[0]

    # make sure all other fields for personal accounts match
    if payerData.fullName != data["CardHolderName"] or payerData.email != data["Email"]:
        return errorHandling(108)

    # make sure that the payee details match those of a registered business account and
    # that the corresponding bank details also match

    allBankData = BankDetails.objects.filter(accountNumber=data["PayeeBankAccNum"],
                                             sortCode=data["PayeeBankSortCode"],
                                             accountName=data["RecipientName"]).all()
    # if no bank details found
    if len(allBankData) != 1:
        return errorHandling(107)

    # see if bank corresponds to business account
    allBusinessData = BusinessAccount.objects.filter(bankDetails=allBankData[0].accountNumber).all()

    # if no corresponding account
    if len(allBusinessData) != 1:
        return errorHandling(109)

    # trim query
    businessData = allBusinessData[0]

    # if other details don't also match
    if businessData.businessName != data["RecipientName"]:
        return errorHandling(109)

    currencyData = {"CurrencyFrom": data["PayerCurrencyCode"], "CurrencyTo": data["PayeeCurrencyCode"],
                    "Date": str(date.today()), "Amount": data["Amount"]}
    currencyResponse = ConvertCurrency(currencyData)  # status, error code, amount

    # error has occurred when converting currency
    if currencyResponse["Status"] != 200:
        return errorHandling(201,body=currencyResponse)

    # we now talk to PNS and get them to initiate the payment itself
    paymentData = {"CardNumber": data["CardNumber"],
                   "Expiry": data["Expiry"],
                   "CVV": data["CVV"],
                   "HolderName": data["CardHolderName"],
                   "BillingAddress": data["CardHolderAddress"],
                   "Amount": currencyResponse["Amount"],
                   "CurrencyCode": currencyData["CurrencyTo"],
                   "AccountNumber": data["PayeeBankAccNum"],
                   "Sort-Code": data["PayeeBankSortCode"],
                   }

    transactionResponse = RequestTransactionPNS(paymentData)
    # error has occurred when doing transaction
    if transactionResponse["StatusCode"] != 200:
        return errorHandling(301)

    # store the transaction in the database
    try:
        confirmedTransaction = Transaction()
        confirmedTransaction.id = transactionResponse["TransactionUUID"]
        confirmedTransaction.payer = payerData
        confirmedTransaction.payee = businessData
        confirmedTransaction.amount = currencyResponse["Amount"]
        confirmedTransaction.currency = data["PayeeCurrencyCode"]
        confirmedTransaction.date = datetime.now()
        confirmedTransaction.transactionStatus = "Complete"
        confirmedTransaction.save()
    except Exception as e:
        return errorHandling(401, str(e))

    # returning positive response
    responseData = {"TransactionUUID": transactionResponse["TransactionUUID"],
                    "ErrorCode": None,
                    "Comment": "Transaction processed successfully"
                    }

    return JsonResponse(responseData, status=200)


@csrf_exempt
def InitiateRefund(request):
    # returns the data or error message and boolean indicating which that is
    data, methodStatus = checkMethod(request)
    print(data)
    # data contains error message if the body wasn't in the correct format
    if not methodStatus:
        return data

    correct_keys = {"TransactionUUID": str,
                    "Amount": float,
                    "CurrencyCode": str,
                    }

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # amount needs to be more than zero
    if data["Amount"] <= 0.00:
        return errorHandling(104, "Amount")

    # check transaction exists
    queriedTransactions = Transaction.objects.filter(id=data["TransactionUUID"]).all()

    # if no corresponding account
    if len(queriedTransactions) != 1:
        return errorHandling(402, data["TransactionUUID"])

    oldTransaction = queriedTransactions[0]
    if oldTransaction.transactionStatus != "Complete":
        return errorHandling(404)

    currencyData = {"CurrencyFrom": data["CurrencyCode"], "CurrencyTo": oldTransaction.currency,
                    "Date": str(date.today()), "Amount": oldTransaction.amount}
    currencyResponse = ConvertCurrency(currencyData)  # status, error code, amount

    # error has occurred when converting currency
    if currencyResponse["Status"] != 200:
        return errorHandling(201)

    # we now talk to PNS and get them to initiate the payment itself
    paymentData = {"TransactionUUID": data["TransactionUUID"],
                   "Amount": currencyResponse["Amount"],
                   "CurrencyCode": data["CurrencyCode"],
                   }

    transactionResponse = RequestRefundPNS(paymentData)
    # error has occurred when doing transaction
    if transactionResponse["StatusCode"] != 200:
        return errorHandling(403)

    # store the transaction in the database
    try:
        refundedTransaction = Transaction()
        refundedTransaction.id = None
        refundedTransaction.payer = oldTransaction.payer
        refundedTransaction.payee = oldTransaction.payee
        refundedTransaction.amount = oldTransaction.amount
        refundedTransaction.currency = oldTransaction.currency
        refundedTransaction.date = datetime.now()
        refundedTransaction.transactionStatus = "Refund"
        refundedTransaction.save()
    except Exception as e:
        return errorHandling(401, str(e))

    # returning positive response
    responseData = {"ErrorCode": None,
                    "Comment": "Transaction refunded successfully"
                    }

    return JsonResponse(responseData, status=200)


@csrf_exempt
def InitiateCancellation(request):
    # returns the data or error message and boolean indicating which that is
    data, methodStatus = checkMethod(request)
    print(data)
    # data contains error message if the body wasn't in the correct format
    if not methodStatus:
        return data

    correct_keys = {"TransactionUUID": str}

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # check transaction exists
    queriedTransactions = Transaction.objects.filter(id=data["TransactionUUID"]).all()

    # if no corresponding account
    if len(queriedTransactions) != 1:
        return errorHandling(402, data["TransactionUUID"])

    oldTransaction = queriedTransactions[0]
    if oldTransaction.transactionStatus != "Complete":
        return errorHandling(404)

    try:
        oldTransaction.transactionStatus = "Cancelled"
        oldTransaction.save()
    except Exception as e:
        return errorHandling(401, str(e))

    # returning positive response
    responseData = {"ErrorCode": None,
                    "Comment": "Transaction cancelled successfully"
                    }

    return JsonResponse(responseData, status=200)


def ConvertCurrency(data):
    # post to currency converter API and get response
    response = requests.post('http://example.com', data=data)

    # this will be changed once their API is up and running
    # content = response.content

    # if success, this will be passed to us
    content = {"Status": 200, "Error code": None, "Amount": data["Amount"]}

    return content


def RequestTransactionPNS(data):
    # post to currency converter API and get response
    response = requests.post('http://example.com', data=data)

    # this will be changed once their API is up and running
    # content = response.content

    content = {"StatusCode": 200, "TransactionUUID": 123, "Comment": 120.00}

    return content

def RequestRefundPNS(data):
    # post to currency converter API and get response
    response = requests.post('http://example.com', data=data)

    # this will be changed once their API is up and running
    # content = response.content

    content = {"StatusCode": 200, "Comment": 120.00}

    return content

