from django.http import HttpResponse
from .models import Tenant
from .threadlocal import set_current_tenant

class TenantMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        # ✅ Permitimos SIEMPRE el admin de tenants sin tenant (para no quedarte encerrado)
        if request.path.startswith("/admin/tenants/"):
            set_current_tenant(None)
            request.tenant = None
            return self.get_response(request)

        host = request.get_host().split(":")[0].lower()

        try:
            tenant = Tenant.objects.get(dominio=host, activo=True)
        except Tenant.DoesNotExist:
            set_current_tenant(None)
            request.tenant = None
            return HttpResponse(f"Tenant no encontrado. Host recibido: {host}", status=404)

        set_current_tenant(tenant)
        request.tenant = tenant

        response = self.get_response(request)

        set_current_tenant(None)
        return response