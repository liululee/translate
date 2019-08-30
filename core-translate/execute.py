# -*- coding utf8 -*-

import translate.translate_google as transhand
import analysis.md_parse as md_parse
import utils.cutword as cutword
import translate.translate_baidu as baidu_trans


def run():
    file_path = 'test.md'
    source_text = md_parse.execute(file_path)
   
    for text in cutword.cut_sent(source_text):
        result = transhand.do_translate(text)
        if result is not None:
            with open('result.md', 'a', encoding='utf-8') as f:
                f.write(result)
                f.flush()
                f.close()
            print(result)
    

def baidu_run():
    file_path = 'test.md'
    source_text = md_parse.execute(file_path)
   
    for text in cutword.cut_sent(source_text):
        result = baidu_trans.send(text)
        if result is not None:
            with open('baidu_result.md', 'a', encoding='utf-8') as f:
                f.write(result)
                f.flush()
                f.close()
            print(result)

if __name__ == '__main__':
    # run()
    baidu_run()