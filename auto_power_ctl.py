#!/usr/bin/env python3
"""自动能源控制端,此程序运行在各个主机端,负责关闭主机电源,注意该程序必须以管理员或者root身份运行
支持平台,Windows,Linux,FreeBSD,OSX
"""
import sys, os, getopt, socket, signal, time

BASE_DIR = os.path.dirname(sys.argv[0])

if not BASE_DIR: BASE_DIR = "."

sys.path.append(BASE_DIR)

PID_PATH = "/tmp/auto_power_ctl.pid"
import pylib.proc as proc


class power_ctl(object):
    __s = None
    __t = None
    __debug = None

    def __init__(self, udp_port, debug=False):
        self.__debug = debug
        self.__t = time.time()
        self.__s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.__s.bind(("0.0.0.0", udp_port))

    def wait(self):
        power_off_msg = bytes([0xff]) * 128

        while 1:
            msg, address = self.__s.recvfrom(4096)
            if msg != power_off_msg:
                sys.stderr.write("wrong power message\r\n")
                continue
            t = time.time()
            # 程序启动的2分钟内不执行关机操作,避免出现其他系统问题
            if t - self.__t < 120:
                if self.__debug: print("the computer cannot shutdown")
                continue
            print("power off")
            break

        self.do_shutdown()

    def do_shutdown(self):
        """执行关机动作
        :return:
        """
        platform = sys.platform
        print("starting shutdown")

        if sys.platform.startswith("win32"):
            self.windows_shutdown()
            return

        self.unix_like_shutdown()

    def windows_shutdown(self):
        os.system("shutdown -s -t 0")

    def unix_like_shutdown(self):
        os.system("halt -p")

    def release(self):
        self.__s.close()


def stop():
    pid = proc.get_pid(PID_PATH)
    if pid < 0: return
    os.remove(PID_PATH)
    os.kill(pid, signal.SIGINT)


def main():
    help_doc = """
    debug | start | stop
    debug | start  [--port=port]
    debug:  windows support it
    start   only unix-like support
    stop    only unix-like support
    """

    if len(sys.argv) < 2:
        print(help_doc)
        return

    action = sys.argv[1]

    if action not in ("debug", "stop", "start"):
        print(help_doc)
        return

    if action == "stop":
        stop()
        return

    try:
        opts, args = getopt.getopt(sys.argv[2:], "", ["port="])
    except getopt.GetoptError:
        print(help_doc)
        return

    port = 1999
    for k, v in opts:
        if k == "--port": port = v

    try:
        port = int(port)
    except ValueError:
        print("wrong port number value")
        return

    if port < 1 or port > 0xfffe:
        print("wrong port number value")
        return

    debug = True

    if action == "start":
        debug = False
        pid = os.fork()
        if pid != 0: sys.exit(0)

        os.setsid()
        os.umask(0)

        pid = os.fork()
        if pid != 0: sys.exit(0)
        proc.write_pid(PID_PATH)

    cls = power_ctl(int(port), debug=debug)
    try:
        cls.wait()
    except KeyboardInterrupt:
        cls.release()


if __name__ == '__main__': main()
