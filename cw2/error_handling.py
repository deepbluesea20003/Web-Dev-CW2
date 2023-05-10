import json

from django.http import HttpResponse, JsonResponse


# gives formatted error messages
def errorHandling(code, body=None):
    """

    :param code: an integer code corresponding to the error message
    :param body: a list of all other strings required for error message, defaults to None
    :return: an HTTP formatted error message
    """
    codes = {
        100: 'Request body empty.',
        101: 'Request body in incorrect format',
        102: 'Could not find field "{}".',
        103: 'Field "{}" is a {}, when {} was expected.',
        104: 'Invalid Field "{}"',
        105: 'Request type is not POST',
        106: 'Payer card details could not be found',
        107: 'Payee bank account details could not be found',
        201: 'An error occurred with currency conversion.',
        301: 'An error occurred with contacting the Payment Network Service.',
        401: 'Could not access database.',
        402: 'Transaction with ID {} could not be located.',
        403: 'Refund could not complete.',
        404: 'Original transaction already refunded or cancelled.'
    }

    if code == 102 or code == 104:
        code_body = codes[code].format(body)
    elif code == 103:
        code_body = codes[code].format(body[0], type(body[1]).__name__, body[2].__name__)
        print(code_body)
    else:
        code_body = codes[code]
    # this needs changing to be status, error code, comment
    return JsonResponse({"ErrorCode": code, "Comment": code_body}, status=400)


# check method is correct and body isn't null
def checkMethod(request):
    """

    :param request: the result sent to the endpoint
    :return: the body if it exists, or returns error code and then boolean indicating which it is
    """

    if request.method != "POST":
        return errorHandling(105), False
    else:
        try:
            data = json.loads(request.body)
            # if data exists then return it
            return data, True
        except Exception:  # body is in bad format
            return errorHandling(101), False


# Checks that the fields passed to the function are correct and aren't none
def checkBody(data, required):
    """

    :param data: the data passed to the endpoint
    :param required: the fields which are required for the endpoint
    :return: None if all fields are there and none are not null, else returns an error message
    """

    # check body isn't empty
    if len(data) == 0:
        return errorHandling(100)

    # check no fields are missing and that all field are the correct data type
    for field in required:
        if field not in data:
            return errorHandling(102, field)
        if not isinstance(data[field], required[field]):
            return errorHandling(103, [field, data[field], required[field]])

    # check for no addition fields in the body
    newFields = set(required).symmetric_difference(set(data))
    if len(newFields) != 0:
        return errorHandling(104, list(newFields)[0])

    # if here then initial validation has been passed
    return None
