from PySide2.QtUiTools import QUiLoader
from PySide2.QtWidgets import QWidget, QPushButton, QVBoxLayout, QFileDialog, QApplication, QLineEdit, QTableWidgetItem
from PySide2.QtCore import Signal, Slot
from subprocess import call
from concurrent.futures import ThreadPoolExecutor
import re
import os
import datetime
import multiprocessing
import time


class Stats:

    def __init__(self):
        # 从文件中加载UI定义

        # 从 UI 定义中动态 创建一个相应的窗口对象
        # 注意：里面的控件对象也成为窗口对象的属性了
        # 比如 self.ui.button , self.ui.textEdit
        # 导入ui
        self.ui = QUiLoader().load('myForm.ui')


        # 信号处理
        self.ui.pushButton.clicked.connect(self.createTask)
        self.ui.pushButton_1.clicked.connect(self.openFileDialog)  # 选择apdl目录
        self.ui.pushButton_2.clicked.connect(self.openTxtDialog)  # 选择命令流模板
        self.ui.pushButton_3.clicked.connect(self.startWork)
        self.ui.pushButton_4.clicked.connect(self.openFolderDialog)  # 选择工作目录
        self.ui.pushButton_5.clicked.connect(self.importTask)
        self.ui.spinBox_1.valueChanged.connect(self.upData)
        self.ui.checkBox_1.stateChanged.connect(self.upData)
        self.ui.checkBox_2.stateChanged.connect(self.upData)
        self.ui.lineEdit.returnPressed.connect(self.createTask)


        # 系统变量
        self.ansyscall = self.ui.lineEdit_1.text()
        self.numprocessors = self.ui.spinBox_1.value()
        self.scriptFilename = "run"
        self.elapsedTime = 0
        self.rstFalg = self.ui.checkBox_1.isChecked()
        self.extractFalg = self.ui.checkBox_2.isChecked()

    @Slot()
    def handleCalc(self):
        print('hello world!')

    @Slot()
    def openFileDialog(self):
        # 生成文件对话框对象
        dialog = QFileDialog()
        # 设置文件过滤器，这里是任何文件，包括目录噢
        dialog.setFileMode(QFileDialog.AnyFile)
        # 设置显示文件的模式，这里是详细模式
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            fileNames = dialog.selectedFiles()
            print(fileNames)
            self.ui.lineEdit_1.setText(fileNames[0])

    @Slot()
    def openFolderDialog(self):
        # 生成文件对话框对象
        dialog = QFileDialog()
        # 设置文件过滤器，这里是目录噢
        dialog.setFileMode(QFileDialog.Directory)
        # 设置显示文件的模式，这里是详细模式
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            fileNames = dialog.selectedFiles()
            print(fileNames)
            self.ui.lineEdit_5.setText(fileNames[0])

    @Slot()
    def openTxtDialog(self):
        # 生成文件对话框对象
        dialog = QFileDialog()
        # 设置文件过滤器
        dialog.setFileMode(QFileDialog.AnyFile)
        dialog.setNameFilter("text (*.txt)")
        # 设置显示文件的模式
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            fileNames = dialog.selectedFiles()

            self.ui.lineEdit_4.setText(fileNames[0])
            self.analysisText()

    # 解析命令流模板
    def analysisText(self):
        # 取命令流模板路径
        text_path = self.ui.lineEdit_4.text()
        # 存放变量
        variableName = []
        # 打开文件
        with open(text_path, 'r', encoding='utf-8') as f:
            # 判断是否找到变量flag
            flag = False
            for line in f:
                if line.startswith('!start!'):
                    flag = True
                    continue
                elif line.startswith('!end!'):
                    break
                if flag and not line.startswith('!'):
                    variableName.append(line)

        self.ui.tableWidget.setColumnCount(2)
        self.ui.tableWidget.setRowCount(len(variableName))  # 设置表格有两列
        # 根据模板中的变量设置表格
        for var_item in range(len(variableName)):
            str = variableName[var_item]
            name = re.split('={|}\n', str)
            self.ui.tableWidget.setItem(var_item, 0, QTableWidgetItem(name[1]))

    @Slot()
    def createTask(self):
        flag = True
        rowcount = self.ui.tableWidget.rowCount()
        for formItem in range(rowcount):

            if not self.ui.tableWidget.item(formItem, 1).text():
                flag = False
        taskName = self.ui.lineEdit.text()
        if flag and taskName:
            #  读取左侧表格的值，根据模板生成任务命令流
            paraDic = {}
            for formItem in range(rowcount):
                dicKey = self.ui.tableWidget.item(formItem, 0).text()
                value = self.ui.tableWidget.item(formItem, 1).text()
                paraDic[dicKey] = value
            baseTextPath = self.ui.lineEdit_4.text()
            workPath = self.ui.lineEdit_5.text()
            baseText = open(baseTextPath, 'r', encoding='utf-8')
            taskPath = workPath + '\\' + taskName
            self.mkdir(taskPath)
            taskText = open(taskPath + '\\' + 'run.txt', 'w', encoding='utf-8')
            taskContent = baseText.read().format(**paraDic)
            taskText.write(taskContent)
            baseText.close()
            taskText.close()
            # 修改右侧表格
            rowPosition = self.ui.tableWidget_2.rowCount()
            self.ui.tableWidget_2.insertRow(rowPosition)
            self.ui.tableWidget_2.setItem(rowPosition, 0, QTableWidgetItem(str(rowPosition)))
            self.ui.tableWidget_2.setItem(rowPosition, 1, QTableWidgetItem(taskName))
            self.ui.tableWidget_2.setItem(rowPosition, 2, QTableWidgetItem(taskPath))
            self.ui.lineEdit.setText('')

    def runAPDL(self, ansyscall, numprocessors, workingdir, scriptFilename):
        """
        runs the APDL script: scriptFilename.inp
        located in the folder: workingdir
        using APDL executable invoked by: ansyscall
        using the number of processors in: numprocessors
        returns the number of ANSYS errors encountered in the run
    """
        inputFile = os.path.join(workingdir,
                                 scriptFilename + ".txt")
        # make the output file be the input file plus timestamp
        outputFile = os.path.join(workingdir,
                                  scriptFilename + ".out")
        # keep the standard ANSYS jobname
        jobname = "file"
        callString = ("\"{}\"-p ane3fl "
                      "-np {} -dir \"{}\" -j \"{}\"-s read "
                      "-b -i \"{}\" -o \"{}\"").format(
            ansyscall,
            numprocessors,
            workingdir,
            jobname,
            inputFile,
            outputFile)

        print("invoking ANSYS with: ", callString)
        call(callString, shell=False)

        # check output file for errors

        numerrors = "undetermined"
        try:
            searchfile = open(outputFile, "r", encoding='utf-8')
        except:
            print("could not open", outputFile)
        else:
            for line in searchfile:
                if "NUMBER OF ERROR" in line:
                    numerrors = int(line.split()[-1])
            searchfile.close()
        return numerrors, outputFile


    @Slot()
    def importTask(self):
        # 生成文件对话框对象
        dialog = QFileDialog()
        # 设置文件过滤器
        dialog.setFileMode(QFileDialog.ExistingFiles)
        dialog.setNameFilter("text (*.txt)")
        # 设置显示文件的模式
        dialog.setViewMode(QFileDialog.Detail)
        if dialog.exec_():
            fileNames = dialog.selectedFiles()
            for namePath in fileNames:

                taskName = re.split('/', namePath)[-1]
                taskName = taskName.split('.txt')[0]

                workPath = self.ui.lineEdit_5.text()
                taskPath = workPath + '\\' + taskName
                self.mkdir(taskPath)

                taskText = open(taskPath + '\\' + 'run.txt', 'w', encoding='utf-8')
                baseText = open(namePath, 'r', encoding='utf-8')
                taskText.write(baseText.read())
                taskText.close()
                baseText.close()

                # 修改右侧表格
                rowPosition = self.ui.tableWidget_2.rowCount()
                self.ui.tableWidget_2.insertRow(rowPosition)
                self.ui.tableWidget_2.setItem(rowPosition, 0, QTableWidgetItem(str(rowPosition)))
                self.ui.tableWidget_2.setItem(rowPosition, 1, QTableWidgetItem(taskName))
                self.ui.tableWidget_2.setItem(rowPosition, 2, QTableWidgetItem(taskPath))

    def mkdir(self, path):
        # 判断文件夹是否存在

        folder = os.path.exists(path)
        if not folder:
            os.makedirs(path)


    def upData(self):
        self.ansyscall = self.ui.lineEdit_1.text()
        self.numprocessors = self.ui.spinBox_1.value()
        self.scriptFilename = "run"
        self.rstFalg = self.ui.checkBox_1.isChecked()
        self.extractFalg = self.ui.checkBox_2.isChecked()

    def remove_rst(self, path):
        rootdir = path
        fileSubfix = ['rst']
        for parent, dirnames, filenames in os.walk(rootdir):
            for filename in filenames:
                delfile = os.path.join(parent, filename)
                if os.path.splitext(filename)[1][1:] in fileSubfix:
                    print('删除:' + delfile)
                    os.remove(delfile)

    def tiqu_data(self, fpath, flag_star, falg_end, save_name):

        copy_falg = False

        save_f = open(fpath + '\\' + save_name, 'w', encoding='utf-8')

        with open(fpath + '\\' + 'run.out', 'r', encoding='utf-8') as f:
            line_content = f.readlines()
            for content in line_content:

                # content = content.rstrip('\n')

                if flag_star in content:
                    copy_falg = True
                    continue
                elif falg_end in content:
                    break
                if copy_falg:
                    save_f.write(content)

        save_f.close()

    def showData(self, workingdir, outputFile, taskItem, taskCount):
        try:
            searchfile = open(outputFile, "r", encoding='utf-8')
        except:
            print('error!')
        else:
            for line in searchfile:
                if "NUMBER OF ERROR" in line:
                    errorCode = int(line.split()[-1])

            searchfile.close()
            # 1.搜索统计数据
            searchFlag = False
            with open(outputFile, 'r', encoding='utf-8') as f:

                for line in f:
                    if '+--------------------- A N S Y S   S T A T I S T I C S ------------------------+' in line:
                        searchFlag = True
                    if searchFlag:

                        print(line)
                        time.sleep(0.2)
                    if '+------------------ E N D   A N S Y S   S T A T I S T I C S -------------------+' in line:
                        searchFlag = False
                    if 'Elapsed Time (sec)' in line:
                        pattern = re.compile(r'-?[1-9&]\d*')
                        useTime = pattern.search(line)[0]
                        print('+---------------本次计算用时{}sec----------------+'.format(useTime))
            # 2. 统计更新时间
            self.elapsedTime += int(useTime)
            needTime = (self.elapsedTime / (taskItem + 1)) * (taskCount - taskItem - 1)
            nowTime = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            endTime = (datetime.datetime.now() + datetime.timedelta(seconds=needTime)).strftime("%Y-%m-%d %H:%M:%S")
            print('当前时间：{}，预计结束时间：{}'.format(nowTime, endTime))
            # 2.判断是否要提取数据与删除结果文件
            if not self.rstFalg:
                self.remove_rst(workingdir)
            if self.extractFalg:
                flag_star = '***** ANSYS POST26 VARIABLE LISTING *****'
                falg_end = ' ***** END OF INPUT ENCOUNTERED *****'
                save_name = 'result.txt'
                self.tiqu_data(workingdir, flag_star, falg_end, save_name)

    @Slot()
    def startWork(self):
        # 取基本参数
        ansyscall = self.ansyscall
        numprocessors = self.numprocessors
        scriptFilename = self.scriptFilename
        taskCount = self.ui.tableWidget_2.rowCount()

        for taskItem in range(taskCount):
            taskId = self.ui.tableWidget_2.item(taskItem, 0).text()
            taskName = self.ui.tableWidget_2.item(taskItem, 1).text()
            workingdir = self.ui.tableWidget_2.item(taskItem, 2).text()
            print('+------------------任务开始-------------------+')
            time.sleep(0.5)
            print('当前任务Id：{}，任务名：{}，任务路径：{}'.format(taskId, taskName, workingdir))
            time.sleep(0.5)

            print('+----------求解过程中程序会卡住请勿动 ----------+')
            eroorCode, outputFile = self.runAPDL(ansyscall, numprocessors, workingdir, scriptFilename)
            time.sleep(0.5)
            print('+--------------out文件处理开始-----------------+')
            # mythread = multiprocessing.Process(target=self.runAPDL, args=(ansyscall, numprocessors, workingdir, scriptFilename))
            # mythread.start()
            # mythread.join()
            self.showData(workingdir, outputFile, taskItem, taskCount)
            time.sleep(0.5)
            print('+----------------本次任务结束------------------+')
            time.sleep(0.5)
        # 所有任务完成清除右侧表格数据
        self.ui.tableWidget_2.setRowCount(0)







app = QApplication([])
stats = Stats()
stats.ui.show()
app.exec_()