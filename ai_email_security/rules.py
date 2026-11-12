from email.utils import parseaddr
from pathlib import PurePath


def find_signals(mail):
    signals = []
    sender = parseaddr(mail['headers']['From'])[1].lower()
    reply = parseaddr(mail['headers']['Reply-To'])[1].lower()
    if sender and reply and sender != reply:
        signals.append('Adres Reply-To różni się od adresu nadawcy.')
    for attachment in mail['attachments']:
        if PurePath(attachment['name']).suffix.lower() in {'.exe', '.scr', '.js', '.vbs', '.bat', '.cmd', '.ps1', '.docm', '.xlsm', '.lnk'}:
            signals.append('Potencjalnie ryzykowne rozszerzenie załącznika: ' + attachment['name'])
    return signals
