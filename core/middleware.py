import uuid
from django.utils.deprecation import MiddlewareMixin


class RequestIDMiddleware(MiddlewareMixin):
    def process_request(self, request):
        request.request_id = str(uuid.uuid4())

    def process_response(self, request, response):
        # Add request_id to response headers
        if hasattr(request, 'request_id'):
            response['X-Request-ID'] = request.request_id
        
        # Add request_id to DRF response body data
        if hasattr(response, 'data') and hasattr(request, 'request_id'):
            # Check if data is mutable (dict)
            if isinstance(response.data, dict):
                response.data = {"request_id": request.request_id, **response.data}
                # Re-render the response to include the modified data
                response._is_rendered = False
                response.render()
        
        return response