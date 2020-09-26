import time
import queue
import threading
import tkinter as tk
from tkinter import messagebox
import PIL.Image
import PIL.ImageTk
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
        self.camera.framerate = 30
        self.width = 480
        self.height = 640

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

    def __init__(self, parent, window):
        self.parent = parent
        self.window = window
        self.canvas = tk.Canvas(window, width=self.parent.cam.width, height=self.parent.cam.height)
        self.canvas.pack()

    def processIncoming(self):
        """
        Handle all messages currently in the queue, if any.
        :return:
        """
        # print("processIncoming: init")
        while self.parent.queue.qsize():
            print("processIncoming: inside while loop")
            try:
                msg = self.parent.queue.get(0)
                if msg[0] == 'frame':
                    print("processIncoming: inside if msg:")
                    photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(msg[1]))
                    self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                else:
                    pass
            except self.parent.queue.Empty:
                # just on general principles, although we don't
                # expect this branch to ever be taken
                pass


class TabBar:
    pass


def ask_quit(self):
    if messagebox.askokcancel("Quit", "Do you want to quit?"):
        self.running = 0


def recordThread(self):
    pass


class App:
    def __init__(self, parent):

        # define our parent frame config
        self.parent = parent
        self.parent.title("PIGOLF")
        self.parent.minsize(480, 800)
        self.parent.maxsize(480, 800)

        # This protocol method is a tkinter built-in method to catch if
        # the user clicks the upper corner, "X" on Windows OS
        self.parent.protocol("WM_DELETE_WINDOW", lambda: ask_quit(self))

        self.cam = Camera()
        self.queue = queue.Queue()

        self.display = Display(self, parent)
        self.toolbar = TabBar(self, parent)

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
                time.sleep(0.034)
                self.cam.camera.wait_recording()
                frame = self.cam.getFrame()
                self.queue.put(frame)
        finally:
            return

    def periodicCall(self):
        """
        Check every 17 ms if there is something new in the queue.
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
        self.parent.after(17, self.periodicCall)


if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)
    root.mainloop()
