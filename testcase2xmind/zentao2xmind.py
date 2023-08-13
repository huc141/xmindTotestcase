import os
import csv
import xmind
import logging
from xmind.core import workbook,saver
from xmind2testcase.utils import get_absolute_path


def zentao_csv_file_to_xmind(zentao_csv_file):
    """将禅道导出的csv用例文件转为xmind思维导图"""
    zentao_csv_file = get_absolute_path(zentao_csv_file)
    zentao_csv_file_name = zentao_csv_file[:-4]
    logging.info('Start converting zentao_csv file(%s) to xmind file...', zentao_csv_file)
    testcases = []
    with open(zentao_csv_file, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        for row in reader:
            testcases.append(row)

    # 创建 XMind 思维导图
    workbook = xmind.load(zentao_csv_file_name + '.xmind')
    sheet = workbook.getPrimarySheet()
    sheet.setTitle(zentao_csv_file_name + '测试用例')
    root_topic = sheet.getRootTopic()
    root_topic.setTitle(zentao_csv_file_name + '测试用例')

    # 将测试用例数据添加到思维导图中
    for testcase in testcases:
        topic = root_topic.addSubTopic()
        topic.setTitle(testcase['用例标题'])
        subtopic1 = topic.addSubTopic()
        subtopic1.setTitle(f'步骤: {testcase["步骤"]}')
        subtopic2 = subtopic1.addSubTopic()
        subtopic2.setTitle(f'预期: {testcase["预期"]}')

    # 保存 XMind 文件
    csv_to_xmind_file = xmind.save(workbook, path = zentao_csv_file_name + '.xmind')
    logging.info('Convert zentao_csv file(%s) to a xmind file(%s) successfully!', zentao_csv_file_name, csv_to_xmind_file)

    return csv_to_xmind_file


if __name__ == '__main__':
    zentao_csv_file = '../webtool/uploads/直采系统-第1期测试用例-转csv.csv'
    zentao_csv_file_to_xmind(zentao_csv_file)