#!/usr/bin/env python

"""Performs simple text formatting on tabular data to produce data
files, readable tables, or LaTeX tables.
Author: Jesse Hatfield"""

import argparse
import pickle
import sys
from math import isnan
from operator import itemgetter

class Field:
    def __init__(self, fieldID, fieldName=None, align=None, type=None,
            precision=None):
        """Create a Field.
        @param fieldID  Used to access the Field (required).
        @param  fieldName   Displayed name (defaults to fieldID).
        @param  align  Determines alignment: <, >, or ^.
        @param  type  Determines how to format values for printing.
                      (int, float, percent, str)
        """
        self.id = fieldID
        self.name = self.id
        self.align = align
        self.format = format
        self.type = type
        self.precision = precision
        if self.align is None and self.type is not None:
            #By default, right-justify numbers.
            if self.type in ('int', 'float', 'percent'):
                self.align = '>'
        if fieldName is not None:
            self.name = fieldName

    def formatData(self, value):
        """Formats a value of the field for printing as data."""
        if value is None:
            if self.type in ('int', 'float', 'percent', 'precise'):
                return 'NaN'
            else:
                return '{0}'.format(value)
        if self.type == 'precise':
            self.precision = 4
            self.type = 'float'
        formatstr = '{0!s}'
        if self.type == 'int':
            value = int(value)
            formatstr = '{0:d}'
        elif self.type == 'float':
            value = float(value)
            if self.precision is None:
                formatstr = '{0:.4f}'
            else:
                formatstr = '{{0:.{0}f}}'.format(self.precision)
        elif self.type == 'percent':
            value = float(value)
            if self.precision is None:
                formatstr = '{0:.6f}'
            else:
                formatstr = '{{0:.{0}f}}'.format(self.precision)
        return formatstr.format(value)

    def formatText(self, value):
        """Formats a value of the field for printing as readable text."""
        if value is None:
            return '{0}'.format(value)
        if self.type == 'precise':
            self.precision = 4
            self.type = 'float'
        formatstr = '{0!s}'
        if self.type == 'int':
            value = int(value)
            formatstr = '{0:d}'
        elif self.type == 'float':
            value = float(value)
            if isnan(value):
                return '---'
            if self.precision is None:
                formatstr = '{0:.2f}'
            else:
                formatstr = '{{0:.{0}f}}'.format(self.precision)
        elif self.type == 'percent':
            value = 100 * float(value)
            if isnan(value):
                return '---'
            if self.precision is None:
                formatstr = '{0:.2f}%'
            else:
                formatstr = '{{0:.{0}f}}%'.format(self.precision)
        return formatstr.format(value)

class Table:
    def printLatex(self, width='9in', boldFirst=False, vrule=False, hrule=False,
            vborder=False, booktabs=False, indent='.25in', size='large',
            stream=sys.stdout):
        """Print the data as a LaTeX table.
        @param  width       The width of the table, default '9in'.
        @param  boldFirst   Bold the first value of each row, default False.
        @param  vrule       Add vertical lines in the table, default False.
        @param  hrule       Add horizontal lines in the table, default False.
        @param  vborder     Add vertical lines on the sides, default False.
        @param  booktabs    Book-style tabes (no vertical lines,
                            different horizontal lines in different
                            places), default False.
        @param  indent      Amount of whitespace to add for each level
                            of indentation.
                            different horizontal lines in different
                            places), default False.
        @param  stream  Output stream to write to (default is stdout).
        """
        def escape(string):
            string = string.replace('%', '\\%')
            string = string.replace('#', '\\#')
            string = string.replace('&', '\\&')
            return string
        vr = ''
        hr = ('', '\hline', '', '')
        border = ''
        if vrule:
            vr = '|'
        if vborder:
            border = '|'
        if booktabs:
            vr = ''
            border = ''
            if hrule:
                hr = ('\\toprule', '\midrule', '\midrule', '\\bottomrule')
            else:
                hr = ('\\toprule', '\midrule', '', '\\bottomrule')
        elif hrule:
            hr = ('\hline', '\hline', '\hline', '\hline')

        fieldNames = [ escape(field.name) for field in self.fields ]
        fieldIDs = [ field.id for field in self.fields ]
        stream.write("\documentclass[12pt]{article}\n")
        stream.write("\pagestyle{empty}\n")
        stream.write("\\usepackage{array}\n")
        stream.write("\\usepackage{xcolor}\n")
        stream.write("\\usepackage{tabularx}\n")
        stream.write("\\usepackage{booktabs}\n")
        stream.write("\\usepackage[top=0in,bottom=0in,left=0in,right=0in]{geometry}\n")
        stream.write("\geometry{papersize={12in,35in}}\n")
        stream.write("\\begin{document}\n")
        stream.write("    {{\{0}{{\sffamily\n".format(size))
        stream.write("    \\begin{{tabularx}}{{{0}}}\n".format(width))
        spec = '{{{0}'.format(border)
        colspecs = []
        for field in self.fields:
            fieldID = field.id
            align = 'l'
            if field.align == '<':
                align = 'l'
            elif field.align == '>':
                align = 'c'
            elif field.align == '^':
                align = 'c'
            colspecs.append(align)
        colspecs[0] = 'X'
        spec += self.formatList(colspecs, prefix=' ', between=vr)
        spec += ' {0}}}'.format(border)
        stream.write("        " + spec + '\n')
        if hr[0]:
            stream.write("        {0}\n".format(hr[0]))
        header = self.formatList(fieldNames, prefix='\\textbf{', suffix='}', between=' & ')
        stream.write("        " + header + '\n')
        stream.write("        \\tabularnewline\n")
        if hr[1]:
            stream.write("        {0}\n".format(hr[1]))
        for i in range(len(self.data)):
            data = self.data[i]
            values = [ escape(field.formatText(data[field.id])) for field in self.fields ]
            if boldFirst:
                values[0] = '\\textbf{' + values[0] + '}'
            if data['_level'] > 0:
                values = [ '\\textit{' + val + '}' for val in values ]
            for j in range(data['_level']):
                values[0] = '\hspace{' + indent + '}' + values[0]
            if i > 0 and hr[2]:
                stream.write("        {0} \n".format(hr[2]))
            stream.write("        " + ' & '.join(values) + "\n")
            stream.write("        \\tabularnewline\n")
        if hr[3]:
            stream.write("        {0}\n".format(hr[3]))
        stream.write("    \end{tabularx}\n")
        stream.write("    }}\n")
        stream.write("\end{document}\n")

    def printDelim(self, delim='\t', stream=sys.stdout):
        """Print table with fields delimited by a given string (defaults to
        tab). Useful as input to some data or text processing
        programs (cut, sort, various plotting methods, etc.).
        @param  stream  Output stream to write to (default is stdout).
        """
        escape = '\\' + delim
        fieldNames = [ field.name.replace(delim, escape) for field in self.fields ]
        fieldIDs = [ field.id for field in self.fields ]
        if self.title:
            stream.write(self.title.replace(delim, escape) + "\n")
        stream.write(self.formatList(fieldNames, between=delim) + "\n")
        for data in self.data:
            strings = [ field.formatData(data[field.id]) for field in self.fields ]
            for i in range(data['_level']):
                strings[0] = '--' + strings[0]
            values = [ string.replace(delim, escape) for string in strings ]
            stream.write(self.formatList(values, between=delim) + "\n")

    def printTable(self, vertical='|', horizontal='-', corner='+',
            padding=' ', align='<', limit=None, stream=sys.stdout):
        """Print as an ASCII table aligned for human viewing.
        @param  vertical  Makes up vertical lines (default '|').
        @param  horizontal  Makes up horizontal lines (default '-').
        @param  corner  Intersection of horizontal and vertical lines (default '+').
        @param  padding Displayed between vertical line and value (default ' '). 
        @param  align   Determines alignment of values: '<', '>', or '^'.
                        Overriden by fields' alignments.
        @param  limit   Only print the top X records.
        @param  stream  Output stream to write to (default is stdout).
        Corner and vertical should be the same width.
        Horizontal should be one character wide.
        """
        sizes = {}
        formatstr = {}
        hline = None
        for field in self.fields:
            values = []
            for data in self.data:
                val = data[field.id]
                val = field.formatText(val)
                for i in range(0, data['_level']):
                    val = '--' + val
                values.append(val)
            lengths = [ len(val) for val in values ]
            lengths.append(len(field.name))
            sizes[field.id] = max(lengths)
            if field.align:
                align = field.align
            formatstr[field.id] = '{{0:{0}{1}}}'.format(align, sizes[field.id])
        if horizontal:
            items = [ horizontal * int(sizes[field.id] / len(horizontal)) for field in self.fields ]
            hpad = horizontal * int(len(padding)/len(horizontal))
            hline = self.formatList(items, begin=corner, end=corner,
                    between=corner, prefix=hpad, suffix=hpad)
        if self.title:
            stream.write(self.title)
            stream.write('\n')
        if hline:
            stream.write(hline)
            stream.write('\n')
        names = [ formatstr[field.id].format(field.name) for field in self.fields ]
        stream.write(self.formatList(names, begin=vertical, end=vertical,
                between=vertical, prefix=padding, suffix=padding))
        stream.write('\n')
        if hline:
            stream.write(hline)
            stream.write('\n')
        count = 0
        for data in self.data:
            values = []
            for i in range(len(self.fields)):
                field = self.fields[i]
                val = data[field.id]
                val = field.formatText(val)
                if i == 0:
                    for j in range(0, data['_level']):
                        val = '--' + val
                val = formatstr[field.id].format(val)
                values.append(val)
            stream.write(self.formatList(values, begin=vertical, end=vertical,
                    between=vertical, prefix=padding, suffix=padding))
            stream.write('\n')
            count += 1
            if limit and count >= limit:
                break
        if hline:
            stream.write(hline)
            stream.write('\n')

    def __init__(self):
        self.title = None
        self.data = []
        self.fields = []

    def addField(self, field):
        """Add a Field (column)."""
        self.fields.append(field)

    def addRecordLevel(self, level, *args):
        """Add a record (tuple, row, etc.), where the first argument is
        the level (0 is top-level), and each argument afterward is a
        field value (in order)."""
        data = { '_level': level }
        for i in range(min(len(self.fields), len(args))):
            data[self.fields[i].id] = args[i]
        self.data.append(data)

    def addRecord(self, *args):
        """Add a record (tuple, row, etc.), where each argument is a
        field value (in order). Sets _level to 0 (top-level)."""
        self.addRecordLevel(0, *args)

    def setTitle(self, string):
        """Add a title."""
        self.title = string

    def formatHeader(self, begin='', end='', between='', prefix='', suffix=''):
        items = [ prefix + field.name + suffix for field in self.fields ]
        header = begin + between.join(items) + end
        return header

    def formatList(self, data, begin='', end='', between='', prefix='', suffix=''):
        items = [ prefix + item + suffix for item in data ]
        line = begin + between.join(items) + end
        return line

    def sortKey(self, *args, **kwargs):
        self.data.sort(key=itemgetter(*args), **kwargs)

    def sortIndex(self, *args, **kwargs):
        keys = [ self.fields[i].id for i in args ]
        self.sortKey(self, *keys, **kwargs)

    @staticmethod
    def aggregate(key, tables, *fieldArgs):
        """Aggregate any number of Tables.
        key: A list of Field IDs. Rows for which all the corresponding
             fields are equal will be combined.
        tables: A list of Table objects sharing the same structure.
        fieldArgs: Any number of (field ID, aggregation function, name) triples
                or (field ID, aggregation function) pairs.

        Only the specified fields will be combined, and each field will be
        aggregated using the specified function. An aggregation function takes
        in the ID of the field in question, the list of fields each row has,
        and any number of data records (from any number of Tables), and returns
        the combined value for the field.
        """
        # Get the Fields for the key
        fieldList = tables[0].fields
        keyFields = []
        for i in range(len(key)):
            for j in range(len(fieldList)):
                if key[i] == fieldList[j].id:
                    keyFields.append(fieldList[j])
        # Get the Fields to be aggregated
        fields = []
        aggFields = {}
        for f in fieldArgs:
            field = f[0]
            func = f[1]
            for i in range(len(fieldList)):
                if field == fieldList[i].id:
                    aggFields[field] = fieldList[i]
            name = aggFields[field].name
            if len(f) > 2:
                name = f[2]
            fields.append((field, func, name))
        # Group the rows by the key
        buckets = {}
        for table in tables:
            for row in table.data:
                keyvalues = tuple([ row[id] for id in key ])
                buckets[keyvalues] = buckets.get(keyvalues, [])
                buckets[keyvalues].append(row)
        # Create a new table
        combined = Table()
        for field in keyFields:
            combined.addField(field)
        for field, func, name in fields:
            datatype = aggFields[field].type
            if datatype == "int" and func not in [sumField]:
                datatype = "float"
            combinedField = Field(field, fieldName=name, type=datatype)
            combined.addField(combinedField)
        # Aggregate each group of rows
        for keyvalues in buckets:
            row = list(keyvalues)
            rows = buckets[keyvalues]
            for field, func, name in fields:
                val = func(field, fieldList, len(tables), *rows)
                row.append(val)
            combined.addRecord(*row)
        # Return the combined Table
        return combined

    @staticmethod
    def combine(tables, key, stat):
        """Combine any number of Tables and print raw data for one
        field, grouped by another.

        tables: A list of Table objects sharing the same structure.
        key: A single field ID. Data will be grouped into columns
             according to this key.
             fields are equal will be combined.
        stat: A single field ID. Values of this column will be
              collected for each group.
        """
        groups = {}
        groupvals = []
        maxn = 0
        # Collect and group the data
        for table in tables:
            for row in table.data:
                if row[key] not in groups:
                    groupvals.append(row[key])
                    groups[row[key]] = []
                groups[row[key]].append(row[stat])
                maxn = max(maxn, len(groups[row[key]]))
        # Pad to the maximum length
        for val in groupvals:
            for i in range(maxn - len(groups[val])):
                groups[val].append(None)
        # Get Field objects
        statField = None
        for field in tables[0].fields:
            if field.id == stat:
                statField = field
        # Construct a Table
        combined = Table()
        for groupval in groupvals:
            combined.addField(Field(str(groupval), type=statField.type))
        for i in range(maxn):
            row = [ groups[val][i] for val in groupvals ]
            combined.addRecord(*row)
        return combined

def sumField(field, fieldList, ntables, *rows):
    """Aggregate a field by summing the values in the rows.
    field: The ID of the field to be aggregated
    fieldList: The list of fields.
    ntables: The number of relevant tables.
    rows: Any number of rows, all of which have the same structure.
    """
    return sum((row[field] for row in rows))

def avgAppearance(field, fieldList, ntables, *rows):
    """Aggregate a field by averaging its values across all rows.
    field: The ID of the field to be aggregated
    fieldList: The list of fields.
    ntables: The number of relevant tables.
    rows: Any number of rows, all of which have the same structure.
    """
    return sumField(field, fieldList, ntables, *rows) / float(len(rows))

def avgField(field, fieldList, ntables, *rows):
    """Aggregate a field by averaging its values across all tables.
    field: The ID of the field to be aggregated
    fieldList: The list of fields.
    ntables: The number of relevant tables.
    rows: Any number of rows, all of which have the same structure.
    """
    return sumField(field, fieldList, ntables, *rows) / float(ntables)

def weighted(other):
    """Aggregate a field by calculating a weighted average with respect
    to another field."""
    def weightedAvg(field, fieldList, ntables, *rows):
        """Aggregate a field by calculating a weighted average with respect
        to another field.
        field: The ID of the field to be aggregated
        fieldList: The list of fields.
        ntables: The number of relevant tables.
        rows: Any number of rows, all of which have the same structure.
        """
        totalWeights = 0.0
        total = 0.0
        for row in rows:
            totalWeights += row[other]
            total += row[other] * row[field]
        return total / float(totalWeights)
    return weightedAvg

def test():
    o = Table()
    o.addField(Field('name', '', align='<'))
    o.addField(Field('X'))
    o.addField(Field('Y', align='>'))
    o.addField(Field('Z', 'Letter Z', align='<'))
    o.addRecord('alpha', 1, 2, 'a')
    o.addRecordLevel(1, 'beta', 3, 4.56, 'b')
    o.addRecordLevel(2, 'gamma', 5, 6, 'c')
    o.addRecordLevel(2, 'lololololol', 7.134, 8.9, 'cdef')
    o.setTitle('table of stuff')
    print
    o.printLatex(colwidth={'Z':'5cm'})
    print
    o.printDelim()
    print
    o.printTable()
    return o

def loadPrint():
    def dataOut(t, args):
        t.printDelim(delim=args.delim)
    def tableOut(t, args):
        t.printTable()
    def latexOut(t, args):
        t.printLatex(width=args.width, boldFirst=args.bold,
                hrule=args.hrule, vrule=args.vrule,
                vborder=args.vborder, booktabs=args.booktabs,
                indent=args.indent, size=args.size)
    def repickleOut(t, args):
        pickle.dump(t, sys.stdout)

    p = argparse.ArgumentParser(description=\
    """Loads a pickled Table object and prints it.""")
    subp = p.add_subparsers(title='formats', help='Specify the output format.')

    dp = subp.add_parser('data', help='Simple data file: seperate\
        fields with a given delimiter.')
    dp.set_defaults(func=dataOut)
    dp.add_argument('infile', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin, help='Input file. If omitted, read from\
            standard input.')
    dp.add_argument('delim', nargs='?', type=str, default='\t',
            help='Delimiter.')

    tp = subp.add_parser('ascii', help='Human-readable ASCII table.')
    tp.set_defaults(func=tableOut)
    tp.add_argument('infile', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin, help='Input file. If omitted, read from\
            standard input.')

    lp = subp.add_parser('latex', help='LaTeX code to produce a\
        formatted table.')
    lp.set_defaults(func=latexOut)
    lp.add_argument('infile', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin, help='Input file. If omitted, read from\
            standard input.')
    lp.add_argument('-b', '--bold', action="store_true", help='Bold the\
            first cell of each row.')
    lp.add_argument('-B', '--booktabs', action="store_true", help="\
            Display book-style tables using LaTeX's booktabs package.")
    lp.add_argument('-H', '--hrule', action="store_true", help='Add\
            horizontal lines between rows.')
    lp.add_argument('-i', '--indent', type=str, default='.25in',
            help='Amount of\ indentation per level of indent, default .25in.')
    lp.add_argument('-s', '--size', type=str, default='large',
            help='Text size (e.g. normal, tiny, Large LARGE), default large.')
    lp.add_argument('-v', '--vrule', action="store_true", help='Add\
            vertical lines between columns.')
    lp.add_argument('-V', '--vborder', action="store_true", help='Add\
            vertical lines on the edges of the table.')
    lp.add_argument('-w', '--width', type=str, default='9in',
            help='Table width (default 9in).')

    pp = subp.add_parser('pickle', help='Re-pickle the table.')
    pp.set_defaults(func=repickleOut)
    pp.add_argument('infile', nargs='?', type=argparse.FileType('r'),
            default=sys.stdin, help='Input file. If omitted, read from\
            standard input.')

    args = p.parse_args()
    t = pickle.load(args.infile)
    args.func(t, args)

if __name__ == "__main__":
    #loadPrint()
    t = Table()
    t.addField(Field('key'))
    t.addField(Field('x', type='int'))
    t.addField(Field('y', type='float'))
    t.addField(Field('z', type='percent'))
    t.addRecord('foo', 23, 15, .54)
    t.addRecord('bar', 53, 25.4, .40)
    t.addRecord('baz', 90, 13.5, .65)

    t2 = Table()
    t2.addField(Field('key'))
    t2.addField(Field('x', type='int'))
    t2.addField(Field('y', type='float'))
    t2.addField(Field('z', type='percent'))
    t2.addRecord('foo', 44, 23.4,  .39)
    t2.addRecord('bar', 83, 63.34, .93)

    a = Table.aggregate(['key'], (t, t2),
            ('x', sumField),
            ('y', sumField),
            ('z', sumField),
            ('x', avgField, 'avg(x)'),
            ('z', avgField, 'avg(z)'),
            ('x', weighted('z'), 'x weighted by z'),
            ('z', avgField, 'avg(z)'),
            ('z', avgAppearance, 'avg2(z)'))

    t.sortKey("key")
    t2.sortKey("key")
    a.sortKey("key")

    t.printTable()
    t2.printTable()
    a.printTable()

    c = Table.combine([t, t2], 'key', 'y')
    c.printTable()
