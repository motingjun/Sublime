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
from takungpaoproject.items import TakungpaoprojectItem


class GuojiSpider(CrawlSpider):
    name = 'GuoJi'
    # allowed_domains = ['www.takungpao.com']
    start_urls = ['http://www.takungpao.com/']

    rules = (
        Rule(LinkExtractor(allow=r'http://news.takungpao.com/world/\w+'), callback='parse_item', follow=True),
    )

    def parse_item(self, response):
        client = Fdfs_client('/etc/fdfs/client.conf')
        # print(response.url)
        item = TakungpaoprojectItem()
        item['NewsID'] = str(uuid.uuid1())
        item['NewsCategory'] = '001.020'
        item['SourceCategory'] = '大公网重点报道'
        item['NewsType'] = 0
        item['NewsTitle'] = response.xpath('//div[@class="tpk_con clearfix"]/h1/text()').extract_first()
        item['NewsRawUrl'] = response.url

        name = response.xpath('//div[@class="fl_dib"][2]/a/text()').extract_first()
        if name is None:
            item['SourceName'] = response.xpath('//div[@class="fl_dib"][2]/text()').extract_first()[3:]
        else:
            item['SourceName'] = name

        item['AuthorName'] = response.xpath('//div[@class="tkp_con_author clearfix"]/span/text()').extract_first()[5:8]
        item['InsertDate'] = time.strftime('%Y-%m-%d %H-%M-%S', time.localtime(time.time()))
        item['NewsDate'] = response.xpath('//div[@class="fl_dib"][1]/text()').extract_first()
        item['NewsClickLike'] = 0
        item['NewsBad'] = 0
        item['NewsRead'] = 0
        item['NewsOffline'] = 0

        # 获取图片链接
        image_urls = response.xpath(
            '//div[@class="tpk_con clearfix"]/div[@class="tpk_text clearfix"]/p/img/@src |'
            '//div[@class="tpk_text clearfix"]/div/center//img/@src').extract()
        try:
            content = ''.join(response.xpath(
                '//div[@class="tpk_con clearfix"]/div[@class="tpk_text clearfix"]/p |'
                '//div[@class="tpk_text clearfix"]/div/p').extract())
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
            item['NewsContent'] = ''.join(response.xpath(
                '//div[@class="tpk_con clearfix"]/div[@class="tpk_text clearfix"]/p |'
                '//div[@class="tpk_text clearfix"]/div/p').extract())
        item['NewsContent'] = content
        item['FileList'] = listFiles

        yield item