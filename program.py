import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QFileDialog
from Ui_MainWindow import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # connect button to function
        self.ui.pushButton.clicked.connect(self.load_torrent)

    def load_torrent(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            "",
            "Torrent Files (*.torrent)"
        )

        if file_path:
            self.ui.textBrowser.setText(file_path)
        else:
            self.ui.textBrowser.setText("No file selected")

    def display_peers(self, peers):
        self.ui.listWidget.clear()
        for peer in peers:
            self.ui.listWidget.addItem(f"{peer['ip']}:{peer['port']}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec_())