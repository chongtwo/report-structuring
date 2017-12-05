# 报告结构化

![](https://img.shields.io/badge/python-3.6-blue.svg)

## 使用

安装依赖

```
pip install -r requirements
```

启动服务器

```
python manage.py runserver 0.0.0.0:80
```

## API

```
nlp/process/?msg={content}
```

`{content}` 代表一段报告

返回结果

```json
{"results" : [
    {
      "主干部位": "",
      "细节部位": "",
      "区域": "",
      "形状": "",
      "诊断": "",
      "量词": "",
      "变化": "",
      "可能性": ""
    }
],
 "origin_msg": "原始报告"}
```

