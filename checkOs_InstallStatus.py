#!/usr/bin/python

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
        print '\nException Occur',str(e)
    finally:
        s.logout()
	s.close()
    return [hostname,output]

def pxe((hostname,commandList)):
    print "pxe %s" % hostname
    result = []
    for command in commandList :
        print 'pxe command:%s' % command
        result.append(subprocess.call(command.split(" ")))
    return [hostname, result]

def rebootAndInstall(processCnt,hostLists):
    from multiprocessing import Pool
    pool = Pool(processes=processCnt)
    print hostLists
    ThreadUnits=[]
    for hostname in hostLists :
        commandList = []
        commandList.append("ipmitool -l lanplus -H %s -U admin -P admin chassis power status" % (hostname))
        # commandList.append("ipmitool -I lanplus -H %s -U admin -P admin power reset" % (hostname))
        ThreadUnits.append((hostname,commandList))

    if ThreadUnits :
        res = pool.map_async(pxe,ThreadUnits)
        result = res.get()
    if  host in result :
        print 'reboot status:%s' % result[1][0]
    pool.close()
    pool.join()

if __name__ == '__main__':
    multiProcessCount = 2 
    hostList=[]
    hostOsTimeList = []
    
    # add the host waiting for check in hostList 
    hostList.append('10.1.4.22')
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
    
    curTime = datetime.datetime.utcnow()
    print 'current Utc Time :%s' % curTime
    print hostOsTimeList    
    oldOsHost = []
    for host in hostOsTimeList :
        if  (curTime - host[1]).days >1 :
            # print 'host %s \'OS is not a fresh one' % host[0]
            oldOsHost.append(host[0])
    if oldOsHost :
        print oldOsHost 
    
    reboot = ['10.0.0.10']
    
    rebootAndInstall(2,reboot)
    
    pool.close()
    pool.join()    
