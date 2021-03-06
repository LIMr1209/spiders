# 台湾金点设计奖
import json

import scrapy
from design.items import DesignItem


class JdsjSpider(scrapy.spiders.Spider):
    name = "jdsj-new"
    allowed_domains = ["goldenpin.org.tw"]
    url = 'https://www.goldenpin.org.tw/project-category/%s/page/%s/'
    prize_level = ['年度最佳设计奖', '年度特别奖循环设计奖', '年度特别奖社会设计奖', '金点概念设计奖年度最佳设计奖', '金点新秀设计奖年度最佳设计奖']
    prize_level_dict = {
        '年度最佳設計獎-金點': '年度最佳设计奖',
        '年度特別獎循環設計獎-金點': '年度特别奖循环设计奖',
        '年度特別獎社會設計獎-金點': '年度特别奖社会设计奖',
        '年度最佳設計獎-概念獎': '金点概念设计奖年度最佳设计奖',
        '年度最佳設計獎-新秀獎': '金点新秀设计奖年度最佳设计奖'
    }
    prize_level_list = ['年度最佳設計獎-金點','年度特別獎循環設計獎-金點', '年度特別獎社會設計獎-金點', '年度最佳設計獎-概念獎', '年度最佳設計獎-新秀獎']

    custom_settings = {
        'DOWNLOAD_DELAY': 0,
        'COOKIES_ENABLED': False,  # enabled by default
        'ITEM_PIPELINES': {
            'design.pipelines.ImagePipeline': 300
        },
        'DOWNLOADER_MIDDLEWARES': {
            'design.middlewares.DesignDownloaderMiddleware': 543,
        }
    }

    def start_requests(self):
        for i in self.prize_level_list:
            yield scrapy.Request(self.url%(i,1), callback=self.parse_list, meta={'page': 1,'level':i})
        # yield scrapy.Request(self.url % ('年度最佳設計獎-金點', 1), callback=self.parse_list, meta={'page': 1, 'level': '年度最佳設計獎-金點'})
    def parse_list(self, response):
        page = response.meta['page']
        level = response.meta['level']
        detail_list = response.xpath('//figure/a[1]/@href').extract()
        print(page, level)
        print(detail_list)
        for i in detail_list:
            # yield scrapy.Request('https://www.goldenpin.org.tw/project/vsr-aerobike/', callback=self.parse_detail, meta={'level': level})
            yield scrapy.Request(i, callback=self.parse_detail, meta={'level': level})
        page_text_list = response.xpath('//div[@class="paginator"]/a/@data-page-num').extract()
        page_text_list = [int(i) for i in page_text_list]
        page_text_list.sort()
        if page_text_list and page < page_text_list[-1]:
            page += 1
            yield scrapy.Request(self.url%(level,page), callback=self.parse_list, meta={'page': page,'level':level})

    def parse_detail(self, response):
        level = response.meta['level']
        item = DesignItem()
        item['url'] = response.url
        item['title'] = response.xpath('//div[@class="wf-wrap"]/descendant::h1[@class="entry-title"]/text()').extract()[
            0]
        item['evt'] = 3
        item['channel'] = 'jdsj'
        tmp_urls = response.xpath('//div[contains(@class,"shortcode-single-image-wrap alignnone")]//img/@data-src').extract()
        item['img_urls'] = ','.join(tmp_urls)
        prize_time = response.xpath('//ol/a[2]/text()').extract()[0]
        prize = {'id': 300, 'level': self.prize_level_dict[level], 'time': prize_time}
        try:
            customer = response.xpath('//span[contains(text(),"產品廠商")]/following-sibling::strong[1]/span/text()').extract()
            item['customer'] = customer[0]
        except:
            pass
        try:
            designer = response.xpath('//span[contains(text(),"設計師 ")]/strong/span/text()').extract()
            item['designer'] = ''.join(designer).strip()
        except:
            pass
        description_list = response.xpath('//div[contains(@class,"wpb_text_column wpb_content_element")][2]//text()').extract()
        description_list = [i.replace('\n','').replace('\t','') for i in description_list]
        description_list = [i for i in description_list if i]
        item['description'] = '\n'.join(description_list)
        item['prize'] = json.dumps(prize)
        # print(item)
        yield item
#