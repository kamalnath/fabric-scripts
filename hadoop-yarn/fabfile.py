#!/usr/bin/env python2
# encoding: utf-8

# Author: Alexandre Fonseca
# Description:
#   Installs, configures and manages Hadoop on a set of nodes
#   in a cluster.
# Associated guide:
#   http://www.alexjf.net/blog/distributed-systems/hadoop-yarn-installation-definitive-guide

import os
from fabric.api import run, cd, env, settings, put, sudo
from fabric.decorators import runs_once, parallel
from fabric.tasks import execute
import json

###############################################################
#  START OF YOUR CONFIGURATION (CHANGE FROM HERE, IF NEEDED)  #
###############################################################

#### Generic ####
SSH_USER = "ubuntu"
# If you need to specify a special ssh key, do it here (e.g EC2 key)
env.key_filename = "~/.ssh/bdata1.pem"


#### EC2 ####
# Is this an EC2 deployment? If so, then we'll autodiscover the right nodes.
EC2 = False
EC2_REGION = "eu-west-1"
# In case this is an EC2 deployment, all cluster nodes must have a tag with
# 'Cluster' as key and the following property as value.
EC2_CLUSTER_NAME = "wisilica"
# Should ResourceManager participate in job execution (also be a slave node?)
EC2_RM_NONSLAVE = True
# Read AWS access key details from env if available
AWS_ACCESSKEY_ID = os.getenv("AWS_ACCESSKEY_ID", "undefined")
AWS_ACCESSKEY_SECRET = os.getenv("AWS_ACCESSKEY_SECRET", "undefined")
# In case the instances you use have an extra storage device which is not
# automatically mounted, specify here the path to that device.
EC2_INSTANCE_STORAGEDEV = None
#EC2_INSTANCE_STORAGEDEV = "/dev/xvdb" For Ubuntu r3.xlarge instances

#zookeeper rellated files
ZOOKEEPER_DATA_DIR = "/HA/data/zookeeper"
IMPORTANT_ZK_DIRS = [ZOOKEEPER_DATA_DIR]

#### Zookeper Package Information ####
ZOOKEEPER_VERSION = "3.4.6"
ZOOKEEPER_PACKAGE = "zookeeper-%s" % ZOOKEEPER_VERSION
#HADOOP_PACKAGE_URL = "http://apache.mirrors.spacedump.net/hadoop/common/stable/%s.tar.gz" % HADOOP_PACKAGE
ZOOKEEPER_PACKAGE_URL = "https://archive.apache.org/dist/zookeeper/%(hadoop)s/%(hadoop)s.tar.gz" % {'hadoop': ZOOKEEPER_PACKAGE}
ZOOKEEPER_PREFIX = "/home/ubuntu/Programs/%s" % ZOOKEEPER_PACKAGE
ZOOKEEPER_CONF = os.path.join(ZOOKEEPER_PREFIX, "conf")

#### Package Information ####
HADOOP_VERSION = "2.8.5"
HADOOP_PACKAGE = "hadoop-%s" % HADOOP_VERSION
#HADOOP_PACKAGE_URL = "http://apache.mirrors.spacedump.net/hadoop/common/stable/%s.tar.gz" % HADOOP_PACKAGE
HADOOP_PACKAGE_URL = "https://archive.apache.org/dist/hadoop/common/%(hadoop)s/%(hadoop)s.tar.gz" % {'hadoop': HADOOP_PACKAGE}
HADOOP_PREFIX = "/home/ubuntu/Programs/%s" % HADOOP_PACKAGE
HADOOP_CONF = os.path.join(HADOOP_PREFIX, "etc/hadoop")


#### Installation information ####
# Change this to the command you would use to install packages on the
# remote hosts.
PACKAGE_MANAGER_INSTALL = "apt-get -qq install %s" # Debian/Ubuntu
#PACKAGE_MANAGER_INSTALL = "pacman -S %s" # Arch Linux
#PACKAGE_MANAGER_INSTALL = "yum install %s" # CentOS

# Change this list to the list of packages required by Hadoop
# In principle, should just be a JRE for Hadoop, Python
# for the Hadoop Configuration replacement script and wget
# to get the Hadoop package
REQUIREMENTS = ["wget", "python", "openjdk-8-jdk","ntp"] # Debian/Ubuntu
#REQUIREMENTS = ["wget", "python", "jre7-openjdk-headless"] # Arch Linux
#REQUIREMENTS = ["wget", "python", "java-1.7.0-openjdk-devel"] # CentOS

# Commands to execute (in order) before installing listed requirements
# (will run as root). Use to configure extra repos or update repos
REQUIREMENTS_PRE_COMMANDS = ["service iptables stop","service ufw stop"]

# If you want to install Oracle's Java instead of using the OpenJDK that
# comes preinstalled with most distributions replace the previous options
# with a variation of the following: (UBUNTU only)
#REQUIREMENTS = ["wget", "python", "oracle-java8-installer"] # Debian/Ubuntu
#REQUIREMENTS_PRE_COMMANDS = [
#    "add-apt-repository ppa:webupd8team/java",
#    "apt-get -qq update",
#    "echo debconf shared/accepted-oracle-license-v1-1 select true | debconf-set-selections",
#    "echo debconf shared/accepted-oracle-license-v1-1 seen true | debconf-set-selections"
#]


#### Environment ####
# Set this to True/False depending on whether or not ENVIRONMENT_FILE
# points to an environment file that is automatically loaded in a new
# shell session
#ENVIRONMENT_FILE_NOTAUTOLOADED = False
#ENVIRONMENT_FILE = "/home/ubuntu/.bashrc"
ENVIRONMENT_FILE_NOTAUTOLOADED = True
ENVIRONMENT_FILE = "/home/ubuntu/hadoop2_env.sh"

# Should the ENVIRONMENT_VARIABLES be applies to a clean (empty) environment
# file or should they simply be merged (only additions and updates) into the
# existing environment file? In any case, the previous version of the file
# will be backed up.
ENVIRONMENT_FILE_CLEAN = False
ENVIRONMENT_VARIABLES = [
    ("JAVA_HOME", "/usr/lib/jvm/java-1.8.0-openjdk-amd64"), # Debian/Ubuntu 64 bits
    #("JAVA_HOME", "/usr/lib/jvm/java-7-openjdk"), # Arch Linux
    #("JAVA_HOME", "/usr/java/jdk1.7.0_51"), # CentOS
    ("HADOOP_PREFIX", HADOOP_PREFIX),
    ("HADOOP_HOME", HADOOP_PREFIX),
    ("HADOOP_COMMON_HOME", HADOOP_PREFIX),
    ("HADOOP_CONF_DIR", r"\\$HADOOP_PREFIX/etc/hadoop"),
    ("HADOOP_YARN_CONF_DIR", r"\\$HADOOP_PREFIX/etc/hadoop"),
    ("HADOOP_HDFS_HOME", r"\\$HADOOP_PREFIX"),
    ("HADOOP_MAPRED_HOME", r"\\$HADOOP_PREFIX"),
    ("HADOOP_YARN_HOME", r"\\$HADOOP_PREFIX"),
    ("HADOOP_PID_DIR", "/tmp/hadoop_%s" % HADOOP_VERSION),
    ("YARN_PID_DIR", r"\\$HADOOP_PID_DIR"),
    ("ZOOKEEPER_HOME", ZOOKEEPER_PREFIX),
    ("PATH", r"\\$ZOOKEEPER_HOME/bin:\\$HADOOP_PREFIX/bin:\\$HADOOP_PREFIX/sbin:\\$PATH")

]


#### Host data (for non-EC2 deployments) ####
HOSTS_FILE="/etc/hosts"
NET_INTERFACE="ens5"
RESOURCEMANAGER_HOST = "10.200.2.154"
NAMENODE_HOST = RESOURCEMANAGER_HOST

#SLAVE_HOSTS = ["slave%d.alexjf.net" % i for i in range(1, 6)]
# Or equivalently
SLAVE_HOSTS = ["10.200.2.175", "10.200.2.107"]

# If you'll be running map reduce jobs, you should choose a host to be
# the job tracker
JOBTRACKER_HOST = SLAVE_HOSTS[0]
JOBTRACKER_PORT = 8021

# If you'll run MapReduce jobs, you might want to set a JobHistory server.
# e.g: JOBHISTORY_HOST = "jobhistory.alexjf.net"
JOBHISTORY_HOST = JOBTRACKER_HOST
JOBHISTORY_PORT = 10020


#### Configuration ####
# Should the configuration options be applied to a clean (empty) configuration
# file or should they simply be merged (only additions and updates) into the
# existing environment file? In any case, the previous version of the file
# will be backed up.
CONFIGURATION_FILES_CLEAN = True

HADOOP_TEMP = "/HA/data/tmp"
HDFS_DATA_DIR = "/HA/data/datanode"
HDFS_NAME_DIR = "/HA/data/namenode"

IMPORTANT_DIRS = [HADOOP_TEMP, HDFS_DATA_DIR, HDFS_NAME_DIR]


#Cluster-Name
CLUSTER_NAME = "wisilica"


# Need to do this in a function so that we can rewrite the values when any
# of the hosts change in runtime (e.g. EC2 node discovery).
def updateHadoopSiteValues():
    global CORE_SITE_VALUES, HDFS_SITE_VALUES, YARN_SITE_VALUES, MAPRED_SITE_VALUES,ZOOKEEPER_CONF_VALUES


    ZOOKEEPER_CONF_VALUES = {
        "tickTime":2000,
        "initLimit":10,
        "syncLimit":5,
        "dataDir": ZOOKEEPER_DATA_DIR,
        "clientPort":2181,
        "server.1":"%s:2888:3888" % NAMENODE_HOST,
        "server.2":"%s:2888:3888" % SLAVE_HOSTS[0],
        "server.3":"%s:2888:3888" % SLAVE_HOSTS[1]
    }

    CORE_SITE_VALUES = {
        "fs.defaultFS": "hdfs://%s/" % CLUSTER_NAME,
        "fs.s3n.awsAccessKeyId": AWS_ACCESSKEY_ID,
        "fs.s3n.awsSecretAccessKey": AWS_ACCESSKEY_SECRET,
        "hadoop.tmp.dir": HADOOP_TEMP,
        "dfs.journalnode.edits.dir" : "/home/ubuntu/HA/data/jn"
    }

    HDFS_SITE_VALUES = {
        "dfs.datanode.data.dir": "file://%s" % HDFS_DATA_DIR,
        "dfs.namenode.name.dir": "file://%s" % HDFS_NAME_DIR,
        "dfs.nameservices" : CLUSTER_NAME,
        "dfs.replication" : "1",
        "dfs.permissions": "false",
        "dfs.ha.namenodes.%s" % CLUSTER_NAME: "nn1,nn2",
        "dfs.namenode.rpc-address.%s.nn1" % CLUSTER_NAME: "%s:9000" % NAMENODE_HOST,
        "dfs.namenode.rpc-address.%s.nn2" % CLUSTER_NAME: "%s:9000" % SLAVE_HOSTS[0], ## TODO: Remove hardcoding
        "dfs.namenode.http-address.%s.nn1" % CLUSTER_NAME: "%s:50070" % NAMENODE_HOST,
        "dfs.namenode.http-address.%s.nn2" % CLUSTER_NAME: "%s:50070" % SLAVE_HOSTS[0], ## TODO: Remove hardcoding
        "dfs.namenode.shared.edits.dir": "qjournal://%s:8485;%s:8485;%s:8485/%s" %(NAMENODE_HOST,SLAVE_HOSTS[0],SLAVE_HOSTS[1],CLUSTER_NAME), ## TODO: Remove hardcoding
        "dfs.client.failover.proxy.provider.%s" % CLUSTER_NAME : "org.apache.hadoop.hdfs.server.namenode.ha.ConfiguredFailoverProxyProvider",
        "dfs.ha.automatic-failover.enabled": "true",
        "ha.zookeeper.quorum":"%s:2181,%s:2181,%s:2181" %(NAMENODE_HOST,SLAVE_HOSTS[0],SLAVE_HOSTS[1]),
        "dfs.ha.fencing.methods":"sshfence",
        "dfs.ha.fencing.ssh.private-key-files": "/home/ubuntu/.ssh/id_rsa",
        "dfs.namenode.datanode.registration.ip-hostname-check":"false"

    }

    YARN_SITE_VALUES = {
        "yarn.resourcemanager.hostname": RESOURCEMANAGER_HOST,
        "yarn.scheduler.minimum-allocation-mb": 128,
        "yarn.scheduler.maximum-allocation-mb": 1024,
        "yarn.scheduler.minimum-allocation-vcores": 1,
        "yarn.scheduler.maximum-allocation-vcores": 2,
        "yarn.nodemanager.resource.memory-mb": 4096,
        "yarn.nodemanager.resource.cpu-vcores": 4,
        "yarn.log-aggregation-enable": "true",
        "yarn.nodemanager.aux-services": "mapreduce_shuffle",
        "yarn.nodemanager.vmem-pmem-ratio": 3.1,
        "yarn.nodemanager.remote-app-log-dir": os.path.join(HADOOP_TEMP, "logs"),
        "yarn.nodemanager.log-dirs": os.path.join(HADOOP_TEMP, "userlogs"),
#HA part
        "yarn.resourcemanager.ha.enabled":"true",
        "yarn.resourcemanager.cluster-id":"cluster_1", ## TODO: can we change this?
        "yarn.resourcemanager.ha.rm-ids" : "rm1,rm2",
        "yarn.resourcemanager.hostname.rm1": NAMENODE_HOST,
        "yarn.resourcemanager.hostname.rm2": SLAVE_HOSTS[0],
        "yarn.resourcemanager.webapp.address.rm1": "%s:8088" % NAMENODE_HOST,
        "yarn.resourcemanager.webapp.address.rm2": "%s:8088" % SLAVE_HOSTS[0],
        "yarn.resourcemanager.zk-address": "%s:2181,%s:2181,%s:2181" %(NAMENODE_HOST,SLAVE_HOSTS[0],SLAVE_HOSTS[1])
    }

    MAPRED_SITE_VALUES = {
        "yarn.app.mapreduce.am.resource.mb": 1024,
        "yarn.app.mapreduce.am.command-opts": "-Xmx768m",
        "mapreduce.framework.name": "yarn",
        "mapreduce.map.cpu.vcores": 1,
        "mapreduce.map.memory.mb": 1024,
        "mapreduce.map.java.opts": "-Xmx768m",
        "mapreduce.reduce.cpu.vcores": 1,
        "mapreduce.reduce.memory.mb": 1024,
        "mapreduce.reduce.java.opts": "-Xmx768m",
    }

##############################################################
#  END OF YOUR CONFIGURATION (CHANGE UNTIL HERE, IF NEEDED)  #
##############################################################

#####################################################################
#  DON'T CHANGE ANYTHING BELOW (UNLESS YOU KNOW WHAT YOU'RE DOING)  #
#####################################################################
CORE_SITE_VALUES = {}
HDFS_SITE_VALUES = {}
YARN_SITE_VALUES = {}
MAPRED_SITE_VALUES = {}

def bootstrapFabric():
    if EC2:
        readHostsFromEC2()

    updateHadoopSiteValues()

    env.user = SSH_USER
    hosts = [NAMENODE_HOST, RESOURCEMANAGER_HOST, JOBHISTORY_HOST] + SLAVE_HOSTS
    seen = set()
    # Remove empty hosts and duplicates
    cleanedHosts = [host for host in hosts if host and host not in seen and not seen.add(host)]
    env.hosts = cleanedHosts

    if JOBTRACKER_HOST:
        MAPRED_SITE_VALUES["mapreduce.jobtracker.address"] = "%s:%s" % \
            (JOBTRACKER_HOST, JOBTRACKER_PORT)

    if JOBHISTORY_HOST:
        MAPRED_SITE_VALUES["mapreduce.jobhistory.address"] = "%s:%s" % \
            (JOBHISTORY_HOST, JOBHISTORY_PORT)


# MAIN FUNCTIONS
def forceStopEveryJava():
    run("jps | grep -vi jps | cut -d ' ' -f 1 | xargs -L1 -r kill")


@runs_once
def debugHosts():
    print("Resource Manager: {}".format(RESOURCEMANAGER_HOST))
    print("Name node: {}".format(NAMENODE_HOST))
    print("Job Tracker: {}".format(JOBTRACKER_HOST))
    print("Job History: {}".format(JOBHISTORY_HOST))
    print("Slaves: {}".format(SLAVE_HOSTS))

def bootstrap():
    installDependencies()
    setupEnvironment()
    setupHosts()
    bootstrapHadoopYarn()
    bootstrapZK()
    journalNodeOps('start')

def bootstrapHadoopYarn():
    with settings(warn_only=True):
        if EC2_INSTANCE_STORAGEDEV and run("mountpoint /mnt").failed:
            sudo("mkfs.ext4 %s" % EC2_INSTANCE_STORAGEDEV)
            sudo("mount %s /mnt" % EC2_INSTANCE_STORAGEDEV)
            sudo("chmod 0777 /mnt")
            sudo("rm -rf /tmp/hadoop-ubuntu")
    ensureImportantDirectoriesExist()
    #installDependencies()
    install()
    #setupEnvironment()
    config()
    #setupHosts()
    #formatHdfs()

def bootstrapZK():
    ensureImportantZKDirectoriesExist()
    #installDependencies()
    install_ZK()
    #setupEnvironment()
    config_ZK()
    #setupHosts()
    startZKserver()

def ensureImportantDirectoriesExist():
    for importantDir in IMPORTANT_DIRS:
        ensureDirectoryExists(importantDir)
def install():
    installDirectory = os.path.dirname(HADOOP_PREFIX)
    run("mkdir -p %s" % installDirectory)
    with cd(installDirectory):
        with settings(warn_only=True):
            if run("test -f %s.tar.gz" % HADOOP_PACKAGE).failed:
                run("wget -O %s.tar.gz %s" % (HADOOP_PACKAGE, HADOOP_PACKAGE_URL))
        run("tar --overwrite -xf %s.tar.gz" % HADOOP_PACKAGE)

def config():
    changeHadoopProperties("core-site.xml", CORE_SITE_VALUES)
    changeHadoopProperties("hdfs-site.xml", HDFS_SITE_VALUES)
    changeHadoopProperties("yarn-site.xml", YARN_SITE_VALUES)
    changeHadoopProperties("mapred-site.xml", MAPRED_SITE_VALUES)

def formatHdfs():
    if env.host == NAMENODE_HOST:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hdfs namenode -format")

def changeHadoopProperties(fileName, propertyDict):
    if not fileName or not propertyDict:
        return

    with cd(HADOOP_CONF):
        with settings(warn_only=True):
            import hashlib
            replaceHadoopPropertyHash = \
                hashlib.md5(
                    open("replaceHadoopProperty.py", 'rb').read()
                ).hexdigest()
            if run("test %s = `md5sum replaceHadoopProperty.py | cut -d ' ' -f 1`"
                   % replaceHadoopPropertyHash).failed:
                put("replaceHadoopProperty.py", HADOOP_CONF + "/")
                run("chmod +x replaceHadoopProperty.py")

        with settings(warn_only=True):
            if not run("test -f %s" % fileName).failed:
                op = "cp"

                if CONFIGURATION_FILES_CLEAN:
                    op = "mv"

                currentBakNumber = getLastBackupNumber(fileName) + 1
                run("%(op)s %(file)s %(file)s.bak%(bakNumber)d" %
                    {"op": op, "file": fileName, "bakNumber": currentBakNumber})

        run("touch %s" % fileName)

        command = "./replaceHadoopProperty.py '%s' %s" % (fileName,
            " ".join(["'%s' '%s'" % (str(key), str(value)) for key, value in propertyDict.items()]))
        run(command)

def formatZK_NN():
    if env.host == NAMENODE_HOST:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hdfs zkfc -formatZK")

def formatZK_SNN():
    if env.host == SLAVE_HOSTS[0]:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hdfs zkfc -formatZK")

def operation_Zkfc_NN(operation):
    if env.host == NAMENODE_HOST:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s zkfc"%operation)

def operation_Zkfc_SNN(operation):
    if env.host == SLAVE_HOSTS[0]:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s zkfc"%operation)

def bootstrapStandby():
    if env.host == SLAVE_HOSTS[0]:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hdfs namenode -bootstrapStandby")
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh start namenode")
def operationInHadoopEnvironment(operation):
    with cd(HADOOP_PREFIX):
        command = operation
        print (HADOOP_PREFIX)
        if ENVIRONMENT_FILE_NOTAUTOLOADED:
            with settings(warn_only=True):
                import hashlib
                executeInHadoopEnvHash = \
                    hashlib.md5(
                        open("executeInHadoopEnv.sh", 'rb').read()
                    ).hexdigest()
                if run("test %s = `md5sum executeInHadoopEnv.sh | cut -d ' ' -f 1`"
                    % executeInHadoopEnvHash).failed:
                    put("executeInHadoopEnv.sh", HADOOP_PREFIX + "/")
                    run("chmod +x executeInHadoopEnv.sh")
            command = ("./executeInHadoopEnv.sh %s " % ENVIRONMENT_FILE) + command
            print (command)
            run(command)
#        sudo(command,user ='hadoop')
@parallel
def journalNodeOps(operation):
    operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s journalnode" % operation)

def namenode_secondarynamenode_OPS():

    formatHdfs()
    with settings(warn_only=True):
        if (env.host == NAMENODE_HOST):
            operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh start namenode")
        bootstrapStandby()
        #startZKserver()
        # Start/Stop DataNode on all slave hosts
        if env.host in SLAVE_HOSTS:
            operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh start datanode")

        formatZK_NN()
        operation_Zkfc_NN('start')
        formatZK_SNN()
        operation_Zkfc_SNN('start')

        # Start/Stop NodeManager on all container hosts
        if env.host in SLAVE_HOSTS:
            operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/yarn-daemon.sh start nodemanager" )
        # Start/Stop ResourceManager
        if (env.host == SLAVE_HOSTS[0] or env.host == NAMENODE_HOST):
            operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/yarn-daemon.sh start resourcemanager")
        if (env.host == JOBHISTORY_HOST):
            operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/mr-jobhistory-daemon.sh start historyserver" )

def operationOnHadoopDaemons(operation):

    # Start/Stop journalnode
    operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s journalnode" % operation)
    # Start/Stop NameNode
    if (env.host == NAMENODE_HOST):
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s namenode" % operation)

    # Start/Stop DataNode on all slave hosts
    if env.host in SLAVE_HOSTS:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh %s datanode" % operation)

    # Start/Stop ResourceManager
    if (env.host == RESOURCEMANAGER_HOST):
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/yarn-daemon.sh %s resourcemanager" % operation)

    # Start/Stop NodeManager on all container hosts
    if env.host in SLAVE_HOSTS:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/yarn-daemon.sh %s nodemanager" % operation)

    # Start/Stop JobHistory daemon
    if (env.host == JOBHISTORY_HOST):
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/mr-jobhistory-daemon.sh %s historyserver" % operation)

    operation_Zkfc_NN('stop')
    operation_Zkfc_SNN('stop')
    run("jps")

def resetAll():
    with settings(warn_only=True):
        sudo("rm -rf /HA/data")
        sudo("rm -rf  /home/ubuntu/Programs/hadoop-2.8.5/logs/*")
        sudo("rm -rf  /home/ubuntu/Programs/hadoop-2.8.5/etc/hadoop/*.bak*")

def start():
    operationOnHadoopDaemons("start")
def stop():
    operationOnHadoopDaemons("stop")
    stopZKserver()
    if env.host == SLAVE_HOSTS[0]:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/sbin/hadoop-daemon.sh stop namenode")


def test():
    if env.host == RESOURCEMANAGER_HOST:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hadoop jar /home/ubuntu/Programs/hadoop-2.8.5/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-%(version)s.jar org.apache.hadoop.yarn.applications.distributedshell.Client --jar /home/ubuntu/Programs/hadoop-2.8.5/share/hadoop/yarn/hadoop-yarn-applications-distributedshell-%(version)s.jar --shell_command date --num_containers %(numContainers)d --master_memory 1024" %
            {"version": HADOOP_VERSION, "numContainers": len(SLAVE_HOSTS)})
def testMapReduce():
    if env.host == RESOURCEMANAGER_HOST:
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hadoop dfs -rm -f -r out")
        operationInHadoopEnvironment(r"/home/ubuntu/Programs/hadoop-2.8.5/bin/hadoop jar /home/ubuntu/Programs/hadoop-2.8.5/share/hadoop/mapreduce/hadoop-mapreduce-examples-%s.jar randomwriter out" % HADOOP_VERSION)

def ensureImportantZKDirectoriesExist():
    for importantDir in IMPORTANT_ZK_DIRS:
        ensureDirectoryExists(importantDir)

def install_ZK():
    installDirectory = os.path.dirname(ZOOKEEPER_PREFIX)
    run("mkdir -p %s" % installDirectory)
    with cd(installDirectory):
        with settings(warn_only=True):
            if run("test -f %s.tar.gz" % ZOOKEEPER_PACKAGE).failed:
                run("wget -O %s.tar.gz %s" % (ZOOKEEPER_PACKAGE, ZOOKEEPER_PACKAGE_URL))
        run("tar --overwrite -xf %s.tar.gz" % ZOOKEEPER_PACKAGE)

def config_ZK():
    changeZKProperties("zoo.cfg", ZOOKEEPER_CONF_VALUES)
    with cd(ZOOKEEPER_DATA_DIR):
        if (env.host == NAMENODE_HOST):
            run("echo 1 >> myid")
        if env.host == SLAVE_HOSTS[0]: ## TODO: Remove hardcoding
            run("echo 2 >> myid")
        if env.host == SLAVE_HOSTS[1]: ## TODO: Remove hardcoding
            run("echo 3 >> myid")

def changeZKProperties(fileName, propertyDict):
    if not fileName or not propertyDict:
        return

    with cd(ZOOKEEPER_CONF):
        with settings(warn_only=True):
            import hashlib
            makeZKconfigHash = \
                hashlib.md5(
                    open("makeZKconfig.py", 'rb').read()
                ).hexdigest()
            if run("test %s = `md5sum makeZKconfig.py | cut -d ' ' -f 1`"
                   % makeZKconfigHash).failed:
                put("makeZKconfig.py", ZOOKEEPER_CONF + "/")
                run("chmod +x makeZKconfig.py")

        with settings(warn_only=True):
            if not run("test -f %s" % fileName).failed:
                op = "cp"

                if CONFIGURATION_FILES_CLEAN:
                    op = "mv"

                currentBakNumber = getLastBackupNumber(fileName) + 1
                run("%(op)s %(file)s %(file)s.bak%(bakNumber)d" %
                    {"op": op, "file": fileName, "bakNumber": currentBakNumber})

        run("touch %s" % fileName)

        command = "./makeZKconfig.py '%s' '%s' " % (fileName, json.dumps(propertyDict))
        run(command)

def startZKserver():
    operationInZKEnvironment(r"/home/ubuntu/Programs/zookeeper-3.4.6/bin/zkServer.sh start")

def stopZKserver():
    operationInZKEnvironment(r"/home/ubuntu/Programs/zookeeper-3.4.6/bin/zkServer.sh stop")
def operationInZKEnvironment(operation):
    with cd(ZOOKEEPER_PREFIX):
        command = operation
        if ENVIRONMENT_FILE_NOTAUTOLOADED:
            with settings(warn_only=True):
                import hashlib
                executeInZookeeperEnvHash = \
                    hashlib.md5(
                        open("executeInZookeeperEnv.sh", 'rb').read()
                    ).hexdigest()
                if run("test %s = `md5sum executeInZookeeperEnv.sh | cut -d ' ' -f 1`"
                    % executeInZookeeperEnvHash).failed:
                    put("executeInZookeeperEnv.sh", ZOOKEEPER_PREFIX + "/")
                    run("chmod +x executeInZookeeperEnv.sh")
            command = ("./executeInZookeeperEnv.sh %s " % ENVIRONMENT_FILE) + command
            print (command)
            run(command)


@runs_once
def setupHosts():
    privateIps = execute(getPrivateIp)
    execute(updateHosts, privateIps)

    if env.host == RESOURCEMANAGER_HOST:
        run("rm -f privateIps")
        run("touch privateIps")

        for host, privateIp in privateIps.items():
            run("echo '%s' >> privateIps" % privateIp)
def configRevertPrevious():
    revertHadoopPropertiesChange("core-site.xml")
    revertHadoopPropertiesChange("hdfs-site.xml")
    revertHadoopPropertiesChange("yarn-site.xml")
    revertHadoopPropertiesChange("mapred-site.xml")
def setupEnvironment():
    with settings(warn_only=True):
        if not run("test -f %s" % ENVIRONMENT_FILE).failed:
            op = "cp"

            if ENVIRONMENT_FILE_CLEAN:
                op = "mv"

            currentBakNumber = getLastBackupNumber(ENVIRONMENT_FILE) + 1
            run("%(op)s %(file)s %(file)s.bak%(bakNumber)d" %
                {"op": op, "file": ENVIRONMENT_FILE, "bakNumber": currentBakNumber})

    run("touch %s" % ENVIRONMENT_FILE)

    for variable, value in ENVIRONMENT_VARIABLES:
        lineNumber = run("grep -n 'export\s\+%(var)s\=' '%(file)s' | cut -d : -f 1" %
                {"var": variable, "file": ENVIRONMENT_FILE})
        try:
            lineNumber = int(lineNumber)
            run("sed -i \"" + str(lineNumber) + "s@.*@export %(var)s\=%(val)s@\" '%(file)s'" %
                {"var": variable, "val": value, "file": ENVIRONMENT_FILE})
        except ValueError:
            run("echo \"export %(var)s=%(val)s\" >> \"%(file)s\"" %
                {"var": variable, "val": value, "file": ENVIRONMENT_FILE})
def installDependencies():
    with settings(warn_only=True):
        for command in REQUIREMENTS_PRE_COMMANDS:
            sudo(command)
        for requirement in REQUIREMENTS:
            sudo(PACKAGE_MANAGER_INSTALL % requirement)
        setup_passwordless_SSH()
def setup_passwordless_SSH(): #TODO remove hardcoding
        run("ssh-keygen -q -t rsa -N '' -f ~/.ssh/id_rsa <<<y 2>&1 >/dev/null")
        if env.host == NAMENODE_HOST:
            for slaves in SLAVE_HOSTS:
                run("cat ~/.ssh/id_rsa.pub | ssh -i ~/.ssh/bdata1.pem ubuntu@%s 'cat >> ~/.ssh/authorized_keys'" % slaves)
        if env.host == SLAVE_HOSTS[0]:
            run("cat ~/.ssh/id_rsa.pub | ssh -i ~/.ssh/bdata1.pem ubuntu@%s 'cat >> ~/.ssh/authorized_keys'" % SLAVE_HOSTS[1])
            run("cat ~/.ssh/id_rsa.pub | ssh -i ~/.ssh/bdata1.pem ubuntu@%s 'cat >> ~/.ssh/authorized_keys'" % NAMENODE_HOST)
        if env.host == SLAVE_HOSTS[1]:
            run("cat ~/.ssh/id_rsa.pub | ssh -i ~/.ssh/bdata1.pem ubuntu@%s 'cat >> ~/.ssh/authorized_keys'" % SLAVE_HOSTS[0])
            run("cat ~/.ssh/id_rsa.pub | ssh -i ~/.ssh/bdata1.pem ubuntu@%s 'cat >> ~/.ssh/authorized_keys'" % NAMENODE_HOST)
def environmentRevertPrevious():
    revertBackup(ENVIRONMENT_FILE)

# HELPER FUNCTIONS
def ensureDirectoryExists(directory):
    with settings(warn_only=True):
        #sudo ("addgroup hadoop")
        #sudo ("adduser --ingroup hadoop --disabled-password --gecos '' hadoop")
        if run("test -d %s" % directory).failed:
            sudo("mkdir -p %s" % directory)
            sudo("chown -R ubuntu %s" % directory )
            run("chmod 755 %s" % directory)

@parallel
def getPrivateIp():
    if not EC2:
        return run("ifconfig %s | grep 'inet\s\+' | awk '{print $2}' | cut -d':' -f2" % NET_INTERFACE).strip()
    else:
        return run("wget -qO- http://instance-data/latest/meta-data/local-ipv4")
@parallel
def updateHosts(privateIps):
    with settings(warn_only=True):
        if not run("test -f %s" % HOSTS_FILE).failed:
            currentBakNumber = getLastBackupNumber(HOSTS_FILE) + 1
            sudo("cp %(file)s %(file)s.bak%(bakNumber)d" %
                {"file": HOSTS_FILE, "bakNumber": currentBakNumber})

    sudo("touch %s" % HOSTS_FILE)

    for host, privateIp in privateIps.items():
        lineNumber = run("grep -n -F -w -m 1 '%(ip)s' '%(file)s' | cut -d : -f 1" %
                {"ip": privateIp, "file": HOSTS_FILE})
        try:
            lineNumber = int(lineNumber)
            sudo("sed -i \"" + str(lineNumber) + "s@.*@%(ip)s %(host)s@\" '%(file)s'" %
                {"host": host, "ip": privateIp, "file": HOSTS_FILE})
        except ValueError:
            sudo("echo \"%(ip)s %(host)s\" >> \"%(file)s\"" %
                {"host": host, "ip": privateIp, "file": HOSTS_FILE})
def getLastBackupNumber(filePath):
    dirName = os.path.dirname(filePath)
    fileName = os.path.basename(filePath)

    with cd(dirName):
        latestBak = run("ls -1 | grep %s.bak | tail -n 1" % fileName)
        latestBakNumber = -1
        if latestBak:
            latestBakNumber = int(latestBak[len(fileName) + 4:])
        return latestBakNumber
def revertBackup(fileName):
    dirName = os.path.dirname(fileName)

    with cd(dirName):
        latestBakNumber = getLastBackupNumber(fileName)

        # We have already reverted all backups
        if latestBakNumber == -1:
            return
        # Otherwise, perform reversion
        else:
            run("mv %(file)s.bak%(bakNumber)d %(file)s" %
                {"file": fileName, "bakNumber": latestBakNumber})
def revertHadoopPropertiesChange(fileName):
    revertBackup(os.path.join(HADOOP_CONF, fileName))


def readHostsFromEC2():
    import boto.ec2

    global RESOURCEMANAGER_HOST, NAMENODE_HOST, JOBTRACKER_HOST, \
        JOBHISTORY_HOST, SLAVE_HOSTS

    RESOURCEMANAGER_HOST = None
    NAMENODE_HOST = None
    JOBTRACKER_HOST = None
    JOBHISTORY_HOST = None
    SLAVE_HOSTS = []

    conn = boto.ec2.connect_to_region(EC2_REGION,
            aws_access_key_id=AWS_ACCESSKEY_ID,
            aws_secret_access_key=AWS_ACCESSKEY_SECRET)
    instances = conn.get_only_instances(filters={'tag:Cluster': EC2_CLUSTER_NAME})

    for instance in instances:
        instanceTags = instance.tags
        instanceHost = instance.public_dns_name

        if "resourcemanager" in instanceTags:
            RESOURCEMANAGER_HOST = instanceHost

        if "namenode" in instanceTags:
            NAMENODE_HOST = instanceHost

        if "jobhistory" in instanceTags:
            JOBHISTORY_HOST = instanceHost

        if "jobtracker" in instanceTags:
            JOBTRACKER_HOST = instanceHost

        if not EC2_RM_NONSLAVE or instanceHost != RESOURCEMANAGER_HOST:
            SLAVE_HOSTS.append(instanceHost)

    if SLAVE_HOSTS:
        if RESOURCEMANAGER_HOST is None:
            RESOURCEMANAGER_HOST = SLAVE_HOSTS[0]

            if EC2_RM_NONSLAVE:
                SLAVE_HOSTS.remove(0)

        if NAMENODE_HOST is None:
            NAMENODE_HOST = RESOURCEMANAGER_HOST

        if JOBTRACKER_HOST is None:
            JOBTRACKER_HOST = SLAVE_HOSTS[0]

        if JOBHISTORY_HOST is None:
            JOBHISTORY_HOST = SLAVE_HOSTS[0]
bootstrapFabric()
