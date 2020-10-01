import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk
from PIL import Image
import picamera
import picamera.array as array


class Camera:
    """
    Video capture class with related methods
    """

    def __init__(self):
        # initialize the camera
        self.camera = picamera.PiCamera()
        self.camera.resolution = (640, 480)
        self.camera.framerate = 90

        self.dispArray = array.PiRGBArray(self.camera, size=(640, 480))

        self.stream = picamera.PiCameraCircularIO(self.camera, seconds=10)

        self.camera.start_recording(self.stream, format='h264')

    def getFrame(self, source):
        # print("getFrame: init")
        if source == "display":
            # print("getFrame: inside if Display")
            disp_output = self.dispArray
            try:
                # print("getFrame: before display capture")
                self.camera.capture(disp_output, format="rgb", use_video_port=True)
                disp_frame = disp_output.array
                disp_output.truncate(0)
                disp_frame = ['disp_frame', disp_frame]
                # print("getFrame: frame returned")
                return disp_frame
            finally:
                pass
        else:
            err_msg = ('error', 'error')
            return err_msg


class Display:
    """
    Video stream display class
    """

    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent
        self.dispWidth = 480
        self.dispHeight = 640
        self.inputImage = None
        self.outputImage = None
        self.frame = None
        self.canvas = tk.Canvas(self.window,
                                width=self.dispWidth, height=self.dispHeight,
                                borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=3)


class TabBar:
    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent

        self.recVar = tk.IntVar()
        self.recImg = ImageTk.PhotoImage(Image.open("./images/recBtn-01.png"))
        self.stpImg = ImageTk.PhotoImage(Image.open("./images/recBtn-02.png"))
        self.recBtn = tk.Checkbutton(self.window, image=self.recImg, selectimage=self.stpImg,
                                     indicatoron=0, variable=self.recVar,
                                     borderwidth=0, cursor="hand1",
                                     relief=tk.FLAT, offrelief=tk.FLAT,
                                     background="gray", highlightbackground="gray",
                                     activebackground="gray", selectcolor="gray")
        self.recBtn.grid(row=1, column=1, pady=(5, 0))

        self.configBtn = tk.Button(self.window, text="CONFIG", command=lambda: show_config(self.parent),
                                   cursor="hand1", height=3)
        self.configBtn.grid(row=1, column=0, pady=(5, 0))


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
        self.parent.geometry("476x730+0+0")
        self.parent.attributes('-zoomed', True)
        self.parent.title("PIGOLF")

        # This protocol method is a tkinter built-in method to catch if
        # the user clicks the upper corner, "X" on Windows OS
        self.parent.protocol("WM_DELETE_WINDOW", lambda: ask_quit(self))

        self.cam = Camera()
        self.queue = queue.Queue()

        self.display = Display(self)
        self.tbar = TabBar(self)

        self.config = Config(create_window(self), self)
        self.config.parent.withdraw()

        self.running = 1
        self.currentFile = ""

        # Thread for handling the video feed
        self.dispThread = threading.Thread(target=self.displayThread)
        self.dispThread.start()

        # Thread for recording
        # self.recThread = threading.Thread(target=recordThread(self))
        # self.recThread.start()

        # Start the periodic call in the GUI to check the queue
        self.periodicCall()

    def displayThread(self):
        """
        This thread handles the video feed to be displayed
        by the gui object.
        :return:
        """
        try:
            while self.running:
                # print("displayThread: inside while loop")
                time.sleep(0.011)
                self.cam.camera.wait_recording()
                disp_frame = self.cam.getFrame("display")
                self.queue.put(disp_frame)
        finally:
            return

    def recordThread(self):
        pass

    def periodicCall(self):
        """
        Check every 1 ms if there is something new in the queue.
        :return:
        """
        processIncoming(self)
        if not self.running:
            # This is the brutal stop of the system. I may want to do
            # some more cleanup before actually shutting it down.
            self.cam.camera.stop_recording()
            self.cam.camera.close()
            # Shuts down the app
            self.parent.destroy()
            import sys
            sys.exit(1)
        self.parent.after(1, self.periodicCall)


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
    # print("processIncoming: init")
    while self.queue.qsize():
        # print("processIncoming: inside while loop")
        try:
            msg = self.queue.get(0)
            if msg[0] == 'disp_frame':
                # print("processIncoming: inside if disp_frame:")
                self.display.inputImage = Image.fromarray(msg[1])
                self.display.outputImage = self.display.inputImage.rotate(270, expand=True)
                self.display.frame = ImageTk.PhotoImage(image=self.display.outputImage)
                self.display.canvas.create_image(0, 0, image=self.display.frame, anchor=tk.NW)
            else:
                pass
        except self.queue.Empty:
            # just on general principles, although we don't
            # expect this branch to ever be taken
            pass


if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)
    root.mainloop()
