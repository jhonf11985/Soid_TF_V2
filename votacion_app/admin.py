from django.contrib import admin
from .models import Votacion, Candidato, Voto  # ajusta los nombres reales

@admin.register(Votacion)
class VotacionAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'tipo', 'estado', 'fecha_inicio', 'fecha_fin')
    search_fields = ('nombre',)
    list_filter = ('estado', 'tipo')

@admin.register(Candidato)
class CandidatoAdmin(admin.ModelAdmin):
    list_display = ('id', 'nombre', 'votacion')
    search_fields = ('nombre',)
    list_filter = ('votacion',)

@admin.register(Voto)
class VotoAdmin(admin.ModelAdmin):
    # 👉 SOLO usa campos que existan en tu modelo Voto
    list_display = ('id', 'votacion', 'miembro', 'candidato')
    list_filter = ('votacion', 'candidato')
