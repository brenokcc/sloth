from sloth.db import models, role, meta
from datetime import date

class Pessoa(models.Model):
    nome = models.CharField('Nome')

    def view(self):
        return self.value_set(
            'badges_renderers',
            'utils_renderers',
            'calendar_renderers',
            'map_renderers',
            'message_renderers',
            'photo_renderers',
            'document_renderers'
        )

    @meta('Badges')
    def badges_renderers(self):
        return self.value_set(('is_casado', 'get_situacao', 'get_profissao'))

    @meta('Casado', renderer='badges/boolean')
    def is_casado(self):
        return True

    @meta('Situação', renderer='badges/status')
    def get_situacao(self):
        return 'primary', 'Empregado'

    @meta('Profissão', renderer='badges/badge')
    def get_profissao(self):
        return '#800080', 'Analista de T.I.'

    @meta('Rico', renderer='badges/boolean')
    def is_rico(self):
        return None

    @meta('Utilitários')
    def utils_renderers(self):
        return self.value_set('get_progresso', 'get_qrcode', 'get_etapas')

    @meta('Progresso', renderer='utils/progress')
    def get_progresso(self):
        return 75

    @meta('QrCode', renderer='utils/qrcode')
    def get_qrcode(self):
        return 'https://google.com'

    @meta('Etapas', renderer='utils/steps')
    def get_etapas(self):
        return [
            ('Início', date(2022, 9, 4)),
            ('Etapa A', date(2022, 9, 7)),
            ('Etapa B', None),
            ('Fim', None),
        ]

    @meta('Calendário')
    def calendar_renderers(self):
        return self.value_set('get_programacao')

    @meta('Programação', renderer='calendar/events')
    def get_programacao(self):
        return [
            ('Inscrição', date(2022, 9, 4), date(2022, 9, 14)),
            ('Abertura', date(2022, 9, 18)),
            ('Enderramento', date(2022, 9, 24)),
        ]

    @meta('Mapas')
    def map_renderers(self):
        return self.value_set('get_mapa_rn', 'get_geolocalizacao')

    @meta('RN', renderer='maps/map')
    def get_mapa_rn(self):
        return []

    @meta('Geolozalização', renderer='maps/geolocation')
    def get_geolocalizacao(self):
        return '-5.8143205', '-35.2038451'

    @meta('Mensagens')
    def message_renderers(self):
        return self.value_set('get_mensagem_sucesso', 'get_mensagem_perigo')

    @meta('Sucesso', renderer='messages/success')
    def get_mensagem_sucesso(self):
        return 'O serviço está em operação.'

    @meta('Perigo', renderer='messages/danger')
    def get_mensagem_perigo(self):
        return 'O serviço está inativo.'

    @meta('Fotos')
    def photo_renderers(self):
        return self.value_set(('get_foto_normal', 'get_foto_redonda'), 'get_banner')

    @meta('Foto Normal', renderer='photos/photo')
    def get_foto_normal(self):
        return '/static/images/user.png'

    @meta('Foto Redonda', renderer='photos/round')
    def get_foto_redonda(self):
        return '/static/images/user.png'

    @meta('Banner', renderer='images/banner')
    def get_banner(self):
        return '/static/images/banner.png'

    @meta('Documentos')
    def document_renderers(self):
        return self.value_set('get_documento')

    @meta('Documento PDF', renderer='documents/document')
    def get_documento(self):
        return '/static/docs/documento.pdf'
