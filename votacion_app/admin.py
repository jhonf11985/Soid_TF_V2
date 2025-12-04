from django.contrib import admin
from .models import Votacion, Candidato, Voto, Ronda


@admin.register(Votacion)
class VotacionAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "tipo", "estado", "fecha_inicio", "fecha_fin")
    search_fields = ("nombre",)
    list_filter = ("estado", "tipo")


@admin.register(Ronda)
class RondaAdmin(admin.ModelAdmin):
    list_display = ("id", "votacion", "numero", "nombre", "estado", "fecha_inicio", "fecha_fin")
    list_filter = ("votacion", "estado")
    search_fields = ("votacion__nombre", "nombre")


@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ("id", "nombre", "votacion")
    search_fields = ("nombre",)
    list_filter = ("votacion",)


@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    list_display = ("id", "votacion", "ronda", "miembro", "candidato")
    list_filter = ("votacion", "ronda", "candidato")
