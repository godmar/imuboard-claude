"""Tiny dependency-free .xlsx writer (one sheet, strings and numbers).

Uses a shared-strings table like the JLCPCB sample files do.
"""
import zipfile
from xml.sax.saxutils import escape

_CT = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
       '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
       '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
       '<Default Extension="xml" ContentType="application/xml"/>'
       '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
       '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
       '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
       '<Override PartName="/xl/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.styles+xml"/>'
       '</Types>')
_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
         '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
         '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>'
         '</Relationships>')
_WB = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
       '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
       'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
       '<sheets><sheet name="Sheet1" sheetId="1" r:id="rId1"/></sheets></workbook>')
_WB_RELS = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
            '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>'
            '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/sharedStrings" Target="sharedStrings.xml"/>'
            '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles" Target="styles.xml"/>'
            '</Relationships>')
_STYLES = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<styleSheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
           '<fonts count="1"><font><sz val="11"/><name val="Calibri"/></font></fonts>'
           '<fills count="2"><fill><patternFill patternType="none"/></fill>'
           '<fill><patternFill patternType="gray125"/></fill></fills>'
           '<borders count="1"><border><left/><right/><top/><bottom/><diagonal/></border></borders>'
           '<cellStyleXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0"/></cellStyleXfs>'
           '<cellXfs count="1"><xf numFmtId="0" fontId="0" fillId="0" borderId="0" xfId="0"/></cellXfs>'
           '</styleSheet>')


def _col(i):
    s = ''
    i += 1
    while i:
        i, r = divmod(i - 1, 26)
        s = chr(65 + r) + s
    return s


def write(path, rows):
    strings, index = [], {}
    body = []
    for ri, row in enumerate(rows, 1):
        cells = []
        for ci, v in enumerate(row):
            ref = '%s%d' % (_col(ci), ri)
            if isinstance(v, (int, float)):
                cells.append('<c r="%s"><v>%s</v></c>' % (ref, '%g' % v))
            else:
                v = str(v)
                if v not in index:
                    index[v] = len(strings)
                    strings.append(v)
                cells.append('<c r="%s" t="s"><v>%d</v></c>' % (ref, index[v]))
        body.append('<row r="%d">%s</row>' % (ri, ''.join(cells)))
    ncols = max(len(r) for r in rows)
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<dimension ref="A1:%s%d"/><sheetData>%s</sheetData></worksheet>'
             % (_col(ncols - 1), len(rows), ''.join(body)))
    sst = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
           '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" count="%d" uniqueCount="%d">%s</sst>'
           % (len(strings), len(strings),
              ''.join('<si><t xml:space="preserve">%s</t></si>' % escape(s) for s in strings)))
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('[Content_Types].xml', _CT)
        z.writestr('_rels/.rels', _RELS)
        z.writestr('xl/workbook.xml', _WB)
        z.writestr('xl/_rels/workbook.xml.rels', _WB_RELS)
        z.writestr('xl/styles.xml', _STYLES)
        z.writestr('xl/sharedStrings.xml', sst)
        z.writestr('xl/worksheets/sheet1.xml', sheet)
