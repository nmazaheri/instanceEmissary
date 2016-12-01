import cmd
import os
import time
import datetime
import readline
import paramiko
import socket
import getpass
import threading
import Tkinter as tk
import ttk
from ScrolledText import ScrolledText

__author__ = 'navid.mazaheri'
STANDARD_COMMANDS = ("RESTART", "START", "STOP", "KILL-START", "CHECK")
running = False
abortCommandIssued = False

class App(tk.Frame):
    # machine name is key and service name (for service restart) is value
    devMachineServiceMap = {'dev-rtb-adpop':'adpopdaemon', 'dev-rtb-hc':'hazelcast', 'dev-rtb-bidder':'bidder', 'dev-rtb-adserver':'ad-server', 'dev-rtb-fastlog':'fastlog', 'dev-rtb-adevent':'adevent', 'dev-rtb-flume-collector':'collector', 'dev-rtb-contextual-service':'contextual-service'}
    prodMachineServiceMap = {'rtb-adevent':'adevent', 'rtb-adpop':'adpopdaemon', 'rtb-adserver':'adserver', 'rtb-adserver-ba':'adserver', 'rtb-bidder':'bidder', 'rtb-bidder-ba':'bidder', 'rtb-bidder-display':'bidder', 'rtb-flume-collector':'collector', 'rtb-contextual-service':'contextual-service', 'rtb-fastlog':'fastlog', 'rtb-fill':'filldaemon', 'rtb-cs-hc':'hazelcast', 'rtb-hc':'hazelcast', 'rtb-sitetour-bidder':'bidder', 'rtb-test':'testdaemon'}
    devZoneList = ('us-east-1b', 'us-east-1b')
    prodZoneList = ('us-east-1a', 'eu-west-1a', 'ap-southeast-1a','rtb.tm-sjc-1a')

    # Static var
    PAD_X = 10
    WIDTH_AMOUNT = 4
    BUTTON_WIDTH = 10
    DEFAULT_COMMAND_DELAY = 30
    DEFAULT_DAEMON_DELAY = 1
    DEFAULT_MAX_ATTEMPTS = 50

    # UI var
    loginEntry = None
    passwordEntry = None
    commandDelayEntry = None
    daemonDelayEntry = None
    maxAttemptsEntry = None
    customMachineSearchMode = None
    machineNumListEntry = None
    customCommandEntry = None
    textBox = None
    runButton = None

    # Volatile UI var
    isDevEnv = None
    machineEntry = None
    machineOptionMenu = None
    zoneEntry = None
    zoneOptionMenu = None

    def __init__(self, master):
        self.initVars(master)
        self.initTopWindow(tk.Frame(master, bg="white"))
        self.initHorizontalLine(master)
        self.initMachineWindow(tk.Frame(master, bg="white"))
        self.initHorizontalLine(master)
        self.initCustomCommandWindow(tk.Frame(master, bg="white"))
        self.initHorizontalLine(master)
        self.initCommandWindow(tk.Frame(master, bg="white"))
        self.initHorizontalLine(master)
        self.initTextWindow(tk.Frame(master, bg="white"))

        abortFrame = tk.Frame(master, bg="white")
        tk.Button(abortFrame, text="Abort Command", height=2, wraplength=1, width=self.BUTTON_WIDTH, command=lambda: self.sendAbortCommand()).grid()
        abortFrame.pack(pady=2)

        # CommandSender().handle("navid", "fakepass", "30", "5", "30",  "dev-rtb-adserver", ["dev-rtb-adserver01.us-east-1b.public"], "KILL-START", self.textBox)

    def initVars(self, master):
        self.isDevEnv = tk.BooleanVar()
        self.customMachineSearchMode = tk.BooleanVar()
        self.zoneEntry = tk.StringVar()
        self.zoneEntry.set('')
        self.machineEntry = tk.StringVar()
        self.machineEntry.set('')
        tk.Frame.__init__(self, master)
        self.master.title('Instance Cycler: RTB\'s best friend (made by navid)')
        self.master.lift()    

    def initHorizontalLine(self, master):
        tempFrame = tk.Frame(master, bg="white")
        ttk.Separator(tempFrame, orient=tk.HORIZONTAL).grid(row=0, padx=5, pady=10, sticky="ew")
        tempFrame.columnconfigure(0, weight=1)
        tempFrame.pack(padx=self.PAD_X, fill="x")

    def initTopWindow(self, inputFrame):
        rowCount = 0

        tk.Label(inputFrame, text="Login:").grid(row=rowCount, column=0, pady=10)
        tk.Label(inputFrame, text="Password:").grid(row=rowCount, column=2, pady=10)
        self.loginEntry = tk.Entry(inputFrame)
        #default is to use shell username
        username = getpass.getuser()
        if (username == "navid.mazaheri"):
            username = "navid"
        self.loginEntry.insert("insert", username)
        self.loginEntry.grid(row=rowCount, column=1)
        
        self.passwordEntry = tk.Entry(inputFrame, show="*")
        self.passwordEntry.grid(row=rowCount, column=3)

        ## ROW 1
        rowCount += 1
        tk.Label(inputFrame, text="Zone:").grid(row=rowCount, column=0)
        tk.Label(inputFrame, text="Machine:").grid(row=rowCount, column=2)
        self.zoneOptionMenu = tk.OptionMenu(inputFrame, self.zoneEntry, *self.getZones())
        self.zoneOptionMenu.grid(row=rowCount, column=1)
        self.machineOptionMenu = tk.OptionMenu(inputFrame, self.machineEntry, *self.getMachineKeys())
        self.machineOptionMenu.grid(row=rowCount, column=3)
        
        ## ROW 2
        rowCount += 1
        tk.Label(inputFrame, text="Failure Delay (sec):").grid(row=rowCount, column=0)
        self.commandDelayEntry = tk.Entry(inputFrame, width=self.WIDTH_AMOUNT)
        self.commandDelayEntry.grid(row=rowCount, column=1)
        self.commandDelayEntry.insert(0, self.DEFAULT_COMMAND_DELAY)

        tk.Label(inputFrame, text="Dev Machine:").grid(row=rowCount, column=2)
        tk.Checkbutton(inputFrame, variable=self.isDevEnv, width=self.WIDTH_AMOUNT, offvalue=False, onvalue=True, command=self.refreshZoneAndMachineLists).grid(row=rowCount, column=3)

        ## ROW 3
        rowCount += 1
        tk.Label(inputFrame, text="Max Attempts:").grid(row=rowCount, column=0)
        self.maxAttemptsEntry = tk.Entry(inputFrame, width=self.WIDTH_AMOUNT)
        self.maxAttemptsEntry.grid(row=rowCount, column=1)
        self.maxAttemptsEntry.insert(0, self.DEFAULT_MAX_ATTEMPTS)

        tk.Label(inputFrame, text="Daemon Delay (sec):").grid(row=rowCount, column=2)
        self.daemonDelayEntry = tk.Entry(inputFrame, width=self.WIDTH_AMOUNT)
        self.daemonDelayEntry.grid(row=rowCount, column=3)
        self.daemonDelayEntry.insert(0, self.DEFAULT_DAEMON_DELAY)

        inputFrame.pack(pady=10, padx=self.PAD_X)

    def getMachineKeys(self):
        if(self.isDevEnv.get()):
            return sorted(self.devMachineServiceMap.keys())
        return sorted(self.prodMachineServiceMap.keys())

    def getCurrentServiceName(self):
        daemonName = self.machineEntry.get()
        if(self.isDevEnv.get()):
            return self.devMachineServiceMap[daemonName]
        return self.prodMachineServiceMap[daemonName]

    def getZones(self):
        if(self.isDevEnv.get()):
            return sorted(self.devZoneList)
        return sorted(self.prodZoneList)

    def refreshZoneAndMachineLists(self):
        self.zoneEntry.set('')
        self.zoneOptionMenu['menu'].delete(0, 'end')
        for choice in self.getZones():
            self.zoneOptionMenu['menu'].add_command(label=choice, command=tk._setit(self.zoneEntry, choice))

        self.machineEntry.set('')
        self.machineOptionMenu['menu'].delete(0, 'end')
        for choice in self.getMachineKeys():
            self.machineOptionMenu['menu'].add_command(label=choice, command=tk._setit(self.machineEntry, choice))

    def initMachineWindow(self, inputFrame):
        ## ROW 0
        rowCount = 0
        tk.Radiobutton(inputFrame, variable=self.customMachineSearchMode, text="Start to End (3,9):", value=False).grid(row=rowCount, column=1, padx=self.PAD_X)
        tk.Radiobutton(inputFrame, variable=self.customMachineSearchMode, text="Specify Each (1,5,12):", value=True).grid(row=rowCount, column=2, padx=self.PAD_X)
        
        ## ROW 1
        rowCount += 1
        tk.Label(inputFrame, text="Machine List:").grid(row=rowCount, column=0)
        self.startMachineNumEntry = tk.Entry(inputFrame, width=2*self.WIDTH_AMOUNT)
        self.startMachineNumEntry.grid(row=rowCount, column=1, padx=self.PAD_X)
        self.machineNumListEntry = tk.Entry(inputFrame)
        self.machineNumListEntry.grid(row=rowCount, column=2, padx=self.PAD_X, sticky = "ew")

        inputFrame.pack(padx=self.PAD_X)

    def initCustomCommandWindow(self, inputFrame):
        ## ROW 0
        rowCount = 0
        tk.Label(inputFrame, text="Custom Shell Command:").grid(row=rowCount, column=0, sticky="w")
        self.customCommandEntry = tk.Entry(inputFrame)
        self.customCommandEntry.grid(row=rowCount, column=1, columnspan=2, sticky="ew")
        self.runButton = tk.Button(inputFrame, text="Run", command=lambda: self.runStart(self.customCommandEntry.get()))
        self.runButton.grid(row=rowCount, column=3)

        inputFrame.columnconfigure(1, weight=1)
        inputFrame.pack(padx=self.PAD_X, fill="x")

    def initCommandWindow(self, inputFrame): 
        rowCount = 0
        startButton = tk.Button(inputFrame, text="Start Machines", height=2, wraplength=1, width=self.BUTTON_WIDTH, command=lambda: self.runStart("START")).grid(row=rowCount, column=0, padx=15)
        restartButton = tk.Button(inputFrame, text="Restart Machines", height=2, wraplength=1, width=self.BUTTON_WIDTH, command=lambda: self.runStart("RESTART")).grid(row=rowCount, column=1, padx=15)
        killStartButton = tk.Button(inputFrame, text="Kill and Start Machines", height=2, wraplength=1, width=self.BUTTON_WIDTH, command=lambda: self.runStart("KILL-START")).grid(row=rowCount, column=2, padx=15)
        stopButton = tk.Button(inputFrame, text="Stop Machines", height=2, wraplength=1, width=self.BUTTON_WIDTH, command=lambda: self.runStart("STOP")).grid(row=rowCount, column=3, padx=15)
        inputFrame.pack(pady=10, padx=self.PAD_X)

    def initTextWindow(self, inputFrame): 
        self.textBox = ScrolledText(inputFrame, wrap="word", height=10, width=90, borderwidth=3, highlightbackground="grey", relief=tk.SUNKEN)
        self.textBox.grid(row=0, column=0, sticky="NEWS")
        appendTextbox(self.textBox, "Initializing Text Box")

        # weird bug, why do i need to pack the individual widget?
        self.textBox.pack(expand=True, fill="both")
        self.textBox.bind("<1>", lambda event: self.textBox.focus_set())
        inputFrame.pack(padx=self.PAD_X, pady=10, expand=True, fill="both")

    def validateAndGetParameterList(self):
        parameterList = []
        hostList = None

        if(self.loginEntry.get()):
            parameterList.append(self.loginEntry.get())
        else:
            appendTextbox(self.textBox, "Login Entry is null")
            return False

        if(self.passwordEntry.get()):
            parameterList.append(self.passwordEntry.get())
        else:
            appendTextbox(self.textBox, "Password Entry is null")
            return False

        if(self.commandDelayEntry.get()):
            parameterList.append(int(self.commandDelayEntry.get()))
        else:
            appendTextbox(self.textBox, "Command Delay Entry is null")
            return False

        if(self.daemonDelayEntry.get()):
            parameterList.append(int(self.daemonDelayEntry.get()))
        else:
            appendTextbox(self.textBox, "Daemon Delay Entry is null")
            return False

        if(self.maxAttemptsEntry.get()):
            parameterList.append(int(self.maxAttemptsEntry.get()))
        else:
            appendTextbox(self.textBox, "Max Attempts Entry is null")
            return False

        if(self.machineEntry.get()):
            parameterList.append(self.getCurrentServiceName())  
        else:
            appendTextbox(self.textBox, "No Machine selected")
            return False
            
        if(self.zoneEntry.get() == ''):
            appendTextbox(self.textBox, "No Zone selected")
            return False

        if(self.customMachineSearchMode.get()):
            # custom machine list
            if(not self.machineNumListEntry):
                appendTextbox(self.textBox, "Custome Machine Entry is null")
                return False

            hostList = self.getCustomHostList()
        else:
            # start and end machine entries
            if(not self.startMachineNumEntry.get()):
                appendTextbox(self.textBox, "Start/End Machine Entry is null")
                return False

            machineList = self.startMachineNumEntry.get().split(',')
            if(len(machineList) != 2):
                appendTextbox(self.textBox, "Start/End Machine does not have 2 values")
                return False

            startIndex = int(machineList[0])
            endIndex = int(machineList[1])
            if(endIndex < startIndex):
                appendTextbox(self.textBox, "End Machine is lower then start machine")
                return False

            hostList = self.getIterativeHostList(startIndex, endIndex)

        appendTextbox(self.textBox, "Valid input: Planning to connect to [%s]" % ', '.join(hostList))
        parameterList.append(hostList)
        return parameterList

    def getCustomHostList(self):
        hostList = []
        machineList = self.machineNumListEntry.get().split(',')
        for val in machineList:
            hostname =  str("%s%s.%s.public" % (self.machineEntry.get(), convertToString(val), self.zoneEntry.get()))
            hostList.append(hostname)

        hostList.reverse()
        return hostList

    def getIterativeHostList(self, startIndex, endIndex):
        hostList = []
        if(endIndex == startIndex):
            hostname =  str("%s%s.%s.public" % (self.machineEntry.get(), convertToString(startIndex), self.zoneEntry.get()))
            hostList.append(hostname)
            return hostList

        for val in range (startIndex, endIndex+1):
            hostname =  str("%s%s.%s.public" % (self.machineEntry.get(), convertToString(val), self.zoneEntry.get()))
            hostList.append(hostname)
        
        hostList.reverse()
        return hostList

    def sendAbortCommand(self):
        appendTextbox(self.textBox, "Aborting previous command")
        global abortCommandIssued
        abortCommandIssued = True

        global running
        if(not running):
            appendTextbox(self.textBox, "Canceling abort command because service is not running")
            abortCommandIssued = False

    def runStart(self, command):
        global running
        if(running):
            appendTextbox(self.textBox, "Already running command, please wait", True)
            return
            
        # if there is a custom command make sure it is filled in
        if(not command):
            appendTextbox(self.textBox, "Not a valid command", True)
            return

        parameterList = self.validateAndGetParameterList()
        if(not parameterList):
            return

        t = threading.Thread(target=CommandSender().handle, args = (parameterList[0], parameterList[1], parameterList[2], parameterList[3], parameterList[4], parameterList[5], parameterList[6], command, self.textBox))
        t.daemon=True
        t.start()

class CommandSender():
    COMMAND_LENGTH = 50
    serviceName = None
    startCommand = None
    stopCommand = None
    killCommand = None
    isProcessRunningCommand = None
    failedMachinePool = []
    textBox = None
    username = None
    password = None
    commandDelay = None

    def handle(self, username, password, commandDelay, daemonDelay, maxAttempts, serviceName, hostList, command, textBox):
        global running
        running = True
        
        self.textBox = textBox
        self.serviceName = serviceName
        self.username = username
        self.password = password
        self.commandDelay = commandDelay
        self.stopCommand = 'nohup sudo -S service ' + serviceName + ' stop'
        self.startCommand = 'nohup sudo -S service ' + serviceName + ' start'
        self.killCommand = "nohup sudo -S kill -9 $(cat /var/run/" + serviceName + ".pid)"
        self.isProcessRunningCommand = 'ps $(cat /var/run/' + serviceName + ".pid)"

        global abortCommandIssued
        while(len(hostList) > 0 and not abortCommandIssued):
            hostname = hostList.pop()
            appendTextbox(self.textBox, "Submitting \"%s\" to %s" % (command, hostname))

            if (abortCommandIssued):
                self.failedMachinePool.append(hostname)
            elif (command in STANDARD_COMMANDS):
                # running a full command set
                isProcessRunning = self.isProcessRunning(hostname, False)
                self.handleCommand(command, hostname, maxAttempts, isProcessRunning)
                appendTextbox(self.textBox, "Finished %s on %s" % (command, hostname))
            else:
                # running a single custom command
                customCommand = 'nohup sudo -S ' + command
                result = self.submitCommand(hostname, customCommand)
                self.printResult(result)
            if(len(hostList) > 0):
                time.sleep(int(daemonDelay))

        appendTextbox(self.textBox, "Finished Executing %s for all machines" % command)
        self.printFailedMachines()

        running = False
        abortCommandIssued = False

    def printFailedMachines(self):
        if self.failedMachinePool:
            for entry in self.failedMachinePool:
                appendTextbox(self.textBox, self.failedMachinePool)

    def printResult(self, result):
        if (result):
            appendTextbox(self.textBox, "%s" % "".join(result))

    def handleCommand(self, command, hostname, maxAttempts, isProcessRunning):
        if (command == 'START'):
            if (isProcessRunning):
                appendTextbox(self.textBox, "Process is already running", True)
            else:
                self.submitCommand(hostname, self.startCommand)
        
        elif (command == 'STOP'):
            if(isProcessRunning): 
                self.stopProcess(hostname, maxAttempts)
            else:
                appendTextbox(self.textBox, "Process is already stopped", True)

        elif (command == 'RESTART'):
            if (isProcessRunning):
                self.stopProcess(hostname, maxAttempts)
            self.submitCommand(hostname, self.startCommand)

        elif (command == 'KILL-START'):
            if (isProcessRunning):
                self.killProcess(hostname, maxAttempts)
            self.submitCommand(hostname, self.startCommand)

        elif (command == 'CHECK'):
            if (isProcessRunning):
                appendTextbox(self.textBox, "Process is running", True)
            else:
                appendTextbox(self.textBox, "Process is stopped", True)


    def isProcessRunning(self, hostname, verbose = False):
        commandOutput = self.submitCommand(hostname, self.isProcessRunningCommand)
        returnBool = False
        if (commandOutput):
            for line in commandOutput:
                if (len(line) > self.COMMAND_LENGTH):
                    returnBool = True
        if(verbose):
            appendTextbox(self.textBox, ''.join(commandOutput), showTime=False)
        return returnBool

    def stopProcess(self, hostname, maxAttempts, verbose = False):
        appendTextbox(self.textBox, "Stopping %s daemon" % (self.serviceName), False, verbose)
        self.submitCommand(hostname, self.stopCommand)
        isProcessRunning = self.isProcessRunning(hostname)
        attempts = 0
        while(isProcessRunning and attempts <= int(maxAttempts)):
            isProcessRunning = self.isProcessRunning(hostname)
            appendTextbox(self.textBox, "Process is still Running " + str(attempts) + "/" + str(maxAttempts))
            attempts += 1
            if(attempts > int(maxAttempts)):
                self.failedMachinePool.append(hostname)
                return
            self.commandSleep()
        appendTextbox(self.textBox, "%s daemon has been stopped" % self.serviceName, False, verbose)

    def killProcess(self, hostname, maxAttempts, verbose = False):
        appendTextbox(self.textBox, "Killing %s daemon" % (self.serviceName), False, verbose)
        self.submitCommand(hostname, self.killCommand)
        isProcessRunning = self.isProcessRunning(hostname)
        attempts = 0
        while(isProcessRunning and attempts <= int(maxAttempts)):
            isProcessRunning = self.isProcessRunning(hostname)
            appendTextbox(self.textBox, "Process is still Running " + str(attempts) + "/" + str(maxAttempts))
            attempts += 1
            if(attempts > int(maxAttempts)):
                self.failedMachinePool.append(hostname)
                return
            self.commandSleep()
        appendTextbox(self.textBox, "%s daemon has been killed" % self.serviceName, False, verbose)

    def commandSleep(self):
        time.sleep(int(self.commandDelay))

    def submitCommand(self, hostname, command, verbose = False):
        errorCondition = False
        s = paramiko.SSHClient()
        s.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        try:
            s.connect(hostname, username=self.username, password=self.password)
            stdin, stdout, stderr = s.exec_command(command)
            # input password for sudo access
            stdin.write(self.password + '\n')
            stdin.flush()
            stdin.close()
            # read result: first entry in list is the machine name, second entry is the command result
            result = hostname,stdout.readlines()
            if not result:
                errorResult = hostname,stderr.read()
                appendTextbox(self.textBox, "no result when running %s: " % command + errorResult, True)
                errorCondition = True
                
        except paramiko.SSHException, e:
            errorCondition = True
            appendTextbox(self.textBox, "SSH Exception: %s" % e, True)
        except paramiko.AuthenticationException, e:
            errorCondition = True
            appendTextbox(self.textBox, "Authentication Exception: %s" % e, True)
        except socket.gaierror, e:
            errorCondition = True
            appendTextbox(self.textBox, "Socket Error: %s. Does the machine Exist? Are you on the VPN? " % e)
        except:
            errorCondition = True
            appendTextbox(self.textBox, "Unknown Exception", True)

        s.close()
        if(errorCondition): 
            return False
        return result[1]


def appendTextbox(textBox, text, error=False, verbose=True):
    if not verbose:
        return
    ts = time.time()
    st = datetime.datetime.fromtimestamp(ts).strftime('%Y-%m-%d %H:%M:%S')
    if error:
        text = st + " - ERROR: " + str(text)
    else:
        text = st + " - " + str(text)
    print text
    textBox.configure(state="normal")
    textBox.insert("end", text + '\n')
    textBox.configure(state="disabled")
    textBox.pack()

def convertToString(val):
    return "%02d" % int(val)

if __name__ == "__main__":
    app = App(master=tk.Tk())
    app.mainloop()
