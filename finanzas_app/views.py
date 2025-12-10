from django.shortcuts import render

def dashboard(request):
    """
    Dashboard principal del módulo de Finanzas.
    De momento solo muestra un diseño estático tipo panel empresarial.
    Luego conectaremos los datos reales.
    """
    context = {
        "resumen": {
            "ventas_semanales": 15000,
            "ordenes_semanales": 45633,
            "visitantes_online": 95574,
        }
    }
    return render(request, 'finanzas_app/dashboard.html', context)
