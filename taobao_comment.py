import json
import re

import requests
from fake_useragent import UserAgent


comment_url = 'http://127.0.0.1:8002/api/comment/save'
comment_data_url_tmail = 'https://rate.tmall.com/list_detail_rate.htm?itemId=%s&spuId=972811287&sellerId=2901218787&order=3&currentPage=%s&append=0&content=1&tagId=&posi=&picture=&groupId=&needFold=0&_ksTS=1606704651028_691&callback=jsonp692'
comment_data_url_taobao = 'https://rate.taobao.com/feedRateList.htm?auctionNumId=%s&currentPageNum=%s&pageSize=20&orderType=sort_weight&attribute=&sku=&hasSku=false&folded=0&callback=jsonp_tbcrate_reviews_list'
comment_impression = 'https://rate.tmall.com/listTagClouds.htm?itemId=%s&isAll=true&isInner=true&t=1606819325936&groupId=&_ksTS=1606819325936_585&callback=jsonp586'


def comment_tmail_js(out_number):
    # ua = UserAgent().random
    # headers = {
    #     'Referer': 'https://detail.tmall.com/item.htm?spm=a230r.1.14.195.7a525f52x0Oy3V&id=559419594149&ns=1&abbucket=16',
    #     'User-Agent': ua
    # }
    # impression_res = requests.get(comment_impression % "564891421863", stream=True, headers=headers)
    # rex = re.compile('({.*})')
    # impression_data = json.loads(rex.findall(impression_res.content.decode('utf-8'))[0])
    # impression = ''
    # for i in impression_data['tags']['tagClouds']:
    #     impression += i['tag'] + '(' + i['count'] + ')  '

    comment_page = 1
    while True:
        ua = UserAgent().random
        headers = {
            'Referer': 'https://detail.tmall.com/item.htm?id='+out_number,
            'User-Agent': ua
        }
        comment_res = requests.get(comment_data_url_tmail % (out_number, comment_page), headers=headers)
        rex = re.compile('({.*})')
        result = json.loads(rex.findall(comment_res.content.decode('utf-8'))[0])
        for i in result['rateDetail']['rateList']:
            comment = {}
            comment['type'] = 1 if i['anony'] else 0
            comment['good_url'] = headers['Referer']
            comment['first'] = i['rateContent']
            comment['add'] = i['appendComment']['content'] if i['appendComment'] else ''
            comment['buyer'] = i['displayUserNick']
            comment['style'] = i['pics']
            comment['date'] = i['rateDate']
            res = requests.post(comment_url, data=comment)
            if res.status_code != 200 or json.loads(res.content)['code']:
                print(json.loads(res.content)['message'])

        pages = result['rateDetail']['paginator']['lastPage']
        if comment_page == pages:
            break
        comment_page += 1


def comment_taobao_js(out_number):
    comment_page = 1
    while True:
        ua = UserAgent().random
        headers = {
            'Referer': 'https://item.taobao.com/item.htm?id='+out_number,
            'User-Agent': ua,
            'Cookie':'_bl_uid=vjkhyfh1kL3up48m99pCr7FrpXtk; _m_h5_tk=a4901680887df4de35e80eca7db44b84_1606823592784; _m_h5_tk_enc=9bc810f0923b6d2ffa1255ef0eb10aee; t=4c621df8e85d4fe9067ccde6f510e986; cookie2=19f934d02e95023c00ef6f6c16247b20; _tb_token_=538f3e759d683; _samesite_flag_=true; xlly_s=1; enc=8VjKAvR5cUAIjOxlCLOZcKJvrc68jolYx%2B%2BXKZSjT9%2FFz8LyOvCmZRJkDd6PtDwSKarI7PYNAY8Xh0A58XSpGw%3D%3D; thw=cn; hng=CN%7Czh-CN%7CCNY%7C156; mt=ci=0_0; tracknick=; uc1=cookie14=Uoe0az6%2FCczAvQ%3D%3D; cna=zasMF12t3zoCATzCuQKpN3kO; v=0; x5sec=7b22726174656d616e616765723b32223a226536393430633233383332336665616466656166333533376635366463646233434c76446d50344645497165377565426c734f453767453d227d; l=eBjqXoucQKR1C6x3BO5aourza779rLAXhsPzaNbMiIncC6pCdopMGYxQKOsKgCtRR8XAMTLB4mWKOPytfF1gJs8X7w3xU-CtloD2B; tfstk=cyklBRcOcbP7_BVm1LwSjSvcCLyhC8Tzzvk-3xwwcEPL8GLYV75cWs5ZriK0u4DdO; isg=BC0t6dP2Dkp6levKmUHve7J9PMmnimFctAAvaW84I0aR5kOYN9gnLBbw0LoA5nkU'
        }
        comment_res = requests.get(comment_data_url_taobao % (out_number, comment_page), headers=headers)
        rex = re.compile('({.*})')
        result = json.loads(rex.findall(comment_res.content.decode('utf-8'))[0])
        for i in result['comments']:
            comment = {}
            if i['raterType'] == 1:
                comment['type'] = 0
            elif i['raterType'] == 0:
                comment['type'] = 2
            elif i['raterType'] == -1:
                comment['type'] = 1
            comment['good_url'] = headers['Referer']
            comment['first'] = i['content']
            comment['add'] = i['append']['content'] if i['append'] else ''
            comment['buyer'] = i['user']['nick']
            comment['style'] = i['auction']['sku']
            comment['date'] = i['date'].replace('年','-').replace('月','-').replace('日','')
            res = requests.post(comment_url, data=comment)
            if res.status_code != 200 or json.loads(res.content)['code']:
                print(json.loads(res.content)['message'])

        pages = result['maxPage']
        if comment_page == pages:
            break
        comment_page += 1


# comment_tmail_js('569676181813')
comment_taobao_js('548396564158')