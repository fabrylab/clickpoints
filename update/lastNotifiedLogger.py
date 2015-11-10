__author__ = 'fox'
import os
import datetime


logfile="lastnotified.log"
timeformat='%Y%m%d-%H%M%S'

class lastNotifiedLogger:
    def __init__(self,file):
        self.file=file
        self.tl=None
        self.dt=None

        if os.path.exists(self.file):
            print('read lnl log')
            self.f=open(file,'r')
            self.line=self.f.readline()
            self.f.close()
            self.dt=datetime.datetime.strptime(self.line.strip(),timeformat)
            #print(self.dt)
        else:
            # no file so we should ask anyway
            self.dt=datetime.datetime(1970,01,01,0,0,0)

    def timeElapsed(self):
        self.tl= datetime.datetime.now()-self.dt
        #print(self.tl)

    def excedTimeElpased(self,hours):
        self.timeElapsed()
        if self.tl > datetime.timedelta(hours=hours):
            return True
        else:
            return False

    def clear(self):
        print('clear lnl log')
        if os.path.exists(self.file):
            os.remove(self.file)
        self.dt=None
        self.tl=None

    def update(self):
        print('update lnl log')
        self.f=open(self.file,'w')
        self.dt=datetime.datetime.now()
        self.f.write(datetime.datetime.now().strftime(timeformat))
        self.f.close()
        #print(self.dt)


if __name__ == "__main__":

    print("Init lastNotifiedLogger class")
    lnl = lastNotifiedLogger(logfile)
    print("calc time elapesd:")
    lnl.timeElapsed()
    print("calc if more than 24h have passed")
    lnl.excedTimeElpased(24)
