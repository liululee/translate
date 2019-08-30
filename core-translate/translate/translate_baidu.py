#/usr/bin/env python
#coding=utf8
 
import requests,json
import random
import hashlib
import urllib
appid = '' #你的appid
secretKey = '' #你的密钥

 
httpClient = None
url = 'http://api.fanyi.baidu.com/api/trans/vip/translate'
fromLang = 'zh'
toLang = 'en'
def send(q):
    if not q:
        return '\n'
    salt = random.randint(32768, 65536)
    appid = '20190725000321293'
    secretKey = '02VSqccQn5ox50H5Cu4a'
    sign = appid+q+str(salt)+secretKey
    m1 = hashlib.md5()
    m1.update(sign.encode())
    sign = m1.hexdigest()
    myurl = url+'?appid='+appid+'&q='+ urllib.parse.quote(q, encoding='utf-8') +'&from='+fromLang+'&to='+toLang+'&salt='+str(salt)+'&sign='+sign
    resp = requests.get(myurl)
    print('百度翻译API返回：', resp)
    print('请求状态：{}'.format(resp.status_code), '返回结果：\n{}'.format(resp.text))
    dst = json.loads(resp.text).get('trans_result')[0].get('dst')
    print(dst)
    return dst
    

if __name__ == '__main__':
    send()