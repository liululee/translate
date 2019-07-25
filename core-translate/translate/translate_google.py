# -*- coding utf8 -*-
from googletrans import Translator

translator = Translator(service_urls=['translate.google.cn', 'translate.google.com'])


def do_translate(source_text):
    if not source_text:
        return '\n'
    txt = translator.translate(source_text, src='zh-cn', dest='en').text
    print('translate result:' + txt)
    return txt


if __name__ == '__main__':
    do_translate('你好！')
