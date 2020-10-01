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
        self.camera.resolution = (1024, 768)
        self.camera.framerate = 40
        self.dispWidth = 480
        self.dispHeight = 640
        self.reviewWidth = 1024
        self.reviewHeight = 768

        self.dispArray = array.PiRGBArray(self.camera, size=(self.dispWidth, self.dispHeight))
        self.reviewArray = array.PiRGBArray(self.camera, size=(self.reviewWidth, self.reviewHeight))

        self.stream = picamera.PiCameraCircularIO(self.camera, seconds=10)

        self.camera.start_recording(self.stream, format='h264')

    def getFrame(self, source):
        # print("getFrame: init")
        if source == "display":
            # print("getFrame: inside if Display")
            disp_output = self.dispArray
            try:
                self.camera.capture(disp_output, format="rgb", use_video_port=True, resize=(self.dispWidth, self.dispHeight))
                frame = disp_output.array
                disp_output.truncate(0)
                disp_frame = ['disp_frame', frame]
                # print("getFrame: disp_frame sent")
                return disp_frame
            finally:
                pass
        elif source == "review":
            print("getFrame: inside if review")
            review_output = self.reviewArray
            try:
                print("getFrame: before capture")
                self.camera.capture(review_output, format="rgb", use_video_port=True)
                print("getFrame: after capture")
                frame = review_output.array
                review_output.truncate(0)
                rev_frame = ['rev_frame', frame]
                print("getFrame: rev_frame sent")
                return rev_frame
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
        self.frame = None
        self.canvas = tk.Canvas(self.window,
                                width=self.parent.cam.dispWidth, height=self.parent.cam.dispHeight,
                                borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0, columnspan=3)


class TabBar:
    def __init__(self, parent):
        self.parent = parent
        self.window = self.parent.parent

        self.recVar = tk.IntVar()
        self.reviewVar = tk.IntVar()
        self.configVar = tk.IntVar()
        self.recImg = ImageTk.PhotoImage(Image.open("./images/recBtn-01.png"))
        self.stpImg = ImageTk.PhotoImage(Image.open("./images/recBtn-02.png"))
        self.recBtn = tk.Checkbutton(self.window, image=self.recImg, selectimage=self.stpImg,
                                     indicatoron=0, variable=self.recVar,
                                     borderwidth=0, cursor="hand1",
                                     relief=tk.FLAT, offrelief=tk.FLAT,
                                     background="gray", highlightbackground="gray",
                                     activebackground="gray", selectcolor="gray")
        self.recBtn.grid(row=1, column=1, pady=(5, 0))
        self.reviewBtn = tk.Button(self.window, text="REVIEW", command=lambda: start_review(self.parent),
                                   cursor="hand1", height=3)
        self.reviewBtn.grid(row=1, column=2, pady=(5, 0))
        self.configBtn = tk.Button(self.window, text="CONFIG", command=lambda: show_config(self.parent),
                                   cursor="hand1", height=3)
        self.configBtn.grid(row=1, column=0, pady=(5, 0))


class Review:
    def __init__(self, parent, mainapp):
        self.parent = parent
        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry("1024x768+480+0")
        self.parent.title("REVIEW")

        self.app = mainapp

        self.frame = None
        self.canvas = tk.Canvas(self.parent,
                                width=self.app.cam.reviewWidth, height=self.app.cam.reviewHeight,
                                borderwidth=0, highlightthickness=0)
        self.canvas.grid(row=0, column=0)

        self.revThread = threading.Thread(target=self.reviewThread)
        self.revThread.start()

    def reviewThread(self):
        try:
            while self.app.running:
                print("reviewThread: inside while loop")
                time.sleep(0.025)
                self.app.cam.camera.wait_recording()
                rev_frame = self.app.cam.getFrame("review")
                self.app.queue.put(rev_frame)
        finally:
            return


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

        self.review = None

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
                frame = self.cam.getFrame("display")
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


def start_review(self):
    self.review = Review(create_window(self), self)
    return


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
                self.display.frame = ImageTk.PhotoImage(image=Image.fromarray(msg[1]))
                self.display.canvas.create_image(0, 0, image=self.display.frame, anchor=tk.NW)
            elif msg[0] == 'rev_frame':
                print("processIncoming: inside if rev_frame:")
                self.review.frame = ImageTk.PhotoImage(image=Image.fromarray(msg[1]))
                self.review.canvas.create_image(0, 0, image=self.review.frame, anchor=tk.NW)
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
