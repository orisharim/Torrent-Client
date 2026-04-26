# data is expected to be bytes, not str. i is the current index in the byte array. capture_info is a flag to indicate whether we should capture the byte range of the 'info' dict for later hashing.
def decode(data: bytes, i: int = 0, capture_info=False):
    prefix = data[i:i+1]

    # Integer
    if prefix == b'i':
        j = data.find(b'e', i)
        if j == -1:
            raise ValueError(f"Invalid bencode at index {i}")
        return int(data[i+1:j]), j + 1, None

    # List
    elif prefix == b'l':
        items = []
        j = i + 1
        info_bounds = None

        while data[j:j+1] != b'e':
            item, j, child_bounds = decode(data, j, capture_info)
            items.append(item)

            if child_bounds:
                info_bounds = child_bounds

        return items, j + 1, info_bounds

    # Dictionary
    elif prefix == b'd':
        d = {}
        j = i + 1
        info_bounds = None

        while data[j:j+1] != b'e':
            key, j, _ = decode(data, j, capture_info)

            # capture start BEFORE decoding value
            val_start = j
            value, j, child_bounds = decode(data, j, capture_info)
            val_end = j

            d[key] = value

            # if this is the info dict, capture its byte range
            if capture_info and key == b'info':
                info_bounds = (val_start, val_end)

            # propagate if found deeper (not really needed, but safe)
            elif child_bounds:
                info_bounds = child_bounds

        return d, j + 1, info_bounds

    # Byte string
    elif prefix.isdigit():
        j = data.find(b':', i)
        if j == -1:
            raise ValueError(f"Invalid bencode at index {i}")
        length = int(data[i:j])
        start = j + 1
        end = start + length

        if end > len(data):
            raise ValueError(f"Invalid bencode at index {i}")

        return data[start:end], end, None

    else:
        raise ValueError(f"Invalid bencode at index {i}")
    
def encode(value) -> bytes:
    if isinstance(value, int):
        return b'i' + str(value).encode() + b'e'
    elif isinstance(value, bytes):
        return str(len(value)).encode() + b':' + value
    elif isinstance(value, list):
        return b'l' + b''.join(encode(item) for item in value) + b'e'
    elif isinstance(value, dict):
        items = []
        for key in sorted(value.keys()):
            if not isinstance(key, bytes):
                raise TypeError("Dictionary keys must be bytes")
            items.append(encode(key))
            items.append(encode(value[key]))
        return b'd' + b''.join(items) + b'e'
    else:
        raise TypeError(f"Unsupported type for encoding: {type(value)}")