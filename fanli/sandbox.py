"""学生代码运行器：独立子进程 + 单次调用超时，超时就杀掉重启。

注意：这只是进程隔离，不是安全沙箱。只运行自建题库和同学自愿提交的代码。
"""
import json
import os
import queue
import subprocess
import sys
import threading

WORKER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "worker.py")
TIMEOUT = "__TIMEOUT__"


class StudentRunner:
    def __init__(self, path, func_name, timeout=2.0):
        self.path, self.func_name, self.timeout = path, func_name, timeout
        self.proc = None
        self.load_error = None
        self._start()

    def _start(self):
        # 白名单环境：学生代码所在的子进程拿不到 LLM 密钥等敏感变量。
        _SAFE_ENV = ("PATH", "SYSTEMROOT", "WINDIR", "TEMP", "TMP", "LANG", "LC_ALL")
        env = {k: os.environ[k] for k in _SAFE_ENV if k in os.environ}
        env["PYTHONIOENCODING"] = "utf-8"
        self.proc = subprocess.Popen(
            [sys.executable, "-I", WORKER, os.path.abspath(self.path), self.func_name],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
            text=True, encoding="utf-8", env=env,
        )
        self._q = queue.Queue()
        threading.Thread(target=self._pump, args=(self.proc, self._q), daemon=True).start()
        first = self._read()
        if first is TIMEOUT or not first.get("ok"):
            self.load_error = "加载超时" if first is TIMEOUT else first["error"]

    @staticmethod
    def _pump(proc, q):
        for line in proc.stdout:
            q.put(line)

    def _read(self):
        try:
            return json.loads(self._q.get(timeout=self.timeout))
        except queue.Empty:
            return TIMEOUT

    def call(self, args):
        """返回 ("ok", 结果) / ("error", 异常描述) / ("timeout", None)。"""
        if self.load_error:
            return "error", self.load_error
        self.proc.stdin.write(json.dumps(list(args)) + "\n")
        self.proc.stdin.flush()
        out = self._read()
        if out is TIMEOUT:
            self.close()
            self._start()
            return "timeout", None
        return ("ok", out["result"]) if out["ok"] else ("error", out["error"])

    def close(self):
        if self.proc and self.proc.poll() is None:
            self.proc.kill()
            self.proc.wait()
