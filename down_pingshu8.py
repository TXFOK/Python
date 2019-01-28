#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
###########################################################
#    时间：2018-11-10 15:29:48
#    作者: ferret
#  Email：ferret@NJTech
#    版本: 0.1
#  评书下载：from  http://www.pingshu8.com
###########################################################
"""


import os
import subprocess
import logging
from datetime import datetime
import requests
from bs4 import BeautifulSoup, Tag
from urllib import parse
import time


# class JobDown:
#     def __init__(self, session, requestUrl, saveFolder, logger=None):
#         self.__sess = session
#         self.__targetLink = requestUrl
#         self.__logger = logger

#     def __header(self):
#         head = {
#             'Accept': 'application/json, text/javascript, */*; q=0.01',
#             'Accept-Encoding': 'gzip, deflate',
#             'Accept-Language': 'zh-CN,zh;q=0.9',
#             'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36'
#         }
#         return head

#     async def __download(self):
#         loop = asyncio.get_event_loop()
#         ret_future = loop.run_in_executor(None, self.download)
#         result = await ret_future
#         return result

#     def download(self, url):
#         print('get :run....')
#         loop = asyncio.get_event_loop()
#         ret_future = loop.run_in_executor(None, requests.get, url)
#         result = await ret_future
#         return result


class Session:

    def __init__(self, links, LogLevel=logging.DEBUG):
        self.__sess = requests.session()

        self.__logger = self.__setupLogger(logLevel=LogLevel)
        self.__logger.info("脚本 {} 开始运行,时间：{} ".format(
                           os.path.basename(__file__), self.__currentTime()))
        # 评书的链接
        self.__psLinks = links

        self.__taskLink = self.__getEpisodes()

    def __getEpisodes(self):
        '''
        获取每集评书的页面，在这个页面上获取音频地址，并添加到任务
        '''
        logger = self.__logger
        for link in self.__psLinks:
            # 获取当前评书分页，
            collections = self.__collectionLinks(link)
            time.sleep(0.1)
            # 遍历每一页，获取素有的音频页面地址
            result = self.__getEpisodeLink(collections)
            # result.extend(r)

            # logger.info(result)
            logger.info("下载完成")

        return result

    def __getEpisodeLink(self, pageUrls):
        logger = self.__logger
        cmds = []
        if not isinstance(pageUrls, list):
            pageUrls = list(pageUrls)

        head = {
            # 'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Accept-Encoding': 'gzip, deflate',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.84 Safari/537.36'
        }

        basePath = os.path.abspath(os.path.dirname(__file__))

        env = os.environ.copy()
        # print(env['PATH'])

        page_counts = len(pageUrls)
        logger.info("共有 {} 个页面".format(page_counts))
        for idx, pageUrl in enumerate(pageUrls):
            logger.info(
                "当前访问第{}/{}个页面: {}".format(idx+1, page_counts, pageUrl))
            r = self.__sess.get(pageUrl, headers=head)
            r.encoding = 'gbk'
            if r.ok and r.text.strip():
                soup = BeautifulSoup(r.text, 'lxml')
                input_tags = soup.findAll('input', attrs={'name': 'id'})
                for input_tag in input_tags:
                    page = "http://www.pingshu8.com/path_{}.html".format(
                        input_tag.attrs['value'])
                    time.sleep(0.1)
                    j = self.__sess.get(page, headers=head)
                    j.encoding = 'utf-8'
                    link = j.json().get('urlpath').replace('flv', 'mp3')
                    _, folder, filename = parse.urlsplit(
                        link).path.rsplit('/', 2)
                    working_path = os.path.join(basePath, folder)
                    cmd = 'wget -c  "{}" -O {}'.format(
                        link, filename)
                    if not os.path.exists(working_path):
                        os.mkdir(working_path)
                    if os.path.exists(os.path.join(working_path, filename)):
                        continue
                    rst = self.__runCommand(
                        cmd, Env=env, workingPath=working_path)
                    logger.info(rst)
                    cmds.append(cmd)
            else:
                logger.error("网络访问错误:{},错误代码：{}".format(
                    r.reason, r.status_code))
        return cmds

    def __collectionLinks(self, link):
        logger = self.__logger
        results = []
        r = self.__sess.get(link)
        r.encoding = 'gbk'
        if r.ok and r.text.strip():
            soup = BeautifulSoup(r.text, 'lxml')
            logger.info('当前评书集名称：{}'.format(soup.title.text.strip()))
            itemContainer = soup.find('select', attrs={'name': 'turnPage'})
            # print(itemContainer)
            if isinstance(itemContainer, Tag):
                items = itemContainer.findAll('option')
                for item in items:
                    results.append('{}{}'.format(
                        'http://www.pingshu8.com', item.attrs['value']))
                logger.info("获取当前评书集所有页面链接完成，总共有 {} 个页面".format(len(results)))
                logger.info("开始获取每个页面内的音频链接")

            else:
                logger.error("找不到音频列表")
        else:
            logger.error("网络访问错误:{},错误代码：{}".format(r.reason, r.status_code))
        logger.debug(results)

        return results

    # 创建日志

    def __setupLogger(self, logLevel=logging.DEBUG):

        # ---- 日志文件
        fName, _ = os.path.splitext(os.path.basename(__file__))
        logFileName = "{}/{}_log.txt".format(
            os.path.abspath(os.path.dirname(__file__)), fName)

        logger = logging.getLogger("runLog")
        logger.setLevel(logLevel)
        fh = logging.FileHandler(logFileName, 'w', 'utf-8')
        ch = logging.StreamHandler()
        fmtStr = ""
        if logLevel == logging.ERROR:
            fmtStr = "%(asctime)s (%(filename)s:%(lineno)d)[%(levelname)s]:%(message)s"
        elif logLevel == logging.CRITICAL:
            fmtStr = "%(asctime)s (%(filename)s:%(lineno)d)[%(levelname)s]:%(message)s"
        elif logLevel == logging.DEBUG:
            fmtStr = "%(asctime)s (%(filename)s:%(lineno)d)[%(levelname)s]:%(message)s"

        logFmt = logging.Formatter(fmtStr, "%Y-%m-%d %H:%M:%S")
        fh.setFormatter(logFmt)
        ch.setFormatter(logFmt)
        logger.addHandler(fh)
        logger.addHandler(ch)
        return logger

        # 关闭日志
    def __closeLogger(self):
        for hdl in self.__logger.handlers[:]:
            hdl.close()
            self.__logger.removeHandler(hdl)

    def end(self):

        # try:
        #     self.__loop.run_until_complete(task)
        # finally:
        #     self.__loop.close()

        self.__logger.info("脚本 %s 运行完成,时间：%s " %
                           (os.path.basename(__file__), self.__currentTime()))
        self.__closeLogger()

    # 区分显示时间格式
    def __currentTime(self, fmtStd=True):
        # 默认为标准显示时间(fmtStd为真)，否则用于文件名
        timeFmt = "%Y-%m-%d %H:%M:%S" if fmtStd else "%Y%m%d-%H%M%S"
        return datetime.now().strftime(timeFmt)

    def __lookforFiles(self, rootdir=".", searchExample=True):
        logger = self.__logger

        result = []
        if searchExample == True:
            for root, _, filenames in os.walk(rootdir):
                mkFiles = [os.path.join(root, f) for f in filenames
                           if f == 'Makefile' and 'examples' in root]
                for f in mkFiles:
                    logger.debug("mkFile :{}".format(f))

                result.extend(mkFiles)
        else:   # 修改 qt creator Makefile
            toModified = ['Makefile', 'Makefile.process_stub', 'Makefile.qmldesignerplugin', 'Makefile.process_ctrlc_stub',
                          'Makefile.data', 'Makefile.static']
            for root, _, filenames in os.walk(rootdir):
                mkFiles = [os.path.join(root, f)
                           for f in filenames if f in toModified]
                for f in mkFiles:
                    logger.debug("mkFile :{}".format(f))

                result.extend(mkFiles)
        return result

    def __runCommand(self, cmd, Env=None, workingPath=None):
        '''
            执行shell命令，windows平台下为dos命令
        '''

        process = subprocess.Popen(cmd, shell=True, env=Env,
                                   stderr=subprocess.STDOUT,
                                   stdout=subprocess.PIPE,
                                   cwd=workingPath)
        rst = process.stdout.read().decode("GBK").strip()
        '''
        while True:
            print('running')
            rst = process.stdout.readline().decode("GBK").strip()
            if rst == '' and process.poll() is not None:
                break
            if rst:
                print(rst)
        rc = process.poll()
        '''
        return rst


if __name__ == "__main__":

    conf = "pingshu8.conf"

    requestLinks = []

    if not os.path.exists(conf):
        with open(conf, 'w', encoding='utf-8') as f:
            f.writelines("# 配置文件示例\n")
            f.writelines(
                '# http://www.pingshu8.com/Musiclist/mmc_38_184_1.htm')
    else:
        with open(conf, 'r', encoding='utf-8') as f:
            requestLinks.extend(
                [line.strip() for line in f if not line.startswith("#") and line.strip()])

    # requestLinks = [
        # 'http://www.pingshu8.com/MusicList/mmc_27_247_1.Htm',
    #    'http://www.pingshu8.com/Musiclist/mmc_38_184_1.htm'
    # ]
    # print(requestLinks)
    if requestLinks:
        j = Session(links=requestLinks, LogLevel=logging.INFO)
        j.end()
    else:
        print('配置文件为空')


# import asyncio
# import requests
# from functools import partial

# def getText(future_result, sub):
#     r = future_result.result()
#     print(len(r.text))
#     print( int(r.status_code)/2)  # 如果访问正常，结果 = 100.0

# async def get(url):
#     print('get :run....')
#     loop =asyncio.get_event_loop()
#     ret_future = loop.run_in_executor(None,requests.get,url)
#     result = await ret_future
#     return result

# link = 'http://www.njtech.edu.cn'
# loop = asyncio.get_event_loop()
# task = loop.create_task(get(link))
# task_call_back = partial(getText,sub=2)
# task.add_done_callback(task_call_back)
# # 也可以用以下两句
# # task = asyncio.ensure_future(get(link))
# # task.add_done_callback(task_call_back)

# try:
#     loop.run_until_complete(task)
# finally:
#     loop.close()
