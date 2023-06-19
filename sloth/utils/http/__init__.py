# -*- coding: utf-8 -*-
import os
import xlwt
import csv
import requests
import tempfile
import datetime
from tempfile import mktemp
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.template.loader import render_to_string


class ApiResponse(JsonResponse):
    def __init__(self, data, **kwargs):
        kwargs.update(safe=False, json_dumps_params={"ensure_ascii": False})
        super().__init__(data, **kwargs)
        self["Access-Control-Allow-Origin"] = "*"
        self["Access-Control-Allow-Headers"] = "*"
        self["X-Frame-Options"] = "SAMEORIGIN"


class XlsResponse(HttpResponse):
    def __init__(self, data):
        wb = xlwt.Workbook(encoding='iso8859-1')
        for title, rows in data:
            sheet = wb.add_sheet(str(title))
            for row_idx, row in enumerate(rows):
                for col_idx, label in enumerate(row):
                    sheet.write(row_idx, col_idx, label=label)
        path = mktemp()
        wb.save(path)
        file = open(path, 'rb')
        content = file.read()
        file.close()
        super().__init__(content=content, content_type='application/vnd.ms-excel')
        self['Content-Disposition'] = 'attachment; filename=Download.xls'


class CsvResponse(HttpResponse):
    def __init__(self, rows):
        path = mktemp()
        with open(path, 'w', encoding='iso8859-1') as output:
            writer = csv.writer(output)
            for row in rows:
                writer.writerow([str(col).replace(' – ',  ' - ') for col in row])
        file = open(path, 'rb')
        content = file.read()
        file.close()
        super().__init__(content=content, content_type='application/csv')
        self['Content-Disposition'] = 'attachment; filename=Download.csv'


class FileResponse(HttpResponse):
    CONTENT_TYPES = {
        'aac': 'audio/aac',
        'abw': 'application/x-abiword',
        'arc': 'application/octet-stream',
        'avi': 'video/x-msvideo',
        'bin': 'application/octet-stream',
        'bz': 'application/x-bzip',
        'bz2': 'application/x-bzip2',
        'csh': 'application/x-csh',
        'css': 'text/css',
        'csv': 'text/csv',
        'doc': 'application/msword',
        'epub': 'application/epub+zip',
        'gif': 'image/gif',
        'htm': 'text/html',
        'html': 'text/html',
        'ico': 'image/x-icon',
        'ics': 'text/calendar',
        'jar': 'application/java-archive',
        'jpeg': 'image/jpeg',
        'jpg': 'image/jpeg',
        'js': 'application/javascript',
        'json': 'application/json',
        'mid': 'audio/midi',
        'midi': 'audio/midi',
        'mpeg': 'video/mpeg',
        'oga': 'audio/ogg',
        'ogv': 'video/ogg',
        'ogx': 'application/ogg',
        'otf': 'font/otf',
        'png': 'image/png',
        'pdf': 'application/pdf',
        'ppt': 'application/vnd.ms-powerpoint',
        'rar': 'application/x-rar-compressed',
        'rtf': 'application/rtf',
        'sh': 'application/x-sh',
        'svg': 'image/svg+xml',
        'swf': 'application/x-shockwave-flash',
        'tar': 'application/x-tar',
        'tiff': 'image/tiff',
        'ts': 'application/typescript',
        'ttf': 'font/ttf',
        'vsd': 'application/vnd.visio',
        'wav': 'audio/x-wav',
        'weba': 'audio/webm',
        'webm': 'video/webm',
        'webp': 'image/webp',
        'woff': 'font/woff',
        'woff2': 'font/woff2',
        'xhtml': 'application/xhtml+xml',
        'xls': 'application/vnd.ms-excel',
        'xlsx': 'application/vnd.ms-excel',
        'xml': 'application/xml',
        'xul': 'application/vnd.mozilla.xul+xml',
        'zip': 'application/zip',
        '7z': 'application/x-7z-compressed'
    }

    def __init__(self, file_path):
        file_name = file_path.split('/')[-1]
        extension = file_name.split('.')[-1].lower()
        content_type = FileResponse.CONTENT_TYPES[extension]
        with open(file_path, 'r+b') as file:
            content = file.read()
        super().__init__(content=content, content_type=content_type)
        self['Content-Disposition'] = 'attachment; filename={}'.format(file_name)


class HtmlToPdfResponse(HttpResponse):

    def __init__(self, html, request, landscape=False):
        base_url = 'http://{}'.format(request.META['HTTP_HOST'])
        html = html.replace('/static/', '{}/static/'.format(base_url))
        html = html.replace('/media/', '{}/media/'.format(base_url))
        if getattr(settings, 'WEASYPRINT_HOST', None):
            url = '{}://{}:{}'.format(settings.WEASYPRINT_PROTOCOL, settings.WEASYPRINT_HOST, settings.WEASYPRINT_PORT)
            data = requests.post(url, html.encode()).content
        else:
            from weasyprint import HTML
            tmp = tempfile.NamedTemporaryFile(mode='w+b')
            HTML(string=html, base_url=base_url).write_pdf(tmp.name)
            data = tmp.read()
        super().__init__(data, content_type='application/pdf')


class PdfReportResponse(HtmlToPdfResponse):
    def __init__(self, request, content, landscape=False, template='dashboard/report.html'):
        context = dict(today=datetime.date.today(), title='Relatório', icon='/static/images/logo.png', content=content)
        html = render_to_string([template], context, request=request)
        super().__init__(html, request, landscape=landscape)
