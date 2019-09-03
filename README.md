## 衢州市政府爬虫

### Introduction

爬取[衢州市政府](http://www.qz.gov.cn)的人员及组织情况, 并生成树形结构, 将所有数据存入 Excel 中

### Requirements

* Python 2.7
* 依赖包
    - requests
    - beautifulsoup4
    - pandas

### Run

```bash
python main.py -entry www.qz.gov.cn -outfile output.xlsx
```

### Details

[具体实现过程](./qz_gov_spider.md)

或使用 reveal-md 查看
```bash
npm install -g reveal-md
reveal-md qz_gov_spider.md --separator "<\!--s-->" --vertical-separator "<\!--v-->"
```
