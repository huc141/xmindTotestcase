#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import csv
import logging
import os
from xmind2testcase.utils import get_xmind_testcase_list, get_absolute_path

here = os.path.abspath(os.path.dirname(__file__))
# 将日志文件名 'running.log' 与 here 拼接起来，得到完整的日志文件路径： log_file
log_file = os.path.join(here, 'running.log')

# log handler
# 创建日志格式器（formatter）：包含了时间、日志名称、日志级别、模块名和函数名等信息。
formatter = logging.Formatter('%(asctime)s  %(name)s  %(levelname)s  [%(module)s - %(funcName)s]: %(message)s')
# 创建文件处理器（file handler）file_handler：传入日志文件路径 log_file 和编码方式 'UTF-8'
file_handler = logging.FileHandler(log_file, encoding='UTF-8')
# 通过 setFormatter() 方法将前面创建的日志格式器 formatter 应用到文件处理器上
file_handler.setFormatter(formatter)
# 最后，通过 setLevel() 方法设置文件处理器的日志级别为 logging.DEBUG，表示输出所有级别的日志，包括 DEBUG、INFO、WARNING、ERROR 和 CRITICAL 等级别的日志信息。
file_handler.setLevel(logging.DEBUG)

root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
# root_logger.addHandler(stream_handler)
root_logger.setLevel(logging.DEBUG)

"""
Convert XMind fie to Zentao testcase csv file 

Zentao official document about import CSV testcase file: https://www.zentao.net/book/zentaopmshelp/243.mhtml 
"""


def xmind_to_zentao_csv_file(xmind_file):
    """Convert XMind file to a zentao csv file"""
    xmind_file = get_absolute_path(xmind_file)
    logging.debug('Start converting XMind file(%s) to zentao file...', xmind_file)
    testcases = get_xmind_testcase_list(xmind_file)

    fileheader = ["所属模块", "用例标题", "前置条件", "步骤", "预期", "关键词", "优先级", "用例类型", "适用阶段"]
    zentao_testcase_rows = [fileheader]
    for testcase in testcases:
        row = gen_a_testcase_row(testcase)
        zentao_testcase_rows.append(row)

    zentao_file = xmind_file[:-6] + '.csv'
    if os.path.exists(zentao_file):
        os.remove(zentao_file)
        # logging.info('The zentao csv file already exists, return it directly: %s', zentao_file)
        # return zentao_file

    with open(zentao_file, 'w', encoding='utf8') as f:
        writer = csv.writer(f)
        writer.writerows(zentao_testcase_rows)
        logging.debug('Convert XMind file(%s) to a zentao csv file(%s) successfully!', xmind_file, zentao_file)

    return zentao_file


def gen_a_testcase_row(testcase_dict):
    case_module = gen_case_module(testcase_dict['suite'])
    case_title = testcase_dict['name']
    case_precontion = testcase_dict['preconditions']
    case_step, case_expected_result = gen_case_step_and_expected_result(testcase_dict['steps'])
    case_keyword = ''
    case_priority = gen_case_priority(testcase_dict['importance'])
    case_type = gen_case_type(testcase_dict['execution_type'])
    case_apply_phase = '功能测试阶段'
    row = [case_module, case_title, case_precontion, case_step, case_expected_result, case_keyword, case_priority, case_type, case_apply_phase]
    return row


def gen_case_module(module_name):
    if module_name:
        module_name = module_name.replace('（', '(')
        module_name = module_name.replace('）', ')')
    else:
        module_name = '/'
    return module_name


def gen_case_step_and_expected_result(steps):
    case_step = ''
    case_expected_result = ''

    for step_dict in steps:
        case_step += str(step_dict['step_number']) + '. ' + step_dict['actions'].replace('\n', '').strip() + '\n'
        case_expected_result += str(step_dict['step_number']) + '. ' + \
            step_dict['expectedresults'].replace('\n', '').strip() + '\n' \
            if step_dict.get('expectedresults', '') else ''

    return case_step, case_expected_result


def gen_case_priority(priority):
    mapping = {1: '1', 2: '2', 3: '3'}
    if priority in mapping.keys():
        return mapping[priority]
    else:
        return '2'


def gen_case_type(case_type):
    mapping = {1: '功能测试', 2: '自动化测试'}
    if case_type in mapping.keys():
        return mapping[case_type]
    else:
        return '功能测试'


if __name__ == '__main__':
    # xmind_file = '../docs/zentao_testcase_template.xmind'
    xmind_file= 'E:/Desktop/myXmindTestCase/Xmind2TestCase模板_空文件.xmind'
    zentao_csv_file = xmind_to_zentao_csv_file(xmind_file)
    print('Conver the xmind file to a zentao csv file succssfully: %s', zentao_csv_file)