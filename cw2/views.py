import json

from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from cw2.error_handling import errorHandling, checkBody, checkMethod


# if it's a guest put the person id as 0 and process transaction as usual
#

@csrf_exempt
def initiatePayment(request):
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
                    "PayerCurrencyCode": int,
                    "PayeeCurrencyCode": int
                    }

    # stores None if formatted correctly, else returns an error message
    bodyStatus = checkBody(data, correct_keys)
    if bodyStatus is not None:
        return bodyStatus

    # carry on as normal
    return HttpResponse("Hello")

