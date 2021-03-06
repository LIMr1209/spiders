# 京东电商
import json
import logging
import re
import time

import requests
import scrapy
from fake_useragent import UserAgent
from pydispatch import dispatcher
from requests.adapters import HTTPAdapter
from scrapy import signals
from scrapy.utils.project import get_project_settings

from design.items import TaobaoItem
from design.spiders.selenium import SeleniumSpider
import urllib3

urllib3.disable_warnings()


class JdSpider(SeleniumSpider):
    name = "jd_good"
    # allowed_domains = ["search.jd.com"]
    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'COOKIES_ENABLED': False,  # enabled by default
        'DOWNLOADER_MIDDLEWARES': {
            'design.middlewares.SeleniumMiddleware': 543,
        },
        # 设置log日志
        'LOG_LEVEL': 'INFO',
        'LOG_FILE': 'log/%s.log' % name
    }

    def __init__(self, key_words=None, *args, **kwargs):
        # self.key_words = key_words.split(',')
        self.key_words = ['筋膜枪', '脱毛仪', '颈椎按摩仪', '扫地机器人', '电动蒸汽拖把', '挂烫机', '烘衣机', '烤箱']
        self.page = 8
        self.error_retry = 0
        self.max_page = 15
        self.max_price_page = 7  # 价格区间的爬10页
        self.price_range_list = {
            '吹风机': ['459-750', '751-999', '1000gt'],
            '真无线蓝牙耳机 降噪 入耳式': ['300-900', '900-3000'],
        }
        self.s = requests.Session()
        self.s.mount('http://', HTTPAdapter(max_retries=5))
        self.s.mount('https://', HTTPAdapter(max_retries=5))
        self.setting = get_project_settings()
        self.goods_url = self.setting['OPALUS_GOODS_URL']
        self.search_url = 'https://search.jd.com/Search?keyword={name}&page={page}&s=53&ev=^exprice_{price_range}^'
        self.comment_data_url = 'https://club.jd.com/comment/skuProductPageComments.action?callback=fetchJSON_comment98&productId=%s&score=0&sortType=5&page=%s&pageSize=10&isShadowSku=0&fold=1'
        self.fail_url = {}
        self.suc_count = 0

        super(JdSpider, self).__init__(*args, **kwargs)
        dispatcher.connect(receiver=self.except_close,
                           signal=signals.spider_closed
                           )
        old_num = len(self.browser.window_handles)
        js = 'window.open("https://www.jd.com/");'
        self.browser.execute_script(js)
        self.browser.switch_to_window(self.browser.window_handles[old_num])  # 切换新窗口

    def fail_url_save(self, response):
        if self.error_retry:
            if self.category in self.fail_url:
                self.fail_url[self.category].append(response.url)
            else:
                self.fail_url[self.category] = [response.url]
        else:
            if self.key_words[0] in self.fail_url:
                self.fail_url[self.key_words[0]].append(response.url)
            else:
                self.fail_url[self.key_words[0]] = [response.url]

    def except_close(self):
        logging.error(self.key_words)
        logging.error(self.page)
        logging.error(self.price_range_list)
        logging.error(self.fail_url)

    def start_requests(self):
        if self.key_words[0] in self.price_range_list:
            url = self.search_url.format(name=self.key_words[0],
                                         price_range=self.price_range_list[self.key_words[0]][0], page=self.page)
        else:
            url = self.search_url.format(name=self.key_words[0], price_range='', page=self.page)
        yield scrapy.Request(url, callback=self.parse_list, meta={'usedSelenium': True}, dont_filter=True)
        # yield scrapy.Request('https://item.jd.com/68157902835.html', callback=self.parse_detail,
        #                      meta={'usedSelenium': True})

        # list_url = ['https://item.jd.com/71466393768.html', 'https://item.jd.com/10022920532947.html']
        # self.category = '筋膜枪'
        # self.error_retry = 1
        # yield scrapy.Request(list_url[0], callback=self.parse_detail, meta={'usedSelenium': True, 'list_url': list_url},
        #                      dont_filter=True)

    def parse_list(self, response):
        urls = self.browser.find_elements_by_xpath('//div[@class="p-img"]/a[@target="_blank"]')
        list_url = []
        for i in urls:
            list_url.append(i.get_attribute('href'))
        if not list_url:
            self.browser.refresh()
        urls = self.browser.find_elements_by_xpath('//div[@class="p-img"]/a[@target="_blank"]')
        for i in urls:
            list_url.append(i.get_attribute('href'))
        yield scrapy.Request(list_url[0], callback=self.parse_detail, meta={'usedSelenium': True, 'list_url': list_url},
                             dont_filter=True)

    def detail_data(self, response):
        if not 'pcitem.jd.hk' in self.browser.current_url:  # 京东国际不爬
            item = TaobaoItem()
            try:
                height = 0
                for i in range(height, 800, 200):
                    self.browser.execute_script('window.scrollTo(0, {})'.format(i))
                    time.sleep(0.2)
                try:
                    promotion_price = self.browser.find_element_by_xpath(
                        '//span[@class="p-price"]/span[2]').text.strip()
                except:
                    promotion_price = ''
                if promotion_price == '':
                    if "预售剩余" in self.browser.page_source:
                        logging.error('预售 {}'.format(response.url))
                        return
                    time.sleep(60)
                    # 删除 cookie, localStorage, 让浏览器自动获取新cookie 旧cookie 限制爬取需要登录
                    js = 'window.localStorage.clear();'
                    self.browser.execute_script(js)
                    self.browser.delete_all_cookies()
                    self.browser.refresh()
                    promotion_price = self.browser.find_element_by_xpath(
                        '//span[@class="p-price"]/span[2]').text.strip()
                item['title'] = self.browser.find_element_by_xpath('//div[@class="sku-name"]').text.strip()
                item['sku_ids'] = ','.join(
                    response.xpath('//div[contains(@id,"choose-attr")]//div[@data-sku]/@data-sku').extract())
                try:
                    original_text = self.browser.find_element_by_xpath(
                        '//del[@id="page_origin_price" or @id="page_opprice" or @id="page_hx_price"]').text.strip().replace(
                        '￥', '')
                except:
                    original_text = ''
                if original_text:
                    item['original_price'] = original_text
                if not 'original_price' in item:
                    item['original_price'] = promotion_price
                    item['promotion_price'] = ''
                else:
                    item['promotion_price'] = promotion_price
                if item['promotion_price'] == '' and item['original_price'] == '':
                    logging.error("反爬价格无法获取失败")
                    return
                try:
                    comment_text = self.browser.find_element_by_xpath(
                        '//a[contains(@class,"count J-comm")]').text.strip()
                except:
                    comment_text = self.browser.find_element_by_xpath('//li[@data-anchor="#comment"]/s').text.strip()
                    comment_text = comment_text.replace('(', '').replace(')', '')
                if comment_text:
                    index = comment_text.find('万')
                    if index != -1:
                        item['comment_count'] = int(float(comment_text[:index]) * 10000)
                    else:
                        comment_count = re.search('\d+', comment_text)
                        if comment_count:
                            item['comment_count'] = int(comment_count.group())
                if self.key_words[0] == '真无线蓝牙耳机 降噪 入耳式':
                    item['category'] = '耳机'
                else:
                    item['category'] = self.key_words[0]
                if hasattr(self, 'category'):
                    item['category'] = self.category
                shop_id = re.findall('shopId.*?(\d+)', self.browser.page_source)[0]
                item['shop_id'] = shop_id
                service_ele = self.browser.find_elements_by_xpath(
                    '//div[@id="J_SelfAssuredPurchase"]/div[@class="dd"]//a')
                service = []
                for i in service_ele:
                    service.append(i.text)
                item['service'] = ','.join(service)
                reputation_keys = self.browser.find_elements_by_xpath('//span[@class="score-desc"]')
                reputation_values = self.browser.find_elements_by_xpath('//span[contains(@class,"score-detail")]/em')
                reputation_list = []
                for j, i in enumerate(reputation_keys):
                    reputation_list.append(i.text + ": " + reputation_values[j].text)
                item['url'] = response.url.replace('http:', 'https:')
                item['reputation'] = ' '.join(reputation_list)
                self.browser.find_element_by_xpath('//li[@data-anchor="#detail"][2]').click()
                detail_keys = self.browser.find_elements_by_xpath('//dl[@class="clearfix"]/dt')
                detail_values = self.browser.find_elements_by_xpath('//dl[@class="clearfix"]/dd')
                detail_dict = {}
                detail_str_list = []
                for j, i in enumerate(detail_keys):
                    detail_str_list.append(i.text + ':' + detail_values[j].text)
                    detail_dict[i.text] = detail_values[j].text
                if not detail_dict:
                    detail_list = self.browser.find_elements_by_xpath('//ul[contains(@class,"parameter2")]/li')
                    for j, i in enumerate(detail_list):
                        s = i.text.replace(' ', '').replace('\n', '').replace('\r', '').replace('\t', '').replace(
                            '\xa0',
                            '')
                        if s.endswith('：') or s.endswith(':'):
                            detail_str_list.append(s + detail_list[j + 1])
                            continue
                        if ':' in s or '：' in s:
                            detail_str_list.append(s)
                    item['detail_str'] = ', '.join(detail_str_list)
                    for i in detail_str_list:
                        tmp = re.split('[:：]', i)
                        detail_dict[tmp[0]] = tmp[1].replace('\xa0', '')
                item['detail_dict'] = json.dumps(detail_dict, ensure_ascii=False)
                item['detail_str'] = ', '.join(detail_str_list)
                if self.key_words[0] in self.price_range_list:
                    price_range = self.price_range_list[self.key_words[0]][0]
                    temp = re.findall('(\d+)', price_range)
                    item['price_range'] = temp[0] + "-" + temp[1] if len(temp) > 1 else temp[0] + '以上'
                else:
                    item['price_range'] = ''
                itemId = re.findall('\d+', response.url)[0]
                item['out_number'] = itemId
                item['site_from'] = 11
                item['site_type'] = 1
                img_urls = []
                img_ele = self.browser.find_elements_by_xpath('//div[@id="spec-list"]/ul/li/img')
                for i in img_ele:
                    img_urls.append('http://img10.360buyimg.com/n12/%s' % i.get_attribute('data-url'))
                item['cover_url'] = img_urls[0]
                item['img_urls'] = ','.join(img_urls)
                good_data = dict(item)
                # data = self.get_impression(itemId)
                # good_data.update(data)
                print(good_data)
                try:
                    res = self.s.post(url=self.goods_url, data=good_data)
                except:
                    time.sleep(10)
                    res = self.s.post(url=self.goods_url, data=good_data)
                if res.status_code != 200 or json.loads(res.content)['code']:
                    logging.error("产品保存失败" + response.url)
                    logging.error(json.loads(res.content)['message'])
                    self.fail_url_save(response)
                else:
                    self.suc_count += 1
            except Exception as e:
                logging.error("行号 {}, 产品爬取失败 {} {}".format(e.__traceback__.tb_lineno, response.url, str(e)))
                self.fail_url_save(response)

    def parse_detail(self, response):
        self.detail_data(response)
        list_url = response.meta['list_url']
        list_url.pop(0)
        # time.sleep(3)
        if list_url:
            yield scrapy.Request(list_url[0], meta={'usedSelenium': True, "list_url": list_url},
                                 callback=self.parse_detail,
                                 dont_filter=True)
        else:
            print(self.fail_url)
            if self.error_retry == 0:
                if self.key_words[0] in self.price_range_list:
                    page = self.max_price_page
                else:
                    page = self.max_page
                if self.page < page:
                    self.page += 1
                else:
                    self.page = 1
                    if self.key_words[0] in self.price_range_list and len(self.price_range_list[self.key_words[0]]) > 1:
                        self.price_range_list[self.key_words[0]].pop(0)
                    else:
                        self.key_words.pop(0)
                if self.key_words:
                    if self.key_words[0] in self.price_range_list:
                        url = self.search_url.format(name=self.key_words[0],
                                                     price_range=self.price_range_list[self.key_words[0]][0],
                                                     page=self.page)
                    else:
                        url = self.search_url.format(name=self.key_words[0], price_range='', page=self.page)
                    yield scrapy.Request(url, callback=self.parse_list, meta={'usedSelenium': True}, dont_filter=True)

    def get_impression(self, itemId):
        data = {}
        cookies = self.browser.get_cookies()
        cookies = [i['name'] + "=" + i['value'] for i in cookies]
        cookies = '; '.join(cookies)

        ua = UserAgent().random
        headers = {
            'Referer': 'https://item.jd.com/%s.html' % itemId,
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.88 Safari/537.36',
            'cookie': cookies
        }
        url = self.comment_data_url % (itemId, 0)
        try:
            comment_res = self.s.get(url, headers=headers, verify=False, timeout=10)
        except:
            time.sleep(10)
            comment_res = self.s.get(url, headers=headers, verify=False, timeout=10)
        rex = re.compile('({.*})')
        result = json.loads(rex.findall(comment_res.text)[0])
        data['positive_review'] = result['productCommentSummary']['goodCount']
        data['comment_count'] = result['productCommentSummary']['commentCount']
        impression = ''
        for j in result['hotCommentTagStatistics']:
            impression += j['name'] + '(' + str(j['count']) + ')  '
        data['impression'] = impression
        return data
