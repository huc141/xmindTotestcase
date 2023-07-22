#!/usr/bin/env python
# _*_ coding:utf-8 _*_
import logging
import os
import re
import arrow
import sqlite3
from contextlib import closing
from os.path import join, exists
from werkzeug.utils import secure_filename
from xmind2testcase.zentao import xmind_to_zentao_csv_file
from xmind2testcase.testlink import xmind_to_testlink_xml_file
from xmind2testcase.utils import get_xmind_testsuites, get_xmind_testcase_list
from flask import Flask, request, send_from_directory, g, render_template, abort, redirect, url_for

# 获取当前脚本所在目录的绝对路径 H:\xmindTotestcase\webtool\application.py
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
# 最后，通过 setLevel() 方法设置文件处理器的日志级别为 logging.DEBUG，表示输出所有DEBUG级别及以上的日志。
file_handler.setLevel(logging.DEBUG)
# 创建流处理器（stream handler）stream_handler：将日志消息输出到控制台。
stream_handler = logging.StreamHandler()
stream_handler.setFormatter(formatter)
stream_handler.setLevel(logging.INFO)

# xmind to testcase logger
# 创建根日志记录器（root logger），并添加文件处理器（file handler）和流处理器（stream handler）作为其处理器。然后，将根日志记录器的日志级别设置为 DEBUG。
# 根日志记录器是日志记录器层次结构中的顶级记录器，它负责处理所有未被其他具体记录器处理的日志消息。通过获取根日志记录器并为其添加处理器，可以确保所有日志消息都会被处理和记录。
# logging.getLogger() 获取了根日志记录器的实例。然后，使用 addHandler() 方法分别将文件处理器和流处理器添加到根日志记录器中，以便将日志消息同时输出到文件和控制台。最后，使用 setLevel() 方法将根日志记录器的日志级别设置为 DEBUG，表示该记录器将处理所有级别的日志消息。
root_logger = logging.getLogger()
root_logger.addHandler(file_handler)
root_logger.addHandler(stream_handler)
root_logger.setLevel(logging.DEBUG)

# flask and werkzeug logger
# 创建名为 'werkzeug' 的日志记录器，并将文件处理器和流处理器添加为其处理器
# werkzeug' 是一个用于处理 Web 请求的 Python 库，常用于开发 Web 应用程序。在 Flask 应用程序中，'werkzeug' 用于处理 HTTP 请求和响应，并生成与请求处理相关的日志消息。
# 的是将 'werkzeug' 的日志消息与应用程序的其他日志消息分开记录和处理。通过单独配置 'werkzeug' 日志记录器，可以更灵活地控制和过滤 'werkzeug' 相关的日志消息，以满足特定需求。
werkzeug_logger = logging.getLogger('werkzeug')
werkzeug_logger.addHandler(file_handler)
werkzeug_logger.addHandler(stream_handler)
werkzeug_logger.setLevel(logging.DEBUG)

# global variable
UPLOAD_FOLDER = os.path.join(here, 'uploads') # 定义了上传文件存储的目录路径。
ALLOWED_EXTENSIONS = ['xmind'] # 定义了允许上传的文件扩展名列表。
DEBUG = True # 表示启用调试模式
DATABASE = os.path.join(here, 'data.db3') # 定义了 SQLite 数据库文件的路径
HOST = '0.0.0.0' # 置为 '0.0.0.0' 表示应用程序监听所有可用的网络接口

# flask app
app = Flask(__name__) # 创建一个 Flask 应用程序实例
app.config.from_object(__name__) # 加载应用程序的配置信息，__name__表示这些配置信息从当前模块中获取。配置项的访问方式为app.config['KEY_NAME']，其中KEY_NAME是配置项的名称。
app.secret_key = os.urandom(32) # 设置了应用程序的 secret_key 为一个随机生成的字节序列，用于保证会话安全。


def connect_db():
    return sqlite3.connect(app.config['DATABASE'])


# 用于初始化数据库，它使用了上述的 connect_db() 函数来获取数据库连接，并执行 schema.sql 脚本文件中的 SQL 语句来创建数据库表格。
def init_db():
    with closing(connect_db()) as db:
        with app.open_resource('schema.sql', mode='r') as f:
            db.cursor().executescript(f.read())
        db.commit()


# 用于初始化应用程序。在该函数中，检查上传文件存储目录和数据库文件是否存在，如果不存在则创建。然后调用 init_db() 函数来初始化数据库表格。
def init():
    app.logger.info('Start initializing the database...')
    if not exists(UPLOAD_FOLDER):
        os.mkdir(UPLOAD_FOLDER)

    if not exists(DATABASE):
        init_db()
    app.logger.info('Congratulations! the xmind2testcase webtool database has initialized successfully!')


# 在 Flask 中，g 是一个特殊的对象，被称为应用程序上下文（Application Context）。它是一个线程安全的对象，用于存储在整个请求生命周期中共享的数据。
# g.db 是在 before_request 函数中创建的数据库连接对象。通过将数据库连接对象保存在 g 对象中，我们可以在整个请求处理过程中共享这个对象，而不需要在每个函数中都显式地创建和传递数据库连接对象。这样可以简化代码，并确保在请求处理过程中使用的是同一个数据库连接。
@app.before_request
def before_request():
    g.db = connect_db() # g.db 被用来存储一个数据库连接对象。db 这个名称是一种常见的选择，表示数据库的缩写。可以根据个人喜好和项目要求选择其他名称，具有一定的描述性即可。


# 在每个请求处理完成后被调用。在这个函数中，我们首先尝试从 g 对象中获取数据库连接对象 g.db，然后判断它是否存在。如果存在，表示之前成功创建了数据库连接，在这里我们将关闭数据库连接。
# 这个函数接受一个可选的异常参数exception，用于捕获请求处理过程中发生的异常。如果请求处理过程中没有发生异常，那么 teardown_request 函数的 exception 参数将为 None。
@app.teardown_request
def teardown_request(exception):
    db = getattr(g, 'db', None)
    if db is not None:
        db.close()


def insert_record(xmind_name, note=''):
    c = g.db.cursor()
    now = str(arrow.now()) # arrow.now() 返回了当前的日期和时间。arrow 是一个用于处理日期和时间的 Python 库，它提供了更方便的日期和时间操作方法。arrow.now() 返回的是一个 Arrow 对象，它表示当前的日期和时间。为了将 Arrow 对象转换为字符串，代码中使用 str(arrow.now()) 进行转换。
    sql = "INSERT INTO records (name,create_on,note) VALUES (?,?,?)"
    c.execute(sql, (xmind_name, now, str(note)))
    g.db.commit()


# 在Flask中，app.config是一个配置对象，用于存储应用程序的配置信息。它是一个字典对象，其中包含了应用程序的各种配置项。
def delete_record(filename, record_id):
    xmind_file = join(app.config['UPLOAD_FOLDER'], filename) # 配置项的访问方式为app.config['KEY_NAME']，其中KEY_NAME是配置项的名称。可以使用点号 (.) 来访问嵌套配置项。我们已在当前文件中使用app.config.from_object(__name__)来加载应用程序的配置信息，__name__表示这些配置信息从当前模块中获取
    testlink_file = join(app.config['UPLOAD_FOLDER'], filename[:-5] + 'xml')
    zentao_file = join(app.config['UPLOAD_FOLDER'], filename[:-5] + 'csv')

    # 使用循环遍历这三个文件路径。如果某个文件存在（使用exists函数进行检查），则使用os.remove函数将其删除。
    for f in [xmind_file, testlink_file, zentao_file]:
        if exists(f):
            os.remove(f)

    # 获取一个数据库游标对象c，通过执行SQL语句来更新记录的状态为已删除。SQL语句使用参数化查询，将record_id作为参数传递给SQL语句中的占位符。
    c = g.db.cursor()
    sql = 'UPDATE records SET is_deleted=1 WHERE id = ?'
    c.execute(sql, (record_id,))
    g.db.commit()


def delete_records(keep=20):
    """Clean up files on server and mark the record as deleted"""
    sql = "SELECT * from records where is_deleted<>1 ORDER BY id desc LIMIT -1 offset {}".format(keep)
    assert isinstance(g.db, sqlite3.Connection) # 是一个断言语句，用于在代码执行时进行条件检查。它用于确保g.db对象是sqlite3.Connection类的实例。
    c = g.db.cursor()
    c.execute(sql)
    rows = c.fetchall() # 使用fetchall方法获取所有的查询结果行。
    for row in rows:
        name = row[1] # 从查询结果中每行包含多个列，其中名称在第二列，这里则是获取行记录的名称
        xmind_file = join(app.config['UPLOAD_FOLDER'], name)
        testlink_file = join(app.config['UPLOAD_FOLDER'], name[:-5] + 'xml')
        zentao_file = join(app.config['UPLOAD_FOLDER'], name[:-5] + 'csv')

        for f in [xmind_file, testlink_file, zentao_file]:
            if exists(f):
                os.remove(f)

        sql = 'UPDATE records SET is_deleted=1 WHERE id = ?'
        c.execute(sql, (row[0],)) # 这里则是获取行记录的id，即从0开始计数
        g.db.commit()

# get_records(limit=8) 函数用于获取指定数量的记录。
def get_records(limit=8):
    short_name_length = 120 # 用于限制名称的显示长度
    c = g.db.cursor()
    sql = "select * from records where is_deleted<>1 order by id desc limit {}".format(int(limit)) # 限制返回的记录数量为 limit
    c.execute(sql)
    rows = c.fetchall()

    for row in rows:
        name, short_name, create_on, note, record_id = row[1], row[1], row[2], row[3], row[0]

        # shorten the name for display
        if len(name) > short_name_length:
            short_name = name[:short_name_length] + '...'

        # more readable time format
        # 使用 Arrow 库中的 get() 函数来将 create_on 时间戳转换为 Arrow 对象
        create_on = arrow.get(create_on).humanize() # .humanize() 是 Arrow 对象的一个方法，用于将日期时间转换为更人性化的形式。它会根据当前时间生成一个可读性较高的字符串，例如 "2 minutes ago" 或 "Yesterday" 等。
        yield short_name, name, create_on, note, record_id

# get_latest_record() 函数用于获取最新的记录。它首先调用了 get_records(1) 函数，并将返回的结果转换为列表 found。然后通过判断 found 是否有元素，如果有，则返回列表中的第一个元素，即最新的记录。
def get_latest_record():
    found = list(get_records(1))
    if found:
        return found[0]


def allowed_file(filename):# 定义一个名为allowed_file的函数，它接收一个文件名filename作为输入参数。
    return '.' in filename and \
           filename.rsplit('.', 1)[1] in ALLOWED_EXTENSIONS # 这是一个布尔表达式，它检查文件名中是否包含句点（.），即判断文件名中是否有扩展名。filename.rsplit('.', 1): 这是对文件名进行分割操作，使用.作为分隔符，然后使用rsplit()方法从右边开始分割，且只分割一次。这将返回一个由文件名的前部分和扩展名组成的列表。
# [1]: 这是用于获取分割后的列表中的第二个元素，即获取文件的扩展名。

# 检查函数给定的文件名，并进行安全处理
def check_file_name(name):
    secured = secure_filename(name) # secure_filename方法是flask内置的一个函数，用于删除文件名中的非法字符和路径信息，以确保文件名不包含任何可能导致安全问题的内容。
    if not secured: # 检查secured 是否为空。如果 secured 为空，意味着 secure_filename 方法处理后的文件名为空，可能是由于原始文件名包含非法字符或路径信息。
        secured = re.sub('[^\w\d]+', '_', name)  # 若为空，则使用正则表达式 re.sub 将文件名中的非字母和非数字字符替换为下划线 _。这样可以确保文件名只包含字母和数字，没有其他特殊字符。
        assert secured, 'Unable to parse file name: {}!'.format(name) # 如果 secured 为空，则触发断言错误，抛出异常并给出提示信息，提示原始文件名解析失败。
    return secured + '.xmind' # 最终将处理后的文件名 secured 加上 .xmind 后缀，并返回作为结果。

# 用于保存上传的文件，并对文件名进行处理。
def save_file(file):
    if file and allowed_file(file.filename): # 检查上传的文件是否存在，并调用 allowed_file 函数检查文件名是否符合允许的扩展名。
        # filename = check_file_name(file.filename[:-6])
        filename = file.filename # 获取上传文件的原始文件名。
        upload_to = join(app.config['UPLOAD_FOLDER'], filename) # 构建上传文件的完整保存路径，其中 UPLOAD_FOLDER 是一个全局变量，表示上传文件保存的文件夹路径。join 函数用于拼接路径。

        if exists(upload_to): #检查文件是否已存在于保存路径中。如果文件已存在，则在文件名末尾添加时间戳，并重新构建保存路径和文件名，以避免文件名冲突
            filename = '{}_{}.xmind'.format(filename[:-6], arrow.now().strftime('%Y%m%d_%H%M%S'))
            upload_to = join(app.config['UPLOAD_FOLDER'], filename)

        file.save(upload_to) # 将上传的文件保存到指定的保存路径
        insert_record(filename) # 调用 insert_record 函数将文件名插入数据库中。
        g.is_success = True # 设置全局变量 g.is_success 为 True，表示文件保存成功。
        return filename # 返回保存后的文件名作为函数结果。
    
# 如果上传的文件为空或文件名不符合要求，设置全局变量 g.is_success 为 False，并将错误信息添加到全局变量 g.error 或 g.invalid_files 中，以便后续处理。
    elif file.filename == '':
        g.is_success = False
        g.error = "Please select a file!"

    else:
        g.is_success = False
        g.invalid_files.append(file.filename)


def verify_uploaded_files(files):
    # download the xml directly if only 1 file uploaded
    # 检查上传的文件列表 files 是否只包含一个文件。如果上传了多个文件，则不满足此条件。
    if len(files) == 1 and getattr(g, 'is_success', False): # 获取全局变量 g.is_success 的值。如果全局变量 g 中没有名为 is_success 的属性，或者获取失败，则返回 False。这里使用 getattr 函数避免因为不存在属性而引发异常。
        g.download_xml = get_latest_record()[1] # 如果只有一个文件被成功上传，将全局变量 g.download_xml 设置为最新上传的文件名。get_latest_record() 函数用于获取最新上传的文件记录，返回一个包含文件名等信息的元组，其中 [1] 表示取第二个元素，即文件名。

    if g.invalid_files: # 检查全局变量 g.invalid_files 是否存在，即是否有无效的文件。
        g.error = "Invalid file: {}".format(','.join(g.invalid_files)) # 如果存在无效的文件，将错误信息设置为 "Invalid file: "，后面跟随逗号分隔的无效文件名列表。


@app.route('/', methods=['GET', 'POST'])
def index(download_xml=None):
    g.invalid_files = []
    g.error = None
    g.download_xml = download_xml
    g.filename = None

    if request.method == 'POST':
        if 'file' not in request.files:
            return redirect(request.url)

        file = request.files['file']

        if file.filename == '':
            return redirect(request.url)

        g.filename = save_file(file)
        verify_uploaded_files([file])
        delete_records()

    else:
        g.upload_form = True

    if g.filename:
        return redirect(url_for('preview_file', filename=g.filename))
    else:
        return render_template('index.html', records=list(get_records()))


@app.route('/uploads/<filename>')
def uploaded_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)


@app.route('/<filename>/to/testlink')
def download_testlink_file(filename):
    full_path = join(app.config['UPLOAD_FOLDER'], filename)

    if not exists(full_path):
        abort(404)

    testlink_xmls_file = xmind_to_testlink_xml_file(full_path)
    filename = os.path.basename(testlink_xmls_file) if testlink_xmls_file else abort(404)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/<filename>/to/zentao')
def download_zentao_file(filename):
    full_path = join(app.config['UPLOAD_FOLDER'], filename)

    if not exists(full_path):
        abort(404)

    zentao_csv_file = xmind_to_zentao_csv_file(full_path)
    filename = os.path.basename(zentao_csv_file) if zentao_csv_file else abort(404)

    return send_from_directory(app.config['UPLOAD_FOLDER'], filename, as_attachment=True)


@app.route('/preview/<filename>')
def preview_file(filename):
    full_path = join(app.config['UPLOAD_FOLDER'], filename)

    if not exists(full_path):
        abort(404)

    testsuites = get_xmind_testsuites(full_path)
    suite_count = 0
    for suite in testsuites:
        suite_count += len(suite.sub_suites)

    testcases = get_xmind_testcase_list(full_path)

    return render_template('preview.html', name=filename, suite=testcases, suite_count=suite_count)


@app.route('/delete/<filename>/<int:record_id>')
def delete_file(filename, record_id):

    full_path = join(app.config['UPLOAD_FOLDER'], filename)
    if not exists(full_path):
        abort(404)
    else:
        delete_record(filename, record_id)
    return redirect('/')


@app.errorhandler(Exception)
def app_error(e):
    return str(e)


def launch(host=HOST, debug=True, port=5001):
    init()  # initializing the database
    app.run(host=host, debug=debug, port=port)


if __name__ == '__main__':
    init()  # initializing the database
    app.run(HOST, debug=DEBUG, port=5001)




"""
`yield` 是一个关键字，用于定义生成器函数。生成器函数在执行时会生成一个迭代器对象，通过迭代器可以逐个返回值，而不是一次性返回所有值。

当生成器函数执行到 `yield` 语句时，会暂停执行并返回一个值，将该值提供给调用方。然后，生成器函数会保留当前的状态，等待下一次调用时继续执行。每次调用生成器函数时，它都会从上次暂停的位置继续执行，直到遇到下一个 `yield` 语句或函数结束。

这种逐个产生值的特性使得生成器函数非常适用于处理大量数据或需要逐步生成结果的情况，可以节省内存并提高效率。

在上述代码中，`get_records()` 函数使用 `yield` 关键字来定义一个生成器函数。它通过执行 SQL 查询从数据库中获取记录，并使用 `yield` 逐个生成每条记录的相关信息。每次迭代时，调用方可以获取生成器函数生成的一个记录信息，并在下一次迭代时继续获取下一个记录。

可以使用 `for` 循环来迭代生成器函数的结果，或者使用 `next()` 函数逐个获取生成器函数生成的值。例如：

```python
for record in get_records():
    print(record)

# 或者

record_generator = get_records()
record1 = next(record_generator)
record2 = next(record_generator)
```

注意，生成器函数并不会立即执行，而是在迭代时按需执行，只生成需要的值，从而提高了效率。

"""