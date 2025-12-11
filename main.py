import wx
from ui import Calculadora

def main():
    app = wx.App()
    frame = Calculadora()
    frame.Show()
    app.MainLoop()

if __name__ == "__main__":
    main()
