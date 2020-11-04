import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk
from PIL import Image
import picamera
import picamera.array as array


class MySteamingOutput(array.PiRGBAnalysis):
    def __init__(self, parent, camera, size):
        super(MySteamingOutput, self).__init__(camera, size)
        self.image = None
        self.frame = None
        self.parent = parent

    def analyze(self, a):
        self.image = Image.fromarray(a).rotate(90, expand=True)
        self.parent.queue.put(self.image)


class Display:
    """
    Video stream display class
    """

    def __init__(self, parent, mainapp):
        self.parent = parent
        self.app = mainapp

        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry(f"{self.app.height}x{self.app.width}+481+0")
        self.parent.title("DISPLAY")

        # self.inputImage = None
        self.frame = None
        self.canvas = tk.Canvas(self.parent,
                                width=self.app.height, height=self.app.width,
                                borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0)


class TabBar:
    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent

        self.recVar = tk.IntVar()
        self.recImg = ImageTk.PhotoImage(Image.open("./images/recBtn-01.png"))
        self.stpImg = ImageTk.PhotoImage(Image.open("./images/recBtn-02.png"))
        self.recBtn = tk.Checkbutton(self.window, image=self.recImg, selectimage=self.stpImg,
                                     indicatoron=0, variable=self.recVar, command=self.hitRec,
                                     borderwidth=0, cursor="hand1",
                                     relief=tk.FLAT, offrelief=tk.FLAT,
                                     background="gray", highlightbackground="gray",
                                     activebackground="gray", selectcolor="gray")
        self.recBtn.grid(row=1, column=1, pady=(5, 0))

        self.configBtn = tk.Button(self.window, text="CONFIG", command=lambda: show_config(self.parent),
                                   cursor="hand1", height=3)
        self.configBtn.grid(row=1, column=0, pady=(5, 0))

    def hitRec(self):
        status = self.recVar.get()
        if status:
            print("hitRec: record")
            self.parent.displayFlag.clear()
            self.parent.delayFlag.set()
            self.parent.recFlag.set()
        if not status:
            print("hitRec: stop")
            self.parent.displayFlag.set()
            self.parent.recFlag.clear()


class Config:
    def __init__(self, parent, mainapp):
        self.parent = parent
        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry("200x100+140+350")
        self.parent.title("CONFIG")
        self.parent.protocol("WM_DELETE_WINDOW", lambda: hide_config(self))

        self.app = mainapp

        self.closeBtn = tk.Button(self.parent, text="Done", command=lambda: hide_config(self))
        self.closeBtn.grid(row=0, column=0)


class App(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        # define our parent frame config
        self.parent = parent
        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry("300x100+0+0")
        self.parent.title("PiGolf")

        # This protocol method is a tkinter built-in method to catch if
        # the user clicks the upper corner, "X" on Windows OS
        self.parent.protocol("WM_DELETE_WINDOW", lambda: ask_quit(self))

        self.width = 960
        self.height = 720
        self.resolution = "1024x768"
        self.framerate = 40
        self.refresh = 22   # int(1000/self.framerate)

        self.queue = queue.Queue()

        self.display = Display(create_window(self), self)
        self.tbar = TabBar(self)

        self.config = Config(create_window(self), self)
        self.config.parent.withdraw()

        self.running = 1
        self.currentFile = ""

        self.camThread = threading.Thread(target=self.cameraThread)
        self.camThread.setDaemon(True)
        self.camThread.start()

        # Start the periodic call in the GUI to check the queue
        time.sleep(3)
        self.update()

    def cameraThread(self):
        with picamera.PiCamera(
                resolution=self.resolution,
                framerate=self.framerate
        ) as camera:
            with MySteamingOutput(self, camera, (self.width, self.height)) as output:
                camera.start_recording(output, format='rgb', resize=(self.width, self.height))
                try:
                    while True:
                        camera.wait_recording(1)
                        camera.start_recording('test.h264', format='h264', splitter_port=2)
                        camera.wait_recording(20)
                        camera.stop_recording(splitter_port=2)
                finally:
                    camera.stop_recording()

    def update(self):
        """
        Check every 1 ms if there is something new in the queue.
        :return:
        """
        if not self.running:
            # This is the brutal stop of the system. I may want to do
            # some more cleanup before actually shutting it down.

            # Shuts down the app
            self.parent.destroy()
            import sys
            sys.exit(1)
        # print("update")
        if self.queue.qsize():
            print(f"update: there are {self.queue.qsize()} message(s) in the queue!")
            processIncoming(self)
        self.parent.after(self.refresh, self.update)


def ask_quit(self):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        self.running = 0


def create_window(self):
    window = tk.Toplevel(self.parent)
    return window


def show_config(self):
    self.config.parent.deiconify()
    return


def hide_config(self):
    self.parent.withdraw()


def processIncoming(self):
    """
    Handle all messages currently in the queue, if any.
    :return:
    """
    print("processIncoming: init")
    try:
        msg = self.queue.get(0)
        print("processIncoming: inside if disp_frame:")
        # self.display.inputImage = Image.fromarray(msg).rotate(90, expand=True)
        self.display.frame = ImageTk.PhotoImage(image=msg)
        self.display.canvas.create_image(0, 0, image=self.display.frame, anchor=tk.NW)
        print("processIncoming: disp_frame created")
    finally:
        return


if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)
    root.mainloop()
