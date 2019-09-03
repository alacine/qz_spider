# -*- coding: utf-8 -*-
"""爬取衢州市政府人员及组织架构
usage: qz_gov_v2.py [-h] entry outfile

example: argpares_test entry="qz.gov.cn" outfile="a.xlsx"

positional arguments:
  entry       the entry of the government
  outfile     the output Excel filename

optional arguments:
  -h, --help  show this help message and exit
"""
from __future__ import print_function, unicode_literals
# from builtins import range

import os
import shutil
import sys
import argparse
import time
import re

import requests
from bs4 import BeautifulSoup
import pandas as pd


def get_args():
    """获取命令行参数
    Return:
        二元元组(入口 url, 保存的文件名称)
    """
    parser = argparse.ArgumentParser(
        description='example: python main.py -entry www.qz.gov.cn -outfile a.xlsx'
    )
    parser.add_argument('-entry', type=str, help='the entry of the government')
    parser.add_argument('-outfile', type=str, help='the output Excel filename')
    args = parser.parse_args()
    entry = args.entry
    outfile = args.outfile
    # 只支持衢州政府
    if entry not in ['qz.gov.cn', 'www.qz.gov.cn', 'http://www.qz.gov.cn']:
        print('Check your entry, Only supoort Quzhou govnment!')
        exit(1)
    # 确保 Excel 文件名有效
    if len(outfile) < 5 or outfile[-4:] != 'xlsx':
        outfile += '.xlsx'
    return (entry, outfile)


def print_status(func):
    """装饰器, 用来查看运行情况"""
    def wrapper(self, *args):
        print('start ' + func.__name__ + '...')
        begin = time.time()
        func(self, *args)
        end = time.time()
        print('done in', end-begin, 's')
    return wrapper


def create_params(i_id, currpage=1):
    """构造请求参数"""
    return {
        'divid': 'div1525479',
        'infotypeId': i_id,  # 类型(领导, 下属单位, 内设机构)
        'jdid': '3084',
        'area': '',
        'sortfield': '',
        'currpage': currpage  # 翻页功能
    }


def get_html(url, params=None):
    """构建请求并获得返回的 html
    Args:
        url (str): 链接
        params (dict): 请求参数
        headers (dict): 请求头部
    Return:
        A BeautifulSoup object
    """
    headers = {
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/75.0.3770.142 Safari/537.36',
        'Cookie': 'xxxxx'
    }
    response = requests.get(url, params=params, headers=headers)
    response.encoding = response.apparent_encoding
    return BeautifulSoup(response.text, features='lxml')


def no_blank(string):
    """用于去掉数据中的空格和换行符号
    Return:
        去掉空白符后的字符串
    """
    return re.sub(r'\s+', '', string).replace(u'\xa0', '')


class GovSpiderV2(object):
    """衢州市政府爬虫"""
    api = '/module/xxgk/search.jsp'
    leader_iid = 'A0102'
    builtin_unit_iid = 'A0103'
    sub_unit_iid = 'A0104'
    i_id = [leader_iid, builtin_unit_iid, sub_unit_iid]
    tmp_data = 'GovSpider_tmp_data/'  # 临时产生的 csv 文件存放目录

    def __init__(self, entry, path, space):
        """ 初始化
        args:
            entry (url): 入口 url
            path (str): 数据存储目录
            space (int): 每 10 次爬取暂停秒数
        """
        self.path = os.path.join(path, self.tmp_data)
        if not entry.startswith('http://'):
            if not entry.startswith('www.'):
                entry = 'www.' + entry
            entry = 'http://' + entry
        self.url = entry + self.api
        self.space = space

        # 第一级页面
        self.dir_heads = []
        self.leaders_dir = []
        self.builtin_units_dir = []
        self.sub_units_dir = []

        # 第二级页面
        self.leader_heads = []
        self.leaders = []
        self.builtin_unit_heads = []
        self.builtin_units = []
        self.sub_unit_heads = []
        self.sub_units = []

        # 整理机构结构
        self.tree_root = '市政府'
        self.unit_tree = [[self.tree_root, '', '']]
        self.unit_tree_head = ['机构', '上级', '类型']

        # 数据对应的所有文件名称
        self.csv_list = {
            'leaders_dir': '领导目录.csv',
            'builtin_units_dir': '内设机构目录.csv',
            'sub_units_dir': '下属单位目录.csv',
            'leaders': '领导详细信息.csv',
            'builtin_units': '内设机构详细信息.csv',
            'sub_units': '下属单位详细信息.csv',
            'unit_tree': '机构层次结构.csv'
        }

    @print_status
    def get_dir_heads(self):
        """获取目录页面的表头"""
        soup = get_html(self.url, create_params(self.i_id[0]))
        heads_html = soup.find_all('strong')
        self.dir_heads = [head.text for head in heads_html]
        self.dir_heads.append('url')

    @print_status
    def get_dir_content(self):
        """获取目录页面的所有数据"""
        for iid in self.i_id:
            print('   ', iid, end=' ')
            page = 0

            while True:
                page += 1
                if page % 10 == 0:
                    print(page, end=' ')
                    time.sleep(self.space)

                soup = get_html(self.url, create_params(iid, page))
                index_html = soup.find_all(
                    'td',
                    attrs={
                        'height': '32',
                        'align': 'center',
                        'width': '220'
                    }
                )
                if not index_html:
                    print('get', page-1, 'pages')
                    break
                names_html = soup.find_all(
                    'a',
                    attrs={
                        'target': '_blank',
                        'style': 'cursor:hand;'
                    }
                )
                date_html = soup.find_all(
                    'td',
                    attrs={
                        'align': 'center',
                        'width': '90'
                    }
                )
                unit_html = soup.find_all(
                    'td',
                    attrs={
                        'align': 'center',
                        'width': '99'
                    }
                )

                index = [ih.text for ih in index_html]
                names = [nh.text for nh in names_html]
                date = [dh.text for dh in date_html]
                units = [uh.text for uh in unit_html]
                links = [nh.get('href') for nh in names_html]

                dir_data = []
                for i in range(len(index)):
                    dir_data.append(
                        [index[i], names[i], date[i], units[i], links[i]]
                    )
                if iid == self.leader_iid:
                    self.leaders_dir.extend(dir_data)
                elif iid == self.builtin_unit_iid:
                    self.builtin_units_dir.extend(dir_data)
                else:
                    self.sub_units_dir.extend(dir_data)

    @print_status
    def get_leaders_heads(self):
        """获取领导详细信息的头部"""
        for ldir in self.leaders_dir:
            link = ldir[4]

            if link.startswith('http://fgw'):
                soup = get_html(link)
                heads_html = soup.find_all(
                    'span',
                    attrs={
                        'style': re.compile(r'color: rgb\(77, 153, 228\);')
                    }
                )
                self.leader_heads = [
                    no_blank(hh.text) for hh in heads_html if len(hh.text) > 1
                ]
                break

    @print_status
    def get_leaders(self):
        """获取领导的详细信息"""
        page = 0
        for ldir in self.leaders_dir:
            page += 1
            if page % 10 == 0:
                time.sleep(self.space)

            link = ldir[4]
            soup = get_html(link)
            if link.startswith('http://fgw'):
                info_html = soup.find_all('td')
                info = [
                    no_blank(ih.text) for ih in info_html if '>' not in ih.text
                ]
                info = [info[2], info[5], info[7], info[9], info[11]]
            elif link.startswith('http://www'):
                info_html = soup.find_all('td', attrs={'bgcolor': '#FFFFFF'})
                info = [no_blank(ih.text) for ih in info_html]
                info.insert(2, '')
            else:
                print('found a new type of link!')
            self.leaders.append(info)

        print('    get', page, 'pages')

    @print_status
    def get_builtin_unit_heads(self):
        """获取内设机构的头部"""
        soup = get_html(self.builtin_units_dir[0][4])
        heads_html = soup.find_all('td', attrs={'bgcolor': '#EBEBEB'})
        heads = [
            no_blank(hh.text).strip(':') for hh in heads_html if len(hh.text) > 1
        ]
        another_head = soup.find(
            'table',
            attrs={
                'width': '100%',
                'cellspacing': '0',
                'cellpadding': '0',
                'border': '0'
            }
        )
        target_head = another_head.find_all('td')[4]
        heads.append(u'是谁的'+no_blank(target_head.text).replace('>', ''))
        self.builtin_unit_heads = heads

    @print_status
    def get_builtin_units(self):
        """获取所有的内设机构详细信息"""
        page = 0
        for bdir in self.builtin_units_dir:
            page += 1
            if page % 10 == 0:
                time.sleep(self.space)

            link = bdir[4]
            soup = get_html(link)
            info_html = soup.find_all('td', attrs={'bgcolor': '#FFFFFF'})
            info = [no_blank(ih.text) for ih in info_html]
            if not info[0]:
                tmp_name = soup.find(
                    'td',
                    attrs={
                        'style': 'font-size:16pt;color:#C02020;font-weight:bold;padding-bottom:10px;'
                    }
                )
                info[0] = tmp_name.text
            another_info = soup.find(
                'table',
                attrs={
                    'width': '100%',
                    'cellspacing': '0',
                    'cellpadding': '0',
                    'border': '0'
                }
            )
            target_info = another_info.find_all('td')[2]
            info.append(no_blank(target_info.text).replace('>', ''))
            self.builtin_units.append(info)
        print('    get', page, 'pages')

    @print_status
    def get_sub_unit_heads(self):
        """获取下属单位的头部(这里头部有两种, 获取长的那一种)"""
        heads_length = 0
        for sdir in self.sub_units_dir:
            link = sdir[4]
            soup = get_html(link)
            heads_html = soup.find_all('td', attrs={'bgcolor': '#EBEBEB'})
            _heads = [
                no_blank(hh.text).strip(':') for hh in heads_html if len(hh.text) > 1
            ]
            _length = len(_heads)
            another_head = soup.find(
                'table',
                attrs={
                    'width': '100%',
                    'cellspacing': '0',
                    'cellpadding': '0',
                    'border': '0'
                }
            )
            target_head = another_head.find_all('td')[4]
            _heads.append(u'是谁的'+no_blank(target_head.text).replace('>', ''))
            if _length > heads_length:
                heads = _heads
                heads_length = _length
        self.sub_unit_heads = heads

    @print_status
    def get_sub_units(self):
        """获取所有的下属单位的详细信息"""
        page = 0
        for sdir in self.sub_units_dir:
            link = sdir[4]
            page += 1
            if page % 10 == 0:
                time.sleep(self.space)

            soup = get_html(link)
            info_html = soup.find_all('td', attrs={'bgcolor': '#FFFFFF'})
            info = [no_blank(ih.text) for ih in info_html]
            if not info[0]:
                tmp_name = soup.find(
                    'td',
                    attrs={
                        'style': 'font-size:16pt;color:#C02020;font-weight:bold;padding-bottom:10px;'
                    }
                )
                info[0] = tmp_name.text
            if len(info_html) == 5:
                info.insert(4, '')
            another_info = soup.find(
                'table',
                attrs={
                    'width': '100%',
                    'cellspacing': '0',
                    'cellpadding': '0',
                    'border': '0'
                }
            )
            target_info = another_info.find_all('td')[2]
            info.append(no_blank(target_info.text).replace('>', ''))
            self.sub_units.append(info)
        print('    get', page, 'pages')

    @print_status
    def create_unit_tree(self):
        """构造机构的层级结构"""
        sub_unit_type = '下属单位'
        builtin_unit_type = '内设机构'
        all_unit, seen = set(), set()
        seen.add(self.tree_root)
        unit_dict = {}
        unit, sunit, bunit = 6, 0, 0

        for row in self.sub_units:
            unit_dict[row[unit]] = [self.tree_root, sub_unit_type]
            unit_dict[row[sunit]] = [row[unit], sub_unit_type]
            all_unit.add(row[unit])
            all_unit.add(row[sunit])
        for row in self.builtin_units:
            unit_dict[row[unit]] = [self.tree_root, builtin_unit_type]
            unit_dict[row[bunit]] = [row[unit], builtin_unit_type]
            all_unit.add(row[unit])
            all_unit.add(row[bunit])

        while unit_dict:
            tmp_seen = set()
            for unit in all_unit:
                if unit in unit_dict and unit_dict[unit][0] in seen:
                    self.unit_tree.append(
                        [unit, unit_dict[unit][0], unit_dict[unit][1]]
                    )
                    unit_dict.pop(unit)
                    tmp_seen.add(unit)
            seen |= tmp_seen

    @print_status
    def write_to_csv(self, sep):
        """数据写入csv文件"""
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        for key, filename in self.csv_list.items():
            if key == 'leaders_dir':
                data = self.leaders_dir
                heads = self.dir_heads
            elif key == 'builtin_units_dir':
                data = self.builtin_units_dir
                heads = self.dir_heads
            elif key == 'sub_units_dir':
                data = self.sub_units_dir
                heads = self.dir_heads
            elif key == 'leaders':
                data = self.leaders
                heads = self.leader_heads
            elif key == 'builtin_units':
                data = self.builtin_units
                heads = self.builtin_unit_heads
            elif key == 'sub_units':
                data = self.sub_units
                heads = self.sub_unit_heads
            else:
                data = self.unit_tree
                heads = self.unit_tree_head

            with open(os.path.join(self.path, self.csv_list[key]), 'w') as data_file:
                print(
                    '    writing data to', os.path.join(self.path, filename)
                )
                data_file.write(sep.join(heads)+'\n')  # 写入头部
                for line in data:
                    data_file.write(sep.join(line)+'\n')  # 写入内容
                print('    done')

    @print_status
    def csv_to_excel(self, excelname, sep=','):
        """将 csv 数据转存入 Excel"""
        if not os.path.exists(self.path):
            os.mkdir(self.path)
        with pd.ExcelWriter(excelname) as writer:
            for key, csv_name in self.csv_list.items():
                print(csv_name)
                csv = pd.read_csv(
                    os.path.join(self.path, csv_name), sep=sep, encoding='utf-8'
                )
                if key == 'builtin_units':
                    csv.rename(
                        columns={'是谁的内设机构': '内设于'}, inplace=True
                    )
                    csv.sort_values('内设于', inplace=True)
                elif key == 'sub_units':
                    csv.rename(
                        columns={'是谁的下属单位': '上级单位'}, inplace=True
                    )
                    csv.sort_values('上级单位', inplace=True)

                csv.reset_index(drop=True, inplace=True)
                csv.to_excel(writer, sheet_name=csv_name)

    @print_status
    def clean_csv(self):
        """删除存放 csv 文件的临时目录"""
        shutil.rmtree(self.tmp_data)


def test_write_to_excel():
    """只测试写入 Excel 功能"""
    path = './data/'
    spider = GovSpiderV2('www.qz.gov.cn', path, 3)
    spider.csv_to_excel('衢州市政府信息.xlsx', '\t')


def test_get_args():
    """测试获取参数的功能"""
    args = get_args()
    print('entry:', args[0])
    print('outfile:', args[1])


def main():
    # 设置参数
    args = get_args()
    path = '.'
    space = 5

    # 爬取数据
    spider = GovSpiderV2(args[0], path, space)
    spider.get_dir_heads()
    spider.get_dir_content()
    spider.get_leaders_heads()
    spider.get_leaders()
    spider.get_sub_unit_heads()
    spider.get_sub_units()
    spider.get_builtin_unit_heads()
    spider.get_builtin_units()
    spider.create_unit_tree()

    # 保存数据
    spider.write_to_csv('\t')
    spider.csv_to_excel(args[1], '\t')

    # 清理临时文件
    spider.clean_csv()


if __name__ == '__main__':
    STDOUT = sys.stdout
    reload(sys)
    sys.setdefaultencoding('utf-8')
    sys.stdout = STDOUT
    # test_get_args()
    # test_write_to_excel()
    main()
