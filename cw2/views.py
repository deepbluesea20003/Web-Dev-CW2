import json
from datetime import datetime, date

from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from cw2.error_handling import errorHandling, checkBody, checkMethod
import requests


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
                    "CVV": int,
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

    # more validation here
    currencyData = {"CurrencyFrom": data["PayerCurrencyCode"], "CurrencyTo": data["PayeeCurrencyCode"],
                    "Date": str(date.today()), "Amount": data["Amount"]}
    currencyResponse = ConvertCurrency(currencyData)  # status, error code, amount

    # error has occurred when converting currency
    if currencyResponse["Status"] != 400:
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
    if transactionResponse["Status"] != 400:
        return errorHandling(301)

    # do I now log the transaction?

    # if here then all was good
    responseData = {"TransactionUUID": transactionResponse["TransactionUUID"],
                    "ErrorCode": None,
                    "Comment": "Success"
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
