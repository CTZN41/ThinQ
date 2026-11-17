import json,re

def flight_records(document):
    chunks = []
    for script in re.findall(r"<script[^>]*>(.*?)</script>", document, re.S | re.I):
        match = re.search(r"self\.__next_f\.push\((\[1,.*\])\)", script, re.S)
        if match:
            try:
                chunks.append(json.loads(match.group(1))[1])
            except (ValueError, IndexError, TypeError):
                continue
    flight = "".join(chunks)
    records = {}
    decoder = json.JSONDecoder()
    for match in re.finditer(r"(?:^|\n)([0-9a-f]+):", flight):
        try:
            records[match.group(1)] = decoder.raw_decode(flight[match.end():])[0]
        except ValueError:
            pass

    def resolve(value, visited=frozenset()):
        if isinstance(value, str) and re.fullmatch(r"\$[0-9a-f]+", value):
            key = value[1:]
            if key in records and key not in visited:
                return resolve(records[key], visited | {key})
        if isinstance(value, dict):
            return {key: resolve(item, visited) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item, visited) for item in value]
        return None if value == "$undefined" else value

    return resolve(records)

def dictionaries(value):
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from dictionaries(child)
    elif isinstance(value, list):
        for child in value:
            yield from dictionaries(child)