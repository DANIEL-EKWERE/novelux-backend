"""Normalise chapter HTML to plain paragraphs.

Bulk upload (Word → mammoth) already produces clean <p> paragraphs and reads
well everywhere. Content typed or pasted into the author-centre editor does
not: Chrome saves typed lines as <div>…</div> with <div><br></div> for blank
lines, and pastes from Google Docs/Word carry inline styles (11pt Arial,
black text, pre-wrap, fixed line-height) that override the reader's font
size and theme. This turns any of that into the same shape bulk upload
produces:

  * one <p> per paragraph; <div> lines, top-level text and <br><br> breaks
    become paragraphs; blank paragraphs are dropped (readers space them)
  * bold/italic/underline/strike kept (including Google Docs' span styles),
    headings, blockquotes, lists and <hr> kept
  * every attribute, style, class, span and font tag removed

It is idempotent: cleaning clean content returns it unchanged.
"""
import re
from html import escape, unescape
from html.parser import HTMLParser

VOID      = {'br', 'hr', 'img', 'meta', 'link', 'input', 'col', 'wbr', 'area', 'base', 'source'}
DROP      = {'script', 'style', 'head', 'title', 'xml', 'template', 'noscript', 'iframe', 'object'}
CONTAINER = {'div', 'section', 'article', 'main', 'header', 'footer', 'body', 'html', 'center',
             'figure', 'aside', 'nav', 'table', 'tbody', 'thead', 'tfoot', 'tr', 'td', 'th', 'dl', 'dd', 'dt',
             'form', 'fieldset', 'address', 'details', 'summary'}
PARA      = {'p', 'pre'}
HEADING   = {'h1': 'h1', 'h2': 'h2', 'h3': 'h3', 'h4': 'h4', 'h5': 'h4', 'h6': 'h4'}
INLINE    = {'strong': 'strong', 'b': 'strong', 'em': 'em', 'i': 'em', 'u': 'u', 'ins': 'u',
             's': 's', 'strike': 's', 'del': 's', 'sub': 'sub', 'sup': 'sup'}


class _Node:
    __slots__ = ('tag', 'attrs', 'children')

    def __init__(self, tag, attrs=None):
        self.tag, self.attrs, self.children = tag, dict(attrs or {}), []


class _Builder(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.root = _Node('root')
        self.stack = [self.root]
        self.skip = 0

    def handle_starttag(self, tag, attrs):
        tag = tag.lower()
        if tag in DROP:
            self.skip += 1
            return
        if self.skip:
            return
        node = _Node(tag, attrs)
        self.stack[-1].children.append(node)
        if tag not in VOID:
            self.stack.append(node)

    def handle_startendtag(self, tag, attrs):
        tag = tag.lower()
        if not self.skip and tag not in DROP:
            self.stack[-1].children.append(_Node(tag, attrs))

    def handle_endtag(self, tag):
        tag = tag.lower()
        if tag in DROP:
            self.skip = max(0, self.skip - 1)
            return
        if self.skip or tag in VOID:
            return
        for i in range(len(self.stack) - 1, 0, -1):     # tolerate unclosed tags
            if self.stack[i].tag == tag:
                del self.stack[i:]
                return

    def handle_data(self, data):
        if not self.skip:
            self.stack[-1].children.append(data)


def _style_wraps(node):
    """Inline formatting a tag stands for, including Google Docs' styled spans."""
    style = (node.attrs.get('style') or '').lower().replace(' ', '')
    tag = node.tag
    if tag == 'b' and re.search(r'font-weight:(normal|400)', style):
        return []                       # Google Docs wraps whole pastes in <b style="font-weight:normal">
    wraps = [INLINE[tag]] if tag in INLINE else []
    if re.search(r'font-weight:(bold|bolder|[6-9]00)', style) and 'strong' not in wraps:
        wraps.append('strong')
    if 'font-style:italic' in style and 'em' not in wraps:
        wraps.append('em')
    if 'text-decoration:underline' in style or 'text-decoration-line:underline' in style:
        if 'u' not in wraps:
            wraps.append('u')
    if 'line-through' in style and 's' not in wraps:
        wraps.append('s')
    return wraps


def _inline(nodes, out):
    """Serialise inline content. `out` gets strings and '\\n' markers for <br>."""
    for n in nodes:
        if isinstance(n, str):
            out.append(escape(re.sub(r'\s+', ' ', n), quote=False))   # source newlines are just spaces
        elif n.tag == 'br':
            out.append('\n')
        elif n.tag in VOID:
            continue
        else:
            wraps = _style_wraps(n)
            inner = []
            _inline(n.children, inner)
            if wraps and _text(''.join(inner)).strip():
                out.append(''.join(f'<{w}>' for w in wraps))
                out.extend(inner)
                out.append(''.join(f'</{w}>' for w in reversed(wraps)))
            else:
                out.extend(inner)


def _text(s):
    return re.sub(r'<[^>]+>', '', s).replace('\n', '').replace('&nbsp;', ' ')


_FMT = r'(strong|em|u|s|sub|sup)'


def _tidy(s):
    s = s.replace('\xa0', ' ')
    s = re.sub(r'[ \t\r\f\v]+', ' ', s)
    # Move spaces outside formatting tags so they don't vanish at paragraph
    # edges, and drop empty formatting — repeated until nothing changes.
    prev = None
    while prev != s:
        prev = s
        s = re.sub(rf'<{_FMT}>([ \n]+)', r'\2<\1>', s)
        s = re.sub(rf'([ \n]+)</{_FMT}>', r'</\2>\1', s)
        s = re.sub(rf'<{_FMT}></\1>', '', s)
        s = re.sub(r' {2,}', ' ', s)
    s = re.sub(r' *\n *', '\n', s)
    return s.strip(' \n')


def _balance(chunks):
    """Formatting can run across a paragraph break (<b>a<br><br>b</b>); close
    open tags at the end of each paragraph and reopen them in the next."""
    out, stack = [], []
    for chunk in chunks:
        res = ''.join(f'<{t}>' for t in stack)
        pos = 0
        for m in re.finditer(rf'<(/?){_FMT}>', chunk):
            res += chunk[pos:m.start()]
            pos = m.end()
            closing, tag = m.group(1), m.group(2)
            if not closing:
                stack.append(tag)
                res += m.group(0)
            elif tag in stack:
                while stack:                    # close anything opened inside it
                    t = stack.pop()
                    res += f'</{t}>'
                    if t == tag:
                        break
        res += chunk[pos:] + ''.join(f'</{t}>' for t in reversed(stack))
        out.append(res)
    return out


def _paragraphs(parts, tag='p'):
    """Inline parts → one or more paragraphs. A double line break starts a new
    paragraph; a single one stays as <br>."""
    s = _tidy(''.join(parts))
    out = []
    for chunk in _balance(re.split(r'\n{2,}', s)):
        chunk = _tidy(chunk)
        if _text(chunk).strip():
            out.append(f'<{tag}>{chunk.replace(chr(10), "<br>")}</{tag}>')
    return out


def _blocks(nodes, out):
    line = []

    def flush():
        if line:
            out.extend(_paragraphs(line))
            line.clear()

    for n in nodes:
        if isinstance(n, str):
            if n.strip():
                line.append(escape(re.sub(r'\s+', ' ', n), quote=False))
            elif line:
                line.append(' ')
            continue
        tag = n.tag
        if tag == 'br':
            # A <br> between blocks (Google Docs: </p><br><p>) separates; inside
            # a run of text it's a line break, and two of them a paragraph break.
            line.append('\n')
        elif tag in CONTAINER:
            flush()
            _blocks(n.children, out)
        elif tag in PARA or tag in HEADING:
            flush()
            parts = []
            if tag == 'pre':           # each line of preformatted text becomes a paragraph
                kids = []
                for c in n.children:
                    if isinstance(c, str):
                        for i, piece in enumerate(c.split('\n')):
                            if i:
                                kids += [_Node('br'), _Node('br')]
                            kids.append(piece)
                    else:
                        kids.append(c)
                _inline(kids, parts)
            else:
                _inline(n.children, parts)
            out.extend(_paragraphs(parts, HEADING.get(tag, 'p')))
        elif tag == 'blockquote':
            flush()
            inner = []
            _blocks(n.children, inner)
            if inner:
                out.append('<blockquote>' + ''.join(inner) + '</blockquote>')
        elif tag in ('ul', 'ol'):
            flush()
            items = []
            for li in n.children:
                if isinstance(li, _Node) and li.tag == 'li':
                    parts = []
                    _inline(li.children, parts)
                    s = _tidy(_balance([''.join(parts)])[0]).replace('\n', '<br>')
                    if _text(s).strip():
                        items.append(f'<li>{s}</li>')
            if items:
                out.append(f'<{tag}>' + ''.join(items) + f'</{tag}>')
        elif tag == 'hr':
            flush()
            out.append('<hr>')
        elif tag in VOID:
            continue
        else:
            # Inline element at block level (span, b, font, o:p, a, …)
            if any(isinstance(c, _Node) and (c.tag in CONTAINER or c.tag in PARA or c.tag in HEADING)
                   for c in n.children):
                flush()                 # e.g. <b id="docs-internal-guid"><p>…</p></b>
                wraps = _style_wraps(n)
                inner = []
                _blocks(n.children, inner)
                if wraps:
                    o, c = ''.join(f'<{w}>' for w in wraps), ''.join(f'</{w}>' for w in reversed(wraps))
                    inner = [re.sub(r'^<(p|h[1-4])>(.*)</\1>$', rf'<\1>{o}\2{c}</\1>', b, flags=re.S) for b in inner]
                out.extend(inner)
            else:
                _inline([n], line)
    flush()


def clean_chapter_html(html):
    if not html or not html.strip():
        return html or ''
    plain = '<' not in html
    # Unicode line/paragraph separators (pasted from some phone editors)
    html = (html.replace('\u2029', '\n\n' if plain else '<br><br>')
                .replace('\u2028', '\n' if plain else '<br>'))
    builder = _Builder()
    builder.feed(html)
    builder.close()
    out = []
    if plain:
        text = html.replace('\r\n', '\n').replace('\r', '\n').strip()
        sep = '\n\n' if re.search(r'\n\s*\n', text) else '\n'
        for chunk in re.split(r'\n\s*\n' if sep == '\n\n' else r'\n', text):
            out.extend(_paragraphs([escape(unescape(chunk), quote=False)]))
    else:
        _blocks(builder.root.children, out)
    return ''.join(out)
