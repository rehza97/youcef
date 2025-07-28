from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
import json


@csrf_exempt
@require_http_methods(["GET", "POST", "OPTIONS"])
def test_cors_view(request):
    """Simple view to test CORS"""

    # Handle preflight OPTIONS request
    if request.method == 'OPTIONS':
        response = JsonResponse({'message': 'CORS preflight successful'})
    elif request.method == 'GET':
        response = JsonResponse({
            'message': 'CORS GET successful',
            'origin': request.META.get('HTTP_ORIGIN', 'No origin'),
            'method': request.method
        })
    elif request.method == 'POST':
        try:
            data = json.loads(request.body) if request.body else {}
        except json.JSONDecodeError:
            data = {}

        response = JsonResponse({
            'message': 'CORS POST successful',
            'origin': request.META.get('HTTP_ORIGIN', 'No origin'),
            'method': request.method,
            'data': data
        })

    # Manually add CORS headers
    origin = request.META.get('HTTP_ORIGIN')
    if origin:
        response['Access-Control-Allow-Origin'] = origin
    else:
        response['Access-Control-Allow-Origin'] = '*'

    response['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS'
    response['Access-Control-Allow-Headers'] = 'Content-Type, Authorization, Origin'
    response['Access-Control-Allow-Credentials'] = 'true'

    return response
