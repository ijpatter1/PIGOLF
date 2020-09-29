import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
from PIL import ImageTk
from PIL import Image
import picamera
from picamera.array import PiRGBArray


class Camera:
    """
    Video capture class with related methods
    """

    def __init__(self):
        # initialize the camera
        self.camera = picamera.PiCamera()
        self.camera.resolution = (480, 640)
        self.camera.framerate = 40
        self.width = 478
        self.height = 638

        self.rawCapture = PiRGBArray(self.camera, size=(self.width, self.height))

        self.stream = picamera.PiCameraCircularIO(self.camera, seconds=10)
        self.camera.start_recording(self.stream, format='h264')

    def getFrame(self):
        # print("getFrame: init")
        if self.rawCapture:
            # print("getFrame: inside if")
            output = self.rawCapture
            try:
                self.camera.capture(output, format="rgb", use_video_port=True)
                frame = output.array
                output.truncate(0)
                msg = ['frame', frame]
                # print("getFrame: msg sent")
                return msg
            finally:
                pass


class Display:
    """
    Video stream display class
    """

    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent
        self.photo = None
        self.canvas = tk.Canvas(self.window,
                                width=self.parent.cam.width, height=self.parent.cam.height,
                                borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=3)

    def processIncoming(self):
        """
        Handle all messages currently in the queue, if any.
        :return:
        """
        # print("processIncoming: init")
        while self.parent.queue.qsize():
            # print("processIncoming: inside while loop")
            try:
                msg = self.parent.queue.get(0)
                if msg[0] == 'frame':
                    # print("processIncoming: inside if msg:")
                    self.photo = ImageTk.PhotoImage(image=Image.fromarray(msg[1]))
                    self.canvas.create_image(0, 0, image=self.photo, anchor=tk.NW)
                else:
                    pass
            except self.parent.queue.Empty:
                # just on general principles, although we don't
                # expect this branch to ever be taken
                pass


class TabBar():
    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent

        self.var = tk.IntVar()
        self.recImg = ImageTk.PhotoImage(Image.open("./images/recBtn-01.png"))
        self.stpImg = ImageTk.PhotoImage(Image.open("./images/recBtn-02.png"))
        self.recBtn = tk.Checkbutton(self.window, image=self.recImg, selectimage=self.stpImg,
                                     indicatoron=0, variable=self.var,
                                     borderwidth=0, cursor="hand1",
                                     relief=tk.FLAT, offrelief=tk.FLAT,
                                     background="gray", highlightbackground="gray",
                                     activebackground="gray", selectcolor="gray")
        self.recBtn.image_ref = (self.recImg, self.stpImg)
        self.recBtn.grid(row=1, column=1, pady=(5, 0))


class App(tk.Frame):
    def __init__(self, parent, *args, **kwargs):
        tk.Frame.__init__(self, parent, *args, **kwargs)
        # define our parent frame config
        self.parent = parent
        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry("478x750+0+0")
        self.parent.title("PIGOLF")

        # This protocol method is a tkinter built-in method to catch if
        # the user clicks the upper corner, "X" on Windows OS
        self.parent.protocol("WM_DELETE_WINDOW", lambda: ask_quit(self))

        self.cam = Camera()
        self.queue = queue.Queue()

        self.display = Display(self)
        self.tbar = TabBar(self)

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
                time.sleep(0.025)
                self.cam.camera.wait_recording()
                frame = self.cam.getFrame()
                self.queue.put(frame)
        finally:
            return

    def recordThread(self):
        pass

    def periodicCall(self):
        """
        Check every 1 ms if there is something new in the queue.
        :return:
        """
        self.display.processIncoming()
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


if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)
    root.mainloop()
