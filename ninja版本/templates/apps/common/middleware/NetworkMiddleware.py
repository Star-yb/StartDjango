class NetworkRequestMiddleware:
    """
    网络请求中间件
    
    用于记录请求信息
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        # 获取请求IP
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0]
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        # 将IP信息添加到请求对象中
        request.client_ip = ip
        
        # 记录请求信息
        # 此处可以添加日志记录等功能
        
        response = self.get_response(request)
        return response
