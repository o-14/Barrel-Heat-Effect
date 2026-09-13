"""Neutralize only the three Fallout 4 compiled-script header strings."""
import re
import struct

def neutralize(data):
    if len(data) < 22 or struct.unpack_from('<I', data)[0] != 0xfa57c0de:
        raise ValueError('Not a supported Fallout 4 compiled script')
    offset = 16
    fields = []
    for _ in range(3):
        length = struct.unpack_from('<H', data, offset)[0]
        offset += 2
        value = data[offset:offset + length]
        if len(value) != length:
            raise ValueError('Truncated compiled-script header')
        fields.append(value.decode('utf-8'))
        offset += length
    source = re.split(r'[\\/]', fields[0])[-1]
    if not source.lower().endswith('.psc'):
        raise ValueError('Expected a script source filename')
    neutral = [source, 'o14', 'build']
    return data[:16] + b''.join(struct.pack('<H', len(s.encode('utf-8'))) + s.encode('utf-8') for s in neutral) + data[offset:]
