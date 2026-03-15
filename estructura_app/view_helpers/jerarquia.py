from estructura_app.models import Unidad


def get_unidades_con_nivel(tenant, queryset=None):
    """
    Devuelve las unidades ordenadas jerárquicamente con su nivel de profundidad.
    """
    if queryset is None:
        queryset = Unidad.objects.filter(tenant=tenant, activa=True, visible=True)

    unidades = list(queryset.select_related("tipo", "categoria", "padre"))

    def calcular_nivel(unidad, cache=None):
        if cache is None:
            cache = {}

        if unidad.id in cache:
            return cache[unidad.id]

        if unidad.padre is None:
            nivel = 0
        else:
            nivel = calcular_nivel(unidad.padre, cache) + 1

        cache[unidad.id] = nivel
        return nivel

    for unidad in unidades:
        unidad.nivel = calcular_nivel(unidad)

    def ordenar_jerarquico(unidades_lista):
        hijos_de = {}
        raices = []

        for u in unidades_lista:
            padre_id = u.padre_id if u.padre else None
            if padre_id is None:
                raices.append(u)
            else:
                hijos_de.setdefault(padre_id, []).append(u)

        resultado = []

        def agregar_con_hijos(unidad):
            resultado.append(unidad)
            hijos = hijos_de.get(unidad.id, [])
            for hijo in sorted(hijos, key=lambda x: (x.orden, x.nombre)):
                agregar_con_hijos(hijo)

        for raiz in sorted(raices, key=lambda x: (x.orden, x.nombre)):
            agregar_con_hijos(raiz)

        return resultado

    return ordenar_jerarquico(unidades)