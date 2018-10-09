# -*- coding: utf-8 -*-
import scrapy
import uuid
import time
import requests
import os

from hashlib import md5
from fdfs_client.client import *
from decimal import *
from PIL import Image

from scrapy.linkextractors import LinkExtractor
from scrapy.spiders import CrawlSpider, Rule
from guangming.items import GuangmingItem


class JunshiSpider(CrawlSpider):
    name = 'TiYu'
    # allowed_domains = ['www.gmw.cn']
    start_urls = ['http://sports.gmw.cn/']

    rules = (
        Rule(LinkExtractor(allow=r'http://sports.gmw.cn/node_\d+\w+\.htm'), callback='parse_item', follow=True),

    )

    def parse_item(self, response):
        print(response.url)
        print('=================')
        div_list = response.xpath('//ul[@class="channel-newsGroup"]/li')
        for div in div_list:
            item = GuangmingItem()
            item['NewsID'] = str(uuid.uuid1())
            item['NewsCategory'] = '001.010'
            item['SourceCategory'] = '光明' + str(div.xpath('./div[@id="channelBreadcrumbs"]/a[last()]/text()').extract_first())
            item['NewsType'] = 0
            item['NewsTitle'] = div.xpath('./a/text()').extract_first()
            item['NewsDate'] = div.xpath('./span/text()').extract_first()
            link = div.xpath('./a/@href').extract_first()
            urls = 'http://sports.gmw.cn/' + str(link)

            yield scrapy.Request(url=urls, callback=self.parse_info, meta={'item': item})


    def parse_info(self, response):
        print(response.url)
        print('================')
        client = Fdfs_client('/etc/fdfs/client.conf')
        item = response.meta['item']
        item['NewsRawUrl'] = response.url
        SourceCategory = response.xpath(
            '//div[@id="contentBreadcrumbs2"]/a[last()]/text() |'
            '//div[@class="picContent-breadCrumbs2"]/a[last()]/text()').extract_first()
        if SourceCategory is not None:
            item['SourceCategory'] = '光明' + str(SourceCategory)
        else:
            item['SourceCategory'] = '光明'

        SourceName = response.xpath('//span[@id="source"]/a/text()').extract_first()
        if SourceName is not None:
            item['SourceName'] = SourceName
        else:
            item['SourceName'] = '光明网'

        # name= response.xpath('//div[@id="contentLiability"]/text() | //div[@id="Content_Liability"]/text()').extract_first()
        # AuthorName = name.split(':')[1].split(']')[0].strip()
        # item['AuthorName'] = AuthorName
        # item['AuthorName'] = name
        item['AuthorName'] = '李超'
        item['InsertDate'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
        item['NewsClickLike'] = 0
        item['NewsBad'] = 0
        item['NewsRead'] = 0
        item['NewsOffline'] = 0

        # 获取图片链接
        image_urls = response.xpath('//div[@id="contentMain"]/p/img/@src').extract()
        try:
            content = ''.join(response.xpath('//div[@id="contentMain"]//p | //div[@id="ArticleContent"]/div/p').extract())
        except:
            content = 'None'
        headers = {
            "user-agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.108 Safari/537.36 "}
        listFiles = []
        if image_urls:
            for image_url in image_urls:

                # 1\存储图片到本地
                response = requests.get(image_url, headers=headers, timeout=60).content
                file_name = md5(response).hexdigest()
                file = '{0}/{1}.{2}'.format(os.getcwd(), file_name, 'jpg')
                if not os.path.exists(file):
                    with open(file, "wb") as f:
                        f.write(response)
                        f.close()

                # 2\判断图片是否已经存在,上传到fdfs服务器
                full_name = os.getcwd() + "/" + file_name + '.jpg'
                a = str(os.path.getsize(full_name) / 1024)
                b = round(float(a), 2)

                ret = client.upload_by_filename(full_name)
                new_url = str(ret['Remote file_id'], encoding="utf8")

                # 3\返回fdfs服务器的远程路径,替换content中的image_url
                content = content.replace(image_url, new_url)
                filemodel = {}
                filemodel['FileID'] = str(uuid.uuid1())
                filemodel['FileType'] = 0
                filemodel['FileDirectory'] = new_url
                filemodel['FileDirectoryCompress'] = new_url
                filemodel['FileDate'] = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time()))
                filemodel['FileLength'] = b
                filemodel['FileUserID'] = None
                filemodel['Description'] = None
                filemodel['NewsID'] = item['NewsID']
                filemodel['image_url'] = image_url
                listFiles.append(filemodel)

                # time.sleep(0.1)
                # 4\删除本地文件
                os.remove(full_name)

        else:
            item['NewsContent'] = ''.join(response.xpath('//div[@id="contentMain"]/p').extract())
        item['NewsContent'] = content
        item['FileList'] = listFiles

        yield item
