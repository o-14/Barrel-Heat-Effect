"""Scan text and encoded string data without storing private search terms."""
import os
import re

DRIVE = re.compile(r'(?<![A-Za-z0-9_])[A-Za-z]:[\\/]')

def strings(data):
    # Readable strings terminated by NUL, newline, end-of-file or another control.
    # A short run cut off by high-bit binary data is not an encoded ASCII path.
    for m in re.finditer(rb'[\x20-\x7e]{4,}', data):
        if m.end() == len(data) or data[m.end()] in (0, 9, 10, 13):
            yield m.group().decode('ascii')
    for parity in (0, 1):
        lane = data[parity:]
        for m in re.finditer(rb'(?:[\x20-\x7e]\x00){4,}', lane):
            yield m.group().decode('utf-16le')

def check(data, *, text=False):
    # The caller supplies additional terms in memory through an environment variable.
    terms = [s for s in os.environ.get('BHE_PRIVATE_TERMS', '').splitlines() if s]
    folded = data.lower()
    for term in terms:
        variants = {term, term.replace('\\', '/'), term.replace('\\', '\\\\')}
        for value in variants:
            if value.lower().encode() in folded or value.lower().encode('utf-16le') in folded:
                raise ValueError('Private search term detected; details intentionally not recorded')
    values = [data.decode('utf-8-sig')] if text else strings(data)
    if any(DRIVE.search(value) for value in values):
        raise ValueError('Absolute local path detected; details intentionally not recorded')
    return 'none found'
