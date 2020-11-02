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

    def __init__(self, parent):
        # initialize the camera
        self.parent = parent
        self.camera = picamera.PiCamera()
        self.width = 1280
        self.height = 960
        self.camera.resolution = (self.width, self.height)
        self.camera.framerate = 25
        # self.camera.hflip = True

        self.dispArray = array.PiRGBArray(self.camera, size=(self.width, self.height))
        self.delayArray = array.PiRGBArray(self.camera, size=(self.width, self.height))

        self.stream = picamera.PiCameraCircularIO(self.camera, seconds=1)

        self.camera.start_recording(self.stream, format='h264')

    def getFrame(self, source):
        # print("getFrame: init")
        if source == "display":
            # print("getFrame: inside if Display")
            disp_output = self.dispArray
            try:
                # print("getFrame: before display capture")
                disp_output.truncate(0)
                self.camera.capture(disp_output, format="rgb", use_video_port=True)
                disp_frame = disp_output.array
                disp_output.truncate(0)
                disp_frame = ['disp_frame', disp_frame]
                # print("getFrame: disp_frame returned")
                return disp_frame
            finally:
                pass
        if source == "delay":
            # print("getFrame: inside if Delay")
            delay_output = self.delayArray
            try:
                # print("getFrame: before delay capture")
                self.camera.capture(delay_output, format="rgb", use_video_port=True)
                delay_frame = delay_output.array
                delay_output.truncate(0)
                disp_frame = ['delay_frame', delay_frame]
                # print("getFrame: delay frame returned")
                return disp_frame
            finally:
                pass
        else:
            err_msg = ('error', 'error')
            return err_msg

    def record(self):
        try:
            self.camera.wait_recording()
            fname = f'{time.strftime("%d-%m-%Y-%H-%M-%S")}.h264'
            self.parent.currentFile = f'./swings/{fname}'
            self.camera.split_recording(self.parent.currentFile, format="h264",
                                        inline_headers=True, sps_timing=True)
        except picamera.exc.PiCameraNotRecording:
            print('Recording interrupted.')
        finally:
            return


class Display:
    """
    Video stream display class
    """

    def __init__(self, parent, mainapp):
        self.parent = parent
        self.app = mainapp

        self.parent.configure(background="gray", borderwidth=0)
        self.parent.geometry(f"{self.app.cam.width}x{self.app.cam.height}+481+0")
        self.parent.title("DISPLAY")

        self.inputImage = None
        # self.outputImage = None
        self.frame = None
        self.canvas = tk.Canvas(self.parent,
                                width=self.app.cam.width, height=self.app.cam.height,
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

        self.delay = 0.040
        self.cam = Camera(self)
        self.queue = queue.Queue()

        self.display = Display(create_window(self), self)
        self.tbar = TabBar(self)

        self.config = Config(create_window(self), self)
        self.config.parent.withdraw()

        self.running = 1
        self.currentFile = ""

        # Event objects to allow threads to communicate
        self.displayFlag = threading.Event()
        self.displayFlag.set()
        self.recFlag = threading.Event()
        self.delayFlag = threading.Event()

        # Thread for handling the video feed
        self.dispThread = threading.Thread(target=self.displayThread)
        self.dispThread.setDaemon(True)
        self.dispThread.start()

        # Thread for recording
        self.recThread = threading.Thread(target=self.recordThread)
        self.recThread.setDaemon(True)
        self.recThread.start()

        # Thread for handling the delay
        self.delThread = threading.Thread(target=self.delayThread)
        self.delThread.setDaemon(True)
        self.delThread.start()

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
                # print("displayThread: waiting")
                self.displayFlag.wait()
                # print("displayThread: displayFlag set")
                while self.displayFlag.isSet():
                    try:
                        time.sleep(self.delay)
                        self.cam.camera.wait_recording()
                        # print("displayThread: getFrame")
                        disp_frame = self.cam.getFrame("display")
                        self.queue.put(disp_frame)
                        # print("displayThread: put disp_frame")
                    except:
                        pass
                    finally:
                        pass
        finally:
            return

    def recordThread(self):
        try:
            while self.running:
                # print("recordThread: waiting")
                self.recFlag.wait()
                # print("recordThread: recFlag set")
                if self.recFlag.isSet():
                    try:
                        print('Recording...')
                        self.cam.record()
                    finally:
                        self.displayFlag.wait()
                        self.cam.camera.split_recording(self.cam.stream, format='h264', level="4.2")
                        print('Saved')
        finally:
            return

    def delayThread(self):
        try:
            while self.running:
                # print("delayThread: waiting")
                self.recFlag.wait()
                # print("delayThread: recFlag set")
                while self.recFlag.isSet():
                    try:
                        time.sleep(self.delay)
                        self.cam.camera.wait_recording()
                        # print("delayThread: getting frame")
                        delay_frame = self.cam.getFrame("delay")
                        self.queue.put(delay_frame)
                        # print("delayThread: frame sent to queue")
                    except:
                        pass
                    finally:
                        pass
        finally:
            return

    def periodicCall(self):
        """
        Check every 1 ms if there is something new in the queue.
        :return:
        """
        if not self.running:
            # This is the brutal stop of the system. I may want to do
            # some more cleanup before actually shutting it down.
            self.cam.camera.stop_recording()
            self.cam.camera.close()
            # Shuts down the app
            self.parent.destroy()
            import sys
            sys.exit(1)
        if self.queue.qsize():
            # print("periodicCall: there is a message in the queue!")
            processIncoming(self)
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
    try:
        if self.delayFlag.isSet():
            # print("processIncoming: inside if delayFlag:")
            time.sleep(5)
            self.delayFlag.clear()
        msg = self.queue.get(0)
        if msg[0] == 'disp_frame' and self.displayFlag.isSet():
            # print("processIncoming: inside if disp_frame:")
            self.display.inputImage = Image.fromarray(msg[1])
            # self.display.outputImage = self.display.inputImage.rotate(90, expand=True)
            self.display.frame = ImageTk.PhotoImage(image=self.display.inputImage)
            self.display.canvas.create_image(0, 0, image=self.display.frame, anchor=tk.NW)
            # print("processIncoming: disp_frame created")
        if msg[0] == 'delay_frame' and self.recFlag.isSet():
            # print("processIncoming: inside if delay_frame:")
            self.display.inputImage = Image.fromarray(msg[1])
            # self.display.outputImage = self.display.inputImage.rotate(90, expand=True)
            self.display.frame = ImageTk.PhotoImage(image=self.display.inputImage)
            time.sleep(self.delay)
            self.display.canvas.create_image(0, 0, image=self.display.frame, anchor=tk.NW)
            # print("processIncoming: delay_frame created")
        else:
            # print("processIncoming: pass")
            pass
    except:
        # just on general principles, although we don't
        # expect this branch to ever be taken
        pass
    finally:
        return


if __name__ == "__main__":
    root = tk.Tk()

    app = App(root)
    root.mainloop()
