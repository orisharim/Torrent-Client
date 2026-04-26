# data is expected to be bytes, not str, i is the current index in the byte array
def decode(data: bytes, i: int = 0):
    prefix = data[i:i+1] # peek at the first byte to determine type

    # Integer
    #Format: i<integer value>e
    if prefix == b'i':
        j = data.find(b'e', i)
        if j == -1:
            raise ValueError(f"Invalid bencode at index {i}")
        return int(data[i+1:j]), j + 1

    # List
    # Format: l<item1><item2>...e
    elif prefix == b'l':
        items = []
        j = i + 1
        while data[j:j+1] != b'e':
            item, j = decode(data, j)
            items.append(item)
        return items, j + 1

    # Dictionary
    # Format: d<key1><value1><key2><value2>...e
    elif prefix == b'd':
        d = {}
        j = i + 1
        while data[j:j+1] != b'e':
            key, j = decode(data, j)
            value, j = decode(data, j)
            d[key] = value
        return d, j + 1

    # Byte string
    # Format: <length>:<data>
    elif prefix.isdigit():
        j = data.find(b':', i)
        if j == -1:
            raise ValueError(f"Invalid bencode at index {i}")
        length = int(data[i:j])
        start = j + 1
        end = start + length
        if end > len(data):
            raise ValueError(f"Invalid bencode at index {i}")
        return data[start:end], end

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