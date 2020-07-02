# coding=utf-8
import maya.OpenMayaUI as mul
import maya.OpenMaya as om
from PySide2.QtWidgets import QMainWindow, QWidget
import maya.cmds as cmds
import shiboken2
from PySide2 import QtCore, QtGui, QtWidgets
import os
import glob
import shutil
import webbrowser
import time
import threading

_win = 'pyside_MainWindow'


def getMayaWindow():
    ptr = mul.MQtUtil.mainWindow()
    return shiboken2.wrapInstance(long(ptr), QWidget)


def getPresetFolder():
    mayaAppDirTemp = os.getenv("MAYA_APP_DIR")
    nodePresets = 'Presets/jn_nodePresets'
    filePath = mayaAppDirTemp + '/' + nodePresets
    # 如果没有就创建这个文件夹
    if not os.path.exists(filePath):
        os.makedirs(filePath)
    return filePath


class JnTreeWidget(QtWidgets.QTreeWidget):
    updateGridLayout = QtCore.Signal(list)

    def __init__(self, parent=None, label='Folder', presetDir=None):
        super(JnTreeWidget, self).__init__(parent)
        self.presetDir = presetDir
        self.setColumnCount(1)  # 设置列数
        self.setHeaderLabel(label)

        # 选择不同的menu出现的事件
        actionEdit = QtWidgets.QAction("New Folder", self)
        actionEdit.triggered.connect(self.addItemAction)
        self.setContextMenuPolicy(QtCore.Qt.ActionsContextMenu)
        self.addAction(actionEdit)

        actionDelete = QtWidgets.QAction("Delete", self)
        actionDelete.triggered.connect(self.deleteItem)
        self.addAction(actionDelete)

        self.style()
        self.connections()

    # 添加右击出线的item
    def addItem(self, name, parent):
        self.expandItem(parent)
        item = QtWidgets.QTreeWidgetItem(parent)
        item.setText(0, name)

        item.setFlags(
            QtCore.Qt.ItemIsSelectable | QtCore.Qt.ItemIsUserCheckable | QtCore.Qt.ItemIsEnabled | QtCore.Qt.ItemIsDragEnabled | QtCore.Qt.ItemIsEditable)
        item.setIcon(0, self.style().standardIcon(QtWidgets.QStyle.SP_DirIcon))
        return item

    # 创建新文件的Item
    def addItemAction(self):
        parent = self.currentItem()
        if parent is None:
            parent = self.invisibleRootItem()
        new_item = self.addItem("New Folder", parent)
        self.editItem(new_item)
        self.setCurrentItem(new_item)
        self.getItemPath(dirList=[], item=new_item)
        os.makedirs(self.parentPath + '/' + new_item.text(0))
        om.MGlobal.displayInfo('The[%s] folder already created.' % new_item.text(0))

    # 删除文件
    def deleteItem(self):
        root = self.invisibleRootItem()
        for item in self.selectedItems():
            self.getItemPath(dirList=[], item=item)
            path = self.parentPath + '/' + item.text(0)
            if os.listdir(path):
                msgBox = QtWidgets.QMessageBox(self)
                msgBox.setWindowTitle('Warning')
                msgBox.setText('This folder has preset files\n\nWe recommend that the backup file.')
                msgBox.setIcon((QtWidgets.QMessageBox.Warning))
                # 如果点了delete要选择yes no和取消
                deleteButton = msgBox.addButton(self.tr("Yes"), QtWidgets.QMessageBox.AcceptRole)
                backupButton = msgBox.addButton(self.tr("Backup"), QtWidgets.QMessageBox.DestructiveRole)
                cancelButton = msgBox.addButton(self.tr("Cancel"), QtWidgets.QMessageBox.RejectRole)
                msgBox.exec_()
                if msgBox.clickedButton() == deleteButton:
                    state = 'Delete'
                elif msgBox.clickedButton() == backupButton:
                    state = 'Backup'
                elif msgBox.clickedButton() == cancelButton:
                    state = 'Cancel'
            else:
                state = 'Delete'
            if state == 'Delete':
                shutil.rmtree(path)
                om.MGlobal.displayInfo('The [%s] folder was deleted.]' % item.text(0))
                (item.parent() or root).removeChild(item)
            elif state == 'Backup':
                webbrowser.open(path)

    def getItemPath(self, dirList=None, item=None):
        parentItem = item.parent()
        if parentItem:
            dirList.insert(0, parentItem.text(0))
            self.getItemPath(dirList=dirList, item=parentItem)
        else:
            tempPath = ''
            for text in dirList:
                tempPath += '/' + text
            self.parentPath = self.presetDir + tempPath

    def getSelectionItemPath(self):
        items = self.selectedItems()
        if items:
            item = items[0]
            self.getItemPath(dirList=[], item=item)
            return self.parentPath + '/' + item.text(0)

    def setPresetsDir(self, presetsDir):
        self.presetDir = presetsDir

    def itemSelectionChangedCmd(self):
        self.selectionItemPath = self.getSelectionItemPath()
        if self.selectionItemPath:
            xmlFiles = glob.glob(self.selectionItemPath + '/*.mb')
            self.updateGridLayout.emit(xmlFiles)

    def itemChangedCmd(self):
        self.newSelectionItemPath = self.getSelectionItemPath()
        if self.newSelectionItemPath:
            os.rename(self.selectionItemPath, self.newSelectionItemPath)
            om.MGlobal.displayInfo('The [%s] folder renamed to [%s]' % (
            os.path.basename(self.selectionItemPath), os.path.basename(self.newSelectionItemPath)))  ####3####
            self.selectionItemPath = self.newSelectionItemPath

    def connections(self):
        self.itemSelectionChanged.connect(self.itemSelectionChangedCmd)
        self.itemChanged.connect(self.itemChangedCmd)


# 写一个类来实现另一个 窗口
class JnGridLayout(QtWidgets.QGridLayout):
    def __init__(self, tb):
        super(JnGridLayout, self).__init__()
        self.maxColumnCount = 5
        self.setSpacing(10)
        self.setGeometry(QtCore.QRect(0, 0, 500, 500))
        self.nodeTypes_textBrowser = tb

    def run(self):
        global if_file_path_changed
        global present_file_path
        global if_window_closed

        while if_window_closed == 0:
            while (if_file_path_changed == 0) and (if_window_closed == 0):
                time.sleep(1)

            if if_file_path_changed == 1:
                self.nodeTypes_textBrowser.showInfo(present_file_path)
                self.nodeTypes_textBrowser.moveCursor(self.nodeTypes_textBrowser.textCursor().End)
                if_file_path_changed = 0

    def open_file(self):

        window2 = OpenImportDialog()
        window2.show()
        global if_window_closed
        if_window_closed = 0
        t = threading.Thread(target=self.run, args=())
        t.setDaemon(True)  # 把子进程设置为守护线程，必须在start()之前设置
        t.start()

    # 刷新网格布局
    def updateGridLayout(self, xmlFiles):
        if xmlFiles:
            while self.count() > 0:
                widget = self.itemAt(0).widget()

                self.removeWidget(widget)
                widget.deleteLater()

            for xmlFile in xmlFiles:
                currentRow = 0
                currentColumn = 0
                while (self.itemAtPosition(currentRow, currentColumn)):
                    if currentColumn == self.maxColumnCount - 1:
                        currentColumn = 0
                        currentRow += 1
                    else:
                        currentColumn += 1
                btn = QtWidgets.QPushButton()
                btn.clicked.connect(self.open_file)

                try:
                    pixmap = QtWidgets.QPixmap(r'D:\pycharmwjj\test5\Icon.png')

                    buttonIcon = QtWidgets.QIcon(pixmap)

                    btn.setIcon(buttonIcon)

                    btn.setFixedSize(pixmap.rect().size())
                    btn.setFixedSize(pixmap.rect().size())
                except:
                    pass

                label = QtWidgets.QLabel(os.path.basename(xmlFile).split('.')[0])
                vLayout = QtWidgets.QVBoxLayout()
                widget = QtWidgets.QWidget()
                widget.setLayout(vLayout)
                vLayout.addStretch(1)
                vLayout.addWidget(btn)
                vLayout.addWidget(label)
                self.addWidget(widget, currentRow, currentColumn)

    def setMaxColumnCount(self, num):
        self.maxColumnCount = num


# 每一个窗口用一个新类来写
class OpenImportDialog(QtWidgets.QDialog):
    FILE_FILTERS = "Maya(*.ma *.mb);;Maya ASCII(*.ma);;Maya Binary(*.mb);;All Files(*.*)"
    selected_filter = "Maya(*.ma *.mb)"

    # 导入界面
    def __init__(self, parent=getMayaWindow()):
        super(OpenImportDialog, self).__init__(parent)

        self.setWindowTitle("Open/Impoet/Edit")
        self.setMinimumSize(300, 80)
        self.setWindowFlags(self.windowFlags() ^ QtCore.Qt.WindowContextHelpButtonHint)

        self.create_widgets()
        self.create_layout()
        self.create_connections()

    def create_widgets(self):
        self.filepath_le = QtWidgets.QLineEdit()
        self.select_file_path_btn = QtWidgets.QPushButton()  # 选择文件的按钮
        self.select_file_path_btn.setIcon(QtGui.QIcon(":fileOpen.png"))  # 设置图标
        self.select_file_path_btn.setToolTip("Select File")

        self.open_rb = QtWidgets.QRadioButton("Open")  # 打开按钮
        self.open_rb.setChecked(True)  # 初始时选定
        self.import_rb = QtWidgets.QRadioButton("Import")  # 导入按钮
        self.edit_rb = QtWidgets.QRadioButton("Edit")  # 参考代理按钮

        self.force_cb = QtWidgets.QCheckBox("Force")

        self.apply_btn = QtWidgets.QPushButton("Apply")  # 应用按钮
        self.close_btn = QtWidgets.QPushButton("Close")  # 关闭按钮

    def create_layout(self):
        file_path_layout = QtWidgets.QHBoxLayout()
        file_path_layout.addWidget(self.filepath_le)
        file_path_layout.addWidget(self.select_file_path_btn)

        radio_btn_layout = QtWidgets.QHBoxLayout()  # 按钮
        radio_btn_layout.addWidget(self.open_rb)
        radio_btn_layout.addWidget(self.import_rb)
        radio_btn_layout.addWidget(self.edit_rb)

        form_layout = QtWidgets.QFormLayout()  # 行布局
        form_layout.addRow("File:", file_path_layout)
        form_layout.addRow("", radio_btn_layout)
        form_layout.addRow("", self.force_cb)

        button_layout = QtWidgets.QHBoxLayout()  # 按钮布局
        button_layout.addStretch()
        button_layout.addWidget(self.apply_btn)  # 添加了两个按钮
        button_layout.addWidget(self.close_btn)

        main_layout = QtWidgets.QVBoxLayout(self)  # 添加到总布局上
        main_layout.addLayout(form_layout)
        main_layout.addLayout(button_layout)

    # closeWindow用来在关窗口的同时改变全局变量if_window_closed的值，使检测停止
    def closeWindow(self):
        global if_window_closed
        if_window_closed = 1
        self.close()

    def create_connections(self):

        self.select_file_path_btn.clicked.connect(self.show_file_select_dialog)  ##选择文件的按钮连接选择文件函数

        self.open_rb.toggled.connect(self.update_force_visibility)
        self.edit_rb.toggled.connect(self.update_force_visibility)

        self.apply_btn.clicked.connect(self.load_file)
        self.close_btn.clicked.connect(self.close)

    def show_file_select_dialog(self):

        file_path, self.selected_filter = QtWidgets.QFileDialog.getOpenFileName(self, "Select File", "",
                                                                                self.FILE_FILTERS, self.selected_filter)
        if file_path:
            self.filepath_le.setText(file_path)
        # 以下：将全局变量if_file_path_changed的值改为1，来通知主窗口已选取文件或选取的文件发生改变
        #      同时将文件路径赋给present_file_path
        global if_file_path_changed
        global present_file_path
        if_file_path_changed = 1
        present_file_path = file_path

    def update_force_visibility(self, checked):
        self.force_cb.setVisible(checked)

    def load_file(self):
        file_path = self.filepath_le.text()
        if not file_path:
            return
        file_info = QtCore.QFileInfo(file_path)
        if not file_info.exists():
            om.MGlobal.displayError("File does not exist:{0}".format(file_path))
            return

        if self.open_rb.isChecked():
            self.open_file(file_path)
        elif self.import_rb.isChecked():
            self.import_file(file_path)
        elif self.edit_rb.isChecked():
            self.edit_file(file_path)

    def open_file(self, file_path):
        force = self.force_cb.isChecked()
        # 打开新的文件时，要将当前文件关闭
        if not force and cmds.file(q=True, modified=True):
            result = QtWidgets.QMessageBox.question(self, "Modified", "Current scene has unsaved changes.Continue?")
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                force = True
            else:
                return

        cmds.file(file_path, open=True, ignoreVersion=True, force=force)
        # 以下：窗口关闭后修改全局变量，停止检测
        global if_window_closed
        if_window_closed = 1

    def import_file(self, file_path):
        cmds.file(file_path, i=True, ignoreVersion=True)
        # 以下：窗口关闭后修改全局变量，停止检测
        global if_window_closed
        if_window_closed = 1

    def edit_file(self, file_path):
        force = self.force_cb.isChecked()
        # 回去编辑那个节点先判断是否保存
        if not force and cmds.file(q=True, modified=True):
            result = QtWidgets.QMessageBox.question(self, "Modified", "Current scene hasn't saved, Continue?")
            if result == QtWidgets.QMessageBox.StandardButton.Yes:
                force = True
            else:
                return

        cmds.file(file_path, open=True, ignoreVersion=True, force=force)
        # 以下：窗口关闭后修改全局变量，停止检测
        global if_window_closed
        if_window_closed = 1


# 两个获取时间的函数
def fileAlteredTime(file):
    t1 = time.ctime(os.path.getmtime(file))
    return t1


def fileCreatedTime(file):
    t2 = time.ctime(os.path.getctime(file))
    return t2


# TextBrowser的类，定义了一个显示时间的函数
class TestTextBrowser(QtWidgets.QTextBrowser):
    def __init__(self, parent=None):
        super(TestTextBrowser, self).__init__(parent)

    def showInfo(self, text):
        self.append('====================')
        self.append('File:')
        self.append(text)
        self.append('Created Time:')
        self.append(fileCreatedTime(text))
        self.append('Altered Time:')
        self.append(fileAlteredTime(text))


class win(QMainWindow):
    def __init__(self, parent=getMayaWindow()):
        super(win, self).__init__(parent)
        self.setObjectName(_win)
        self.resize(600, 400)
        self.presetDir = getPresetFolder()
        # self.gridCloumnCount = 5

    def create(self):
        self.createControls()
        self.createMenuBar()
        self.createLayouts()
        self.retranslateUi()
        self.setting()
        self.createConnections()
        self.setTabOrders()

    def createControls(self):
        self.dir_label = QtWidgets.QLabel()
        self.dir_lineEdit = QtWidgets.QLineEdit()
        self.dir_pushButton = QtWidgets.QPushButton()
        self.search_lineEdit = QtWidgets.QLineEdit()
        self.grid_horizontalSlider = QtWidgets.QSlider()
        self.grid_horizontalSlider.setOrientation(QtCore.Qt.Horizontal)
        self.grid_spinBox = QtWidgets.QSpinBox()

        self.grid_horizontalSlider.setMaximum(10)
        self.grid_horizontalSlider.setMinimum(1)
        self.grid_horizontalSlider.setTickInterval(1)
        self.grid_horizontalSlider.setTickPosition(QtWidgets.QSlider.TicksAbove)

        self.favorites_treeWidget = JnTreeWidget(self, label='Favorites', presetDir=self.presetDir)
        self.nodeTypes_textBrowser = TestTextBrowser(self)

    def createMenuBar(self):
        self.menubar = QtWidgets.QMenuBar(self)
        self.menubar.setGeometry(QtCore.QRect(0, 0, 697, 26))
        self.menu_Edit = QtWidgets.QMenu(self.menubar)
        self.menuTools = QtWidgets.QMenu(self.menubar)
        self.menu_Help = QtWidgets.QMenu(self.menubar)
        self.setMenuBar(self.menubar)
        self.menubar.addAction(self.menu_Edit.menuAction())
        self.menubar.addAction(self.menuTools.menuAction())
        self.menubar.addAction(self.menu_Help.menuAction())

        # QtCore.QMetaObject.connectSlotsByName(self)

    def createLayouts(self):
        self.centralwidget = QtWidgets.QWidget(self)
        self.main_verticalLayout = QtWidgets.QVBoxLayout(self.centralwidget)

        self.dir_horizontalLayout = QtWidgets.QHBoxLayout()
        self.dir_horizontalLayout.addWidget(self.dir_label)
        self.dir_horizontalLayout.addWidget(self.dir_lineEdit)
        self.dir_horizontalLayout.addWidget(self.dir_pushButton)
        self.main_verticalLayout.addLayout(self.dir_horizontalLayout)

        self.gridSetting_horizontalLayout = QtWidgets.QHBoxLayout()
        self.gridSetting_horizontalLayout.addWidget(self.grid_horizontalSlider)
        self.gridSetting_horizontalLayout.addWidget(self.grid_spinBox)

        self.main_formLayout = QtWidgets.QFormLayout()

        self.left_verticalLayout = QtWidgets.QVBoxLayout()
        self.left_verticalLayout.addWidget(self.favorites_treeWidget)
        self.left_verticalLayout.addWidget(self.nodeTypes_textBrowser)
        self.main_formLayout.setWidget(0, QtWidgets.QFormLayout.LabelRole, self.search_lineEdit)
        self.main_formLayout.setLayout(1, QtWidgets.QFormLayout.LabelRole, self.left_verticalLayout)

        self.presets_gridLayout = JnGridLayout(self.nodeTypes_textBrowser)
        self.presets_gridLayout.setSpacing(5)

        self.presets_scrollWidget = QtWidgets.QWidget()
        self.presets_scrollWidget.setLayout((self.presets_gridLayout))

        self.presets_scrollArea = QtWidgets.QScrollArea()
        self.presets_scrollArea.setWidgetResizable(True)
        self.presets_scrollArea.setWidget(self.presets_scrollWidget)

        self.presets_horizontalLayout = QtWidgets.QHBoxLayout()
        self.presets_horizontalLayout.addWidget(self.presets_scrollArea)

        self.main_formLayout.setLayout(0, QtWidgets.QFormLayout.FieldRole, self.gridSetting_horizontalLayout)
        self.main_formLayout.setLayout(1, QtWidgets.QFormLayout.FieldRole, self.presets_horizontalLayout)

        self.main_verticalLayout.addLayout(self.main_formLayout)
        self.main_verticalLayout.addStretch(1)

        self.setCentralWidget(self.centralwidget)

    def retranslateUi(self):
        self.setWindowTitle(QtWidgets.QApplication.translate("MainWindow", "Node Presets Library", None, -1))
        self.dir_label.setText(QtWidgets.QApplication.translate("MainWindow", "&Dir", None, -1))
        self.dir_pushButton.setText(QtWidgets.QApplication.translate("MainWindow", "&Set", None, -1))
        self.menu_Edit.setTitle(QtWidgets.QApplication.translate("MainWindow", "&Edit", None, -1))
        self.menuTools.setTitle(QtWidgets.QApplication.translate("MainWindow", "Tools", None, -1))
        self.menu_Help.setTitle(QtWidgets.QApplication.translate("MainWindow", "&Help", None, -1))

    def setTabOrders(self):

        self.setTabOrder(self.dir_lineEdit, self.dir_pushButton)
        self.setTabOrder(self.dir_pushButton, self.search_lineEdit)
        self.setTabOrder(self.search_lineEdit, self.favorites_treeWidget)
        self.setTabOrder(self.favorites_treeWidget, self.nodeTypes_textBrowser)
        self.setTabOrder(self.nodeTypes_textBrowser, self.grid_horizontalSlider)
        self.setTabOrder(self.grid_horizontalSlider, self.grid_spinBox)

    def setting(self):
        # self.search_lineEdit.setFixedSize(QtCore.QSize(255,1677215))
        self.dir_lineEdit.setText(self.presetDir)
        self.updateTreeWidget(dir=self.presetDir, treeWidgetItem=self.favorites_treeWidget.invisibleRootItem())
        QtCore.QMetaObject.connectSlotsByName(self)
        # self.grid_horizontalSlider.setValue(self.gridCloumnCount)
        # self.presets_gridLayout.setMaxColumnCount(self.gridColumnCount)
        # self.grid_spinBox.setValue(self.gridClumnCount)

    def createConnections(self):
        self.grid_horizontalSlider.valueChanged.connect(self.grid_spinBox.setValue)
        self.grid_spinBox.valueChanged.connect(self.grid_horizontalSlider.setValue)
        self.dir_pushButton.clicked.connect(self.dirBtnCmd)
        self.dir_lineEdit.editingFinished.connect(self.lineEditCmd)
        self.favorites_treeWidget.updateGridLayout.connect(self.presets_gridLayout.updateGridLayout)
        self.grid_horizontalSlider.valueChanged.connect(self.presets_gridLayout.setMaxColumnCount)

    def dirBtnCmd(self):
        options = QtWidgets.QFileDialog.DontResolveSymlinks | QtWidgets.QFileDialog.ShowDirsOnly
        directory = QtWidgets.QFileDialog.getExistingDirectory(self, "Setting Presets Dir", self.dir_lineEdit.text(),
                                                               options)
        if directory:
            self.dir_lineEdit.setText(directory)
            self.presetDir = directory
            self.grid_horizontalSlider.setValue(1)
            # self.favorites_treeWidget.setPresetsDir(self.presetDir)
            self.updateTreeWidget(dir=self.presetDir,
                                  treeWidgetItem=self.favorites_treeWidget.invisibleRootItem())  #####s

    def lineEditCmd(self):
        self.presetDir = self.dir_lineEdit.text()
        # self.favorites_treeWidget.setPresetsDir(self.presetsDir)
        self.updateTreeWidget(dir=self.presetDir, treeWidgetItem=self.favorites_treeWidget.invisibleRootItem())

    def updateTreeWidget(self, dir, treeWidgetItem):
        if dir is self.presetDir:
            self.favorites_treeWidget.clear()
        files = os.listdir(dir)
        if files:
            for f in files:
                tempPath = dir + '/' + f
                if os.path.isdir(tempPath):
                    item = self.favorites_treeWidget.addItem(f, treeWidgetItem)
                    self.updateTreeWidget(dir=tempPath, treeWidgetItem=item)


def main():
    if cmds.window(_win, exists=True):
        cmds.deleteUI(_win)
    w = win()
    w.create()
    w.show()


if __name__ == '__main__':
    main()
