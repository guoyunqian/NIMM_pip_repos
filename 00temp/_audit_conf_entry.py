# -*- coding: utf-8 -*-
"""对照各子模块 resource/conf.ini 与入口 process / CLI 参数。"""
from __future__ import annotations

import ast
import configparser
import io
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SKIP = {"utils", "__pycache__"}


def parse_ini_keys(path: Path) -> dict[str, list[str]]:
    text = path.read_text(encoding="utf-8")
    lines = []
    for line in text.splitlines():
        s = line.strip()
        if not s or s.startswith("#") or s.startswith(";"):
            continue
        lines.append(line)
    body = "\n".join(lines)
    has_section = any(s.strip().startswith("[") and s.strip().endswith("]") for s in lines)
    parser = configparser.ConfigParser(interpolation=None)
    parser.optionxform = str
    if has_section:
        parser.read_file(io.StringIO(body))
    else:
        parser.read_file(io.StringIO("[__flat__]\n" + body))
    out: dict[str, list[str]] = {}
    for section in parser.sections():
        name = "" if section == "__flat__" else section
        out[name] = list(parser.options(section))
    return out


def _expr(node) -> str:
    if node is None:
        return ""
    if isinstance(node, ast.Constant):
        return repr(node.value)
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _expr(node.value) + "." + node.attr
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return "-" + _expr(node.operand)
    return type(node).__name__


def process_funcs(path: Path) -> list[tuple[str, list[tuple[str, str]]]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    found = []
    for node in tree.body:
        if not isinstance(node, ast.FunctionDef) or node.name != "process":
            continue
        args = []
        pos = node.args.args
        defaults = node.args.defaults
        pad = len(pos) - len(defaults)
        for i, arg in enumerate(pos):
            if arg.arg in ("self", "cls"):
                continue
            default = ""
            di = i - pad
            if di >= 0:
                default = _expr(defaults[di])
            args.append((arg.arg, default))
        kw = node.args.kwonlyargs
        kd = node.args.kw_defaults
        for arg, default_node in zip(kw, kd):
            default = _expr(default_node) if default_node is not None else ""
            args.append((arg.arg, default))
        found.append((str(path.relative_to(ROOT)), args))
    return found


def cli_dests(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    dests = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = ""
        if isinstance(func, ast.Attribute):
            name = func.attr
        elif isinstance(func, ast.Name):
            name = func.id
        if name != "add_argument":
            continue
        dest = None
        flags = []
        for kw in node.keywords:
            if kw.arg == "dest" and isinstance(kw.value, ast.Constant):
                dest = str(kw.value.value)
        for arg in node.args:
            if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and arg.value.startswith("--"):
                flags.append(arg.value)
        if dest is None and flags:
            dest = flags[0].lstrip("-").replace("-", "_")
        if dest and dest != "help":
            dests.append(dest)
    return dests


def overlay_keys(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    keys = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else "")
        if name not in ("overlay_none", "_nimm_overlay", "resolve_args", "resolve_process_args"):
            continue
        for arg in node.args:
            if isinstance(arg, ast.Dict):
                for key in arg.keys:
                    if isinstance(key, ast.Constant):
                        keys.append(str(key.value))
        for kw in node.keywords:
            if kw.arg and kw.arg not in ("config", "module", "anchor_file"):
                keys.append(kw.arg)
    return keys


def preset_keys(path: Path) -> list[str]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except SyntaxError:
        return []
    keys = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in ("PRESET", "FIELDS"):
                    keys.extend(_dict_keys(node.value))
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id in ("PRESET", "FIELDS"):
            if node.value is not None:
                keys.extend(_dict_keys(node.value))
    return keys


def _dict_keys(node, prefix=""):
    keys = []
    if isinstance(node, ast.Dict):
        for key, value in zip(node.keys, node.values):
            if isinstance(key, ast.Constant):
                name = str(key.value)
                full = f"{prefix}.{name}" if prefix else name
                if isinstance(value, ast.Dict):
                    keys.append(full)
                    keys.extend(_dict_keys(value, full))
                elif isinstance(value, (ast.Tuple, ast.List)):
                    keys.append(full)
                    for elt in value.elts:
                        if isinstance(elt, ast.Tuple) and elt.elts and isinstance(elt.elts[0], ast.Constant):
                            keys.append(f"{full}.{elt.elts[0].value}")
                else:
                    keys.append(full)
    return keys


def main():
    for pkg in sorted(p for p in ROOT.iterdir() if p.is_dir() and p.name not in SKIP):
        conf = pkg / "resource" / "conf.ini"
        if not conf.is_file():
            continue
        try:
            _audit_one(pkg, conf)
        except Exception as exc:
            print(f"\n===== {pkg.name} =====")
            print("  ERROR:", type(exc).__name__, exc)


def _audit_one(pkg: Path, conf: Path) -> None:
        sections = parse_ini_keys(conf)
        ini_keys = []
        for section, keys in sections.items():
            for key in keys:
                ini_keys.append(f"{section}.{key}" if section else key)
        bare = {key.split(".", 1)[-1] for key in ini_keys}

        procs = []
        overlays = []
        presets = []
        clis = []
        for py in pkg.rglob("*.py"):
            if any(part in {"__pycache__", "resource", "nbs", "test", "log"} for part in py.parts):
                continue
            if py.name.startswith("test"):
                continue
            procs.extend(process_funcs(py))
            overlays.extend(overlay_keys(py))
            if py.name == "util_env.py":
                presets.extend(preset_keys(py))
            if "cli" in py.parts and py.name != "__init__.py":
                dests = cli_dests(py)
                if dests:
                    clis.append((str(py.relative_to(pkg)), dests))

        proc_names = set()
        for _, args in procs:
            proc_names.update(name for name, _ in args)

        missing_proc = sorted(k for k in bare if k not in proc_names and k != "config")
        print(f"\n===== {pkg.name} =====")
        print("INI:", ", ".join(ini_keys))
        if procs:
            for loc, args in procs:
                shown = ", ".join(f"{n}={d}" if d else n for n, d in args)
                print(f"  process {loc}: {shown}")
        else:
            print("  process: NONE")
        if missing_proc:
            print("  MISSING IN process:", ", ".join(missing_proc))
        else:
            print("  MISSING IN process: (none)")
        if overlays:
            missing_overlay = sorted(k for k in bare if k not in set(overlays) and k not in proc_names)
            print("  overlay/resolve keys:", ", ".join(sorted(set(overlays))))
        if presets:
            print("  PRESET:", ", ".join(presets))
        if clis:
            for loc, dests in clis:
                miss = sorted(k for k in bare if k not in dests and k != "config")
                print(f"  cli {loc} missing ini keys: {', '.join(miss) if miss else '(none)'}")


if __name__ == "__main__":
    main()
