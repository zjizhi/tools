#!/usr/bin/python

## ################################################################################
## the package and lib that must install:
##
## OpenIPMI
##  yum install OpenIPMI-python
##
## Pexpect:Version 3.3 or higher
##  caution: a lower version will cause some error like "timeout nonblocking() in read" when you log to a host by ssh
##      wget https://pypi.python.org/packages/source/p/pexpect/pexpect-3.3.tar.gz
##      tar xvf pexpect-3.3.tar.gz
##      cd pexpect-3.3
##      python setup install
##
##        
## Be aware:
##    2014-08-24 : using multiprocessing.dummy to archieve multi-thread instead of multi-processing with multiprocessing
##         in multi-process, the function pssh will cause error like "local variable 's' referenced before assignment"
##      
## ################################################################################

import os
import sys
import pexpect
import pxssh
from multiprocessing.dummy import Pool
import subprocess
import OpenIPMI

def pssh((hostname,username,password,cli)):
    print 'host:%s,cli:%s' % (hostname,cli)
    output=''
    try:
        s = pxssh.pxssh()
        s.login(hostname,username,password)
        s.sendline(cli)
        s.expect(pexpect.EOF, timeout=None)
        # print 'except'
        output=s.before
    except Exception,e:
        print '\nException Occur in ssh to host %s ,Error is:\n %s' % (hostname, str(e))
    finally:
	s.close()
    return [hostname,output]

def pxe((hostname,commandList)):
    print "pxe %s" % hostname
    result = 0
    for command in commandList :
        print 'pxe command:%s' % command
        res=subprocess.call(command.split(" "))

        if res == 1:
            result = 1
            print 'pxe error in host %s' % hostname
            break

    return [hostname, result]

def rebootAndInstall(_hostList):
     TimeInterval=5
     RebootHostInPerInterval=2
    
     with open('restartError.log','w') as file:
         file.truncate()

     while True:
         for i in range(1,RebootHostInPerInterval+1) :
             if _hostList :
                 commandList = []
                 commandList.append("ipmitool -l lanplus -H %s -U admin -P admin chassis power status" % (_hostList[0]))
                 commandList.append("ipmitool -I lanplus -H %s -U admin -P admin power reset" % (_hostList[0]))
                 result = pxe((_hostList[0],commandList))
                 
                 if result[1] == 1:
                     with open('restartError.log','a') as file:
                         file.write(result[0]+'\n')
                 
                 #print 'host :%s ,restart state: %s' % (result[0],result[1])
                 del _hostList[0]

         if _hostList:
             time.sleep(TimeInterval)
         else:
             break



if __name__ == '__main__':
    multiProcessCount = 2 
    hostList=[]
    hostOsTimeList = []
    NewOSFilterInterval = 1 #days
    # add the host waiting for check in hostList 
    hostList.append('10.1.4.100')
    hostList.append('10.1.4.23')
#    print hostList

    cli = "stat /lost+found/ | grep Modify | awk -F ' ' {'print $2,$3,$4'};"
    cli += "exit $?" ## auto logout
    username='root'
    password='qinghua'
    
    pool = Pool(processes=multiProcessCount)
    res=pool.map_async(pssh,((host,username,password,cli) for host in hostList))
    result=res.get()

    import time
    import datetime
    import string
    for output in result:
        if output[1] and output[1] != '' :
            timeArr=output[1].split('\n')[1].split(' ')
            realTimeStruct = time.strptime(timeArr[0]+' '+timeArr[1].split('.')[0],'%Y-%m-%d %H:%M:%S')
            realTime = datetime.datetime(*realTimeStruct[:6])
            osInstallTime_UTC = None
            utcDelta=string.atoi(timeArr[2][1:])
            if '+' in timeArr[2]:
                osInstallTime_UTC = realTime + datetime.timedelta(hours=-1*(utcDelta/100))
            elif '-' in timeArr[2]:
                osInstallTime_UTC = realTime + datetime.timedelta(hours=1*(utcDelta/100))
            
            hostOsTimeList.append((output[0],osInstallTime_UTC))
        else:
            print 'Host %s connection failed' % output[0]

    curTime = datetime.datetime.utcnow()
    print 'current Utc Time :%s' % curTime
    # print hostOsTimeList
    
    oldOsHost = []
    for host in hostOsTimeList :
        print (curTime - host[1]).days
        if  (curTime - host[1]).days > NewOSFilterInterval :
            print 'host %s \'OS is not a fresh one' % host[0]
            oldOsHost.append(host[0])
    if oldOsHost :
        print 'These Hosts\' Os are not reinstall: \n'
        print oldOsHost 
    
    reboot = oldOsHost    
    rebootAndInstall(reboot)
    
    pool.close()
    pool.join()    
