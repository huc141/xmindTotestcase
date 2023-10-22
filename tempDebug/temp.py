
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
        print('start to parse a sheet: %s', sheet['title'])
        root_topic = sheet['topic'] # 从当前Sheet的字典中获取根Topic（根主题），根Topic是整个Sheet的顶层主题。
        print("root_topic: " + str(root_topic))
        sub_topics = root_topic.get('topics', []) # 使用get()方法从根主题的字典中获取'topics'键对应的值（子主题列表）。如果'topics'键不存在或者没有值，即根主题没有子主题，get()方法将返回一个空列表[]，表示当前Sheet中没有包含任何测试用例信息。
        print("sub_topics: " + str(sub_topics))

        if sub_topics: # 检查sub_topics是否非空，即该Sheet是否包含测试用例信息。
            root_topic['topics'] = filter_empty_or_ignore_topic(sub_topics) # 对子主题列表进行过滤和处理，去除空的主题或被忽略的主题。
        else: # 如果sub_topics为空，即该Sheet没有包含测试用例信息，将记录一个警告信息到日志，并继续下一个Sheet的解析。
            logging.debug('This is a blank sheet(%s), should have at least 1 sub topic(test suite)', sheet['title'])
            continue
        suite = sheet_to_suite(root_topic) # 将当前画布的根主题数据转换为测试套件对象
        # suite.sheet_name = sheet['title']  # root testsuite has a sheet_name attribute
        print('sheet(%s) parsing complete: %s', sheet['title'], suite.to_dict())
        suites.append(suite) # 将转换得到的测试套件对象添加到suites列表中

    return suites


def sheet_to_suite(root_topic):
    """convert a xmind sheet to a `TestSuite` instance"""
    suite = TestSuite() # 创建一个空的TestSuite对象，并赋值给变量suite。
    root_title = root_topic['title'] # 从root_topic中提取根主题的名称，存储在变量root_title中。
    separator = root_title[-1] # 获取root_title的最后一个字符，将其存储在变量separator中。
    print("separator: " + str(separator))

    if separator in config['valid_sep']: # 判断separator是否存在于全局配置项config['valid_sep']中，即是否为一个有效的分隔符。
        logging.debug('find a valid separator for connecting testcase title: %s', separator)
        config['sep'] = separator  # set the separator for the testcase's title
        root_title = root_title[:-1] # 如果是有效的分隔符，则从测试套件的名称root_title中去掉分隔符
        print("root_title: " + str(root_title))
    else:
        config['sep'] = ' ' # 如果separator不是有效的分隔符，则将全局配置项config['sep']设置为默认值' '（空格）

    suite.name = root_title # 将经过处理的测试套件名称root_title赋值给suite的name属性。
    suite.details = root_topic['note'] # 将root_topic中的测试套件备注信息(用例的前提条件)赋值给suite的details属性。
    suite.sub_suites = []

    # 使用递归调用函数 parse_testsuite 来处理 root_topic['topics'] 中的每个字典元素，并将其转换为对应的子测试套件对象，并添加到 suite.sub_suites 列表中。
    for suite_dict in root_topic['topics']:
        parsed_suite = parse_testsuite(suite_dict)
        suite.sub_suites.append(parsed_suite)
    print("parsed_suite: " + str(parsed_suite))
        # suite.sub_suites.append(parse_testsuite(suite_dict))

    return suite


def parse_testsuite(suite_dict):
    testsuite = TestSuite()
    testsuite.name = suite_dict['title']
    print("testsuite.name: " + suite_dict['title'])
    testsuite.details = suite_dict['note']
    print("testsuite.details: " + suite_dict['note'])
    testsuite.testcase_list = []
    print('start to parse a testsuite: %s', testsuite.name)

    for cases_dict in suite_dict.get('topics', []):
        for case in recurse_parse_testcase(cases_dict):
            testsuite.testcase_list.append(case)

    print('testsuite(%s) parsing complete: %s', testsuite.name, testsuite.to_dict())
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


def filter_empty_or_ignore_topic(topics):
    """过滤空白或以config.ignore_char开头的主题"""
    result = []

    for topic in topics:
        if (
            topic['title'] is not None
            and topic['title'].strip() != ''
            or topic['title'][0] not in config['ignore_char']
        ):
            result.append(topic)
        print("result: " + str(result))

    for topic in result:
        sub_topics = topic.get('topics', [])
        print("sub_topics02: " + str(sub_topics) )
        topic['topics'] = filter_empty_or_ignore_topic(sub_topics)

    return result


if __name__ == '__main__':
    xmind_content_dict= [
     {
          "id": "655pi8tii4gmlm1q2n7u50culg",
          "title": "画布 1",
          "topic": {
               "id": "0otcjn5vkkfsluopcuf2asbre3",
               "link": None,
               "title": "Xmind2TestCase模板(填你的迭代版本/产品名称)&",
               "note": None,
               "label": None,
               "comment": None,
               "markers": [],
               "topics": [
                    {
                         "id": "0t7ejedr55bea9eiru6paaen03",
                         "link": None,
                         "title": "无用例的子主题01",
                         "note": "【无用例的子主题备注】",
                         "label": None,
                         "comment": None,
                         "markers": [
                              "priority-1"
                         ]
                    }
               ]
          }
     }
]
    content = xmind_to_testsuites(xmind_content_dict)
    print(content)