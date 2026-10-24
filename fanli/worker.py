"""在独立子进程里运行学生代码：从 stdin 逐行读 JSON 参数，往 stdout 写 JSON 结果。"""
import importlib.util
import json
import sys


def main():
    path, func_name = sys.argv[1], sys.argv[2]
    spec = importlib.util.spec_from_file_location("student", path)
    mod = importlib.util.module_from_spec(spec)
    real_stdout = sys.stdout
    sys.stdout = sys.stderr  # 学生代码里的 print 不能污染通信通道
    try:
        spec.loader.exec_module(mod)
        fn = getattr(mod, func_name)
    except Exception as e:  # noqa: BLE001
        real_stdout.write(json.dumps({"ok": False, "error": f"加载失败 {type(e).__name__}: {e}"}) + "\n")
        real_stdout.flush()
        return
    real_stdout.write(json.dumps({"ok": True, "ready": True}) + "\n")
    real_stdout.flush()
    for line in sys.stdin:
        args = json.loads(line)
        try:
            result = fn(*args)
            out = {"ok": True, "result": json.loads(json.dumps(result, default=repr))}
        except Exception as e:  # noqa: BLE001
            out = {"ok": False, "error": f"{type(e).__name__}: {e}"}
        real_stdout.write(json.dumps(out, ensure_ascii=False) + "\n")
        real_stdout.flush()


if __name__ == "__main__":
    main()
