#!/usr/bin/env python
# _*_ coding:utf-8 _*_

import logging
from xmind2testcase.metadata import TestSuite, TestCase, TestStep

config = {'sep': ' ',
          'valid_sep': '&>+/-',
          'precondition_sep': '\n----\n',
          'summary_sep': '\n----\n',
          'ignore_char': '#!！'
          }


def xmind_to_testsuites(xmind_content_dict):
    """convert xmind file to `xmind2testcase.metadata.TestSuite` list"""
    suites = [] # 创建一个空列表suites，用于存储将要生成的TestSuite对象。

    for sheet in xmind_content_dict: # sheet在这里代表xmind文件中的画布，使用for循环遍历列表中的字典
        logging.debug('start to parse a sheet: %s', sheet['title'])
        root_topic = sheet['topic'] # 从当前Sheet的字典中获取根Topic（根主题），根Topic是整个Sheet的顶层主题。
        sub_topics = root_topic.get('topics', []) # 使用get()方法从根主题的字典中获取'topics'键对应的值（子主题列表）。如果'topics'键不存在或者没有值，即根主题没有子主题，get()方法将返回一个空列表[]，表示当前Sheet中没有包含任何测试用例信息。

        if sub_topics: # 检查sub_topics是否非空，即该Sheet是否包含测试用例信息。
            root_topic['topics'] = filter_empty_or_ignore_topic(sub_topics) # 对子主题列表进行过滤和处理，去除空的主题或被忽略的主题。
        else: # 如果sub_topics为空，即该Sheet没有包含测试用例信息，将记录一个警告信息到日志，并继续下一个Sheet的解析。
            logging.debug('This is a blank sheet(%s), should have at least 1 sub topic(test suite)', sheet['title'])
            continue
        suite = sheet_to_suite(root_topic) # 将当前画布的根主题数据转换为测试套件对象
        # suite.sheet_name = sheet['title']  # root testsuite has a sheet_name attribute
        logging.debug('sheet(%s) parsing complete: %s', sheet['title'], suite.to_dict())
        suites.append(suite) # 将转换得到的测试套件对象添加到suites列表中

    return suites


def filter_empty_or_ignore_topic(topics):
    """filter blank or start with config.ignore_char topic"""
    # result = [...]：这是将新列表的结果存储在名为 result 的变量中。
    result = [topic for topic in topics if not(  # [topic for topic in topics]：这部分是一个列表解析，它遍历名为 topics 的列表中的每个元素（在这种情况下，每个元素都是一个主题），然后将它们包含在新的列表中。第一个topic：这是一个占位符变量，它代表在遍历 topics 列表时的每个元素。for topic in topics：这是一个循环语句，它遍历名为 topics 的列表中的每个元素，并将每个元素依次赋给占位符变量 topic。
            topic['title'] is None or # 这部分检查主题的标题是否为 None（表示没有标题）。
            topic['title'].strip() == '' or # 这部分检查主题的标题是否是空字符串，通过使用 .strip() 方法来删除标题中的额外空格并检查是否为空。
            topic['title'][0] in config['ignore_char'])] # 这部分检查主题的标题是否以 config 中定义的字符列表中的任何字符开头，这样的主题会被忽略。

    for topic in result: #函数递归地处理 topics 列表中的子主题（sub_topics）。这是因为主题可以包含子主题。过滤之后，将有效的主题添加到 result 中
        sub_topics = topic.get('topics', [])
        topic['topics'] = filter_empty_or_ignore_topic(sub_topics)

    return result # 最终，返回包含有效主题的 result 列表。

# 上述filter_empty_or_ignore_topic方法可以改写为更易懂的传统方法：
def filter_empty_or_ignore_topic2(topics):
    """过滤空白或以config.ignore_char开头的主题"""
    result = []

    for topic in topics:
        if (
            topic['title'] is not None
            and topic['title'].strip() != ''
            or topic['title'][0] not in config['ignore_char']
        ):
            result.append(topic)

    for topic in result:
        sub_topics = topic.get('topics', [])
        topic['topics'] = filter_empty_or_ignore_topic(sub_topics)

    return result


def filter_empty_or_ignore_element(values):
    """Filter all empty or ignore XMind elements, especially notes、comments、labels element"""
    result = []
    for value in values:
        if isinstance(value, str) and not value.strip() == '' and not value[0] in config['ignore_char']:
            result.append(value.strip())
    return result


def sheet_to_suite(root_topic):
    """convert a xmind sheet to a `TestSuite` instance"""
    suite = TestSuite() # 创建一个空的TestSuite对象，并赋值给变量suite。
    root_title = root_topic['title'] # 从root_topic中提取根主题的名称，存储在变量root_title中。
    separator = root_title[-1] # 获取root_title的最后一个字符，将其存储在变量separator中。

    if separator in config['valid_sep']: # 判断separator是否存在于全局配置项config['valid_sep']中，即是否为一个有效的分隔符。
        logging.debug('find a valid separator for connecting testcase title: %s', separator)
        config['sep'] = separator  # set the separator for the testcase's title
        root_title = root_title[:-1] # 如果是有效的分隔符，则从测试套件的名称root_title中去掉分隔符
    else:
        config['sep'] = ' ' # 如果separator不是有效的分隔符，则将全局配置项config['sep']设置为默认值' '（空格）

    suite.name = root_title # 将经过处理的测试套件名称root_title赋值给suite的name属性。
    suite.details = root_topic['note'] # 将root_topic中的测试套件详细信息赋值给suite的details属性。
    suite.sub_suites = []

    # 使用递归调用函数 parse_testsuite 来处理 root_topic['topics'] 中的每个字典元素，并将其转换为对应的子测试套件对象，并添加到 suite.sub_suites 列表中。
    for suite_dict in root_topic['topics']:
        suite.sub_suites.append(parse_testsuite(suite_dict))

    return suite


def parse_testsuite(suite_dict):
    testsuite = TestSuite()
    testsuite.name = suite_dict['title']
    testsuite.details = suite_dict['note']
    testsuite.testcase_list = []
    logging.debug('start to parse a testsuite: %s', testsuite.name)

    for cases_dict in suite_dict.get('topics', []):
        for case in recurse_parse_testcase(cases_dict):
            testsuite.testcase_list.append(case)

    logging.debug('testsuite(%s) parsing complete: %s', testsuite.name, testsuite.to_dict())
    return testsuite


def recurse_parse_testcase(case_dict, parent=None):
    if is_testcase_topic(case_dict):
        case = parse_a_testcase(case_dict, parent)
        yield case
    else:
        if not parent:
            parent = []

        parent.append(case_dict)

        for child_dict in case_dict.get('topics', []):
            for case in recurse_parse_testcase(child_dict, parent):
                yield case

        parent.pop()


def is_testcase_topic(case_dict):
    """A topic with a priority marker, or no subtopic, indicates that it is a testcase"""
    priority = get_priority(case_dict)
    if priority:
        return True

    children = case_dict.get('topics', [])
    if children:
        return False

    return True


def parse_a_testcase(case_dict, parent):
    testcase = TestCase()
    topics = parent + [case_dict] if parent else [case_dict]

    testcase.name = gen_testcase_title(topics)

    preconditions = gen_testcase_preconditions(topics)
    testcase.preconditions = preconditions if preconditions else '无'

    summary = gen_testcase_summary(topics)
    testcase.summary = summary if summary else testcase.name
    testcase.execution_type = get_execution_type(topics)
    testcase.importance = get_priority(case_dict) or 2

    step_dict_list = case_dict.get('topics', [])
    if step_dict_list:
        testcase.steps = parse_test_steps(step_dict_list)

    # the result of the testcase take precedence over the result of the teststep
    testcase.result = get_test_result(case_dict['markers'])

    if testcase.result == 0 and testcase.steps:
        for step in testcase.steps:
            if step.result == 2:
                testcase.result = 2
                break
            if step.result == 3:
                testcase.result = 3
                break

            testcase.result = step.result  # there is no need to judge where test step are ignored

    logging.debug('finds a testcase: %s', testcase.to_dict())
    return testcase


def get_execution_type(topics):
    labels = [topic.get('label', '') for topic in topics]
    labels = filter_empty_or_ignore_element(labels)
    exe_type = 1
    for item in labels[::-1]:
        if item.lower() in ['自动', 'auto', 'automate', 'automation']:
            exe_type = 2
            break
        if item.lower() in ['手动', '手工', 'manual']:
            exe_type = 1
            break
    return exe_type


def get_priority(case_dict):
    """Get the topic's priority（equivalent to the importance of the testcase)"""
    if isinstance(case_dict['markers'], list): # 检查测试用例数据字典中的 'markers' 是否是一个列表。
        for marker in case_dict['markers']: # 如果 'markers' 是一个列表，就遍历其中的每个标记。
            if marker.startswith('priority'): # 检查标记是否以 'priority' 开头，这是一个表示优先级的标记。
                return int(marker[-1]) # 如果找到优先级相关的标记，将标记的最后一个字符（通常是优先级的数值）转换为整数并返回。


def gen_testcase_title(topics):
    """Link all topic's title as testcase title"""
    titles = [topic['title'] for topic in topics]
    titles = filter_empty_or_ignore_element(titles)

    # when separator is not blank, will add space around separator, e.g. '/' will be changed to ' / '
    separator = config['sep']
    if separator != ' ':
        separator = ' {} '.format(separator)

    return separator.join(titles)


def gen_testcase_preconditions(topics):
    notes = [topic['note'] for topic in topics]
    notes = filter_empty_or_ignore_element(notes)
    return config['precondition_sep'].join(notes)


def gen_testcase_summary(topics):
    comments = [topic['comment'] for topic in topics]
    comments = filter_empty_or_ignore_element(comments)
    return config['summary_sep'].join(comments)


def parse_test_steps(step_dict_list):
    steps = []

    for step_num, step_dict in enumerate(step_dict_list, 1):
        test_step = parse_a_test_step(step_dict)
        test_step.step_number = step_num
        steps.append(test_step)

    return steps


def parse_a_test_step(step_dict):
    test_step = TestStep()
    test_step.actions = step_dict['title']

    expected_topics = step_dict.get('topics', [])
    if expected_topics:  # have expected result
        expected_topic = expected_topics[0]
        test_step.expectedresults = expected_topic['title']  # one test step action, one test expected result
        markers = expected_topic['markers']
        test_step.result = get_test_result(markers)
    else:  # only have test step
        markers = step_dict['markers']
        test_step.result = get_test_result(markers)

    logging.debug('finds a teststep: %s', test_step.to_dict())
    return test_step


def get_test_result(markers):
    """test result: non-execution:0, pass:1, failed:2, blocked:3, skipped:4"""
    if isinstance(markers, list):
        if 'symbol-right' in markers or 'c_simbol-right' in markers:
            result = 1
        elif 'symbol-wrong' in markers or 'c_simbol-wrong' in markers:
            result = 2
        elif 'symbol-pause' in markers or 'c_simbol-pause' in markers:
            result = 3
        elif 'symbol-minus' in markers or 'c_simbol-minus' in markers:
            result = 4
        else:
            result = 0
    else:
        result = 0

    return result








