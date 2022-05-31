# -*- coding: utf-8 -*-
import os
import xlwt
import csv
import tempfile
import datetime
from tempfile import mktemp
from django.conf import settings
from django.http import HttpResponse
from django.template.loader import render_to_string


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
                writer.writerow([col.replace(' – ',  ' - ') for col in row])
        file = open(path, 'rb')
        content = file.read()
        file.close()
        super().__init__(content=content, content_type='application/csv')
        self['Content-Disposition'] = 'attachment; filename=Download.csv'


class FileResponse(HttpResponse):

    def __init__(self, file_path):
        extension = file_path.split('.')[-1]
        content_type = CONTENT_TYPES[extension]
        with open(file_path, 'r+b') as file:
            content = file.read()
        super().__init__(content=content, content_type=content_type)


class HtmlToPdfResponse(HttpResponse):

    def __init__(self, html, landscape=False):
        import pdfkit
        file_name = tempfile.mktemp('.pdf')
        if landscape:
            html = html.replace('logo_if_portrait', 'logo_if_landscape')
            html = html.replace('content="Portrait"', 'content="Landscape"')
        html = html.replace('/media', settings.MEDIA_ROOT)
        html = html.replace('/static', '{}/{}/static'.format(settings.BASE_DIR, settings.BASE_DIR.name))
        pdfkit.from_string(html, file_name)
        str_bytes = open(file_name, "rb").read()
        os.unlink(file_name)
        super().__init__(str_bytes, content_type='application/pdf')


class PdfReportResponse(HtmlToPdfResponse):
    def __init__(self, request, data, landscape=False, template='app/report.html'):
        data.update(
            today=datetime.date.today(), settings=settings
        )
        html = render_to_string([template], data, request=request)
        super().__init__(html, landscape=landscape)
