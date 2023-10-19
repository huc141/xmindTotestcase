config = {'sep': ' ',
          'valid_sep': '&>+/-',
          'precondition_sep': '\n----\n',
          'summary_sep': '\n----\n',
          'ignore_char': '#!！'
          }

def filter_empty_or_ignore_topic(topics):
    """过滤空白或以config.ignore_char开头的主题"""
    result = []

    for topic in topics:
        if (
            topic['title'] is not None
            and topic['title'].strip() != ''
            and topic['title'][0] not in config['ignore_char']
        ):
            result.append(topic)

    for topic in result:
        sub_topics = topic.get('topics', [])
        topic['topics'] = filter_empty_or_ignore_topic(sub_topics)

    return result


if __name__ == '__main__':
    topics= [{
     "id": "0t7ejedr55bea9eiru6paaen03",
     "link": None,
     "title": "无用例的子主题01",
     "note": "【无用例的子主题备注】",
     "label": None,
     "comment": None,
     "markers": [
          "priority-1"
     ]
}]
    content = filter_empty_or_ignore_topic(topics)
    print(content)