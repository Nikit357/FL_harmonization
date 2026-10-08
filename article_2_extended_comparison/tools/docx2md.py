#!/usr/bin/env python3
"""Convert a .docx to Markdown preserving document order: headings, paragraphs,
lists, tables, inline formatting, image placeholders, footnotes and comments."""
import sys, re, zipfile
from xml.etree import ElementTree as ET

W = '{http://schemas.openxmlformats.org/wordprocessingml/2006/main}'
A = '{http://schemas.openxmlformats.org/drawingml/2006/main}'
R = '{http://schemas.openxmlformats.org/officeDocument/2006/relationships}'
PIC = '{http://schemas.openxmlformats.org/drawingml/2006/picture}'

def q(tag): return W + tag

class Conv:
    def __init__(self, path):
        self.z = zipfile.ZipFile(path)
        self.doc = ET.fromstring(self.z.read('word/document.xml'))
        self.styles = self._styles()
        self.numfmt = self._numbering()
        self.rels = self._rels()
        self.imgcount = 0

    def _styles(self):
        m = {}
        try: s = ET.fromstring(self.z.read('word/styles.xml'))
        except KeyError: return m
        for st in s.iter(q('style')):
            sid = st.get(q('styleId'))
            nm = st.find(q('name'))
            if sid is not None and nm is not None:
                m[sid] = nm.get(q('val'))
        return m

    def _numbering(self):
        """map numId -> ilvl -> 'bullet'|'decimal'"""
        res = {}
        try: n = ET.fromstring(self.z.read('word/numbering.xml'))
        except KeyError: return res
        abs_ = {}
        for a in n.findall(q('abstractNum')):
            aid = a.get(q('abstractNumId'))
            lv = {}
            for l in a.findall(q('lvl')):
                fmt = l.find(q('numFmt'))
                lv[l.get(q('ilvl'))] = fmt.get(q('val')) if fmt is not None else 'decimal'
            abs_[aid] = lv
        for num in n.findall(q('num')):
            nid = num.get(q('numId'))
            ai = num.find(q('abstractNumId'))
            if ai is not None:
                res[nid] = abs_.get(ai.get(q('val')), {})
        return res

    def _rels(self):
        m = {}
        try: r = ET.fromstring(self.z.read('word/_rels/document.xml.rels'))
        except KeyError: return m
        for rel in r:
            m[rel.get('Id')] = (rel.get('Target'), rel.get('Type', '').rsplit('/', 1)[-1])
        return m

    # ---------- inline ----------
    def runs(self, el, in_del=False):
        out = []
        for ch in el:
            t = ch.tag
            if t == q('r'):
                out.append(self.run(ch))
            elif t == q('hyperlink'):
                inner = ''.join(self.run(r) for r in ch.findall(q('r')))
                tgt = self.rels.get(ch.get(R + 'id'), ('', ''))[0]
                out.append(f'[{inner}]({tgt})' if tgt else inner)
            elif t == q('ins'):          # tracked insertion -> keep
                out.append(self.runs(ch))
            elif t == q('del'):          # tracked deletion -> mark
                txt = ''.join(''.join(x.text or '' for x in r.findall(q('delText')))
                              for r in ch.findall(q('r')))
                if txt.strip(): out.append(f'~~{txt}~~')
            elif t == q('smartTag') or t == q('sdt'):
                sub = ch.find(q('sdtContent'))
                out.append(self.runs(sub if sub is not None else ch))
            elif t == q('commentRangeStart'):
                out.append(f'[[COMMENT-{ch.get(q("id"))}-START]]')
            elif t == q('commentRangeEnd'):
                out.append(f'[[COMMENT-{ch.get(q("id"))}-END]]')
        return ''.join(out)

    def run(self, r):
        txt = ''
        for ch in r:
            t = ch.tag
            if t == q('t'):
                txt += ch.text or ''
            elif t == q('tab'):
                txt += '\t'
            elif t in (q('br'), q('cr')):
                txt += '\n'
            elif t == q('drawing') or t == q('pict') or t == q('object'):
                txt += self.image(ch)
            elif t == q('footnoteReference'):
                txt += f'[^fn{ch.get(q("id"))}]'
            elif t == q('endnoteReference'):
                txt += f'[^en{ch.get(q("id"))}]'
            elif t == q('commentReference'):
                txt += f'[[comment:{ch.get(q("id"))}]]'
            elif t == q('sym'):
                try: txt += chr(int(ch.get(q('char')), 16) & 0xFF)
                except Exception: pass
        if not txt.strip():
            return txt
        pr = r.find(q('rPr'))
        if pr is not None:
            def on(tag):
                e = pr.find(q(tag))
                return e is not None and e.get(q('val')) not in ('0', 'false', 'none')
            vert = pr.find(q('vertAlign'))
            if vert is not None and vert.get(q('val')) == 'superscript': txt = f'^{txt}^'
            elif vert is not None and vert.get(q('val')) == 'subscript': txt = f'~{txt}~'
            lead = txt[:len(txt) - len(txt.lstrip())]
            trail = txt[len(txt.rstrip()):]
            core = txt.strip()
            if on('b'): core = f'**{core}**'
            if on('i'): core = f'*{core}*'
            if on('strike'): core = f'~~{core}~~'   # struck-through form options, etc.
            txt = lead + core + trail
        return txt

    def image(self, el):
        names = []
        for blip in el.iter(A + 'blip'):
            rid = blip.get(R + 'embed')
            tgt = self.rels.get(rid, (None, None))[0]
            if tgt: names.append(tgt.split('/')[-1])
        for im in el.iter('{urn:schemas-microsoft-com:vml}imagedata'):
            rid = im.get(R + 'id')
            tgt = self.rels.get(rid, (None, None))[0]
            if tgt: names.append(tgt.split('/')[-1])
        if not names:
            return ''
        # capture alt text / drawing name if present
        alt = ''
        for d in el.iter():
            if d.tag.endswith('}docPr'):
                alt = d.get('descr') or d.get('name') or ''
                break
        self.imgcount += len(names)
        return ''.join(f'\n\n![{alt or "figure"}](media/{n})\n\n' for n in names)

    # ---------- block ----------
    def para(self, p):
        text = self.runs(p).strip()
        pr = p.find(q('pPr'))
        style_id = None
        ilvl = numid = None
        if pr is not None:
            ps = pr.find(q('pStyle'))
            if ps is not None: style_id = ps.get(q('val'))
            npr = pr.find(q('numPr'))
            if npr is not None:
                il = npr.find(q('ilvl')); ni = npr.find(q('numId'))
                ilvl = il.get(q('val')) if il is not None else '0'
                numid = ni.get(q('val')) if ni is not None else None
        name = self.styles.get(style_id, style_id or '')
        if not text:
            return ''
        m = re.match(r'^[Hh]eading\s*(\d)', name or '')
        if m:
            return '#' * min(6, int(m.group(1)) + 1) + ' ' + text
        if (name or '').lower() in ('title',):
            return '# ' + text
        if (name or '').lower() in ('subtitle',):
            return '## ' + text
        if numid is not None:
            fmt = self.numfmt.get(numid, {}).get(ilvl, 'bullet')
            indent = '  ' * int(ilvl or 0)
            marker = '-' if fmt == 'bullet' else '1.'
            return f'{indent}{marker} {text}'
        if (name or '').lower().startswith('list paragraph'):
            return f'- {text}'
        if (name or '').lower().startswith('caption'):
            return f'*{text}*'
        if (name or '').lower().startswith('quote'):
            return f'> {text}'
        return text

    def cell_text(self, tc):
        bits = []
        for ch in tc:
            if ch.tag == q('p'):
                t = self.runs(ch).strip()
                if t: bits.append(t)
            elif ch.tag == q('tbl'):
                bits.append('[nested table]')
        return ' <br> '.join(bits).replace('|', '\\|')

    def table(self, tbl):
        rows = []
        for tr in tbl.findall(q('tr')):
            cells = [self.cell_text(tc) for tc in tr.findall(q('tc'))]
            if cells: rows.append(cells)
        if not rows: return ''
        w = max(len(r) for r in rows)
        rows = [r + [''] * (w - len(r)) for r in rows]
        out = ['| ' + ' | '.join(rows[0]) + ' |',
               '|' + '---|' * w]
        for r in rows[1:]:
            out.append('| ' + ' | '.join(r) + ' |')
        return '\n'.join(out)

    def notes(self, part, label):
        try: x = ET.fromstring(self.z.read(f'word/{part}.xml'))
        except KeyError: return []
        out = []
        for n in x:
            nid = n.get(q('id'))
            if n.get(q('type')) in ('separator', 'continuationSeparator'): continue
            txt = ' '.join(self.runs(p).strip() for p in n.findall(q('p'))).strip()
            if txt: out.append(f'[^{label}{nid}]: {txt}')
        return out

    def comments(self):
        try: x = ET.fromstring(self.z.read('word/comments.xml'))
        except KeyError: return []
        out = []
        for c in x.findall(q('comment')):
            txt = ' '.join(self.runs(p).strip() for p in c.findall(q('p'))).strip()
            if txt:
                out.append(f'- **[{c.get(q("id"))}] {c.get(q("author"),"?")}** ({c.get(q("date"),"")}): {txt}')
        return out

    def convert(self):
        body = self.doc.find(q('body'))
        blocks, prev_blank = [], True
        def emit(s):
            if s: blocks.append(s)
        for el in body:
            if el.tag == q('p'):
                emit(self.para(el))
            elif el.tag == q('tbl'):
                emit('\n' + self.table(el) + '\n')
            elif el.tag == q('sdt'):
                c = el.find(q('sdtContent'))
                if c is not None:
                    for sub in c:
                        if sub.tag == q('p'): emit(self.para(sub))
                        elif sub.tag == q('tbl'): emit('\n' + self.table(sub) + '\n')
        text = '\n\n'.join(b for b in blocks if b.strip())
        text = re.sub(r'\n{4,}', '\n\n\n', text)
        fn = self.notes('footnotes', 'fn') + self.notes('endnotes', 'en')
        if fn: text += '\n\n---\n\n## Footnotes\n\n' + '\n\n'.join(fn)
        cm = self.comments()
        if cm: text += '\n\n---\n\n## Comments in document\n\n' + '\n'.join(cm)
        return text

if __name__ == '__main__':
    src, dst = sys.argv[1], sys.argv[2]
    c = Conv(src)
    md = c.convert()
    title = src.rsplit('/', 1)[-1]
    header = f'# {title}\n\n> Extracted from `{title}`. Images are referenced by their name inside the .docx package (`word/media/`).\n\n---\n\n'
    open(dst, 'w').write(header + md + '\n')
    print(f'{dst}: {len(md)} chars, {c.imgcount} images')
