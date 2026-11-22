"""Small CRUD helpers for the app's trusted local pickle files."""

from pickle_storage import load, load_all as load_all_from_storage, save


def get_all():
    """Read all app data and apply any pending one-time migrations."""
    return load_all_from_storage()


def save_many(**collections):
    """Save changed collections through one small, consistent helper."""
    for collection, records in collections.items():
        save(collection, records)


def get(collection, key=None):
    """Read a whole collection or one record from a dictionary collection."""
    records = load(collection)
    return records if key is None else records.get(key)


def add(collection, record, key=None):
    """Add a record to a dictionary (with a key) or list collection."""
    records = load(collection)
    if isinstance(records, dict):
        if key is None:
            raise ValueError(f"A key is required to add to {collection}.")
        if key in records:
            raise ValueError(f"{key} already exists in {collection}.")
        records[key] = record
    else:
        records.append(record)
    save(collection, records)
    return record


def update(collection, key, changes, id_field=None):
    """Update a dictionary record or find a list record by its ID field."""
    records = load(collection)
    if isinstance(records, dict):
        record = records.get(key)
    else:
        record = next((row for row in records if row.get(id_field) == key), None)
    if record is None:
        raise KeyError(f"{key} was not found in {collection}.")
    record.update(changes)
    save(collection, records)
    return record


def delete(collection, key, id_field=None):
    """Delete a dictionary record or find a list record by its ID field."""
    records = load(collection)
    if isinstance(records, dict):
        if key not in records:
            return None
        removed = records.pop(key)
    else:
        index = next((i for i, row in enumerate(records) if row.get(id_field) == key), None)
        if index is None:
            return None
        removed = records.pop(index)
    save(collection, records)
    return removed
