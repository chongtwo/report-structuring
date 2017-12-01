import jieba
import xlrd
import xlwt
import re
from datetime import datetime
from xlutils.copy import copy
# import xlutils
# 此代码存在的隐患：file.readline()可造成内存占用过大


# 断句
def whole_seg(in_file_loc, out_file_loc):  # 断句函数
    with open(in_file_loc, 'r', encoding='UTF-8', errors='ignore') as inf:
        with open(out_file_loc, 'w', encoding='UTF-8') as outf:
            for line in inf.readlines():
                segment = line.replace('，', '，\n').replace('。','。\n').replace('；', '；\n')
                outf.write(segment)


# 分词
def whole_tokenize(in_file_loc, out_file_loc):  # 分词函数
    jieba.load_userdict('./static/术语.txt')
    with open(in_file_loc, 'r', encoding='UTF-8', errors='ignore') as inf:
        f_seg = jieba.cut(inf.read())
        outcome = ("/".join(f_seg))
    with open(out_file_loc, 'w', encoding='UTF-8') as outf:
        outf.write(outcome)


# 生成字典
def gen_term_dict(in_file_loc):
    data = xlrd.open_workbook(in_file_loc)
    table = data.sheet_by_index(0)
    term_dict = {}
    for i in range(table.nrows):
        term_dict[table.cell(i, 0).value] = table.cell(i, 1).value
        # print("%s" % str(term_dict))
    return term_dict


class RawText(object):

    def __init__(self, term_f, modtoken_f):
        self.term_dict = gen_term_dict(term_f)  # 生成术语词典
        self.total_nword = 0  # 分词后的总词数
        self.match_nword = 0  # 匹配到的词数
        self.modtoken_dict = gen_term_dict(modtoken_f)
        self.row = 1
        self.last_list_zgbw = [1]  # 上一句话的主干部位列表，用于缺乏主干部位的句子

        self.workbook = xlwt.Workbook(encoding='utf-8')
        self.sheet1 = self.workbook.add_sheet("Sheet1")  # 直接抽取的结果
        self.sheet2 = self.workbook.add_sheet("Sheet2")  # 语义类有重复的结果
        self.sheet3 = self.workbook.add_sheet("Sheet3")  # 主干部位有重复的结果
        self.sheet4 = self.workbook.add_sheet("Sheet4")  # 主干部位没有重复的结果
        row0 = ['原句', '语义匹配', '主干部位', '细节部位', '区域', '性状', '诊断', '量词', '变化', '可能性']
        for i in range(len(row0)):
            self.sheet1.write(0, i, row0[i])
            self.sheet2.write(0, i, row0[i])
            self.sheet3.write(0, i, row0[i])
            self.sheet4.write(0, i, row0[i])

        r0 = r'(性状#[0-9]+#)(诊断后缀#[0-9]+#)'  # 密度影，充气征
        r1 = r'(性状#[0-9]+#)(变化#[0-9]+#)(诊断后缀#[0-9]+#)'  # 密度增高影
        r2 = r'(细节部位#[0-9]+#)(诊断后缀#[0-9]+#)'  # 淋巴结影
        r3 = r'(诊断#[0-9]+#)(诊断后缀#[0-9]+#)'  # 结节影
        r4 = r'(诊断#[0-9]+#)(性状后缀#[0-9]+#)'  # 结节状
        r5 = r'(性状#[0-9]+#)(性状后缀#[0-9]+#)'  # 液体样
        self.r6 = re.compile(r'(主干部位#[0-9]+#)|(区域#[0-9]+#)(细节部位#[0-9]+#)(主干部位#[0-9]+#)')
        self.rule_list = [r0, r1, r2, r3, r4, r5]
        for i, r in enumerate(self.rule_list):
            self.rule_list[i] = re.compile(r)

    # 分词后处理
    def whole_post_token(self, in_file_loc, out_file_loc):
        with open(in_file_loc, 'r', encoding='UTF-8', errors='ignore') as inf:
            with open(out_file_loc, 'w', encoding='UTF-8', errors='ignore') as outf:
                line = inf.readline()
                while line:
                    for key in self.modtoken_dict:
                        line = line.replace(key, self.modtoken_dict[key])
                    outf.write(line)
                    line = inf.readline()

    # 单句话的语义匹配
    def line_semantic_match(self, content):
        match_dict = {}
        word_list = content.split("/")
        word_list.pop(0)
        word_list.pop(-1)
        after_match = ''
        bd_list = ["，", "。", "、", "；"]
        if word_list:
            count = 0
            nword = 0
            for word in word_list:
                if self.term_dict.get(word):
                    self.match_nword += 1
                    #  加序号，不然key会重复
                    word_list[nword] = self.term_dict[word] + "#" + str(count) + "#"
                    match_dict[self.term_dict[word] + "#" + str(count) + "#"] = word
                    count = count + 1
                elif word in bd_list:
                    self.match_nword += 1
                else:
                    word_list[nword] = "其他" + "#" + str(count) + "#"
                    count = count + 1
                nword = nword + 1
            after_match = after_match.join(word_list)  # 语义匹配后的句子
            # print(after_match)  # 打印匹配后的句子
        return after_match, match_dict

    #  小词合并
    def line_rule_set1(self, semString, match_dict):
        count = 0
        for i, r in enumerate(self.rule_list):
            match = r.finditer(semString)
            if match:
                if i in [0, 2, 3]:
                    for find in match:
                        string = ''
                        string = string + match_dict[find.group(1)] + match_dict[find.group(2)]  # 合并“密度”与“影”
                        match_dict['诊断$' + str(count) + '$'] = string
                        match_dict.pop(find.group(1))
                        match_dict.pop(find.group(2))
                        count += 1

                elif i == 1:
                    for find in match:
                        string = ''
                        string = string + match_dict[find.group(1)] + match_dict[find.group(3)]
                        match_dict['诊断$' + str(count) + '$'] = string
                        match_dict.pop(find.group(1))
                        match_dict.pop(find.group(3))
                        count += 1

                elif i in [4, 5]:
                    for find in match:
                        string = ''
                        count = 0
                        string = string + match_dict[find.group(1)] + match_dict[find.group(2)]
                        match_dict['性状$' + str(count) + '$'] = string
                        match_dict.pop(find.group(1))
                        match_dict.pop(find.group(2))
                        count += 1

    # 一对多，多对一，多对多的抽取
    def cline_extract(self, m_dict, sem_string, out_file_loc):
        list_zgbw = []
        result = dict()
        for k, v in m_dict.items():
            if '主干部位' in k:
                list_zgbw.append(v)

        if len(list_zgbw) == 0:
            list_zgbw.append(self.last_list_zgbw)
        else:
            self.last_list_zgbw = list_zgbw[-1]

        # if len(list_zgbw) > 1:
        for i in range(len(list_zgbw)):
            result['item' + str(i)] = ['' for n in range(8)]

        try:
            next(self.r6.finditer(sem_string))
            for i, find in enumerate(self.r6.finditer(sem_string)):  # find=主干部位 or 区域细节部位主干部位
                for j in range(len(find.groups())):  # 对每一条find中的每一组
                    if find.group(j + 1):
                        if '主干部位' in find.group(j + 1):
                            result['item' + str(i)][0] += m_dict[find.group(j + 1)] + ','
                        elif '细节部位' in find.group(j + 1):
                            result['item' + str(i)][1] += m_dict[find.group(j + 1)] + ','
                        elif '区域' in find.group(j + 1):
                            result['item' + str(i)][2] += m_dict[find.group(j + 1)] + ','
                        m_dict.pop(find.group(j + 1))
        except StopIteration:
            result['item0'][0] = list_zgbw[0]
        for i in range(len(list_zgbw)):
            for k, v in m_dict.items():
                if '细节部位' in k:
                    result[f'item{i}'][1] += v + ','
                elif '区域' in k:
                    result[f'item{i}'][2] += v + ','
                elif '性状' in k:
                    result[f'item{i}'][3] += v + ','
                elif '诊断' in k and '诊断后缀' not in k:
                    result[f'item{i}'][4] += v + ','
                elif '量词' in k:
                    result[f'item{i}'][5] += v + ','
                elif '变化' in k:
                    result[f'item{i}'][6] += v + ','
                elif '可能性' in k:
                    result[f'item{i}'][7] += v + ','

            for l in range(8):
                self.sheet1.write(self.row, l, result[f'item{i}'][l-2])
            self.row += 1
        self.workbook.save(out_file_loc)

    def whole_match(self, in_file_loc, out_file_loc):
        with open(in_file_loc, encoding='utf-8', errors='ignore') as inf:
            line = inf.readline().strip()
            n = 0  # 跑程序标记
            while line:
                if line != r'/':
                    self.sheet1.write(self.row, 0, line)  # 写原句
                    sem_line, sem_dict = self.line_semantic_match(line)  # 语义匹配
                    self.sheet1.write(self.row, 1, sem_line)  # 写语义匹配
                    self.line_rule_set1(sem_line, sem_dict)
                    self.cline_extract(sem_dict, sem_line, out_file_loc)
                line = inf.readline().strip()
                n += 1
                print(n)
        print("已匹配,总词数：%d, %d" % (self.match_nword, self.total_nword))


if __name__ == "__main__":
    token_mod_loc = './static/分词修改词典.xlsx'
    term_xl_loc = './static/人工词典积累.xlsx'
    now = datetime.now().strftime('%Y-%m-%d-%H-%M-%S')

    ct_seg_in_file_loc = "./static/CT胸部平扫约4000份-描述.txt"
    ct_seg_out_file_loc = r"./static/CT胸部平扫约4000份-描述-分句.txt"
    ct_token_out_file_loc = r"./static/CT胸部平扫约4000份-描述-分词" + now + r".txt"
    ct_modtoken_out_file_loc = r"./static/CT胸部平扫约4000份-描述-分词处理后" + now + r".txt"
    ct_mat_out_file_loc = r"./static/test4" + now + r".xls"

    ct = RawText(term_xl_loc, token_mod_loc)
    whole_seg(ct_seg_in_file_loc, ct_seg_out_file_loc)
    whole_tokenize(ct_seg_out_file_loc, ct_token_out_file_loc)
    ct.whole_post_token(ct_token_out_file_loc, ct_modtoken_out_file_loc)
    ct.whole_match(ct_modtoken_out_file_loc, ct_mat_out_file_loc)

