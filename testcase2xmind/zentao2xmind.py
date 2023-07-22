import csv
import xmind
from xmind.core import workbook,saver

# 读取 禅道CSV 文件中的测试用例数据
testcases = []
with open('ERP-仓储物流管理系统-所有用例.csv', newline='', encoding='utf-8') as csvfile:
    reader = csv.DictReader(csvfile)
    for row in reader:
        testcases.append(row)

# 创建 XMind 思维导图
workbook = xmind.load('test.xmind')
sheet = workbook.getPrimarySheet()
sheet.setTitle('仓储测试用例')
root_topic = sheet.getRootTopic()
root_topic.setTitle('仓储测试用例')

# 将测试用例数据添加到思维导图中
for testcase in testcases:
    topic = root_topic.addSubTopic()
    topic.setTitle(testcase['用例标题'])
    subtopic1 = topic.addSubTopic()
    subtopic1.setTitle(f'步骤: {testcase["步骤"]}')
    subtopic2 = subtopic1.addSubTopic()
    subtopic2.setTitle(f'预期: {testcase["预期"]}')

# 保存 XMind 文件
xmind.save(workbook, path='test.xmind')