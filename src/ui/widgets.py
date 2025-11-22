import ctypes
from PyQt6.QtWidgets import QComboBox

class CustomComboBox(QComboBox):
    """Custom QComboBox that hides popup from screen capture."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.screen_share_hidden = False
        self.user32 = ctypes.windll.user32
        self.WDA_EXCLUDEFROMCAPTURE = 0x11
        self.WDA_NONE = 0x00
        
    def showPopup(self):
        """Override to apply screen capture exclusion before showing popup."""
        super().showPopup()
        if self.screen_share_hidden:
            popup = self.view().window()
            if popup:
                hwnd = int(popup.winId())
                self.user32.SetWindowDisplayAffinity(hwnd, self.WDA_EXCLUDEFROMCAPTURE)
    
    def set_screen_share_hidden(self, hidden):
        """Set whether popup should be hidden from screen sharing."""
        self.screen_share_hidden = hidden
