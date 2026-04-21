import sys
from PySide6.QtWidgets import QApplication, QMainWindow, QFileDialog
from Ui_MainWindow import Ui_MainWindow

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.ui = Ui_MainWindow()
        self.ui.setupUi(self)

        # Reset progress bar to 0
        self.ui.progressBar.setValue(0)

        # Connect buttons
        self.ui.download_BTN.clicked.connect(self.load_torrent)
        self.ui.stop_BTN.clicked.connect(self.stop_download)
        self.ui.start_BTN.clicked.connect(self.start_download)

    def load_torrent(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Torrent File",
            ""

        )

        if file_path:
            self.ui.textBrowser.setText(file_path)
            self.ui.progressBar.setValue(0)
        else:
            self.ui.textBrowser.setText("No file selected")

    def stop_download(self):
        # TODO: add actual stop logic here
        self.ui.progressBar.setValue(0)
        self.ui.listWidget.clear()

    def display_peers(self, peers):
        self.ui.listWidget.clear()
        for peer in peers:
            self.ui.listWidget.addItem(f"{peer['ip']}:{peer['port']}")


    def start_download(self):
        self.ui.progressBar.setValue(0)
        self.ui.listWidget.clear()


    def update_progress(self, value: int):
        """Call this with 0-100 to update the progress bar."""
        self.ui.progressBar.setValue(value)




if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())