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

    # the data being stored in the database, of any conversions are required they're stored here
    modelData = {}

    # check all fields fit their specific criteria

    # in case of spaces in credit card number
    data["CardNumber"] = data["CardNumber"].strip()
    # check correct length and card number formatting
    if len(data["CardNumber"]) < 8 or len(data["CardNumber"]) > 16 or not luhn.verify(data["CardNumber"]):
        return errorHandling(104, "CardNumber")

    # check made up of only numbers and is 3-4 characters long
    if not data["CVV"].isdigit() or len(data["CVV"]) not in (3,4):
        return errorHandling(104, "CVV")

    # check expiry is in date format
    try:
        modelData["Expiry"] = datetime.strptime(data["Expiry"], '%Y-%m-%d').date()
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
    modelData["PayeeBankSortCode"] = data["PayeeBankSortCode"].replace("-", "")
    if not modelData["PayeeBankSortCode"].isdigit() or len(modelData["PayeeBankSortCode"]) !=6:
        return errorHandling(104, "PayeeBankSortCode")

    # Check card-holder name isn't too long
    if len(data["RecipientName"]) > 80:
        return errorHandling(104, "RecipientName")

    # positive amounts only
    if data["Amount"] < 0:
        return errorHandling(104, "Amount")

    # check that the personal account of the payer exists
    personalData = PaymentDetails.objects.filter(cardNumber=data["CardNumber"],
                                           securityCode=data["CVV"]).values()

    # incorrect card number of CVV
    if len(personalData) != 1:
        return errorHandling(108)

    # incorrect expiry date
    if personalData[0]["expiryDate"].date() != modelData["Expiry"]:
        return errorHandling(108)



    # check that the payee exists with the correct bank details


    currencyData = {"CurrencyFrom": data["PayerCurrencyCode"], "CurrencyTo": data["PayeeCurrencyCode"],
                    "Date": str(date.today()), "Amount": data["Amount"]}
    currencyResponse = ConvertCurrency(currencyData)  # status, error code, amount

    # error has occurred when converting currency
    if currencyResponse["Status"] != 200:
        return errorHandling(201)

    # the card we receive is for the payer, the bank details are for the payee

    # else we now talk to PNS and get them to initiate the payment itself
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
    confirmedTransaction = Transaction()

    # if here then all was good
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
                    "CurrencyCode": int,
                    }

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # carry on as normal
    return HttpResponse("refundPayment")


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

    # carry on as normal
    return HttpResponse("initiate cancellation")


def ConvertCurrency(data):
    # post to currency converter API and get response
    response = requests.post('http://example.com', data=data)

    # this will be changed once their API is up and running
    # content = response.content

    content = {"Status": 200, "Error code": 123, "Amount": 120.00}


    return content


def RequestTransactionPNS(data):
    # post to currency converter API and get response
    response = requests.post('http://example.com', data=data)

    # this will be changed once their API is up and running
    # content = response.content

    content = {"StatusCode": 200, "TransactionUUID": 123, "Comment": 120.00}

    return content


@csrf_exempt
def RequestRefundPNS(request):
    # returns the data or error message and boolean indicating which that is
    data, methodStatus = checkMethod(request)
    print(data)
    # data contains error message if the body wasn't in the correct format
    if not methodStatus:
        return data

    correct_keys = {"TransactionUUID": str,
                    "Amount": float,
                    "CurrencyCode": int}

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # carry on as normal
    return HttpResponse("request refund PNS")
