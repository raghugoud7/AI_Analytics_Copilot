import json


def dict_to_text(data):

    return json.dumps(
        data,
        indent=2,
        default=str
    )