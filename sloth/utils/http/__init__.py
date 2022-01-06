# -*- coding: utf-8 -*-
import xlwt
import csv
from tempfile import mktemp
from django.http import HttpResponse


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
