import jieba
import xlrd
import re
import xlwt
from datetime import datetime


jieba.load_userdict('static/术语.txt')


# 生成字典
def gen_term_dict(in_file_loc):
    data = xlrd.open_workbook(in_file_loc)
    table = data.sheet_by_index(0)
    term_dict_inner = {}
    for i in range(table.nrows):
        term_dict_inner[table.cell(i, 0).value] = table.cell(i, 1).value
    return term_dict_inner


term_dict = gen_term_dict('static/人工词典积累.xlsx')
mod_token_dict = gen_term_dict('static/分词修改词典.xlsx')


def compile_rule(rules_file):
    with open(rules_file, 'r', encoding='utf-8-sig') as f:
        rule_list_inner = []
        for line in f:
            rule_list_inner.append(re.compile(line.strip()))

        return rule_list_inner


rule_list = compile_rule('static/combine_rule.txt')


def seg_sentence(document):
    """断句

    :param document: 一篇文档，或一个句子
    :return:
    """
    return document.replace('，', '，\n').replace('。', '。\n').replace('；', '；\n')


def word_segment(sentence):
    """分词

    :param sentence: 一篇句子，中间不带逗号和句号
    :return: 分词的结果，如傻不拉几/小瓜皮
    """
    seg = jieba.cut(sentence)
    return "/".join(seg)


def modify_segment(seg_result):
    for key in mod_token_dict:
        seg_result = seg_result.replace(key, mod_token_dict[key])
    return seg_result


def semantic_match(sentence):
    match_dict = dict()
    word_list = sentence.split('/')

    count = 0
    n_word = 0

    for word in word_list:
        if word in term_dict:
            word_list[n_word] = f'{term_dict[word]}#{count}#'
            match_dict[f'{term_dict[word]}#{count}#'] = word
        else:
            word_list[n_word] = f'其他#{count}#'
        count += 1
        n_word += 1
    after_match = "".join(word_list)
    return after_match, match_dict


def combine_word(after_match, match_dict):
    """将一些小型的词合并，如 密度 和 影 合并成 密度影

    :param after_match: 匹配之后的结果
    :param match_dict: 匹配到的词
    :return:
    """
    count = 0
    for i, r in enumerate(rule_list):
        match = r.finditer(after_match)
        if match:
            if i in [0, 1, 2]:
                for find in match:
                    string = ''
                    string = string + match_dict[find.group(1)] + match_dict[find.group(2)]  # 合并“密度”与“影”
                    match_dict[f'诊断${count}$'] = string
                    match_dict.pop(find.group(1))
                    match_dict.pop(find.group(2))
                    count += 1

            elif i == 3:
                for find in match:
                    string = ''
                    string = string + match_dict[find.group(1)] + match_dict[find.group(3)]
                    match_dict[f'诊断${count}$'] = string
                    match_dict.pop(find.group(1))
                    match_dict.pop(find.group(3))
                    count += 1

            elif i in [4, 5]:
                for find in match:
                    string = ''
                    count = 0
                    string = string + match_dict[find.group(1)] + match_dict[find.group(2)]
                    match_dict[f'性状${count}$'] = string
                    match_dict.pop(find.group(1))
                    match_dict.pop(find.group(2))
                    count += 1


last_list_zgbw = ''


# 一对多，多对一，多对多的抽取
def cline_extract(match_dict, after_match):
    global last_list_zgbw
    list_zgbw = []
    for k, v in match_dict.items():
        if '主干部位' in k:
            list_zgbw.append(v)

    if len(list_zgbw) == 0:
        list_zgbw.append(last_list_zgbw)
    else:
        last_list_zgbw = list_zgbw[-1]

    # if len(list_zgbw) > 1:
    results = []
    keys = ['主干部位', '细节部位', '区域', '性状', '诊断', '量词', '变化', '可能性']
    for i in range(len(list_zgbw)):
        # result['item' + str(i)] = ['' for n in range(8)]
        results.append({k: "" for k in keys})

    rule = re.compile(r'(主干部位#[0-9]+#)|(区域#[0-9]+#)(细节部位#[0-9]+#)(主干部位#[0-9]+#)')
    try:
        next(rule.finditer(after_match))
        for i, find in enumerate(rule.finditer(after_match)):  # find=主干部位 or 区域细节部位主干部位
            for j in range(len(find.groups())):  # 对每一条find中的每一组
                if find.group(j + 1):
                    if '主干部位' in find.group(j + 1):
                        results[i]['主干部位'] += match_dict[find.group(j + 1)]
                    elif '细节部位' in find.group(j + 1):
                        results[i]['细节部位'] += match_dict[find.group(j + 1)]+ ','
                    elif '区域' in find.group(j + 1):
                        results[i]['区域'] += match_dict[find.group(j + 1)]
                    match_dict.pop(find.group(j + 1))
    except StopIteration:
        results[0]['主干部位'] = list_zgbw[0]
    for j in range(len(list_zgbw)):
        for k, v in match_dict.items():
            if '细节部位' in k:
                results[j]['细节部位'] += v + ','
            elif '区域' in k:
                results[j]["区域"] += v + ','
            elif '性状' in k:
                results[j]['性状'] += v + ','
            elif '诊断' in k and '诊断后缀' not in k:
                results[j]['诊断'] += v + ','
            elif '量词' in k:
                results[j]['量词'] += v + ','
            elif '变化' in k:
                results[j]['变化'] += v + ','
            elif '可能性' in k:
                results[j]['可能性'] += v + ','
    return results


def write_excel(rslt, sentence, aftermatch):
    """

    :param rslt: 抽取后的字典
    :param sentence: 分词及修正后的句子
    :param aftermatch: 语义匹配后的句子
    :return:
    """
    global nrow
    global sheet
    sheet.write(nrow, 0, sentence)
    sheet.write(nrow, 1, aftermatch)
    for r in rslt:
        for k, v in r.items():
            if "主干部位" in k:
                sheet.write(nrow, 2, v)
            elif "细节部位" in k:
                sheet.write(nrow, 3, v)
            elif "区域" in k:
                sheet.write(nrow, 4, v)
            elif "性状" in k:
                sheet.write(nrow, 5, v)
            elif "诊断" in k:
                sheet.write(nrow, 6, v)
            elif "量词" in k:
                sheet.write(nrow, 7, v)
            elif "变化" in k:
                sheet.write(nrow, 8, v)
            elif "可能性" in k:
                sheet.write(nrow, 9, v)
        nrow += 1
        print(nrow)


def processing_procedure(sentence):
    global sheet
    sentences = seg_sentence(sentence)
    sentence_list = sentences.split('\n')
    sentence_list.pop(-1)
    results = []
    for s in sentence_list:
        words = word_segment(s)
        words = modify_segment(words)
        after_match, match_dict = semantic_match(words)
        combine_word(after_match, match_dict)
        result = cline_extract(match_dict, after_match)
        results.extend(result)
        write_excel(result, words, after_match)
    return results, sentence_list




if __name__ == "__main__":
    # s = "胸部CT平扫未见异常，双肺野清晰。"
    now = datetime.now().strftime("%Y-%m-%d-%H-%M-%S")
    source_file = "D:/1.放射报告结构化/公司给的原始数据/CT胸部平扫约4000份-描述.txt"
    output_file = "D:/1.放射报告结构化/公司给的原始数据/CT胸部平扫约4000份-output" + now + ".xls"
    wb = xlwt.Workbook(encoding='utf-8')
    global sheet
    sheet = wb.add_sheet("Result")
    row0 = ['原句', '语义匹配', '主干部位', '细节部位', '区域', '性状', '诊断', '量词', '变化', '可能性']
    for i in range(len(row0)):
        sheet.write(0, i, row0[i])
    global nrow
    nrow = 1  # 记录总行数
    with open(source_file, 'r', encoding='utf-8-sig', errors='ignore') as inf:
        s = inf.readline()
        while s:
            if s != r'/':
                results, sentence_list = processing_procedure(s)
                wb.save(output_file)
            s = inf.readline().strip()
    # print(results, nrow)
