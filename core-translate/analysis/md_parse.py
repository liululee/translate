# -*- coding utf8 -*-
import mistune

markdown = mistune.Markdown()

def parse(text):
    return markdown(text)


def execute(filepath):
    with open(file=filepath, mode='r', encoding='utf8') as f:
        source_text = f.read()
        return source_text