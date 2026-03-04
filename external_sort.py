import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import struct
import os
import math
import time
import tempfile
import threading
import random



FLOAT_SIZE = 8  
CHUNK_SIZE = 4  


def read_floats(path):
    with open(path, "rb") as f:
        data = f.read()
    n = len(data) // FLOAT_SIZE
    return list(struct.unpack(f"{n}d", data[:n * FLOAT_SIZE]))


def write_floats(path, values):
    with open(path, "wb") as f:
        f.write(struct.pack(f"{len(values)}d", *values))


def read_one(f):
    b = f.read(FLOAT_SIZE)
    if not b or len(b) < FLOAT_SIZE:
        return None
    return struct.unpack("d", b)[0]


def write_one(f, v):
    f.write(struct.pack("d", v))


def external_sort(src_path, dst_path, chunk_size, log_cb=None, progress_cb=None):
    values = read_floats(src_path)
    total = len(values)
    if total == 0:
        write_floats(dst_path, [])
        return []


    tmp_dir = tempfile.mkdtemp()
    run_paths = []
    steps = []  

    for i in range(0, total, chunk_size):
        chunk = sorted(values[i: i + chunk_size])
        run_path = os.path.join(tmp_dir, f"run_{len(run_paths)}.bin")
        write_floats(run_path, chunk)
        run_paths.append(run_path)

        step = {
            "phase": "split",
            "run_index": len(run_paths) - 1,
            "chunk_raw": values[i: i + chunk_size],
            "chunk_sorted": chunk,
            "all_values": values[:],
        }
        steps.append(step)

        if log_cb:
            log_cb(f"[Bước 1] Run #{len(run_paths) - 1}: {[f'{v:.2f}' for v in values[i:i+chunk_size]]} → {[f'{v:.2f}' for v in chunk]}")
        if progress_cb:
            progress_cb((i + chunk_size) / total * 50)
        time.sleep(0.05)

    
    if log_cb:
        log_cb(f"\n[Bước 2] Merge {len(run_paths)} run(s) → file kết quả")

    files = [open(p, "rb") for p in run_paths]
    heap = []  
    for idx, f in enumerate(files):
        v = read_one(f)
        if v is not None:
            heap.append((v, idx))
    heap.sort()

    result = []
    with open(dst_path, "wb") as out:
        done = 0
        while heap:
            val, fi = heap.pop(0)
            write_one(out, val)
            result.append(val)
            done += 1

            nxt = read_one(files[fi])
            if nxt is not None:
                inserted = False
                for k in range(len(heap)):
                    if heap[k][0] >= nxt:
                        heap.insert(k, (nxt, fi))
                        inserted = True
                        break
                if not inserted:
                    heap.append((nxt, fi))

            if progress_cb:
                progress_cb(50 + done / total * 50)
            time.sleep(0.02)

    for f in files:
        f.close()
    for p in run_paths:
        os.remove(p)
    os.rmdir(tmp_dir)

    if log_cb:
        log_cb(f"\n✅ Xong! {total} phần tử đã được sắp xếp tăng dần.")

    return result, steps


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Minh Họa Sắp Xếp Ngoại — External Sort")
        self.geometry("1000x720")
        self.configure(bg="#0f1117")
        self.resizable(True, True)

        self.src_path = tk.StringVar()
        self.dst_path = tk.StringVar()
        self.chunk_var = tk.IntVar(value=4)
        self.status_var = tk.StringVar(value="Sẵn sàng")

        self._build_ui()

    def _build_ui(self):
        # ── Header ──
        hdr = tk.Frame(self, bg="#1a1d2e", pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="🗂  SẮP XẾP NGOẠI", font=("Courier New", 20, "bold"),
                 bg="#1a1d2e", fg="#00e5ff").pack()
        tk.Label(hdr, text="External Sort · Số thực 8-byte · Binary File",
                 font=("Courier New", 10), bg="#1a1d2e", fg="#5c6bc0").pack()

        # ── Controls ──
        ctrl = tk.Frame(self, bg="#0f1117", pady=8, padx=16)
        ctrl.pack(fill="x")

        # Row 1: file nguồn
        r1 = tk.Frame(ctrl, bg="#0f1117")
        r1.pack(fill="x", pady=3)
        tk.Label(r1, text="File nguồn:", width=12, anchor="w",
                 bg="#0f1117", fg="#90caf9", font=("Courier New", 10)).pack(side="left")
        tk.Entry(r1, textvariable=self.src_path, width=52,
                 bg="#1a1d2e", fg="#e0e0e0", insertbackground="white",
                 font=("Courier New", 10), relief="flat").pack(side="left", padx=4)
        self._btn(r1, "Chọn…", self._pick_src).pack(side="left", padx=2)
        self._btn(r1, "Tạo mẫu", self._gen_sample).pack(side="left", padx=2)

        # Row 2: file đích
        r2 = tk.Frame(ctrl, bg="#0f1117")
        r2.pack(fill="x", pady=3)
        tk.Label(r2, text="File đích:", width=12, anchor="w",
                 bg="#0f1117", fg="#90caf9", font=("Courier New", 10)).pack(side="left")
        tk.Entry(r2, textvariable=self.dst_path, width=52,
                 bg="#1a1d2e", fg="#e0e0e0", insertbackground="white",
                 font=("Courier New", 10), relief="flat").pack(side="left", padx=4)
        self._btn(r2, "Chọn…", self._pick_dst).pack(side="left", padx=2)

        # Row 3: chunk + run
        r3 = tk.Frame(ctrl, bg="#0f1117")
        r3.pack(fill="x", pady=3)
        tk.Label(r3, text="Chunk size:", width=12, anchor="w",
                 bg="#0f1117", fg="#90caf9", font=("Courier New", 10)).pack(side="left")
        tk.Spinbox(r3, from_=2, to=20, textvariable=self.chunk_var, width=5,
                   bg="#1a1d2e", fg="#e0e0e0", buttonbackground="#1a1d2e",
                   font=("Courier New", 10), relief="flat").pack(side="left", padx=4)
        tk.Label(r3, text="phần tử/run",
                 bg="#0f1117", fg="#546e7a", font=("Courier New", 9)).pack(side="left")

        self._btn(r3, "▶  BẮT ĐẦU SẮP XẾP", self._run, accent=True).pack(side="right", padx=4)

        # ── Progress ──
        pg_frame = tk.Frame(self, bg="#0f1117", padx=16)
        pg_frame.pack(fill="x")
        self.progress = ttk.Progressbar(pg_frame, length=960, mode="determinate")
        self.progress.pack(fill="x", pady=4)
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TProgressbar", troughcolor="#1a1d2e",
                        background="#00e5ff", thickness=8)

        # ── Main area: canvas + log ──
        main = tk.Frame(self, bg="#0f1117")
        main.pack(fill="both", expand=True, padx=16, pady=6)

        # Canvas minh họa
        left = tk.Frame(main, bg="#0f1117")
        left.pack(side="left", fill="both", expand=True)
        tk.Label(left, text="Minh họa trực quan", bg="#0f1117", fg="#546e7a",
                 font=("Courier New", 9)).pack(anchor="w")
        self.canvas = tk.Canvas(left, bg="#12151f", highlightthickness=0)
        self.canvas.pack(fill="both", expand=True)

        # Log
        right = tk.Frame(main, bg="#0f1117", width=300)
        right.pack(side="right", fill="y", padx=(8, 0))
        right.pack_propagate(False)
        tk.Label(right, text="Nhật ký", bg="#0f1117", fg="#546e7a",
                 font=("Courier New", 9)).pack(anchor="w")
        self.log_txt = tk.Text(right, bg="#12151f", fg="#a5d6a7",
                               font=("Courier New", 9), relief="flat",
                               state="disabled", wrap="word")
        sb = tk.Scrollbar(right, command=self.log_txt.yview, bg="#1a1d2e")
        sb.pack(side="right", fill="y")
        self.log_txt.config(yscrollcommand=sb.set)
        self.log_txt.pack(fill="both", expand=True)

        # ── Status bar ──
        tk.Label(self, textvariable=self.status_var, bg="#1a1d2e", fg="#546e7a",
                 font=("Courier New", 9), anchor="w", padx=8).pack(fill="x", side="bottom")

    def _btn(self, parent, text, cmd, accent=False):
        bg = "#00e5ff" if accent else "#1e2235"
        fg = "#0f1117" if accent else "#90caf9"
        return tk.Button(parent, text=text, command=cmd,
                         bg=bg, fg=fg, activebackground="#00b8d4",
                         font=("Courier New", 9, "bold" if accent else "normal"),
                         relief="flat", cursor="hand2", padx=8, pady=4)

    # ── Select file ──────────────────────────────────────────────────────────
    def _pick_src(self):
        p = filedialog.askopenfilename(filetypes=[("Binary", "*.bin"), ("All", "*.*")])
        if p:
            self.src_path.set(p)
            if not self.dst_path.get():
                base, _ = os.path.splitext(p)
                self.dst_path.set(base + "_sorted.bin")

    def _pick_dst(self):
        p = filedialog.asksaveasfilename(defaultextension=".bin",
                                          filetypes=[("Binary", "*.bin")])
        if p:
            self.dst_path.set(p)

    def _gen_sample(self):
        p = filedialog.asksaveasfilename(title="Lưu file mẫu",
                                          defaultextension=".bin",
                                          filetypes=[("Binary", "*.bin")])
        if not p:
            return
        n = 16  # 16 số — đủ nhỏ để minh họa
        vals = [round(random.uniform(-99, 99), 2) for _ in range(n)]
        write_floats(p, vals)
        self.src_path.set(p)
        base, _ = os.path.splitext(p)
        self.dst_path.set(base + "_sorted.bin")
        self._log(f"✨ Đã tạo file mẫu {n} số: {[f'{v:.2f}' for v in vals]}\n")
        self.status_var.set(f"Đã tạo file mẫu: {os.path.basename(p)}")

    # ── Log ────────────────────────────────────────────────────────────────
    def _log(self, msg):
        self.log_txt.config(state="normal")
        self.log_txt.insert("end", msg + "\n")
        self.log_txt.see("end")
        self.log_txt.config(state="disabled")

    def _clear_log(self):
        self.log_txt.config(state="normal")
        self.log_txt.delete("1.0", "end")
        self.log_txt.config(state="disabled")

    # ── Canvas drawing ──────────────────────────────────────────────────────────
    def _draw_values(self, values, title, y_off, highlight=None, color="#00e5ff"):
        W = self.canvas.winfo_width() or 650
        n = len(values)
        if n == 0:
            return
        cell_w = min(60, (W - 20) // n)
        x0 = 10
        self.canvas.create_text(x0, y_off - 14, text=title, anchor="w",
                                 fill="#546e7a", font=("Courier New", 8))
        for i, v in enumerate(values):
            x = x0 + i * cell_w
            is_hi = highlight is not None and i in highlight
            fill = "#1e3a5f" if not is_hi else "#004d66"
            border = "#00e5ff" if is_hi else "#263238"
            self.canvas.create_rectangle(x, y_off, x + cell_w - 2, y_off + 28,
                                          fill=fill, outline=border)
            self.canvas.create_text(x + cell_w // 2, y_off + 14,
                                     text=f"{v:.1f}", fill=color,
                                     font=("Courier New", 8, "bold"))

    def _animate_step(self, values, runs_so_far, current_chunk_idx, chunk_size):
        self.canvas.delete("all")
        W = self.canvas.winfo_width() or 650
        y = 30

        
        self._draw_values(values, "▸ Dữ liệu gốc", y,
                           highlight=set(range(current_chunk_idx * chunk_size,
                                               min((current_chunk_idx + 1) * chunk_size, len(values)))),
                           color="#ffcc80")
        y += 55

        
        for ri, run in enumerate(runs_so_far):
            self._draw_values(run, f"  Run #{ri}", y, color="#80cbc4")
            y += 50
            if y > self.canvas.winfo_height() - 30:
                break

    def _animate_result(self, values, result):
        self.canvas.delete("all")
        y = 30
        self._draw_values(values, "▸ Trước khi sắp xếp", y, color="#ef9a9a")
        y += 60
        self._draw_values(result, "▸ Sau khi sắp xếp (tăng dần)", y, color="#a5d6a7")

    
    def _run(self):
        src = self.src_path.get().strip()
        dst = self.dst_path.get().strip()
        if not src or not os.path.exists(src):
            messagebox.showerror("Lỗi", "File nguồn không tồn tại!")
            return
        if not dst:
            messagebox.showerror("Lỗi", "Chưa chọn file đích!")
            return

        self._clear_log()
        self.progress["value"] = 0
        self.status_var.set("Đang sắp xếp…")

        chunk = self.chunk_var.get()
        values_orig = read_floats(src)

        def worker():
            runs_so_far = []
            chunk_idx = [0]

            def log_cb(msg):
                self.after(0, self._log, msg)

            def progress_cb(pct):
                self.after(0, lambda: self.progress.__setitem__("value", pct))

            
            total = len(values_orig)
            tmp_dir = tempfile.mkdtemp()
            run_paths = []

            for i in range(0, total, chunk):
                chunk_raw = values_orig[i: i + chunk]
                chunk_sorted = sorted(chunk_raw)
                run_path = os.path.join(tmp_dir, f"run_{len(run_paths)}.bin")
                write_floats(run_path, chunk_sorted)
                run_paths.append(run_path)
                runs_so_far.append(chunk_sorted)
                ci = len(runs_so_far) - 1

                self.after(0, self._animate_step,
                           values_orig, list(runs_so_far), ci, chunk)
                self.after(0, log_cb,
                           f"[Split] Run #{ci}: {[f'{v:.2f}' for v in chunk_raw]} → {[f'{v:.2f}' for v in chunk_sorted]}")
                self.after(0, progress_cb, (i + chunk) / total * 50)
                time.sleep(0.3)

            
            self.after(0, log_cb, f"\n[Merge] Trộn {len(run_paths)} run(s)…")
            files = [open(p, "rb") for p in run_paths]
            heap = []
            for idx, f in enumerate(files):
                v = read_one(f)
                if v is not None:
                    heap.append((v, idx))
            heap.sort()

            result = []
            with open(dst, "wb") as out:
                done = 0
                while heap:
                    val, fi = heap.pop(0)
                    write_one(out, val)
                    result.append(val)
                    done += 1
                    nxt = read_one(files[fi])
                    if nxt is not None:
                        ins = False
                        for k in range(len(heap)):
                            if heap[k][0] >= nxt:
                                heap.insert(k, (nxt, fi))
                                ins = True
                                break
                        if not ins:
                            heap.append((nxt, fi))
                    self.after(0, progress_cb, 50 + done / total * 50)
                    time.sleep(0.02)

            for f in files:
                f.close()
            for p in run_paths:
                os.remove(p)
            os.rmdir(tmp_dir)

            self.after(0, log_cb,
                       f"\n✅ Hoàn tất! Kết quả: {[f'{v:.2f}' for v in result]}")
            self.after(0, self._animate_result, values_orig, result)
            self.after(0, self.status_var.set,
                       f"Đã sắp xếp {total} phần tử → {os.path.basename(dst)}")
            self.after(0, self.progress.__setitem__, "value", 100)

        threading.Thread(target=worker, daemon=True).start()


# ─── Main ──────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()
