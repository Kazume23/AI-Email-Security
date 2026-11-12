"""Offline MIME parsing. Never executes attachments or fetches URLs."""
import re
from email import policy
from email.parser import BytesParser
from html.parser import HTMLParser

MAX_BYTES = 5 * 1024 * 1024
MAX_TEXT = 16000


class InputError(ValueError):
    pass


class HTMLText(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.text, self.links, self.hidden = [], [], 0

    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style'):
            self.hidden += 1
        if tag in ('p', 'br', 'div', 'li'):
            self.text.append('\n')
        if tag == 'a':
            self.links.extend(v for k, v in attrs if k == 'href' and v)

    def handle_endtag(self, tag):
        if tag in ('script', 'style') and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        if not self.hidden:
            self.text.append(data)


def read_eml(raw):
    if not raw or len(raw) > MAX_BYTES:
        raise InputError('Plik jest pusty lub przekracza limit 5 MB.')
    try:
        msg = BytesParser(policy=policy.default).parsebytes(raw)
        if not list(msg.keys()) or any(p.defects for p in msg.walk()):
            raise InputError('Uszkodzony lub nieprawidłowy plik EML.')
        texts, links, attachments = [], [], []
        def visit(part):
            if part.get_content_disposition() == 'attachment' or part.get_filename() or part.get_content_type() == 'message/rfc822':
                payload = part.get_payload(decode=True)
                attachments.append({'name': part.get_filename() or '(bez nazwy)',
                                    'mime': part.get_content_type(),
                                    'size_bytes': len(payload) if payload is not None else len(part.as_bytes())})
                return
            if part.is_multipart():
                for child in part.iter_parts():
                    visit(child)
            elif part.get_content_type() in ('text/plain', 'text/html'):
                body = part.get_content()
                if part.get_content_type() == 'text/html':
                    parser = HTMLText()
                    parser.feed(body)
                    links.extend(parser.links)
                    body = ''.join(parser.text)
                texts.append(body)
        visit(msg)
        body = '\n'.join(texts).strip()
        links.extend(re.findall(r'https?://[^\s<>\"\']+', body))
        result = {'headers': {k: str(msg.get(k, '')) for k in
                  ('Subject', 'From', 'To', 'Reply-To', 'Date', 'Message-ID', 'Return-Path', 'Authentication-Results')},
                  'text': body, 'links': sorted(set(links)), 'attachments': attachments}
        import json
        if len(json.dumps(result, ensure_ascii=False)) > MAX_TEXT:
            raise InputError('Wiadomość przekracza limit demo: 16000 znaków danych do analizy.')
        return result
    except InputError:
        raise
    except (ValueError, LookupError, TypeError) as exc:
        raise InputError('Nie można odczytać kodowania lub struktury wiadomości.') from exc
