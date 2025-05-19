import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import os
import time
import subprocess
import requests
from pynput import keyboard
from selenium import webdriver
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from datetime import datetime
import base64
import re

# 默认热键设置
hotkey = keyboard.Key.f8
save_dir = os.path.join(os.getcwd(), "temu_downloads")
url_file = "last_url.txt"

# 热键监听线程控制
driver = None
listener = None

def save_last_url(url):
    with open(url_file, 'w', encoding='utf-8') as f:
        f.write(url)

def load_last_url():
    if os.path.exists(url_file):
        with open(url_file, 'r', encoding='utf-8') as f:
            return f.read().strip()
    return None

def open_browser():
    global driver
    options = uc.ChromeOptions()
    driver = uc.Chrome(options=options)

    last_url = load_last_url()
    if last_url:
        resume = messagebox.askyesno("继续上次页面", "检测到上次采集页面，是否打开以继续采集？")
        if resume:
            driver.get(last_url)
            return

    driver.get("https://www.temu.com")
    messagebox.showinfo("提示", "请登录 TEMU 并手动打开店铺页面")

def on_press(key):
    global hotkey
    if key == hotkey:
        scrape_selected_windows()

def clean_filename(name):
    name = re.sub(r'[\\/:*?"<>|]', '', name)
    return name.strip()[:100]

def open_folder(path):
    try:
        if os.name == 'nt':
            os.startfile(path)
        elif os.uname().sysname == 'Darwin':
            subprocess.run(['open', path])
        else:
            subprocess.run(['xdg-open', path])
    except Exception as e:
        messagebox.showerror("错误", f"无法打开文件夹：{str(e)}")

def scrape_products_for_handle(handle):
    global driver, save_dir
    try:
        driver.switch_to.window(handle)
        current_url = driver.current_url
        save_last_url(current_url)

        folder_time = datetime.now().strftime('%Y%m%d_%H%M%S')
        folder = os.path.join(save_dir, folder_time)
        os.makedirs(folder, exist_ok=True)

        items = driver.find_elements(By.CSS_SELECTOR, '[data-tooltip^="goodsImage-"]')
        count = 0

        for item in items:
            try:
                title = item.get_attribute("data-tooltip-title") or "item"
                img = item.find_element(By.CSS_SELECTOR, 'img')
                img_url = img.get_attribute("src")

                if img_url:
                    response = requests.get(img_url, timeout=10)
                    response.raise_for_status()

                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S_%f')
                    filename = f"{clean_filename(title)}_{timestamp}.jpg"
                    with open(os.path.join(folder, filename), "wb") as f:
                        f.write(response.content)
                    count += 1
            except Exception:
                continue

        messagebox.showinfo("采集完成", f"[{driver.title}] 采集完成，共保存 {count} 项于：\n{folder}")
        open_folder(folder)

    except Exception as e:
        messagebox.showerror("错误", f"采集时出错：{str(e)}")

def get_all_windows():
    handles = driver.window_handles
    options = []
    for i, handle in enumerate(handles):
        driver.switch_to.window(handle)
        title = driver.title or f"窗口 {i + 1}"
        options.append((i, handle, title))
    return options

def choose_windows():
    all_windows = get_all_windows()
    if not all_windows:
        messagebox.showwarning("无窗口", "未检测到任何打开的店铺窗口。")
        return []

    choices = "\n".join([f"{i+1}: {title}" for i, _, title in all_windows])
    input_str = simpledialog.askstring("选择窗口", f"输入要采集的窗口编号（多个请用英文逗号分隔）：\n{choices}")
    if not input_str:
        return []

    try:
        indices = [int(i.strip()) - 1 for i in input_str.split(",")]
        return [all_windows[i][1] for i in indices if 0 <= i < len(all_windows)]
    except Exception:
        messagebox.showerror("输入错误", "请输入有效的窗口编号")
        return []

def scrape_selected_windows():
    selected_handles = choose_windows()
    if not selected_handles:
        return

    messagebox.showinfo("开始采集", f"即将开始采集 {len(selected_handles)} 个窗口…")

    for handle in selected_handles:
        scrape_products_for_handle(handle)

    messagebox.showinfo("全部完成", f"所有窗口采集完成，共处理 {len(selected_handles)} 个窗口。")

def change_hotkey():
    def on_new_key(key):
        global hotkey, listener
        hotkey = key
        messagebox.showinfo("热键设置", f"新的热键设置为：{key}")
        listener.stop()

    messagebox.showinfo("设置热键", "请按下新的热键")
    listener = keyboard.Listener(on_press=on_new_key)
    listener.start()

def change_save_path():
    global save_dir
    path = filedialog.askdirectory()
    if path:
        save_dir = path

def open_save_location():
    global save_dir
    if os.path.exists(save_dir):
        open_folder(save_dir)
    else:
        messagebox.showwarning("未找到目录", "保存路径不存在，请先采集或设置保存路径。")

def run_gui():
    global listener

    window = tk.Tk()
    window.title("TEMU 商品采集器")
    window.geometry("300x300")

    tk.Button(window, text="打开 TEMU 网页", command=lambda: threading.Thread(target=open_browser).start()).pack(pady=10)
    tk.Button(window, text="开始采集（多窗口选择）", command=scrape_selected_windows).pack(pady=10)
    tk.Button(window, text="更改热键", command=change_hotkey).pack(pady=10)
    tk.Button(window, text="更改图片保存路径", command=change_save_path).pack(pady=10)
    tk.Button(window, text="打开保存位置", command=open_save_location).pack(pady=10)

    listener = keyboard.Listener(on_press=on_press)
    listener.start()

    window.mainloop()

if __name__ == "__main__":
    run_gui()
