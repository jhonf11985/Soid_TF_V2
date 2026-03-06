from django.shortcuts import render

# Create your views here.
# ia_app/views.py
import json
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required

from .services.nl_query import run_natural_query


def _get_tenant_from_request(request):
    """
    TenantMiddleware normalmente coloca el tenant en request.tenant
    """
    tenant = getattr(request, "tenant", None)
    return tenant


@require_POST
@login_required
def nl_query(request):
    tenant = _get_tenant_from_request(request)
    if tenant is None:
        return JsonResponse(
            {"ok": False, "intent": "tenant_missing", "message": "Tenant no encontrado en la petición.", "data": {}},
            status=400,
        )

    try:
        payload = json.loads(request.body.decode("utf-8") or "{}")
    except json.JSONDecodeError:
        payload = {}

    text = (payload.get("text") or "").strip()
    result = run_natural_query(tenant=tenant, user=request.user, text=text)

    return JsonResponse(
        {"ok": result.ok, "intent": result.intent, "message": result.message, "data": result.data},
        status=200 if result.ok else 400,
    )